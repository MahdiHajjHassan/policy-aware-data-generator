"""Run generation without a browser or frontend dependencies."""
import argparse
import base64
import json
from pathlib import Path

from service import Product


def main():
    parser = argparse.ArgumentParser(description="PolicyForge local synthetic dataset compiler")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / ".product-data")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("state", help="Print current saved contract, policy and package")
    compile_parser = sub.add_parser("compile", help="Compile the saved metadata without generation")
    compile_parser.add_argument("--recipient", choices=["finance-demo", "operations-demo", "partner-demo"])
    generate = sub.add_parser("generate", help="Generate, validate and export a deterministic package")
    generate.add_argument("--recipient", default="finance-demo", choices=["finance-demo", "operations-demo", "partner-demo"])
    generate.add_argument("--contract", type=Path, help="JSON contract file")
    generate.add_argument("--schema", type=Path, help="JSON schema file")
    generate.add_argument("--countries", nargs="+", choices=["Aster", "Boreal"])
    generate.add_argument("--rows", type=int)
    generate.add_argument("--seed")
    generate.add_argument("--format", choices=["zip", "json", "csv"], default="zip")
    generate.add_argument("--country", choices=["Aster", "Boreal"], default="Aster", help="CSV partition")
    generate.add_argument("--table", choices=["employees", "assignments"], default="employees", help="CSV table")
    generate.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    try:
        product = Product(args.data_dir)
        if args.command == "state":
            print(json.dumps(product.state(), indent=2))
            return
        if getattr(args, "recipient", None):
            product.action("select_recipient", {"recipient_id": args.recipient})
        if args.command == "compile":
            print(json.dumps(product.action("compile", {}), indent=2))
            return
        config = product.state()["config"]
        for key in ("contract", "schema"):
            path = getattr(args, key)
            if path:
                config[key] = json.loads(path.read_text(encoding="utf-8"))
        for key in ("rows", "seed", "countries"):
            value = getattr(args, key)
            if value is not None:
                config["contract"][key] = value
        product.action("save_config", config)
        package = product.action("generate", {})["package"]
        result = product.action("export", {"package_id": package["package_id"], "format": args.format, "country": args.country, "table": args.table})
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output / result["filename"]
        target.write_bytes(base64.b64decode(result["content_base64"]) if "content_base64" in result else result["content"].encode())
        print(json.dumps({"package_id": package["package_id"], "recipient": package["recipient_id"], "countries": list(package["partitions"]), "rows_per_table_per_country": package["contract"]["rows"], "validation": "passed", "output": str(target.resolve())}, indent=2))
    except (ValueError, PermissionError, RuntimeError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"Release stopped: {error}\n")


if __name__ == "__main__":
    main()
