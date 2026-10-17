#!/bin/bash
set -eu
dnf install -y nginx python3-pip
install -d -m 755 /opt/cloudhub /usr/share/nginx/html/cloudhub
python3 -m venv /opt/cloudhub/venv
/opt/cloudhub/venv/bin/pip install 'boto3>=1.35,<2'
if [ ! -f /usr/share/nginx/html/cloudhub/.cloudhub-seeded ]; then
  /opt/cloudhub/venv/bin/python -c 'import boto3; boto3.client("s3", region_name="${AWS::Region}").download_file("${CodeBucket}", "${AppBundleKey}", "/opt/cloudhub/site.zip")'
  /opt/cloudhub/venv/bin/python -m zipfile -e /opt/cloudhub/site.zip /usr/share/nginx/html/cloudhub
  test -f /usr/share/nginx/html/cloudhub/index.html
  touch /usr/share/nginx/html/cloudhub/.cloudhub-seeded
fi
find /usr/share/nginx/html/cloudhub -type d -exec chmod 755 {} \;
find /usr/share/nginx/html/cloudhub -type f -exec chmod 644 {} \;
restorecon -R /usr/share/nginx/html/cloudhub || true
cat > /etc/nginx/nginx.conf <<'NGINX'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /run/nginx.pid;
events { worker_connections 256; }
http {
  include /etc/nginx/mime.types;
  server_tokens off;
  access_log off;
  server {
    listen 8080 default_server;
    root /usr/share/nginx/html/cloudhub;
    index index.html;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    location = /health {
      if (!-f $document_root/index.html) { return 503; }
      default_type application/json;
      return 200 '{"status":"ok"}';
    }
    location ~ /\. { deny all; }
    location / { try_files $uri $uri/ =404; }
  }
}
NGINX
nginx -t
systemctl enable --now nginx
