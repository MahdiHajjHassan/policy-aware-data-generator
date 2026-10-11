"""Typed metadata compiler, deterministic relational generator and release validator.

Only declared generators execute. Metadata is data; no expression is evaluated.
Trusted recipient definitions come from local source, never request attributes.
"""
from copy import deepcopy
import csv
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import io
import json
import math
from pathlib import Path
import random
import re

FIXTURES = Path(__file__).resolve().parent / "fixtures"
POLICY = json.loads((FIXTURES / "policies.json").read_text(encoding="utf-8"))
BASE_SCHEMA = json.loads((FIXTURES / "schema.json").read_text(encoding="utf-8"))
DEFAULT_CONTRACT = json.loads((FIXTURES / "contract.json").read_text(encoding="utf-8"))
SUBJECTS = POLICY["subjects"]
CATEGORIES = POLICY["categories"]
TABLES = ["employees", "assignments"]
GENERATORS = {"employee_id", "assignment_id", "country", "name", "choice", "number", "boolean", "start_date", "end_date"}
CORE = {"employees": ["employee_id", "country"], "assignments": ["assignment_id", "employee_id", "country", "start_date", "end_date"]}
CHECKS = ["Exact policy field sets", "Declared types and required values", "Enum and range constraints", "Unique primary identifiers", "Country-local foreign keys", "Assignment date order", "Table content checksums"]
GENERATOR_VERSION = "typed-relational-1.0"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def initial_config():
    return {"schema": deepcopy(BASE_SCHEMA), "contract": deepcopy(DEFAULT_CONTRACT)}


def valid_type(value, kind):
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_schema(schema):
    if not isinstance(schema, dict) or set(schema) != set(TABLES):
        raise ValueError("Schema must declare employees and assignments; unknown tables are outside the trusted dataset policy.")
    metadata_keys = {"type", "category", "required", "generator", "choices", "minimum", "maximum", "step", "description"}
    for table, fields in schema.items():
        if not isinstance(fields, dict) or not 1 <= len(fields) <= 80:
            raise ValueError(f"{table}: declare between 1 and 80 fields.")
        for name, meta in fields.items():
            if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", name):
                raise ValueError("Field names must use lowercase letters, digits and underscores, up to 48 characters.")
            if not isinstance(meta, dict) or set(meta) - metadata_keys:
                raise ValueError(f"{table}.{name}: metadata contains an unknown property.")
            if meta.get("category") not in CATEGORIES:
                raise ValueError(f"{table}.{name}: missing or unknown classification. Declare structural, identity, work or financial.")
            baseline = BASE_SCHEMA[table].get(name)
            if baseline and meta["category"] != baseline["category"]:
                raise ValueError(f"{table}.{name}: its trusted {baseline['category']} classification cannot be changed.")
            if meta.get("type") not in {"string", "number", "boolean"} or not isinstance(meta.get("required"), bool):
                raise ValueError(f"{table}.{name}: declare a valid type and a boolean required flag.")
            rule = meta.get("generator")
            if rule not in GENERATORS:
                raise ValueError(f"{table}.{name}: unsupported generator. Metadata cannot execute expressions.")
            if rule in {"employee_id", "assignment_id", "country", "name", "start_date", "end_date"} and meta["type"] != "string":
                raise ValueError(f"{table}.{name}: {rule} requires type string.")
            if rule == "boolean" and meta["type"] != "boolean":
                raise ValueError(f"{table}.{name}: boolean generation requires type boolean.")
            if rule == "choice":
                choices = meta.get("choices")
                if not isinstance(choices, list) or not 1 <= len(choices) <= 100 or any(not valid_type(v, meta["type"]) or (isinstance(v, str) and len(v) > 160) for v in choices):
                    raise ValueError(f"{table}.{name}: choices must contain 1 to 100 values of its declared type.")
            if rule == "number":
                lo, hi, step = meta.get("minimum"), meta.get("maximum"), meta.get("step")
                if meta["type"] != "number" or any(not valid_type(v, "number") for v in (lo, hi, step)) or not -1e9 <= lo <= hi <= 1e9 or step <= 0:
                    raise ValueError(f"{table}.{name}: declare a finite numeric range and a positive step.")
                if any(Decimal(str(v)).normalize().as_tuple().exponent < -6 for v in (lo, hi, step)):
                    raise ValueError(f"{table}.{name}: minimum, maximum and step support at most 6 decimal places. Use coarser numeric metadata before saving.")
                if not math.isfinite((hi - lo) / step) or (hi - lo) / step > 1e9:
                    raise ValueError(f"{table}.{name}: increase the step or narrow the range; at most one billion numeric steps are supported.")
            if "description" in meta and (not isinstance(meta["description"], str) or len(meta["description"]) > 300):
                raise ValueError(f"{table}.{name}: description must be text of at most 300 characters.")
        for name in CORE[table]:
            if name not in fields or any(fields[name].get(k) != BASE_SCHEMA[table][name][k] for k in ("type", "category", "required", "generator")):
                raise ValueError(f"{table}.{name}: this required relational field must retain its declared type, classification and generator.")
    return schema


