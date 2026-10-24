"""Coordinator-only isolated Nginx/source-Gunicorn acceptance. Never installs/deploys.

Run with the candidate venv Python and a mode0600 private JSON config. This runner
does not create/drop databases or alter any service, firewall, live file or port.
Only fixed candidate paths and its own process groups are mutable.
"""
import argparse
import base64
from datetime import timedelta
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import ssl
import subprocess
import sys
import time
import uuid

PREFIX = Path('/opt/hms/validation/network-edge-20261024')
SOURCE = Path('/opt/hms/validation/network-edge-source-20261024')
VENV = '/opt/hms/validation/identity-20261023/venv'
DB_NAME = 'hms_edge_validation_20261024'
HOST = 'hms.praritsidana.com'
PROBE = '/api/v1/network-policy/edge-probe/'
OPEN = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
RESTRICTED = {'allowlist_only': True, 'allowlist': ['127.0.0.1'], 'blocklist': []}


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {'venv', 'database'} or config['venv'] != VENV:
        raise ValueError('Unsafe candidate configuration')
    db = config['database']
    if not isinstance(db, dict) or set(db) != {'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT', 'OPTIONS'}:
        raise ValueError('Unsafe database configuration')
    if db['NAME'] != DB_NAME or db['OPTIONS'] != {'sslmode': 'require'}:
        raise ValueError('Unsafe disposable database or TLS configuration')
    if any(not isinstance(db[key], str) or not db[key] or '\x00' in db[key]
           for key in ('USER', 'PASSWORD', 'HOST')):
        raise ValueError('Invalid private database setting')
    if isinstance(db['PORT'], bool) or not str(db['PORT']).isdigit() or not 1 <= int(db['PORT']) <= 65535:
        raise ValueError('Invalid database port')


def render_nginx(root):
    """Render the reviewed TLS server and inline only its two reviewed includes."""
    source = (root / 'infra/hostinger/nginx.conf').read_text()
    start = source.index('server {\n    listen 443 ssl http2;')
    server = source[start:]
    substitutions = {
        'listen 443 ssl http2;': 'listen 127.0.0.1:18186 ssl;',
        '    listen [::]:443 ssl http2;\n': '',
        '/etc/letsencrypt/live/hms.praritsidana.com/fullchain.pem': str(PREFIX / 'tls.crt'),
        '/etc/letsencrypt/live/hms.praritsidana.com/privkey.pem': str(PREFIX / 'tls.key'),
        '/opt/hms/static': str(PREFIX / 'static'),
        '/opt/hms/secrets/preview.htpasswd': str(PREFIX / 'basic.htpasswd'),
        '/opt/hms/logs/access.log': str(PREFIX / 'access.log'),
        '/opt/hms/logs/error.log': str(PREFIX / 'error.log'),
    }
    for old, new in substitutions.items():
        if server.count(old) != 1:
            raise ValueError('Reviewed server template changed; review renderer')
        server = server.replace(old, new)
    for relative in ('edge/network-guard.conf', 'hostinger/proxy.conf'):
        include = f'include /opt/hms/current/infra/{relative};'
        if include not in server:
            raise ValueError('Reviewed include is absent')
        replacement = (root / 'infra' / relative).read_text().replace('127.0.0.1:8185', '127.0.0.1:18185')
        server = server.replace(include, replacement)
    if '/opt/hms/current' in server or '/etc/letsencrypt' in server:
        raise ValueError('Live path survived isolated rendering')
    # No master/worker privilege transition: isolated process reads private0700 prefix.
    return f'''daemon off;
master_process off;
pid {PREFIX}/nginx.pid;
error_log {PREFIX}/startup.log warn;
events {{ worker_connections 128; }}
http {{
    client_body_temp_path {PREFIX}/client_temp;
    proxy_temp_path {PREFIX}/proxy_temp;
    fastcgi_temp_path {PREFIX}/fastcgi_temp;
    uwsgi_temp_path {PREFIX}/uwsgi_temp;
    scgi_temp_path {PREFIX}/scgi_temp;
    limit_req_zone $binary_remote_addr zone=hms_login:1m rate=5r/m;
    log_format hms_safe '$remote_addr [$time_local] $request_method $uri $status $body_bytes_sent';
    {server}
}}
'''


