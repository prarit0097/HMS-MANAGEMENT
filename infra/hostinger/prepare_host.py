"""Root-only, first-install preparation for the dedicated HMS preview directory.

No package/global nginx changes. Run only after reviewing free path/ports on host.
"""
import base64
import crypt
import json
import os
from pathlib import Path
import pwd
import secrets
import subprocess

os.umask(0o077)
root = Path('/opt/hms')
if root.exists():
    raise SystemExit('Refusing first-install preparation over existing /opt/hms')
root.mkdir(mode=0o755)
root.chmod(0o755)
for folder in ['secrets', 'data', 'backups', 'releases', 'logs', 'acme', 'static']:
    (root/folder).mkdir(mode=0o700 if folder in {'secrets', 'backups', 'data'} else 0o755)
    (root/folder).chmod(0o700 if folder in {'secrets', 'backups', 'data'} else 0o755)
try:
    pwd.getpwnam('hms-preview')
    raise SystemExit('Existing hms-preview user: inspect ownership before continuing.')
except KeyError:
    subprocess.run(['useradd', '--system', '--user-group', '--home-dir', '/opt/hms', '--shell', '/usr/sbin/nologin', 'hms-preview'], check=True)
user = 'hms-owner'
password = secrets.token_urlsafe(24)
db_password = secrets.token_hex(32)
admin_password = secrets.token_hex(32)
app_env = {
    'HMS_ENV': 'production', 'HMS_SECRET_KEY': secrets.token_hex(48),
    'HMS_ALLOWED_HOSTS': 'hms.praritsidana.com',
    'HMS_CSRF_TRUSTED_ORIGINS': 'https://hms.praritsidana.com',
    'HMS_DB_ENGINE': 'postgresql', 'HMS_DB_HOST': '127.0.0.1', 'HMS_DB_PORT': '5548',
    'HMS_DB_NAME': 'hms_preview', 'HMS_DB_USER': 'hms_app', 'HMS_DB_PASSWORD': db_password,
    'HMS_DB_SSLMODE': 'require', 'HMS_TRUSTED_PROXIES': '127.0.0.1/32',
    'HMS_IP_ALLOWLIST_ONLY': '0',
}
(root/'secrets/app.env').write_text(''.join(f'{k}={v}\n' for k,v in app_env.items()))
(root/'secrets/postgres.env').write_text(f'POSTGRES_USER=hms_db_admin\nPOSTGRES_PASSWORD={admin_password}\nPOSTGRES_DB=hms_preview\nPOSTGRES_INITDB_ARGS=--auth-host=scram-sha-256\n')
(root/'secrets/init-db.sql').write_text(f"CREATE ROLE hms_app LOGIN PASSWORD '{db_password}';\nALTER DATABASE hms_preview OWNER TO hms_app;\n")
(root/'secrets/bootstrap.env').write_text(f'HMS_PREVIEW_BOOTSTRAP=1\nHMS_PREVIEW_USER={user}\nHMS_PREVIEW_PASSWORD={password}\n')
(root/'secrets/preview.htpasswd').write_text(user + ':' + crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512)) + '\n')
subprocess.run(['chgrp', 'www-data', str(root/'secrets')], check=True)
(root/'secrets').chmod(0o710)
subprocess.run(['chgrp', 'www-data', str(root/'secrets/preview.htpasswd')], check=True)
(root/'secrets/preview.htpasswd').chmod(0o640)
tls = root/'secrets/postgres-tls'
tls.mkdir(mode=0o755)
tls.chmod(0o755)
subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-days', '365', '-subj', '/CN=hms-preview-db', '-keyout', str(tls/'server.key'), '-out', str(tls/'server.crt')], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for filename in ['server.key', 'server.crt']:
    os.chown(tls/filename, 999, 999)
(tls/'server.key').chmod(0o600)
(tls/'server.crt').chmod(0o644)
# Entry-point SQL must be readable by the container's postgres user only.
os.chown(root/'secrets/init-db.sql', 999, 999)
(root/'secrets/init-db.sql').chmod(0o600)
access = {'url': 'https://hms.praritsidana.com', 'username': user, 'password': password,
          'instructions': 'Private preview only. Use these credentials at the browser security prompt and app login. Synthetic test records only. Do not send this file to GitHub.'}
(root/'secrets/owner-access.json').write_text(json.dumps(access, indent=2))
subprocess.run(['bash', '-c', 'find /etc/nginx -type f -exec sha256sum {} + > /opt/hms/backups/nginx-before.sha256'], check=True)
print('Dedicated preview folder, root-only secrets and unprivileged account prepared. No credentials printed.')
