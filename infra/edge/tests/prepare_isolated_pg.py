"""Coordinator-only fixed ephemeral PG lifecycle. No live/shared PG operation.

Use candidate-venv Python. up/down have no configurable resource/path arguments.
All generated credentials/logs stay mode0600 under the fixed private prefix.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid

PREFIX = Path('/opt/hms/validation/network-edge-pg-20261024')
CONTAINER = 'hms-edge-validation-pg-20261024'
NETWORK = 'hms-edge-validation-20261024'
IMAGE_ID = 'sha256:858bb5e98eed02eb8cafbcdc007f9a65d1b613972028944a8ec2133ccaf80d27'
DB = 'hms_edge_validation_20261024'
APP = 'hms_edge_app'
ADMIN = 'hms_edge_admin'
VENV = '/opt/hms/validation/identity-20261023/venv'


def new_receipt():
    return {'prefix': str(PREFIX), 'run': uuid.uuid4().hex, 'image_id': IMAGE_ID,
            'container_id': None, 'network_id': None, 'stage': 'journaled'}


def labels(receipt):
    return {'hms.validation': 'network-edge-20261024', 'hms.validation.run': receipt['run']}


def expected_mounts():
    return [{'Source': str(PREFIX / source), 'Destination': destination, 'RW': writable, 'Type': 'bind'}
            for source, destination, writable in (
                ('data', '/var/lib/postgresql/data', True), ('tls', '/tls', False),
                ('init', '/docker-entrypoint-initdb.d', False),
                ('secrets', '/run/edge-secrets', False), ('pg_hba.conf', '/etc/edge-pg_hba.conf', False))]


def validate_receipt(receipt):
    if not isinstance(receipt, dict) or receipt.get('prefix') != str(PREFIX) or receipt.get('image_id') != IMAGE_ID:
        raise ValueError('Unsafe lifecycle receipt')
    token = receipt.get('run')
    if not isinstance(token, str) or len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Invalid unique lifecycle token')


def validate_resource(receipt, info, kind):
    validate_receipt(receipt)
    expected_id = receipt.get(kind + '_id')
    if not info.get('Id') or expected_id is not None and info['Id'] != expected_id:
        raise ValueError('Lifecycle resource ID mismatch')
    actual_labels = info.get('Labels', {}) if kind == 'network' else info.get('Config', {}).get('Labels', {})
    if any(actual_labels.get(key) != value for key, value in labels(receipt).items()):
        raise ValueError('Refusing unowned lifecycle resource')
    if kind == 'network':
        if info.get('Name') != NETWORK or info.get('Containers'):
            raise ValueError('Refusing nonempty or foreign network')
    elif kind == 'container':
        mounts = [{key: mount.get(key) for key in ('Source', 'Destination', 'RW', 'Type')}
                  for mount in info.get('Mounts', [])]
        ports = {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '15549'}]}
        if info.get('Name') != '/' + CONTAINER or info.get('Image') != IMAGE_ID or \
                sorted(mounts, key=lambda m: str(m['Destination'])) != sorted(expected_mounts(), key=lambda m: m['Destination']) or \
                info.get('HostConfig', {}).get('PortBindings') != ports or \
                info.get('HostConfig', {}).get('NetworkMode') != NETWORK:
            raise ValueError('Container mounts, image, port or network mismatch')
    else:
        raise ValueError('Unknown resource class')


class Lifecycle:
    def __init__(self):
        self.receipt = None

    def save(self, stage):
        self.receipt['stage'] = stage
        temporary = PREFIX / 'receipt.tmp'
        with temporary.open('w') as output:
            json.dump(self.receipt, output)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(PREFIX / 'receipt.json')

    def command(self, args, *, input=None, allowed_failure=False):
        result = subprocess.run(args, input=input, capture_output=True, timeout=45)
        if result.returncode and not allowed_failure:
            if PREFIX.is_dir():
                with (PREFIX / 'private-command.log').open('ab') as log:
                    log.write(result.stdout + result.stderr)
            raise RuntimeError('Isolated lifecycle command failed; inspect private log')
        return result

    def inspect(self, kind, name):
        result = self.command(['docker', kind, 'inspect', name], allowed_failure=True)
        if result.returncode:
            # Distinguish a genuine absent resource from daemon/permission failures.
            if b'No such' not in result.stderr and b'not found' not in result.stderr:
                raise RuntimeError('Unable to establish resource absence')
            return None
        values = json.loads(result.stdout)
        if len(values) != 1:
            raise ValueError('Ambiguous isolated resource')
        return values[0]

    def require_paths(self):
        if PREFIX.is_symlink() or PREFIX.resolve() != PREFIX:
            raise ValueError('Unsafe PG prefix')
        for parent in PREFIX.parents:
            if parent.is_symlink():
                raise ValueError('Symlink in PG prefix ancestry')

    def owned_resource(self, kind, name):
        recorded_id = self.receipt.get(kind + '_id')
        if recorded_id is not None:
            resource = self.inspect(kind, recorded_id)
            if resource is None:
                if self.inspect(kind, name) is not None:
                    raise ValueError('Named resource differs from recorded lifecycle ID')
                return None
        else:
            # Only an interrupted create without a saved ID can recover by name.
            resource = self.inspect(kind, name)
        if resource is not None:
            validate_resource(self.receipt, resource, kind)
        return resource

    def up(self):
        self.require_paths()
        if PREFIX.exists() or self.inspect('container', CONTAINER) or self.inspect('network', NETWORK):
            raise ValueError('Pre-existing candidate resources require reviewed recovery')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 15549))
        version = self.command(['docker', 'version', '--format', '{{.Server.Version}}']).stdout.decode().strip()
        if int(version.split('.')[0]) < 28:
            raise ValueError('Docker Engine28+ is required for published-loopback isolation')
        if self.inspect('image', IMAGE_ID).get('Id') != IMAGE_ID:
            raise ValueError('Existing reviewed image unavailable')
        PREFIX.mkdir(mode=0o700)
        self.receipt = new_receipt()
        self.save('before-files')
        for name in ('data', 'tls', 'init', 'secrets'):
            path = PREFIX / name
            path.mkdir(mode=0o700 if name == 'data' else 0o750)
            os.chown(path, 999 if name == 'data' else 0, 999)
            os.chmod(path, 0o700 if name == 'data' else 0o750)
        admin_password, app_password = secrets.token_urlsafe(36), secrets.token_urlsafe(36)
        (PREFIX / 'secrets/admin-password').write_text(admin_password + '\n')
        os.chown(PREFIX / 'secrets/admin-password', 999, 999)
        # token_urlsafe alphabet is known; sql.Literal still handles exact SQL quoting.
        from psycopg import sql
        statement = sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD {};\nCREATE DATABASE {} OWNER {};\n').format(
            sql.Identifier(APP), sql.Literal(app_password), sql.Identifier(DB), sql.Identifier(APP)).as_string()
        (PREFIX / 'init/10-edge.sql').write_text(statement)
        os.chown(PREFIX / 'init/10-edge.sql', 999, 999)
        hba = f'local all {ADMIN} trust\nlocal all all reject\nhostnossl all all all reject\nhostssl {DB} {APP} all scram-sha-256\nhost all all all reject\n'
        (PREFIX / 'pg_hba.conf').write_text(hba)
        os.chown(PREFIX / 'pg_hba.conf', 0, 999)
        os.chmod(PREFIX / 'pg_hba.conf', 0o640)
        self.command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
            '-subj', '/CN=isolated-edge-pg', '-addext', 'subjectAltName=IP:127.0.0.1',
            '-keyout', str(PREFIX / 'tls/server.key'), '-out', str(PREFIX / 'tls/server.crt')])
        os.chown(PREFIX / 'tls/server.key', 999, 999)
        os.chmod(PREFIX / 'tls/server.key', 0o600)
        os.chown(PREFIX / 'tls/server.crt', 0, 999)
        os.chmod(PREFIX / 'tls/server.crt', 0o640)
        self.save('before-network-create')
        tag_args = [arg for item in labels(self.receipt).items() for arg in ('--label', '='.join(item))]
        network = self.command(['docker', 'network', 'create', '--driver', 'bridge', *tag_args, NETWORK]).stdout.decode().strip()
        self.receipt['network_id'] = network
        self.save('before-container-create')
        args = ['docker', 'container', 'create', '--name', CONTAINER, *tag_args, '--network', NETWORK,
                '--publish', '127.0.0.1:15549:5432', '--restart', 'no', '--memory', '384m', '--cpus', '0.5',
                '--pids-limit', '128', '--env', 'POSTGRES_USER=' + ADMIN, '--env', 'POSTGRES_DB=postgres',
                '--env', 'POSTGRES_PASSWORD_FILE=/run/edge-secrets/admin-password',
                '--env', 'PGDATA=/var/lib/postgresql/data']
        for mount in expected_mounts():
            options = f"type=bind,src={mount['Source']},dst={mount['Destination']}"
            if not mount['RW']:
                options += ',readonly'
            args.extend(['--mount', options])
        args.extend([IMAGE_ID, 'postgres', '-c', 'hba_file=/etc/edge-pg_hba.conf',
                     '-c', 'ssl=on', '-c', 'ssl_cert_file=/tls/server.crt', '-c', 'ssl_key_file=/tls/server.key',
                     '-c', 'ssl_min_protocol_version=TLSv1.2', '-c', 'password_encryption=scram-sha-256',
                     '-c', 'max_connections=20', '-c', 'shared_buffers=32MB'])
        self.receipt['container_id'] = self.command(args).stdout.decode().strip()
        self.save('before-container-start')
        validate_resource(self.receipt, self.inspect('container', CONTAINER), 'container')
        self.command(['docker', 'container', 'start', self.receipt['container_id']])
        self.save('waiting-pg')
        config = {'venv': VENV, 'database': {'NAME': DB, 'USER': APP, 'PASSWORD': app_password,
                   'HOST': '127.0.0.1', 'PORT': '15549', 'OPTIONS': {'sslmode': 'require'}}}
        self.verify_pg(config)
        (PREFIX / 'runner-config.json').write_text(json.dumps(config))
        self.save('ready')
        return {'ready': True, 'private_config_path': str(PREFIX / 'runner-config.json'),
                'image_id': IMAGE_ID, 'server_version_num': 170011, 'app_tls': True}

    def verify_pg(self, config):
        import psycopg
        db = config['database']
        kwargs = dict(dbname=DB, user=APP, password=db['PASSWORD'], host='127.0.0.1', port=15549,
                      sslmode='require', connect_timeout=2)
        deadline = time.monotonic() + 50
        while True:
            try:
                with psycopg.connect(**kwargs) as connection, connection.cursor() as cursor:
                    cursor.execute("SELECT current_setting('server_version_num')::int,ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
                    if cursor.fetchone() != (170011, True):
                        raise ValueError('Incorrect isolated PostgreSQL version/TLS')
                    cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=current_user')
                    if cursor.fetchone() != (False, False, False, False):
                        raise ValueError('Unsafe isolated app authority')
                    cursor.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
                    if cursor.fetchone() != (0,):
                        raise ValueError('Isolated app DB is not empty')
                break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Isolated PG app TLS readiness failed') from None
                time.sleep(.25)
        for changes in ({'password': secrets.token_urlsafe(32)}, {'sslmode': 'disable'},
                        {'dbname': 'postgres'}, {'user': ADMIN}):
            try:
                with psycopg.connect(**{**kwargs, **changes}):
                    raise ValueError('Isolated PG accepted forbidden connection')
            except psycopg.OperationalError:
                pass

    def down(self):
        self.require_paths()
        receipt_path = PREFIX / 'receipt.json'
        if receipt_path.is_symlink() or receipt_path.stat().st_uid != 0 or receipt_path.stat().st_mode & 0o077:
            raise ValueError('Unsafe lifecycle receipt permissions')
        self.receipt = json.loads(receipt_path.read_text())
        validate_receipt(self.receipt)
        container = self.owned_resource('container', CONTAINER)
        if container is not None:
            validate_resource(self.receipt, container, 'container')
            self.receipt['container_id'] = container['Id']  # Recover journaled partial create safely.
            self.save('before-container-remove')
            self.command(['docker', 'container', 'stop', '--time', '10', container['Id']])
            self.command(['docker', 'container', 'rm', container['Id']])
        network = self.owned_resource('network', NETWORK)
        if network is not None:
            validate_resource(self.receipt, network, 'network')
            self.receipt['network_id'] = network['Id']
            self.save('before-network-remove')
            self.command(['docker', 'network', 'rm', network['Id']])
        if self.inspect('container', CONTAINER) or self.inspect('network', NETWORK):
            raise RuntimeError('Owned isolated resources remain')
        self.require_paths()
        shutil.rmtree(PREFIX)  # Exact constant prefix, verified above; no arbitrary input path.
        with socket.socket() as connection:
            if connection.connect_ex(('127.0.0.1', 15549)) == 0:
                raise RuntimeError('Isolated DB listener remains after cleanup')
        return {'removed': True, 'isolated_db_port_closed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('up', 'down'))
    args = parser.parse_args()
    os.umask(0o077)
    if os.geteuid() != 0 or Path(sys.prefix).resolve() != Path(VENV).resolve():
        raise ValueError('Root and the exact candidate virtualenv are required')
    lifecycle = Lifecycle()
    try:
        result = getattr(lifecycle, args.action)()
    except Exception as error:
        # No raw subprocess/framework/DB error contents escape private prefix.
        print(json.dumps({'passed': False, 'type': type(error).__name__,
                          'stage': lifecycle.receipt.get('stage') if lifecycle.receipt else 'preflight'}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
