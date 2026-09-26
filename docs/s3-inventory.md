# S3 backup inventory (Task 7) — non-secret

| Mục | Giá trị |
|-----|---------|
| Bucket name | `cloudrescue-dev-backups-800591602832` |
| Bucket ARN | `arn:aws:s3:::cloudrescue-dev-backups-800591602832` |
| Region | `ap-southeast-1` |
| Block Public Access | **All four settings ON** |
| Encryption | SSE-S3 (`AES256`) |
| Versioning | **Enabled** |
| Ownership | BucketOwnerEnforced |
| Lifecycle | Noncurrent versions under `backups/` expire after 30 days |

## Prefix layout (OpenStack → AWS backups)

```text
s3://cloudrescue-dev-backups-800591602832/
├── backups/          # per job: database/, uploads/, manifest.json
├── metadata/
└── manifests/
```

Example job:

```text
backups/<job-id>/
├── database/
├── uploads/
└── manifest.json
```

## Verify versioning (optional CLI)

```powershell
$env:AWS_PROFILE = "cloudrescue-dev"
aws s3api put-object --bucket cloudrescue-dev-backups-800591602832 --key backups/demo/hello.txt --body "$env:TEMP\hello.txt"
# Create a small file first, upload twice, then:
aws s3api list-object-versions --bucket cloudrescue-dev-backups-800591602832 --prefix backups/demo/
```

Làm mới outputs: `cd terraform; terraform output backup_bucket_name`