def listening(port):
    with socket.socket() as connection:
        connection.settimeout(.15)
        return connection.connect_ex(('127.0.0.1', port)) == 0


class Validation:
    def __init__(self, config, root):
        self.config, self.root = config, root
        self.processes = []
        self.handles = []
        self.checks = []
        self.stage = 'preflight'
        self.private_files = []
        self.backend = None
        self.cleaned_groups = set()

    def check(self, name, condition, **metadata):
        self.checks.append({'name': name, 'passed': bool(condition), **metadata})
        if not condition:
            raise AssertionError(name)

    def run_command(self, args, *, input=None):
        result = subprocess.run(args, input=input, capture_output=True, env=self.env, timeout=40)
        if result.returncode:
            # Child output can contain private settings; retain only inside prefix.
            with (PREFIX / 'command-error.log').open('ab') as log:
                log.write(result.stdout + result.stderr)
            raise RuntimeError('Candidate command failed; private log retained')
        return result.stdout + result.stderr

    def launch(self, args, env=None):
        log = (PREFIX / 'process.log').open('ab')
        self.handles.append(log)
        process = subprocess.Popen(args, cwd=self.root / 'backend', env=env or self.env,
                                   stdout=log, stderr=log, start_new_session=True)
        self.processes.append(process)
        return process

    def stop(self, process):
        if process is None or process.pid in self.cleaned_groups:
            return
        if not any(owned is process for owned in self.processes):
            raise ValueError('Refusing unmanaged process-group cleanup')
        # Our process-group IDs come exclusively from Popen(start_new_session=True).
        try:
            os.killpg(process.pid, signal.SIGCONT)
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            process.poll()  # Reap leader; workers may outlive it and keep the PGID.
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                process.wait(timeout=1)
                self.cleaned_groups.add(process.pid)
                return
            time.sleep(.05)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=4)
        self.cleaned_groups.add(process.pid)

    def start_backend(self, wrong_db=False):
        if self.backend is not None:
            self.stop(self.backend)
        env = dict(self.env)
        if wrong_db:
            env['HMS_DB_PORT'] = '1'  # No shared DB/service mutation.
        self.backend = self.launch([
            str(Path(VENV) / 'bin/gunicorn'), '--bind', '127.0.0.1:18185', '--workers', '1',
            '--timeout', '20', '--forwarded-allow-ips=127.0.0.1', '--no-control-socket',
            '--error-logfile', '-', 'hms.wsgi:application'], env)
        self.wait_port(18185, self.backend)

    def wait_port(self, port, process):
        until = time.monotonic() + 12
        while time.monotonic() < until:
            if process.poll() is not None:
                raise RuntimeError('Managed candidate exited before readiness')
            if listening(port):
                return
            time.sleep(.05)
        raise RuntimeError('Managed candidate listener did not become ready')

    def request(self, path='/', *, source='127.0.0.1', method='GET', headers=None,
                body=None, basic=True, direct=False):
        values = {'Host': HOST}
        if basic:
            values['Authorization'] = self.basic
        values.update(headers or {})
        if direct:
            connection = http.client.HTTPConnection('127.0.0.1', 18185, timeout=7,
                                                    source_address=(source, 0))
        else:
            connection = http.client.HTTPSConnection('127.0.0.1', 18186, timeout=7,
                source_address=(source, 0), context=self.tls)
        try:
            connection.request(method, path, body=body, headers=values)
            response = connection.getresponse()
            return response.status, {key.lower(): value for key, value in response.getheaders()}, response.read()
        finally:
            connection.close()

    def expect(self, name, path='/', *, statuses=(200,), empty=False, protected=True, **kwargs):
        status, headers, body = self.request(path, **kwargs)
        self.check(name, status in statuses, status=status)
        if empty:
            self.check(name + ':empty', body == b'')
        if protected:
            self.check(name + ':no-store', 'no-store' in headers.get('cache-control', ''))
        return status, headers, body

    def probe(self, name, *, status=204, headers=None, **kwargs):
        values = {'X-Forwarded-Proto': 'https', 'X-Forwarded-For': '127.0.0.1',
                  'X-HMS-Network-Probe': '1'}
        values.update(headers or {})
        result = self.expect(name, PROBE, statuses=(status,), empty=True,
                             headers=values, direct=True, basic=False, **kwargs)
        self.check(name + ':no-session-or-redirect', not any(
            key in result[1] for key in ('set-cookie', 'www-authenticate', 'location')))
        return result

    def prepare(self):
        validate_config(self.config)
        if self.root.resolve() != SOURCE or PREFIX.exists() or PREFIX.is_symlink():
            raise ValueError('Unsafe source location or pre-existing runtime prefix')
        if any(listening(port) for port in (18185, 18186)):
            raise ValueError('Candidate port already occupied')
        if Path(sys.prefix).resolve() != Path(VENV).resolve():
            raise ValueError('Use the exact candidate virtualenv Python')
        import psycopg
        db = self.config['database']
        with psycopg.connect(dbname=db['NAME'], user=db['USER'], password=db['PASSWORD'],
                            host=db['HOST'], port=db['PORT'], sslmode='require', connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                if cursor.fetchall():
                    raise ValueError('Disposable candidate DB must be empty')
                cursor.execute('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()')
                if cursor.fetchone() != (True,):
                    raise ValueError('Disposable PG connection must use TLS')
        PREFIX.mkdir(mode=0o700)
        self.owns_prefix = True
        os.umask(0o077)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith('HMS_')}
        from cryptography.fernet import Fernet
        self.owner_id = uuid.uuid4()
        self.env.update({'HMS_ENV': 'staging', 'HMS_SECRET_KEY': secrets.token_urlsafe(48),
            'HMS_DB_ENGINE': 'postgresql', 'HMS_ALLOWED_HOSTS': HOST,
            'HMS_TRUSTED_PROXIES': '127.0.0.1', 'HMS_NETWORK_PROBE_PEERS': '127.0.0.1',
            'HMS_SECURITY_ORGANISATION_ID': str(self.owner_id),
            'HMS_MFA_ENCRYPTION_KEYS': Fernet.generate_key().decode(), 'HMS_REQUIRE_ADMIN_MFA': '1',
            'HMS_CSRF_TRUSTED_ORIGINS': 'https://' + HOST,
            'HMS_IP_ALLOWLIST_ONLY': '0', 'HMS_DB_SSLMODE': 'require',
            'PYTHONDONTWRITEBYTECODE': '1'})
        for key in ('NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
            self.env['HMS_DB_' + key] = str(db[key])
        for key in tuple(os.environ):
            if key.startswith('HMS_'):
                del os.environ[key]
        os.environ.update(self.env)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'hms.settings'
        sys.path.insert(0, str(self.root / 'backend'))
        import django
        django.setup()
        from django.conf import settings
        self.check('non-DEBUG secure redirect enabled', not settings.DEBUG and settings.SECURE_SSL_REDIRECT)
        from django.core.management import call_command
        # Output remains private; migrations target only the verified disposable DB.
        with (PREFIX / 'migration.log').open('w') as log:
            call_command('migrate', interactive=False, verbosity=1, stdout=log, stderr=log)
        self.create_fixtures()
        password = secrets.token_urlsafe(24)
        hashed = self.run_command(['openssl', 'passwd', '-6', '-stdin'], input=(password + '\n').encode()).decode().strip()
        (PREFIX / 'basic.htpasswd').write_text('edge:' + hashed + '\n')
        self.private_files.append(PREFIX / 'basic.htpasswd')
        self.basic = 'Basic ' + base64.b64encode(('edge:' + password).encode()).decode()
        self.run_command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
            '-keyout', str(PREFIX / 'tls.key'), '-out', str(PREFIX / 'tls.crt'),
            '-days', '1', '-subj', '/CN=' + HOST,
            '-addext', 'subjectAltName=IP:127.0.0.1,DNS:' + HOST])
        self.private_files.append(PREFIX / 'tls.key')
        self.tls = ssl.create_default_context(cafile=str(PREFIX / 'tls.crt'))
        (PREFIX / 'static/assets').mkdir(parents=True)
        (PREFIX / 'static/index.html').write_text('<!doctype html><title>Synthetic HMS edge shell</title>EDGE-SYNTHETIC-SHELL')
        (PREFIX / 'static/assets/edge.js').write_text('/* synthetic edge static fixture */\n' * 5)
        (PREFIX / 'nginx.conf').write_text(render_nginx(self.root))
        self.versions = self.run_command(['nginx', '-V']).decode()
        self.check('Nginx auth_request and SSL compiled', '--with-http_auth_request_module' in self.versions
                   and '--with-http_ssl_module' in self.versions)
        self.run_command(['nginx', '-t', '-p', str(PREFIX) + '/', '-c', str(PREFIX / 'nginx.conf')])
        self.start_backend()
        self.nginx = self.launch(['nginx', '-p', str(PREFIX) + '/', '-c', str(PREFIX / 'nginx.conf')])
        self.wait_port(18186, self.nginx)

    def create_fixtures(self):
        from django.contrib.auth import get_user_model, HASH_SESSION_KEY, SESSION_KEY, BACKEND_SESSION_KEY
        from django.contrib.sessions.backends.db import SessionStore
        from django.utils import timezone
        from apps.core.models import Organisation, Branch, Membership, IdentitySecurity, NetworkOperator, NetworkPolicyState
        from apps.core.identity_security import encrypt
        from apps.security.network_policy import policy_digest
        import pyotp
        self.owner = Organisation.objects.create(id=self.owner_id, name='Synthetic isolated edge owner')
        branch = Branch.objects.create(organisation=self.owner, name='Synthetic edge branch', code='EDGE')
        self.user = get_user_model().objects.create_user(username='synthetic-edge-owner', password=secrets.token_urlsafe(24))
        Membership.objects.create(user=self.user, branch=branch, role='master_admin')
        binding = uuid.uuid4()
        IdentitySecurity.objects.create(user=self.user, device_id=binding,
            active_ciphertext=encrypt(pyotp.random_base32(), self.user.pk, binding, 'active'), auth_epoch=0)
        NetworkOperator.objects.create(user=self.user, organisation=self.owner)
        NetworkPolicyState.objects.filter(pk=1).update(bound_owner=self.owner, confirmed_policy=RESTRICTED,
            confirmed_policy_digest=policy_digest(RESTRICTED))
        session = SessionStore()
        session[SESSION_KEY] = str(self.user.pk)
        session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
        session[HASH_SESSION_KEY] = self.user.get_session_auth_hash()
        session['auth_epoch'] = 0
        session['factor_verified_at'] = timezone.now().timestamp()
        session.save()
        self.cookie = 'sessionid=' + session.session_key

    def matrix(self):
        self.stage = 'private-probe'
        self.probe('trusted non-DEBUG actual-Gunicorn probe')
        self.probe('probe ignores supplied auth/cookie', headers={'Cookie': self.cookie, 'Authorization': 'Basic ignored'})
        self.probe('probe denies verified client', status=403, headers={'X-Forwarded-For': '127.0.0.2'})
        for name, path, headers, body, method in (
            ('missing-marker', PROBE, {'X-HMS-Network-Probe': ''}, None, 'GET'),
            ('wrong-marker', PROBE, {'X-HMS-Network-Probe': 'yes'}, None, 'GET'),
            ('query', PROBE + '?unexpected=1', {}, None, 'GET'),
            ('body', PROBE, {}, b'unexpected', 'GET'),
            ('head', PROBE, {}, None, 'HEAD'),
            ('post', PROBE, {}, None, 'POST')):
            values = {'X-Forwarded-Proto': 'https', 'X-Forwarded-For': '127.0.0.1', 'X-HMS-Network-Probe': '1', **headers}
            self.expect('invalid probe ' + name, path, direct=True, basic=False,
                        headers=values, body=body, method=method, statuses=((204,) if method == 'HEAD' else (405,) if method == 'POST' else (404,)), empty=method != 'POST')
        self.expect('untrusted peer cannot forge HTTPS', PROBE, source='127.0.0.2', direct=True,
            basic=False, headers={'X-Forwarded-Proto': 'https', 'X-HMS-Network-Probe': '1'}, statuses=(301,), protected=False)
        self.stage = 'ordinary-http'
        app_paths = ('/', '/index.html', '/administration/network-access', '/assets/edge.js',
                     '/api/v1/auth/me/', '/api/v1/auth/login/')
        for path in app_paths:
            allowed = (403,) if path.endswith('/me/') else (405,) if path.endswith('/login/') else (200,)
            result = self.expect('allowed ' + path, path, statuses=allowed)
            if path.endswith('/me/'):
                self.check('anonymous API application auth distinct from network gate',
                           json.loads(result[2]).get('code') != 'network_denied')
            self.expect('denied ' + path, path, source='127.0.0.2', statuses=(403,))
        self.expect('valid synthetic session me', '/api/v1/auth/me/', headers={'Cookie': self.cookie})
        self.expect('valid synthetic enrolled operator state', '/api/v1/platform/network-policy/', headers={'Cookie': self.cookie})
        for client in ('127.0.0.1', '127.0.0.2'):
            self.expect('missing Basic ' + client, source=client, basic=False, statuses=(401, 403))
            self.expect('wrong Basic ' + client, source=client, headers={'Authorization': 'Basic invalid'}, statuses=(401, 403))
            for path in ('/_hms_network_check', PROBE):
                self.expect('external private route ' + path + client, path, source=client, statuses=(404,))
        spoof = {'X-Forwarded-For': '127.0.0.1', 'Forwarded': 'for=127.0.0.1;proto=https',
                 'X-Real-IP': '127.0.0.1', 'X-HMS-Network-Probe': '1', 'Cookie': self.cookie}
        for path in app_paths:
            self.expect('forged path ' + path, path, source='127.0.0.2', headers=spoof, statuses=(403,))
        self.expect('allowed query does not contaminate internal probe', '/?synthetic=1')
        self.expect('dotfile cannot serve', '/.env', statuses=(403,))
        self.expect('missing asset', '/assets/missing.js', statuses=(404,))
        self.stage = 'cache-headers'
        for path in ('/', '/index.html', '/assets/edge.js'):
            for name, method, headers, statuses in (
                ('head', 'HEAD', {}, (200,)), ('range', 'GET', {'Range': 'bytes=0-9'}, (206,)),
                ('modified', 'GET', {'If-Modified-Since': 'Wed, 31 Dec 2098 23:59:59 GMT'}, (200,)),
                ('etag', 'GET', {'If-None-Match': '*'}, (200,))):
                _, observed, _ = self.expect(name + path, path, method=method, headers=headers,
                                             statuses=statuses, empty=method == 'HEAD')
                for key in ('strict-transport-security', 'content-security-policy', 'x-content-type-options',
                            'x-frame-options', 'referrer-policy', 'permissions-policy'):
                    self.check(name + path + ':' + key, key in observed)
                self.expect('denied-' + name + path, path, method=method, headers=headers,
                            source='127.0.0.2', statuses=(403,), empty=method == 'HEAD')
        self.stage = 'backend-failures'
        self.stop(self.backend)
        self.expect('backend down failclosed', statuses=(500,))
        self.start_backend()
        self.probe('restored after backend stop')
        self.expect('restored shell after backend stop')
        os.killpg(self.backend.pid, signal.SIGSTOP)
        try:
            started = time.monotonic()
            self.expect('probe read timeout failclosed', statuses=(500,))
            self.check('probe timeout bounded', 2.5 <= time.monotonic() - started < 6)
        finally:
            os.killpg(self.backend.pid, signal.SIGCONT)
        self.probe('restored after timeout')
        self.start_backend(wrong_db=True)
        self.probe('database unavailable probe', status=503)
        self.expect('database unavailable edge failclosed', statuses=(500,))
        self.start_backend()
        self.probe('restored after DB fault')
        self.expect('restored shell after DB fault')
        self.expect('restored denied policy after DB fault', source='127.0.0.2', statuses=(403,))
        self.stage = 'deadline-fallback'
        self.rollback_fixture()

    def rollback_fixture(self):
        from django.utils import timezone
        from apps.core.models import NetworkPolicyState as State, NetworkPolicyPreview as Preview, NetworkPolicyChange as Change
        from apps.security.network_policy import policy_digest
        from apps.core.network_environment import environment_snapshot
        now = timezone.now()
        activated = now - timedelta(seconds=297)
        created = activated - timedelta(seconds=1)
        binding = dict(owner=self.owner, actor=self.user, session_digest=hashlib.sha256(self.cookie.encode()).hexdigest(),
            epoch=0, operator_version=1, verified_ip='127.0.0.1', environment_digest=environment_snapshot().digest,
            base_revision=1)
        preview = Preview.objects.create(**binding, policy=RESTRICTED, policy_digest=policy_digest(RESTRICTED),
            request_digest='a'*64, reason='Synthetic edge deadline fallback', normalisations=[],
            created_at=created, expires_at=created+timedelta(seconds=300), request_key=uuid.uuid4())
        change = Change.objects.create(**binding, preview=preview, candidate_policy=RESTRICTED,
            candidate_policy_digest=policy_digest(RESTRICTED), fallback_policy=OPEN,
            fallback_policy_digest=policy_digest(OPEN), activation_revision=2, activated_at=activated,
            rollback_at=activated+timedelta(seconds=300), reason='Synthetic edge deadline fallback')
        Preview.objects.filter(pk=preview.pk).update(result_change=change)
        State.objects.filter(pk=1).update(confirmed_policy=OPEN, confirmed_policy_digest=policy_digest(OPEN),
                                         pending_change=change, revision=2)
        self.expect('before rollback denied', source='127.0.0.2', statuses=(403,))
        until = time.monotonic() + 5
        while timezone.now() < change.rollback_at and time.monotonic() < until:
            time.sleep(.03)
        self.expect('after rollback fallback allowed', source='127.0.0.2')
        change.refresh_from_db()
        state = State.objects.get(pk=1)
        self.check('edge GET fallback did not reconcile', change.status == 'pending' and state.revision == 2
                   and state.pending_change_id == change.pk)

    def cleanup(self):
        failures = []
        for process in reversed(self.processes):
            try:
                self.stop(process)
            except Exception:
                failures.append('managed process cleanup failed')
        for handle in self.handles:
            handle.close()
        for path in self.private_files:
            if path.parent == PREFIX and not path.is_symlink():
                path.unlink(missing_ok=True)
        if getattr(self, 'owns_prefix', False):
            self.checks.append({'name': 'candidate listeners cleaned', 'passed': not any(listening(p) for p in (18185, 18186))})
        return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='Absolute mode0600 private JSON path; contents never printed')
    args = parser.parse_args()
    private_path = Path(args.config)
    if not private_path.is_absolute() or private_path.is_symlink() or private_path.stat().st_mode & 0o077:
        raise ValueError('Private config must be an absolute mode0600 ordinary file')
    config = json.loads(private_path.read_text())
    validation = Validation(config, Path(__file__).resolve().parents[3])
    failure = None
    try:
        validation.prepare()
        validation.matrix()
    except Exception as error:
        # Do not print exception text/traceback: DB/framework errors may include secrets.
        failure = {'stage': validation.stage, 'type': type(error).__name__}
    finally:
        cleanup = validation.cleanup()
    report = {'checks': validation.checks, 'passed': failure is None and not cleanup
              and all(check['passed'] for check in validation.checks), 'failure': failure,
              'cleanup_errors': cleanup, 'nginx_version': getattr(validation, 'versions', ''),
              'external_origin_test': 'Coordinator must separately verify external unreachability; local bind is insufficient.',
              'deployment': 'No live deployment or global service mutation.'}
    if getattr(validation, 'owns_prefix', False):
        (PREFIX / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
