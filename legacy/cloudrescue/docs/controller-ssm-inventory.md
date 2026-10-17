# Controller IAM and SSM inventory (Task 9) — no secrets

> Verified against AWS in `ap-southeast-1` on 2026-09-26. No access keys,
> session tokens, database passwords, or secret values are recorded here.

## Instance profile

| Property | Value |
|----------|-------|
| EC2 instance | `i-09dad9aa959760e33` |
| Instance state during test | `running` |
| Instance profile | `cloudrescue-dev-profile-controller` |
| Instance profile ARN | `arn:aws:iam::800591602832:instance-profile/cloudrescue-dev-profile-controller` |
| IAM role | `cloudrescue-dev-role-controller` |
| IAM role ARN | `arn:aws:iam::800591602832:role/cloudrescue-dev-role-controller` |
| SSM managed policy | `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore` |
| SSM agent | `3.3.4624.0`, ping status `Online` |

The controller role also has the project inline policy for the backup bucket and
the RDS-managed master secret used by the private RDS connectivity test. The
controller obtains temporary role credentials through the instance profile; no
long-lived access key is installed on the EC2 instance.

## Run Command smoke test

| Property | Value |
|----------|-------|
| Document | `AWS-RunShellScript` |
| Command ID | `1be1ff84-fcde-45cd-84b7-3ff75647f2df` |
| Status / response code | `Success` / `0` |
| Caller identity | `assumed-role/cloudrescue-dev-role-controller/i-09dad9aa959760e33` |
| S3 check | `head-bucket` succeeded for `cloudrescue-dev-backups-800591602832` |
| Region | `ap-southeast-1` |

This confirms the controller receives the intended IAM role credentials, is
managed by Systems Manager, can receive Run Command, and can access the project
backup bucket. The command only read bucket metadata and did not alter data.

## Evidence capture

Suggested screenshot path: `evidence/person2/t09-controller-ssm-run-command.png`.
Capture the Systems Manager Run Command invocation with `Success` and its
non-secret output visible. Do not include secret values or credentials.