def validate_contract(contract):
    keys = {"name", "description", "version", "dataset", "tables", "countries", "rows", "seed"}
    if not isinstance(contract, dict) or set(contract) != keys:
        raise ValueError("Contract must declare name, description, version, dataset, tables, countries, rows and seed only.")
    for key, limit in (("name", 100), ("description", 500), ("version", 40), ("seed", 80)):
        if not isinstance(contract[key], str) or not contract[key].strip() or len(contract[key]) > limit:
            raise ValueError(f"Contract {key} must be nonempty text of at most {limit} characters.")
    if contract["dataset"] != POLICY["dataset"]["id"]:
        raise PermissionError("Unknown dataset. Its table and field policies cannot be established.")
    tables = contract["tables"]
    if not isinstance(tables, list) or not tables or any(t not in TABLES for t in tables) or len(set(tables)) != len(tables):
        raise ValueError("Choose employees, or employees and assignments, without duplicates.")
    if "assignments" in tables and "employees" not in tables:
        raise ValueError("Assignments require the employees parent table for foreign-key integrity.")
    countries = contract["countries"]
    if not isinstance(countries, list) or not countries or any(not isinstance(c, str) for c in countries) or len(set(countries)) != len(countries):
        raise ValueError("Choose one or two distinct countries.")
    if any(c not in POLICY["countries"] for c in countries):
        raise PermissionError("Unknown country. The entire release is blocked.")
    rows = contract["rows"]
    if isinstance(rows, bool) or not isinstance(rows, int) or not 1 <= rows <= 500:
        raise ValueError("Rows per country must be an integer from 1 to 500.")
    return contract


