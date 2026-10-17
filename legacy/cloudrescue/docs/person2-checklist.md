# Người 2 — Checklist tiến độ (Nền AWS)

Ánh xạ đúng danh sách công việc trong đề tài CloudRescue.

## Đầu ra yêu cầu (từ đề bài)

| Tiêu chí | Trạng thái |
|----------|------------|
| `terraform validate` pass | **PASS** (xem lệnh bên dưới) |
| Controller truy cập S3/RDS/SSM | **PASS** — S3 và RDS kiểm tra từ controller qua SSM; xem Task 8–9 |
| S3 Versioning evidence | Chưa — Task 7 |
| RDS private evidence | Chưa — Task 8 |
| AWS Budget evidence | Bạn đã làm Task 3 (giữ screenshot) |

---

## Task 1 — Account / Region / Naming / Tags

**Trạng thái:** Hoàn thành (theo khai báo của bạn + `docs/aws-convention.md`)

| Mục | Giá trị trong repo |
|-----|-------------------|
| Naming | `{project}-{env}-{resource}` → `cloudrescue-dev-...` |
| Tags | Project, Environment, Owner, JobId, Mode, ExpiresAt |
| Owner | `nhom01-person2` |
| ExpiresAt | `2026-12-31` |
| CLI profile | `cloudrescue-dev` |
| Region (tfvars) | `ap-southeast-1` — xác nhận đúng region nhóm đã chọn |

**Evidence đề xuất:** `evidence/person2/t01-account-region-tags.png`

---

## Task 2 — MFA / không root access key

**Trạng thái:** Hoàn thành (theo khai báo của bạn — không thể verify từ code)

**Evidence đề xuất:**

- `evidence/person2/t02-root-mfa.png`
- `evidence/person2/t02-root-no-access-keys.png`
- `evidence/person2/t02-admin-mfa.png`
- `evidence/person2/t02-sts-caller-identity.png` (`aws sts get-caller-identity`)

---

## Task 3 — AWS Budget 50% / 75% / 90%

**Trạng thái:** Hoàn thành (theo khai báo của bạn)

**Evidence đề xuất:**

- `evidence/person2/t03-budget-overview.png`
- `evidence/person2/t03-budget-alerts-50-75-90.png`

---

## Task 4 — Terraform skeleton ✅

**Trạng thái: HOÀN THÀNH**

Đã có đủ 6 module theo đề bài:

| Module | Path | Việc sẽ implement |
|--------|------|-------------------|
| network | `terraform/modules/network` | Task 5 — VPC / subnet |
| storage | `terraform/modules/storage` | Task 7 — S3 |
| iam | `terraform/modules/iam` | Task 6 (+ prep Task 9) |
| database | `terraform/modules/database` | Task 8 — RDS |
| controller | `terraform/modules/controller` | Task 8–9 — EC2 + SSM |
| observability | `terraform/modules/observability` | Log/alarm (optional) |

Root wire + feature flags: `terraform/main.tf`  
Tags chung: `terraform/locals.tf` (`ManagedBy = terraform`)  
Không hard-code access key; `terraform.tfvars` đã gitignore.

### Kiểm chứng Task 4

```powershell
cd terraform
$env:AWS_PROFILE = "cloudrescue-dev"
terraform fmt -recursive
terraform init
terraform validate
```

Kỳ vọng: `Success! The configuration is valid.`

**Evidence:** `evidence/person2/t04-terraform-validate.png`

---

## Task 5 — VPC + public subnet + 2 private DB subnets (2 AZs)

**Trạng thái: HOÀN THÀNH** (`Apply complete! Resources: 12 added`)

Xem IDs: `docs/network-inventory.md`

**Evidence:**

- `evidence/person2/t05-vpc.png`
- `evidence/person2/t05-subnets.png`
- `evidence/person2/t05-route-tables.png`
- `evidence/person2/t05-terraform-output.png`

---

## Task 6 — Security Groups (controller / target / database)

**Trạng thái: HOÀN THÀNH** (`13 added`)

Xem IDs: `docs/sg-inventory.md`

RDS port 5432 **không** mở `0.0.0.0/0`. IAM role/instance profile đã hoàn tất ở Task 9.

**Evidence:**

- `evidence/person2/t06-sg-list.png`
- `evidence/person2/t06-sg-database-inbound.png` (chỉ controller + target)
- `evidence/person2/t06-sg-controller-inbound.png`
- `evidence/person2/t06-terraform-output-sg.png`

---

## Task 7 — S3 backup bucket (BPA + encryption + versioning)

**Trạng thái: HOÀN THÀNH**

Bucket: `cloudrescue-dev-backups-800591602832` — xem `docs/s3-inventory.md`

**Evidence:**

- `evidence/person2/t07-s3-bucket.png`
- `evidence/person2/t07-s3-block-public-access.png`
- `evidence/person2/t07-s3-encryption.png`
- `evidence/person2/t07-s3-versioning.png`
- `evidence/person2/t07-terraform-output-s3.png`

---

## Task 8 — RDS PostgreSQL nhỏ, Single-AZ, private ✅

**Trạng thái: HOÀN THÀNH**

- RDS PostgreSQL `db.t3.micro`, PostgreSQL 16, Single-AZ tại `ap-southeast-1a`.
- Storage mã hóa; `publicly_accessible = false`.
- DB subnet group dùng hai private subnet ở hai AZ; security group chỉ cho phép TCP 5432 từ controller/target SG.
- Controller và RDS cùng VPC. Kiểm thử từ controller qua SSM Run Command đã PASS cả DNS private, TCP 5432 và truy vấn PostgreSQL có TLS.

Xem inventory và kết quả kiểm thử không chứa secret tại `docs/rds-inventory.md`.

**Evidence đề xuất:**

- `evidence/person2/t08-rds-connectivity.png`
- `evidence/person2/t08-rds-private.png`
- `evidence/person2/t08-rds-subnet-sg.png`

---

## Task 9 — Instance profile + SSM Run Command ✅

**Trạng thái: HOÀN THÀNH**

- EC2 `i-09dad9aa959760e33` đang gắn instance profile `cloudrescue-dev-profile-controller`.
- Profile chứa role `cloudrescue-dev-role-controller`; trust principal là EC2 và role gắn `AmazonSSMManagedInstanceCore`.
- SSM managed node báo `Online`. Run Command thử nghiệm đã PASS: xác nhận assumed-role identity bên trong controller và quyền truy cập metadata bucket S3.
- SSM Command ID: `1be1ff84-fcde-45cd-84b7-3ff75647f2df`.

Xem kết quả tại `docs/controller-ssm-inventory.md`.

**Evidence đề xuất:** `evidence/person2/t09-controller-ssm-run-command.png` (chụp trang SSM Run Command với trạng thái Success và output; không chụp secret).

---

## Task 10 — Reviewed plan + ARN/ID inventory ✅

**Trạng thái: HOÀN THÀNH**

- Plan mới đã được tạo từ trạng thái AWS và xem lại bằng `terraform show`: **No changes**, 0 added / 0 changed / 0 destroyed.
- Bản plan nhị phân được lưu cục bộ tại `terraform/tfplan-task10.tfplan`; `.gitignore` loại plan khỏi Git vì binary plan có thể chứa dữ liệu nhạy cảm.
- Biên bản review và SHA-256: `docs/terraform-plan-review.md`.
- Inventory ARN/ID đã xác minh trực tiếp trên AWS, không ghi DB endpoint hoặc secret ARN: `docs/aws-resource-inventory.md`.
