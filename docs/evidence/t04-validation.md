# T04 — kiểm tra ngày 17/10/2026

- cfn-lint, CloudFormation Guard và 19 kiểm thử catalog/settings/template: đạt.
- Kiểm tra cấu hình: HTTPS listener, ELB health, signal-gated rolling update và giới hạn ASG.
- Terraform validate: đạt, bao gồm quyền DNS giới hạn zone/suffix và quyền SignalResource nằm trong workload boundary.
- Chưa có domain/hosted zone/certificate theo xác nhận của nhóm. Chưa deploy ALB/ASG, chưa thử tải hoặc ghi số đo hiệu năng thực tế.
