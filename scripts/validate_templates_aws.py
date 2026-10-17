"""Read-only CloudFormation template validation; creates no stacks."""

import argparse
import json
from pathlib import Path
import sys

import boto3
from botocore.config import Config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from cloudhub.worker import database_restore_stage
    client = boto3.Session(profile_name=args.profile, region_name=args.region).client("cloudformation", config=Config(retries={"mode": "standard", "total_max_attempts": 3}, connect_timeout=5, read_timeout=15))
    results = []
    for path in sorted((root / "src/cloudhub/templates").glob("*.json")):
        body = json.loads(path.read_text(encoding="utf-8"))
        variants = [(path.name, body)]
        if path.name.startswith(("t03-", "t04-")):
            variants.append((path.name + ":database-restore-stage", database_restore_stage(body)))
        for name, template in variants:
            encoded = json.dumps(template)
            if len(encoded.encode()) > 51200:
                raise ValueError("Template exceeds inline limit")
            result = client.validate_template(TemplateBody=encoded)
            results.append({"template": name, "result": "OK", "parameters": len(result.get("Parameters", []))})
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
