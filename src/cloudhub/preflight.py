"""Read-only checks; reports quota limits, never claims remaining capacity."""

import argparse
import json
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


QUOTAS = {"ec2": "L-1216C47A", "rds": "L-7B6409FD", "fargate": "L-3032A538"}


def inspect(session, expected_account, vpc_id=None):
    config = Config(retries={"mode": "standard", "total_max_attempts": 3}, connect_timeout=5, read_timeout=15)
    identity = session.client("sts", config=config).get_caller_identity()
    if identity["Account"] != expected_account or identity["Arn"].endswith(":root"):
        raise ValueError("Account mismatch or root identity; deployment is blocked.")
    quotas = session.client("service-quotas", config=config)
    report = {"account": identity["Account"], "region": session.region_name, "quota_limits": {}}
    for service, code in QUOTAS.items():
        quota = quotas.get_service_quota(ServiceCode=service, QuotaCode=code)["Quota"]
        report["quota_limits"][service] = {"name": quota["QuotaName"], "limit": quota["Value"]}
    if vpc_id:
        subnets = session.client("ec2", config=config).describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
        report["subnets"] = [{"id": x["SubnetId"], "az": x["AvailabilityZone"], "free_ips": x["AvailableIpAddressCount"]} for x in subnets]
        if len({x["AvailabilityZone"] for x in subnets}) < 2:
            raise ValueError("CloudHub networking requires subnets in two availability zones.")
    report["notes"] = ["Quota limits are not remaining capacity.", "This check does not prove provisioning IAM permissions; review the change set and AWS events."]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--vpc-id")
    args = parser.parse_args()
    try:
        result = inspect(boto3.Session(profile_name=args.profile, region_name=args.region), args.expected_account, args.vpc_id)
    except (ValueError, BotoCoreError, ClientError) as exc:
        print(f"Preflight failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
