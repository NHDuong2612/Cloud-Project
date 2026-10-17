#!/bin/bash
set -eu
dnf install -y python3-pip
id cloudhub >/dev/null 2>&1 || useradd --system --home-dir /opt/cloudhub --shell /sbin/nologin cloudhub
install -d -m 755 /opt/cloudhub
python3 -m venv /opt/cloudhub/venv
/opt/cloudhub/venv/bin/pip install 'boto3>=1.35,<2' 'psycopg[binary]>=3.2,<4'
/opt/cloudhub/venv/bin/python -c 'import boto3; boto3.client("s3", region_name="${AWS::Region}").download_file("${CodeBucket}", "${AppBundleKey}", "/opt/cloudhub/application.zip")'
/opt/cloudhub/venv/bin/python -m zipfile -e /opt/cloudhub/application.zip /opt/cloudhub/application
curl --fail --silent --show-error https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /opt/cloudhub/rds-ca.pem
cat > /opt/cloudhub/environment <<'CONFIG'
DB_HOST=${Database.Endpoint.Address}
DB_SECRET_ARN=${Database.MasterUserSecret.SecretArn}
DB_CA_FILE=/opt/cloudhub/rds-ca.pem
AWS_DEFAULT_REGION=${AWS::Region}
PORT=8080
PYTHONDONTWRITEBYTECODE=1
CONFIG
chown root:cloudhub /opt/cloudhub/environment
chmod 640 /opt/cloudhub/environment
cat > /etc/systemd/system/cloudhub.service <<'SERVICE'
[Unit]
Description=CloudHub CRUD demo
After=network-online.target
Wants=network-online.target
[Service]
User=cloudhub
Group=cloudhub
EnvironmentFile=/opt/cloudhub/environment
WorkingDirectory=/opt/cloudhub/application
ExecStart=/opt/cloudhub/venv/bin/python /opt/cloudhub/application/server.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable --now cloudhub
