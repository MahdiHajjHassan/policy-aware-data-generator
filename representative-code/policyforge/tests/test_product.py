"""Executable release boundaries, not presentation checks."""
import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from service import Product
from domain import validate_package


class PolicyProductTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.product = Product(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def generate(self, **changes):
        return self.product.action("generate", changes)["package"]

    def test_reproducible_relations_and_country_denials(self):
        first = self.generate(rows=17, seed="same-seed")
        self.assertEqual(first, self.generate(rows=17, seed="same-seed"))
        self.assertNotIn("annual_salary", first["partitions"]["Boreal"]["fields"]["employees"])
        self.assertIn("annual_salary", first["partitions"]["Aster"]["fields"]["employees"])
        for country, partition in first["partitions"].items():
            employees = {r["employee_id"] for r in partition["tables"]["employees"]}
            self.assertEqual(17, len(employees))
            self.assertTrue(all(r["employee_id"] in employees and r["country"] == country for r in partition["tables"]["assignments"]))

    def test_editable_metadata_changes_actual_generation_and_persists(self):
        config = deepcopy(self.product.state()["config"])
        config["schema"]["employees"]["department"]["choices"] = ["Research"]
        config["schema"]["employees"]["review_flag"] = {"type": "boolean", "category": "work", "required": False, "generator": "boolean"}
        config["contract"]["rows"] = 4
        self.product.action("save_config", config)
        package = self.generate()
        self.assertEqual(["Research"] * 4, [r["department"] for r in package["partitions"]["Aster"]["tables"]["employees"]])
        self.assertTrue(all(isinstance(r["review_flag"], bool) for r in package["partitions"]["Aster"]["tables"]["employees"]))
        self.assertEqual(config, Product(Path(self.temp.name)).state()["config"])

    def test_added_field_keeps_existing_values_and_dates_reproducible(self):
        before = self.generate(rows=4, seed="schema-extension")
        config = deepcopy(self.product.state()["config"])
        config["schema"]["employees"]["review_flag"] = {"type": "boolean", "category": "work", "required": False, "generator": "boolean"}
        self.product.action("save_config", config)
        after = self.generate()
        for country in before["partitions"]:
            for table in ("employees", "assignments"):
                old_rows = before["partitions"][country]["tables"][table]
                new_rows = after["partitions"][country]["tables"][table]
                for old, new in zip(old_rows, new_rows):
                    self.assertEqual(old, {key: new[key] for key in old})

    def test_numeric_precision_is_rejected_at_save_and_supported_precision_generates(self):
        original = deepcopy(self.product.state()["config"])
        for bounds in ({"minimum": 0.0000004, "maximum": 0.0000005, "step": 0.0000001},
                       {"minimum": 0, "maximum": 0.0000001, "step": 0.000001},
                       {"minimum": 0, "maximum": 1, "step": 0.0000001}):
            with self.subTest(bounds=bounds):
                config = deepcopy(original)
                config["schema"]["employees"]["tiny_measure"] = {"type": "number", "category": "work", "required": False, "generator": "number", **bounds}
                with self.assertRaisesRegex(ValueError, "at most 6 decimal places"):
                    self.product.action("save_config", config)
                self.assertEqual(original, self.product.state()["config"])
        config = deepcopy(original)
        config["schema"]["employees"]["tiny_measure"] = {"type": "number", "category": "work", "required": False, "generator": "number", "minimum": 0.000004, "maximum": 0.000005, "step": 0.000001}
        self.product.action("save_config", config)
        package = self.generate(rows=20, countries=["Aster"])
        self.assertTrue(all(r["tiny_measure"] in (0.000004, 0.000005) for r in package["partitions"]["Aster"]["tables"]["employees"]))
        self.assertEqual("passed", package["manifest"]["validation"]["status"])

    def test_unknown_unclassified_and_downgraded_fields_fail_closed(self):
        for change in ("unclassified", "downgraded", "unknown_generator"):
            config = deepcopy(self.product.state()["config"])
            if change == "unclassified":
                config["schema"]["employees"]["private_note"] = {"type": "string", "required": False, "generator": "name"}
            elif change == "downgraded":
                config["schema"]["employees"]["annual_salary"]["category"] = "work"
            else:
                config["schema"]["employees"]["display_name"]["generator"] = "eval"
            with self.assertRaises(ValueError):
                self.product.action("save_config", config)

    def test_required_denied_field_blocks_entire_release(self):
        config = deepcopy(self.product.state()["config"])
        config["schema"]["employees"]["annual_salary"]["required"] = True
        self.product.action("save_config", config)
        with self.assertRaises(PermissionError):
            self.generate()
        self.assertEqual("denied", self.product.state()["last_decision"]["status"])

    def test_request_cannot_override_trusted_recipient(self):
        self.product.action("select_recipient", {"recipient_id": "partner-demo"})
        with self.assertRaises(PermissionError):
            self.generate(countries=["Aster", "Boreal"])
        for attribute, value in (("subject_id", "finance-demo"), ("team", "finance"), ("role", "finance_analyst")):
            with self.assertRaises(PermissionError):
                self.generate(**{attribute: value})
        package = self.generate(countries=["Aster"])
        self.assertNotIn("display_name", package["partitions"]["Aster"]["fields"]["employees"])

    def test_exports_recheck_recipient_and_current_contract(self):
        package = self.generate()
        self.product.action("select_recipient", {"recipient_id": "partner-demo"})
        with self.assertRaises(PermissionError):
            self.product.action("export", {"package_id": package["package_id"], "format": "json"})
        self.product.action("select_recipient", {"recipient_id": "finance-demo"})
        config = deepcopy(self.product.state()["config"])
        config["schema"]["employees"]["department"]["choices"] = ["Research"]
        self.product.action("save_config", config)
        with self.assertRaises(RuntimeError):
            self.product.action("export", {"package_id": package["package_id"], "format": "json"})

    def test_zip_contains_validated_csv_manifest_schema_contract_and_audit(self):
        package = self.generate(rows=3, countries=["Aster"])
        result = self.product.action("export", {"package_id": package["package_id"], "format": "zip"})
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["content_base64"]))) as archive:
            self.assertTrue({"manifest.json", "schema.json", "contract.json", "audit.json", "dataset.json", "Aster/employees.csv", "Aster/assignments.csv"}.issubset(archive.namelist()))
            self.assertEqual("passed", json.loads(archive.read("manifest.json"))["validation"]["status"])
            self.assertEqual(4, len(archive.read("Aster/employees.csv").decode().splitlines()))

    def test_release_validation_detects_shape_and_fk_tampering(self):
        package = self.generate(rows=3)
        config = self.product.state()["config"]
        subject = self.product.state()["recipient"]
        for tamper in ("shape", "fk"):
            bad = deepcopy(package)
            row = bad["partitions"]["Aster"]["tables"]["assignments"][0]
            if tamper == "shape":
                row["secret"] = "not-allowed"
            else:
                row["employee_id"] = "missing"
            with self.assertRaises(ValueError):
                validate_package(bad, config["schema"], subject)

    def test_assignment_table_requires_parent_and_unknown_tables_block(self):
        config = deepcopy(self.product.state()["config"])
        config["contract"]["tables"] = ["assignments"]
        with self.assertRaises(ValueError):
            self.product.action("save_config", config)
        config["contract"]["tables"] = ["employees"]
        self.product.action("save_config", config)
        self.assertEqual(["employees"], list(self.generate()["partitions"]["Aster"]["tables"]))
        config["schema"]["undeclared"] = {}
        with self.assertRaises(ValueError):
            self.product.action("save_config", config)


if __name__ == "__main__":
    unittest.main()
