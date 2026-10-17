"""Ask AWS to validate the ASL definition without deploying a state machine."""

import argparse
import json
from pathlib import Path
import sys

import boto3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    account = session.client("sts").get_caller_identity()["Account"]
    body = (Path(__file__).resolve().parents[1] / "workflow/deploy.asl.json").read_text()
    body = body.replace("${WorkerArn}", f"arn:aws:lambda:{args.region}:{account}:function:cloudhub-validation-only")
    result = session.client("stepfunctions").validate_state_machine_definition(definition=body, type="STANDARD", severity="WARNING", maxResults=100)
    print(json.dumps({key: result[key] for key in ("result", "diagnostics", "truncated")}, indent=2))
    return 0 if result["result"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