def compile_policy(schema, contract, subject):
    validate_schema(schema)
    validate_contract(contract)
    if subject.get("id") not in SUBJECTS or subject != SUBJECTS[subject["id"]]:
        raise PermissionError("Recipient attributes differ from the trusted local definition.")
    team = POLICY["teams"][subject["team"]]
    role_name = subject["roles"][0]
    if role_name not in team["roles"]:
        raise PermissionError("The role is not assigned to this recipient team.")
    role = POLICY["roles"][role_name]
    if any(c not in team["countries"] or c not in role["countries"] for c in contract["countries"]):
        raise PermissionError("A requested country is outside this recipient's scope. Choose an allowed country; no partial package is delivered.")
    trace = [{"stage": "Recipient", "detail": f"{subject['label']} / {subject['team']} / {role_name}", "status": "passed"},
             {"stage": "Country scope", "detail": ", ".join(contract["countries"]), "status": "passed"}]
    result = {"status": "allowed", "recipient_id": subject["id"], "role": role_name, "partitions": {}, "trace": trace, "field_matrix": []}
    for country in contract["countries"]:
        named_layers = [("Dataset", POLICY["dataset"]), ("Team", team), ("Role", role), (country, POLICY["countries"][country])]
        categories = set(CATEGORIES)
        allowed_tables = set(TABLES)
        denied_fields = set()
        for _, layer in named_layers:
            categories.intersection_update(layer["categories"])
            allowed_tables.intersection_update(layer["tables"])
            denied_fields.update(layer["deny"])
        if any(t not in allowed_tables for t in contract["tables"]):
            raise PermissionError(f"{country}: a required table is denied by the current policy.")
        part = {"fields": {}, "omitted_fields": {}, "categories": [c for c in CATEGORIES if c in categories]}
        for table in TABLES:
            if table not in contract["tables"]:
                continue
            part["fields"][table], part["omitted_fields"][table] = [], []
            for name, meta in schema[table].items():
                reasons = [label for label, layer in named_layers if meta["category"] not in layer["categories"] or name in layer["deny"]]
                allowed = not reasons
                result["field_matrix"].append({"country": country, "table": table, "field": name, "category": meta["category"], "required": meta["required"], "allowed": allowed, "reason": "Permitted by all four layers" if allowed else "Excluded by " + ", ".join(reasons)})
                if not allowed and meta["required"]:
                    raise PermissionError(f"{table}.{name} is required but denied in {country}. Make it optional or narrow the country/recipient scope.")
                part["fields"][table].append(name) if allowed else part["omitted_fields"][table].append(name)
        result["partitions"][country] = part
        trace.append({"stage": f"{country} field policy", "detail": "Dataset ∩ team ∩ role ∩ country: " + ", ".join(part["categories"]), "status": "passed"})
    return result


def _value(meta, context, rng):
    rule = meta["generator"]
    if rule in context:
        return context[rule]
    if rule == "name":
        return f"{rng.choice(['Alex', 'Morgan', 'Taylor', 'Casey', 'Jordan', 'Riley'])} Rowan {context['index']:03d}"
    if rule == "choice":
        return rng.choice(meta["choices"])
    if rule == "boolean":
        return bool(rng.getrandbits(1))
    if rule == "number":
        lo, hi, step = meta["minimum"], meta["maximum"], meta["step"]
        value = lo + rng.randint(0, int((hi - lo) / step)) * step
        return round(value, 6) if isinstance(value, float) else value
    raise ValueError("No declared generator is available for this field.")


def generate_package(schema, contract, subject):
    compiled = compile_policy(schema, contract, subject)
    config_hash = digest({"schema": schema, "contract": contract})
    package_id = "pkg-" + digest({"config": config_hash, "subject": subject["id"], "policy": digest(POLICY), "generator": GENERATOR_VERSION})[:16]
    package = {"package_id": package_id, "recipient_id": subject["id"], "team": subject["team"], "role": compiled["role"], "contract": deepcopy(contract), "config_hash": config_hash, "policy_hash": digest(POLICY), "generator_version": GENERATOR_VERSION, "partitions": {}}
    for country, permitted in compiled["partitions"].items():
        part = deepcopy(permitted)
        part["tables"] = {table: [] for table in TABLES if table in contract["tables"]}
        rng = random.Random(digest({"seed": contract["seed"], "subject": subject["id"], "country": country}))
        for index in range(1, contract["rows"] + 1):
            suffix = digest({"seed": contract["seed"], "subject": subject["id"], "country": country, "index": index})[:14]
            start = date(2026, 1, 1) + timedelta(days=rng.randint(0, 150))
            context = {"employee_id": "emp-" + suffix, "assignment_id": "asg-" + suffix, "country": country, "index": index,
                       "start_date": start.isoformat(), "end_date": (start + timedelta(days=rng.randint(30, 180))).isoformat()}
            for table in part["tables"]:
                # Independent field streams keep existing values stable when another field is added.
                record = {name: _value(schema[table][name], context, random.Random(digest({"seed": contract["seed"], "recipient": subject["id"], "country": country, "table": table, "field": name, "index": index, "metadata": schema[table][name]}))) for name in permitted["fields"][table]}
                part["tables"][table].append(record)
        package["partitions"][country] = part
    package["manifest"] = {"package_id": package_id, "name": contract["name"], "contract_version": contract["version"], "policy_version": POLICY["version"], "generator_version": GENERATOR_VERSION, "data_kind": "synthetic_only", "recipient": subject["id"], "seed": contract["seed"], "config_hash": config_hash,
                           "partitions": {country: {"fields": part["fields"], "omitted_fields": part["omitted_fields"], "row_counts": {t: len(rows) for t, rows in part["tables"].items()}, "sha256": {t: digest(rows) for t, rows in part["tables"].items()}} for country, part in package["partitions"].items()},
                           "validation": {"status": "passed", "checks": CHECKS}}
    validate_package(package, schema, subject)
    return package, compiled


