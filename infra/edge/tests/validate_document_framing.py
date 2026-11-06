"""Coordinator-only, disposable real HTTP framing gate; never deploys or installs.

Use the fixed candidate venv on Linux, after the owned PG helper's ``up``.
The coordinator must run that helper's ``down`` even if this runner is interrupted.
No live credentials, request bodies or header values appear in its public report.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import timezone
import hashlib
import http.client
from http.cookies import SimpleCookie
import importlib.metadata
from ipaddress import ip_interface
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import signal
import socket
import ssl
import stat
import subprocess
import sys
import time
import uuid

# Candidate source is immutable, including during the runner's own imports.
sys.dont_write_bytecode = True
from validate_isolated import validate_config, render_nginx

PREFIX = Path('/opt/hms/validation/document-http-edge-20261103')
SOURCE = Path('/opt/hms/validation/document-http-source-20261103')
CONFIG = Path('/opt/hms/validation/network-edge-pg-20261024/runner-config.json')
REPORT = Path('/opt/hms/validation/document-http-framing-report-20261103.json')
VENV = Path('/opt/hms/validation/identity-20261023/venv')
HOST = 'hms.praritsidana.com'
SCENARIOS = frozenset({'login', 'csrf', 'list', 'detail', 'create4096', 'withdraw4096',
    'create4097', 'withdraw4097', 'get-body', 'missing', 'short-json', 'incomplete',
    'duplicate', 'conflicting', 'te-cl', 'bad-chunk', 'bad-terminal', 'conflicting-te',
    'chunk4096', 'chunk4097', 'valid-first', 'h2-list', 'h2-create4096',
    'h2-create4097', 'h2-missing', 'h2-mismatch'})


def child_environment():
    return {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': str(PREFIX), 'LANG': 'C.UTF-8'}


@contextmanager
def blocked_interrupts():
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def isolated_pg_identity(row, database, server_address):
    name, user, address, port, pg, tls = row
    return (name == database['NAME'] and user == database['USER'] and
        ip_interface(address).ip == ip_interface(server_address).ip and
        port == 5432 and pg >= 170000 and tls is True)


def render_document_nginx(root):
    rendered = render_nginx(Path(root), baseline=False)
    # The pure renderer is unit-tested on Windows as well as its Linux runtime.
    rendered = re.sub(r'\\opt\\[A-Za-z0-9\\/_.-]+',
                      lambda match: match[0].replace('\\', '/'), rendered)
    rendered = rendered.replace('/opt/hms/validation/network-edge-20261024', PREFIX.as_posix())
    rendered = rendered.replace('listen 127.0.0.1:18186 ssl;',
                                'listen 127.0.0.1:18186 ssl http2;')
    rendered = rendered.replace('client_max_body_size 64k;',
                                'client_max_body_size 64k;\n    client_body_timeout 2s;')
    for forbidden in ('/opt/hms/current', '/etc/letsencrypt',
                      '/opt/hms/validation/network-edge-', '127.0.0.1:8185'):
        if forbidden in rendered:
            raise ValueError('Unsafe path survived isolated rendering')
    if rendered.count('client_body_timeout 2s;') != 1:
        raise ValueError('Reviewed renderer changed')
    return rendered


def framing_observation(environ):
    """Pure metadata classifier: deliberately never accesses wsgi.input."""
    length = environ.get('CONTENT_LENGTH')
    if length is None or length == '':
        length_class = 'absent'
    elif isinstance(length, str) and re.fullmatch(r'[0-9]{1,10}', length):
        length_class = int(length)
    else:
        length_class = 'invalid'
    encoding = environ.get('HTTP_TRANSFER_ENCODING', '')
    scenario = environ.get('HTTP_X_HMS_FRAMING_SCENARIO')
    return {'scenario': scenario if scenario in SCENARIOS else 'unknown',
            'length': length_class,
            'transfer_encoding': 'absent' if not encoding else
                'chunked' if encoding == 'chunked' else 'other'}


def safe_path(path, *, private=False, directory=False):
    if not path.is_absolute():
        raise ValueError('Absolute fixed path required')
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unsafe path ownership or ancestry')
    info = path.stat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or private and stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('Unsafe file type or private mode')


def verify_source():
    safe_path(SOURCE, directory=True)
    manifest_path = SOURCE / 'candidate-manifest.json'
    safe_path(manifest_path, private=True)
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError('Missing canonical source manifest')
    if any(not isinstance(key, str) or not key or '\\' in key or
           PurePosixPath(key).is_absolute() or '..' in PurePosixPath(key).parts or
           PurePosixPath(key).as_posix() != key for key in manifest):
        raise ValueError('Unsafe canonical manifest path')
    actual = set()
    for path in SOURCE.rglob('*'):
        if path.is_symlink():
            raise ValueError('Symlink in candidate source')
        if path.is_dir():
            safe_path(path, directory=True)
            continue
        if not path.is_file():
            raise ValueError('Special file in candidate source')
        if path.is_file() and path != manifest_path:
            relative = path.relative_to(SOURCE).as_posix()
            actual.add(relative)
            safe_path(path)
            digest = manifest.get(relative)
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or \
                    hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Candidate source hash mismatch')
    if actual != set(manifest) or not {'backend/hms/wsgi.py',
            'backend/apps/core/document_api.py', 'infra/edge/tests/validate_document_framing.py'} <= actual:
        raise ValueError('Incomplete candidate source manifest')
    if Path(__file__).resolve() != SOURCE / 'infra/edge/tests/validate_document_framing.py':
        raise ValueError('Runner must execute from verified candidate')
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def listening(port):
    with socket.socket() as connection:
        connection.settimeout(.15)
        return connection.connect_ex(('127.0.0.1', port)) == 0


class Gate:
    def __init__(self, config):
        self.config = config
        self.processes = []
        self.handles = []
        self.checks = []
        self.stage = 'preflight'
        self.owns_runtime = False
        self.observations = []
        self.versions = {}
        self.cookies = SimpleCookie()
        self.env = child_environment()
        self.cleanup_errors = []

    def check(self, name, condition, **metadata):
        self.checks.append({'name': name, 'passed': bool(condition), **metadata})
        if not condition:
            raise AssertionError(name)

    def command(self, args, *, data=None, timeout=40):
        result = subprocess.run(args, input=data, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=self.env, timeout=timeout)
        if result.returncode:
            if self.owns_runtime:
                with (PREFIX / 'command.log').open('ab') as output:
                    output.write(result.stdout + result.stderr)
            raise RuntimeError('Private command failed')
        return result.stdout + result.stderr

    def launch(self, args):
        handle = (PREFIX / 'process.log').open('ab')
        self.handles.append(handle)
        # The child inherits the critical-section mask; clear it before same-PID exec.
        child = 'import os,signal,sys; signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM}); os.execvpe(sys.argv[1], sys.argv[1:], os.environ)'
        with blocked_interrupts():
            process = subprocess.Popen([sys.executable, '-c', child, *args], cwd=SOURCE / 'backend', env=self.env,
                stdout=handle, stderr=handle, start_new_session=True)
            self.processes.append(process)
        return process

    def claim_runtime(self):
        with blocked_interrupts():
            PREFIX.mkdir(mode=0o700)
            self.owns_runtime = True
            self.runtime_inode = PREFIX.stat().st_ino

    def wait_port(self, port, process):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Owned process exited')
            if listening(port):
                return
            time.sleep(.05)
        raise RuntimeError('Owned process readiness inconclusive')

    def setup(self):
        if sys.platform != 'linux' or os.geteuid() != 0 or Path(sys.prefix).resolve() != VENV:
            raise ValueError('Exact root Linux candidate venv required')
        validate_config(self.config)
        safe_path(CONFIG, private=True)
        safe_path(PREFIX.parent, directory=True)
        if PREFIX.exists() or PREFIX.is_symlink() or REPORT.exists() or REPORT.is_symlink():
            raise ValueError('Preexisting runtime/report requires reviewed recovery')
        self.manifest_sha256 = verify_source()
        if any(listening(port) for port in (18185, 18186)):
            raise ValueError('Candidate listener collision')
        for package, version in [('Django', '5.2.18'), ('djangorestframework', '3.16.1'),
                                 ('psycopg', '3.2.12'), ('gunicorn', '26.2.0')]:
            actual = importlib.metadata.version(package)
            self.check('version ' + package, actual == version)
            self.versions[package] = actual
        nginx = subprocess.run(['nginx', '-V'], capture_output=True, env=self.env, timeout=5)
        version = (nginx.stdout + nginx.stderr).decode('ascii', 'replace')
        self.check('Nginx reviewed version/modules', nginx.returncode == 0 and
            'nginx/1.24.' in version and all(flag in version for flag in
                ('--with-http_v2_module', '--with-http_ssl_module', '--with-http_auth_request_module')))
        self.versions['nginx'] = re.search(r'nginx/[0-9.]+', version).group()
        from prepare_isolated_pg import validate_receipt, validate_resource, CONTAINER, NETWORK
        receipt_path = CONFIG.parent / 'receipt.json'
        safe_path(receipt_path, private=True)
        receipt = json.loads(receipt_path.read_text())
        validate_receipt(receipt)
        if receipt.get('stage') != 'ready':
            raise ValueError('Owned PG helper is not ready')
        resource = self.command(['docker', 'container', 'inspect', CONTAINER])
        resources = json.loads(resource)
        if not isinstance(resources, list) or len(resources) != 1:
            raise ValueError('Ambiguous owned PG resource')
        validate_resource(receipt, resources[0], 'container')
        server_address = resources[0]['NetworkSettings']['Networks'][NETWORK]['IPAddress']
        # Probe only the fixed helper-owned endpoint; no DB creation/drop here.
        import psycopg
        db = self.config['database']
        with psycopg.connect(dbname=db['NAME'], user=db['USER'], password=db['PASSWORD'],
                host=db['HOST'], port=db['PORT'], sslmode='require', connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT current_database(), current_user, inet_server_addr()::text, '
                    'inet_server_port(), current_setting(\'server_version_num\')::int, '
                    '(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())')
                identity = cursor.fetchone()
                self.check('actual isolated TLS PG identity', isolated_pg_identity(identity, db, server_address))
                cursor.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
                self.check('disposable DB initially empty', cursor.fetchone() == (0,))
                cursor.execute('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user')
                self.check('disposable app role least privilege', cursor.fetchone() == (False, False, False))
                self.versions['postgresql'] = identity[4]
        self.claim_runtime()
        from cryptography.fernet import Fernet
        owner_id = uuid.uuid4()
        self.env.update({'HMS_ENV': 'staging', 'HMS_SECRET_KEY': secrets.token_urlsafe(48),
            'HMS_DB_ENGINE': 'postgresql', 'HMS_ALLOWED_HOSTS': HOST,
            'HMS_TRUSTED_PROXIES': '127.0.0.1', 'HMS_NETWORK_PROBE_PEERS': '127.0.0.1',
            'HMS_SECURITY_ORGANISATION_ID': str(owner_id), 'HMS_IP_ALLOWLIST_ONLY': '0',
            'HMS_MFA_ENCRYPTION_KEYS': Fernet.generate_key().decode(), 'HMS_REQUIRE_ADMIN_MFA': '1',
            'HMS_CSRF_TRUSTED_ORIGINS': 'https://' + HOST, 'HMS_DB_SSLMODE': 'require',
            'HMS_DOCUMENT_METADATA_ENABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1',
            'DJANGO_SETTINGS_MODULE': 'hms.settings',
            'PYTHONPATH': str(PREFIX) + ':' + str(SOURCE / 'backend') + ':' + str(Path(__file__).parent)})
        for key in ('NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
            self.env['HMS_DB_' + key] = str(db[key])
        os.environ.clear()
        os.environ.update(self.env)
        sys.path.insert(0, str(SOURCE / 'backend'))
        import django
        django.setup()
        from django.core.management import call_command
        with (PREFIX / 'migrate.log').open('w') as output:
            call_command('migrate', interactive=False, verbosity=1, stdout=output, stderr=output)
        self.fixtures(owner_id)
        password = secrets.token_urlsafe(24)
        hashed = self.command(['openssl', 'passwd', '-6', '-stdin'], data=(password + '\n').encode()).decode().strip()
        (PREFIX / 'basic.htpasswd').write_text('edge:' + hashed + '\n')
        self.basic = 'Basic ' + base64.b64encode(('edge:' + password).encode()).decode()
        self.command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
            '-keyout', str(PREFIX / 'tls.key'), '-out', str(PREFIX / 'tls.crt'),
            '-days', '1', '-subj', '/CN=' + HOST,
            '-addext', 'subjectAltName=IP:127.0.0.1,DNS:' + HOST])
        self.tls = ssl.create_default_context(cafile=str(PREFIX / 'tls.crt'))
        (PREFIX / 'static/assets').mkdir(parents=True, mode=0o700)
        (PREFIX / 'static/index.html').write_text('<!doctype html><title>Synthetic framing fixture</title>')
        # The wrapper observes metadata only and delegates unchanged WSGI input.
        wrapper = '''import json
from pathlib import Path
from hms.wsgi import application as actual_application
from validate_document_framing import framing_observation
def application(environ, start_response):
    observed = framing_observation(environ)
    def start(status, headers, exc_info=None):
        observed['status'] = int(status.split(' ', 1)[0])
        observed['app_reached'] = True
        with Path(%r).open('a') as output:
            output.write(json.dumps(observed) + '\\n')
        return start_response(status, headers, exc_info)
    return actual_application(environ, start)
''' % str(PREFIX / 'observations.jsonl')
        (PREFIX / 'framing_wsgi.py').write_text(wrapper)
        backend = self.launch([str(VENV / 'bin/gunicorn'), '--bind', '127.0.0.1:18185',
            '--workers', '1', '--timeout', '20', '--forwarded-allow-ips=127.0.0.1',
            '--no-control-socket', '--error-logfile', '-', 'framing_wsgi:application'])
        self.wait_port(18185, backend)
        (PREFIX / 'nginx.conf').write_text(render_document_nginx(SOURCE))
        self.command(['nginx', '-t', '-p', str(PREFIX) + '/', '-c', str(PREFIX / 'nginx.conf')])
        nginx = self.launch(['nginx', '-p', str(PREFIX) + '/', '-c', str(PREFIX / 'nginx.conf')])
        self.wait_port(18186, nginx)

    def fixtures(self, owner_id):
        from django.contrib.auth import get_user_model
        from apps.core.models import (Organisation, Branch, Membership, Patient,
            NetworkOperator, NetworkPolicyState)
        from apps.security.network_policy import policy_digest
        owner = Organisation.objects.create(id=owner_id, name='Synthetic framing network owner')
        branch = Branch.objects.create(organisation=owner, name='Synthetic framing reception', code='FRAME')
        operator = get_user_model().objects.create_user(username='synthetic-framing-network', password=secrets.token_urlsafe(24))
        Membership.objects.create(user=operator, branch=branch, role='master_admin')
        NetworkOperator.objects.create(user=operator, organisation=owner)
        policy = {'allowlist_only': True, 'allowlist': ['127.0.0.1/32'], 'blocklist': []}
        NetworkPolicyState.objects.filter(pk=1).update(bound_owner=owner,
            confirmed_policy=policy, confirmed_policy_digest=policy_digest(policy))
        self.password = secrets.token_urlsafe(24)
        self.user = get_user_model().objects.create_user(username='synthetic-framing-reception', password=self.password)
        Membership.objects.create(user=self.user, branch=branch, role='reception')
        patient = Patient.objects.create(branch=branch, full_name='Synthetic framing patient')
        self.base = f'/api/v1/patients/{patient.pk}/documents/'

    def headers(self, scenario):
        values = {'Host': HOST, 'Authorization': self.basic, 'Origin': 'https://' + HOST,
            'X-HMS-Framing-Scenario': scenario, 'Connection': 'close'}
        if self.cookies:
            values['Cookie'] = '; '.join(key + '=' + value.value for key, value in self.cookies.items())
        if 'csrftoken' in self.cookies:
            values['X-CSRFToken'] = self.cookies['csrftoken'].value
        return values

    def request(self, path, scenario, method='GET', body=None):
        connection = http.client.HTTPSConnection('127.0.0.1', 18186, context=self.tls, timeout=6)
        values = self.headers(scenario)
        if body is not None:
            values.update({'Content-Type': 'application/json', 'Idempotency-Key': str(uuid.uuid4())})
        try:
            connection.request(method, path, body=body, headers=values)
            response = connection.getresponse()
            result = response.read(262145)
            self.check('bounded normal response', len(result) <= 262144)
            for key, value in response.getheaders():
                if key.lower() == 'set-cookie':
                    self.cookies.load(value)
            return response.status, result
        finally:
            connection.close()

    def snapshot(self):
        from apps.core.models import (DocumentMetadataRateWindow, PatientDocumentIntent,
            DocumentIntentReceipt, DocumentAccessEvent)
        # Compare full persisted state privately, not just table counts.
        return tuple(tuple(model.objects.order_by('pk').values_list()) for model in
            (DocumentMetadataRateWindow, PatientDocumentIntent, DocumentIntentReceipt, DocumentAccessEvent))

    def observation_rows(self):
        path = PREFIX / 'observations.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def raw(self, path, scenario, framing, entity, *, method='POST'):
        values = self.headers(scenario)
        values.update({'Content-Type': 'application/json', 'Idempotency-Key': str(uuid.uuid4())})
        head = f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{key}: {value}\r\n' for key, value in values.items())
        wire = (head + framing + '\r\n').encode('ascii') + entity
        deadline = time.monotonic() + 10
        received = bytearray()
        closed = False
        try:
            with socket.create_connection(('127.0.0.1', 18186), timeout=6) as plain:
                with self.tls.wrap_socket(plain, server_hostname=HOST) as connection:
                    connection.settimeout(6)
                    connection.sendall(wire)
                    # Do not TLS shutdown/write-half-close: it can discard the HTTP response.
                    while time.monotonic() < deadline:
                        connection.settimeout(min(6, deadline - time.monotonic()))
                        chunk = connection.recv(8192)
                        if not chunk:
                            closed = True
                            break
                        received.extend(chunk)
                        if len(received) > 300000:
                            raise RuntimeError('Oversize raw response')
        except (ConnectionResetError, ssl.SSLEOFError):
            closed = True
        except (TimeoutError, socket.timeout):
            raise RuntimeError('Client timeout is inconclusive, never protocol rejection') from None
        status = None
        match = re.match(rb'HTTP/1\.[01] ([0-9]{3}) ', received)
        if match:
            status = int(match[1])
        return status, closed

    def no_effect(self, path, scenario, framing, body, *, statuses=(400, 408, 413, 501),
                  method='POST', allow_close=True):
        before = self.snapshot()
        status, closed = self.raw(path, scenario, framing, body, method=method)
        self.check(scenario + ': explicit rejection or confirmed close',
                   status in statuses or allow_close and status is None and closed,
                   status=status, confirmed_close=closed)
        self.check(scenario + ': zero allowance/business/audit effects', self.snapshot() == before)

    def admitted(self, name, operation, *, intents=0, receipts=0, events=1):
        from apps.core.models import DocumentMetadataRateWindow
        from django.utils import timezone as django_timezone
        before = self.snapshot()
        prior = DocumentMetadataRateWindow.objects.filter(actor=self.user).values_list('window_started_at', 'admitted_count').first()
        started = django_timezone.now().astimezone(timezone.utc).replace(second=0, microsecond=0)
        result = operation()
        finished = django_timezone.now().astimezone(timezone.utc).replace(second=0, microsecond=0)
        after = self.snapshot()
        window, count = DocumentMetadataRateWindow.objects.filter(actor=self.user).values_list('window_started_at', 'admitted_count').get()
        self.check(name + ': exactly one minute-safe allowance', started <= window <= finished and
            count == (prior[1] + 1 if prior and prior[0] == window else 1))
        self.check(name + ': expected durable effects', tuple(len(after[n]) - len(before[n]) for n in (1, 2, 3)) ==
                   (intents, receipts, events))
        return result

    def rate_sample(self):
        from apps.core.models import DocumentMetadataRateWindow
        from django.utils import timezone as django_timezone
        return (DocumentMetadataRateWindow.objects.filter(actor=self.user).values_list(
            'window_started_at', 'admitted_count').first(),
            django_timezone.now().astimezone(timezone.utc).replace(second=0, microsecond=0))

    def one_allowance(self, name, sample):
        prior, started = sample
        current, finished = self.rate_sample()
        self.check(name + ': exactly one persisted allowance', current is not None and
            started <= current[0] <= finished and current[1] ==
                (prior[1] + 1 if prior and prior[0] == current[0] else 1))

    @staticmethod
    def padded(body, length):
        if len(body) > length:
            raise ValueError('Synthetic body exceeds target')
        return body + b' ' * (length - len(body))

    def matrix(self):
        self.stage = 'real-session'
        status, _ = self.request('/api/v1/auth/csrf/', 'csrf')
        self.check('real TLS CSRF cookie', status == 200 and 'csrftoken' in self.cookies)
        status, _ = self.request('/api/v1/auth/login/', 'login', 'POST', json.dumps({
            'username': self.user.username, 'password': self.password}).encode())
        self.check('real ordinary reception password login', status == 200 and 'sessionid' in self.cookies)
        create = json.dumps({'category': 'registration', 'filename': 'synthetic-framing.png',
            'media_type': 'image/png', 'size_bytes': 128, 'sha256': 'a' * 64}).encode()
        withdraw = b'{"expected_version":1,"reason":"Synthetic framing correction"}'
        self.stage = 'http1-lifecycle'
        status, body = self.admitted('finite create4096', lambda: self.request(self.base,
            'create4096', 'POST', self.padded(create, 4096)), intents=1, receipts=1)
        self.check('create4096 succeeds', status == 201)
        document = json.loads(body)['document']['id']
        detail = self.base + document + '/'
        for scenario, path in [('list', self.base), ('detail', detail)]:
            status, _ = self.admitted(scenario, lambda p=path, s=scenario: self.request(p, s))
            self.check(scenario + ' succeeds', status == 200)
        withdraw_path = detail + 'withdraw/'
        status, _ = self.admitted('finite withdraw4096', lambda: self.request(withdraw_path,
            'withdraw4096', 'POST', self.padded(withdraw, 4096)), receipts=1)
        self.check('withdraw4096 succeeds', status == 200)
        self.stage = 'raw-http1-framing'
        for path, valid, over in [(self.base, create, 'create4097'), (withdraw_path, withdraw, 'withdraw4097')]:
            self.no_effect(path, over, 'Content-Length: 4097\r\n', self.padded(valid, 4097),
                           statuses=(413,), allow_close=False)
            self.no_effect(path, 'missing', '', b'')
            self.no_effect(path, 'short-json', 'Content-Length: 1\r\n', valid)
            self.no_effect(path, 'incomplete', f'Content-Length: {len(valid)+32}\r\n', valid, statuses=(400, 408))
            self.no_effect(path, 'duplicate', 'Content-Length: 2\r\nContent-Length: 2\r\n', b'{}')
            self.no_effect(path, 'conflicting', 'Content-Length: 2\r\nContent-Length: 3\r\n', b'{}')
            self.no_effect(path, 'te-cl', 'Transfer-Encoding: chunked\r\nContent-Length: 2\r\n', b'2\r\n{}\r\n0\r\n\r\n')
            self.no_effect(path, 'bad-chunk', 'Transfer-Encoding: chunked\r\n', b'Z\r\n{}\r\n0\r\n\r\n')
            self.no_effect(path, 'bad-terminal', 'Transfer-Encoding: chunked\r\n', b'2\r\n{}\r\nQ\r\n\r\n')
            self.no_effect(path, 'conflicting-te', 'Transfer-Encoding: chunked\r\nTransfer-Encoding: gzip\r\n', b'0\r\n\r\n')
        self.no_effect(self.base, 'get-body', 'Content-Length: 1\r\n', b'x',
                       statuses=(400,), method='GET', allow_close=False)
        self.chunked(create)
        # Valid first entity can commit; inaccessible trailing bytes are NOT a zero-effect assertion.
        before = self.snapshot()
        status, closed = self.raw(self.base, 'valid-first', f'Content-Length: {len(create)}\r\n', create + b'EXTRA')
        after = self.snapshot()
        self.check('valid first entity observation', status in (201, 400) or status is None and closed,
            status=status, first_command_may_commit=True,
            intent_delta=len(after[1]) - len(before[1]), event_delta=len(after[3]) - len(before[3]))
        self.http2(create)

    def chunked(self, create):
        before = self.snapshot()
        rate_sample = self.rate_sample()
        body = self.padded(create, 4096)
        start = len(self.observation_rows())
        status, _ = self.raw(self.base, 'chunk4096', 'Transfer-Encoding: chunked\r\n',
            b'1000\r\n' + body + b'\r\n0\r\n\r\n')
        observations = [row for row in self.observation_rows()[start:] if row['scenario'] == 'chunk4096']
        self.check('chunk4096 actual app observation', len(observations) == 1)
        length = observations[0]['length']
        after = self.snapshot()
        if length == 4096:
            self.check('chunk4096 canonical length succeeds', status == 201 and
                tuple(len(after[n])-len(before[n]) for n in (1, 2, 3)) == (1, 1, 1))
            self.one_allowance('chunk4096', rate_sample)
        else:
            self.check('chunk4096 unsupported framing is not admitted', length == 'absent' and status == 400 and before == after)
        self.no_effect(self.base, 'chunk4097', 'Transfer-Encoding: chunked\r\n',
            b'1001\r\n' + self.padded(create, 4097) + b'\r\n0\r\n\r\n', statuses=(400, 413))

    def http2(self, create):
        self.stage = 'http2'
        version = self.command(['curl', '--version']).decode('ascii', 'replace')
        self.check('existing curl supports HTTP2', 'HTTP2' in version)
        self.versions['curl'] = version.splitlines()[0]
        for scenario, length, declared in [('h2-list', 0, None), ('h2-create4096', 4096, '4096'),
                ('h2-create4097', 4097, '4097'), ('h2-missing', 4096, ''), ('h2-mismatch', 4096, '4095')]:
            body = self.padded(create, length) if length else b''
            body_path = PREFIX / 'curl-body'
            body_path.write_bytes(body)
            config = ['silent', 'show-error', 'http2', 'max-time = 8',
                'url = "https://' + HOST + ':18186' + self.base + '"',
                'resolve = "' + HOST + ':18186:127.0.0.1"',
                'cacert = "' + str(PREFIX / 'tls.crt') + '"',
                'output = "' + str(PREFIX / 'curl-response') + '"',
                'write-out = "%{http_version} %{http_code}"']
            for key, value in self.headers(scenario).items():
                if key not in ('Host', 'Connection'):
                    config.append('header = "' + key + ': ' + value + '"')
            if length:
                config.extend(['request = "POST"', 'data-binary = "@' + str(body_path) + '"',
                    'header = "Content-Type: application/json"',
                    'header = "Idempotency-Key: ' + str(uuid.uuid4()) + '"',
                    'header = "Content-Length:' + (' ' + declared if declared else '') + '"'])
            config_path = PREFIX / 'curl.conf'
            config_path.write_text('\n'.join(config) + '\n')
            before = self.snapshot()
            rate_sample = self.rate_sample()
            start = len(self.observation_rows())
            result = subprocess.run(['curl', '-q', '--noproxy', '*', '--config', str(config_path)], capture_output=True,
                env=self.env, timeout=10)
            output = result.stdout.decode('ascii', 'replace').strip().split()
            self.check(scenario + ': actual negotiated HTTP2', len(output) == 2 and output[0] == '2')
            status = int(output[1])
            after = self.snapshot()
            canonical_missing = False
            if scenario == 'h2-missing':
                observations = [row for row in self.observation_rows()[start:] if row['scenario'] == scenario]
                self.check(scenario + ': one actual app observation', len(observations) == 1)
                delivered = observations[0]['length']
                self.check(scenario + ': canonical or absent length', delivered in (4096, 'absent'))
                canonical_missing = delivered == 4096
            if scenario in ('h2-list', 'h2-create4096') or canonical_missing:
                self.check(scenario + ': success', result.returncode == 0 and status == (200 if not length else 201))
                self.check(scenario + ': real durable effects', len(after[3]) == len(before[3]) + 1 and
                    len(after[1]) == len(before[1]) + bool(length) and
                    len(after[2]) == len(before[2]) + bool(length))
                self.one_allowance(scenario, rate_sample)
            else:
                # curl errors alone do not establish server rejection. Require an explicit HTTP error.
                expected = (413,) if scenario == 'h2-create4097' else (400,) if scenario == 'h2-missing' else (400, 413)
                self.check(scenario + ': explicit rejection', status in expected)
                self.check(scenario + ': zero persisted effects', before == after)

    def cleanup(self):
        for process in reversed(self.processes):
            try:
                # Only Popen handles registered immediately after start_new_session.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                until = time.monotonic() + 6
                while time.monotonic() < until:
                    process.poll()
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(.05)
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait(timeout=4)
                until = time.monotonic() + 4
                while time.monotonic() < until:
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(.05)
                else:
                    raise RuntimeError('Owned process group survived cleanup')
            except Exception:
                self.cleanup_errors.append('owned-process-cleanup')
        for handle in self.handles:
            handle.close()
        if 'django.db' in sys.modules:
            from django.db import connections
            connections.close_all()
        if self.owns_runtime:
            self.checks.append({'name': 'candidate listeners closed',
                'passed': not any(listening(port) for port in (18185, 18186))})
            try:
                self.observations = self.observation_rows()
            except Exception:
                self.cleanup_errors.append('private-observation-read')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, choices=[str(CONFIG)])
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Linux candidate execution only')
    os.umask(0o077)
    safe_path(Path(args.config), private=True)
    gate = Gate(json.loads(CONFIG.read_text()))
    failure = None
    previous = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.signal(signum, interrupted)
    try:
        gate.setup()
        gate.matrix()
    except BaseException as error:
        failure = {'stage': gate.stage, 'type': type(error).__name__}
    finally:
        for signum in previous:
            signal.signal(signum, signal.SIG_IGN)
        try:
            gate.cleanup()
        except Exception:
            gate.cleanup_errors.append('cleanup-incomplete')
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    report = {'passed': failure is None and not gate.cleanup_errors and
        all(item['passed'] for item in gate.checks), 'checks': gate.checks,
        'failure': failure, 'cleanup_errors': gate.cleanup_errors,
        'observations': gate.observations, 'versions': gate.versions,
        'manifest_sha256': getattr(gate, 'manifest_sha256', None),
        'limits': ['Chunked support follows observed server-delivered length only.',
            'Valid first entity may commit despite inaccessible trailing bytes.',
            'Scoped protocol compatibility, not complete request-smuggling certification.',
            'Coordinator must run owned PG helper down after ORM/process closure.',
            'No live deployment, dependency install or global service mutation.'],
        'isolated_deviations': {'client_body_timeout_seconds': 2,
            'socket_timeout_seconds': 6, 'case_deadline_seconds': 10}}
    if gate.owns_runtime:
        with REPORT.open('x') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
        # Literal owned runtime only; preserve source and redacted external report.
        if not gate.cleanup_errors and all(item['passed'] for item in gate.checks
                if item['name'] == 'candidate listeners closed'):
            safe_path(PREFIX, directory=True)
            if PREFIX.stat().st_ino != gate.runtime_inode or PREFIX.resolve() != PREFIX:
                raise ValueError('Owned runtime changed; refusing removal')
            shutil.rmtree(PREFIX)
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
