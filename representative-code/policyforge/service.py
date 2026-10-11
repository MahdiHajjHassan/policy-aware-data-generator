"""Persistent product actions shared by the independent API and CLI."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import zipfile

from domain import CATEGORIES, GENERATORS, GENERATOR_VERSION, POLICY, SUBJECTS, compile_policy, csv_content, digest, generate_package, initial_config, validate_contract, validate_package, validate_schema


class Product:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "policyforge.json"
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if self.data.get("recipient_id") not in SUBJECTS:
                raise ValueError("Stored recipient is unknown; use a fresh data directory.")
            self._check_config(self.data["config"])
        else:
            self.data = {"recipient_id": "finance-demo", "config": initial_config(), "packages": {}, "decisions": {}, "audit": []}
            self._generate({})

    @property
    def recipient(self):
        return SUBJECTS[self.data["recipient_id"]]

    def _save(self):
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)

    @staticmethod
    def _check_config(config):
        if not isinstance(config, dict) or set(config) != {"schema", "contract"}:
            raise ValueError("Configuration must contain schema and contract only.")
        validate_schema(config["schema"])
        validate_contract(config["contract"])

    def _audit(self, action, status, detail, package_id=None):
        self.data["audit"].append({"id": max((event["id"] for event in self.data["audit"]), default=0) + 1, "time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "recipient_id": self.recipient["id"], "action": action, "status": status, "detail": detail, "package_id": package_id, "policy_version": POLICY["version"]})
        self.data["audit"] = self.data["audit"][-150:]

    def _denied(self, action, error):
        self.data["decisions"][self.recipient["id"]] = {"status": "denied", "message": str(error), "trace": [{"stage": "Release stopped", "status": "denied", "detail": str(error)}]}
        self._audit(action, "denied", str(error))
        self._save()

    def state(self):
        config = self.data["config"]
        try:
            compilation = compile_policy(config["schema"], config["contract"], self.recipient)
        except (ValueError, PermissionError) as error:
            compilation = {"status": "denied", "error": str(error), "partitions": {}, "field_matrix": [], "trace": []}
        package = self.data["packages"].get(self.recipient["id"])
        return deepcopy({"product": "PolicyForge", "recipient": self.recipient, "recipients": list(SUBJECTS.values()), "countries": list(POLICY["countries"]), "country_scope": POLICY["teams"][self.recipient["team"]]["countries"], "categories": CATEGORIES, "generators": sorted(GENERATORS), "policy_version": POLICY["version"], "policy": POLICY,
                         "config": config, "config_hash": digest(config), "compilation": compilation, "package": package, "package_stale": bool(package and (package["config_hash"] != digest(config) or package["policy_hash"] != digest(POLICY) or package.get("generator_version") != GENERATOR_VERSION)),
                         "last_decision": self.data["decisions"].get(self.recipient["id"]), "audit": [a for a in self.data["audit"] if a["recipient_id"] == self.recipient["id"]][-30:]})

    def _generate(self, payload):
        if any(k in payload for k in ("recipient_id", "subject_id", "team", "role", "policy")):
            raise PermissionError("Generation inputs cannot override recipient, team, role or policy. Select a trusted recipient profile first.")
        if set(payload) - {"rows", "seed", "countries"}:
            raise ValueError("Generation accepts rows, seed and countries only; save metadata through save_config.")
        config = deepcopy(self.data["config"])
        config["contract"].update(payload)
        self._check_config(config)
        package, compiled = generate_package(config["schema"], config["contract"], self.recipient)
        self.data["config"] = config
        self.data["packages"][self.recipient["id"]] = package
        delivered = sum(len(rows) for p in package["partitions"].values() for rows in p["tables"].values())
        trace = compiled["trace"] + [{"stage": "Generation", "status": "passed", "detail": f"{delivered} deterministic relational records generated."}, {"stage": "Release validation", "status": "passed", "detail": "Types, enums, field sets, primary keys, foreign keys, dates and checksums passed."}]
        self.data["decisions"][self.recipient["id"]] = {"status": "allowed", "message": "Package generated and validated.", "trace": trace}
        self._audit("generate", "allowed", f"{delivered} records / seed {config['contract']['seed']}", package["package_id"])
        self._save()
        return {"package": deepcopy(package), "message": "Package generated and validated."}

    def _release(self, payload):
        package = self.data["packages"].get(self.recipient["id"])
        if not package or payload.get("package_id") != package["package_id"]:
            raise PermissionError("This package is unavailable to the selected recipient. Generate a package for this profile.")
        if package["config_hash"] != digest(self.data["config"]) or package.get("generator_version") != GENERATOR_VERSION:
            raise RuntimeError("The contract, schema or generator changed after generation. Generate again before validating or downloading.")
        validation = validate_package(package, self.data["config"]["schema"], self.recipient)
        return package, validation

    def _export(self, payload):
        if set(payload) - {"package_id", "format", "country", "table"}:
            raise ValueError("Export accepts package_id, format, country and table only.")
        package, _ = self._release(payload)
        fmt = payload.get("format", "zip")
        stem = package["package_id"]
        if fmt == "json":
            result = {"content": json.dumps(package, indent=2, ensure_ascii=False), "mime": "application/json", "filename": stem + ".json"}
        elif fmt == "csv":
            country, table = payload.get("country"), payload.get("table", "employees")
            result = {"content": csv_content(package, country, table), "mime": "text/csv", "filename": f"{stem}-{country}-{table}.csv"}
        elif fmt == "zip":
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for name, value in {"dataset.json": package, "manifest.json": package["manifest"], "schema.json": self.data["config"]["schema"], "contract.json": package["contract"], "policy.json": POLICY, "audit.json": [a for a in self.data["audit"] if a["recipient_id"] == self.recipient["id"]]}.items():
                    bundle.writestr(name, json.dumps(value, indent=2, ensure_ascii=False))
                for country, part in package["partitions"].items():
                    for table in part["tables"]:
                        bundle.writestr(f"{country}/{table}.csv", csv_content(package, country, table))
            result = {"content_base64": base64.b64encode(archive.getvalue()).decode(), "mime": "application/zip", "filename": stem + ".zip"}
        else:
            raise ValueError("Choose CSV, JSON or ZIP.")
        self._audit("export", "allowed", f"Validated {fmt.upper()} download", stem)
        self._save()
        return result

    def action(self, name, payload):
        if not isinstance(payload, dict):
            raise ValueError("Action payload must be a JSON object.")
        try:
            if name == "generate":
                return self._generate(payload)
            if name == "export":
                return self._export(payload)
            if name == "save_config":
                self._check_config(payload)
                self.data["config"] = deepcopy(payload)
                self._audit("save_config", "allowed", "Contract and typed schema saved")
                self._save()
                return {"message": "Contract and schema saved. Generate again to apply the changes."}
            if name == "select_recipient":
                if set(payload) != {"recipient_id"} or payload["recipient_id"] not in SUBJECTS:
                    raise PermissionError("Select a declared trusted recipient profile.")
                self.data["recipient_id"] = payload["recipient_id"]
                self._audit("select_recipient", "allowed", "Trusted local recipient selected")
                self._save()
                return {"message": "Recipient selected. Its role and team come from the trusted local definition."}
            if name == "compile":
                if payload:
                    raise ValueError("Compile uses the saved contract; no policy overrides are accepted.")
                result = compile_policy(self.data["config"]["schema"], self.data["config"]["contract"], self.recipient)
                self.data["decisions"][self.recipient["id"]] = {"status": "allowed", "message": "Field policy compiled.", "trace": result["trace"]}
                self._audit("compile", "allowed", "Dataset, team, role and country policies intersected")
                self._save()
                return result
            if name == "validate":
                package, validation = self._release(payload)
                self._audit("validate", "allowed", "All release checks passed", package["package_id"])
                self._save()
                return {"message": "All release checks passed.", "validation": validation}
            if name == "reset_config":
                if payload:
                    raise ValueError("Reset config takes no overrides.")
                self.data["config"] = initial_config()
                self._audit("reset_config", "allowed", "Restored bundled schema and contract")
                self._save()
                return {"message": "Default schema and contract restored."}
            raise ValueError("Unknown PolicyForge action.")
        except (ValueError, PermissionError, RuntimeError, TypeError, KeyError) as error:
            self._denied(name, error)
            raise