def validate_package(package, schema, subject):
    contract = package["contract"]
    compiled = compile_policy(schema, contract, subject)
    if package.get("recipient_id") != subject["id"] or package.get("team") != subject["team"] or package.get("role") != compiled["role"]:
        raise PermissionError("Package recipient does not match the selected trusted profile.")
    if package.get("policy_hash") != digest(POLICY) or package.get("config_hash") != digest({"schema": schema, "contract": contract}) or package.get("generator_version") != GENERATOR_VERSION:
        raise ValueError("Package schema or policy provenance no longer matches.")
    if set(package["partitions"]) != set(compiled["partitions"]):
        raise ValueError("Package countries differ from its permitted scope.")
    seen = {table: set() for table in TABLES}
    for country, part in package["partitions"].items():
        allowed = compiled["partitions"][country]
        manifest = package["manifest"]["partitions"][country]
        if part["fields"] != allowed["fields"] or manifest["fields"] != allowed["fields"] or set(part["tables"]) != set(contract["tables"]):
            raise ValueError("Package tables or field sets differ from compiled policy.")
        employee_ids = {r.get("employee_id") for r in part["tables"].get("employees", [])}
        for table, records in part["tables"].items():
            if len(records) != contract["rows"] or manifest["row_counts"][table] != len(records):
                raise ValueError("Table row counts differ from the generation contract.")
            for record in records:
                if set(record) != set(allowed["fields"][table]):
                    raise ValueError("Record shape differs from permitted fields.")
                for name, value in record.items():
                    meta = schema[table][name]
                    if not valid_type(value, meta["type"]) or (meta["required"] and value in (None, "")):
                        raise ValueError(f"{table}.{name}: value fails its type or required constraint.")
                    if meta["generator"] == "choice" and value not in meta["choices"]:
                        raise ValueError(f"{table}.{name}: value is outside its declared choices.")
                    if meta["generator"] == "number" and not meta["minimum"] <= value <= meta["maximum"]:
                        raise ValueError(f"{table}.{name}: value is outside its declared range.")
                identifier = record["employee_id" if table == "employees" else "assignment_id"]
                if identifier in seen[table] or record["country"] != country:
                    raise ValueError("Identifier uniqueness or country partition constraint failed.")
                seen[table].add(identifier)
                if table == "assignments" and (record["employee_id"] not in employee_ids or date.fromisoformat(record["start_date"]) > date.fromisoformat(record["end_date"])):
                    raise ValueError("Assignment foreign key or date order failed.")
            if manifest["sha256"][table] != digest(records):
                raise ValueError("Table content checksum failed.")
    return {"status": "passed", "checks": CHECKS, "tables": sum(len(p["tables"]) for p in package["partitions"].values()), "rows": sum(len(rows) for p in package["partitions"].values() for rows in p["tables"].values())}


def csv_content(package, country, table):
    if country not in package["partitions"] or table not in package["partitions"][country]["tables"]:
        raise ValueError("Choose a country and table included in this package.")
    part = package["partitions"][country]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=part["fields"][table], lineterminator="\n")
    writer.writeheader()
    writer.writerows(part["tables"][table])
    return buffer.getvalue()
