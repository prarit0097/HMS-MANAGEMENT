"""First framing-runner safety RED; never starts a process or opens a socket."""
import ast
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / 'infra/edge/tests/validate_document_framing.py'


class DocumentFramingSafety(unittest.TestCase):
    def runner(self):
        self.assertTrue(RUNNER.is_file(), 'Frozen isolated document framing runner is absent')
        spec = importlib.util.spec_from_file_location('document_framing_candidate', RUNNER)
        module = importlib.util.module_from_spec(spec)
        # The runner must be safely importable for pure config/renderer checks.
        sys.path.insert(0, str(RUNNER.parent))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        return module

    def config(self):
        return {'venv': '/opt/hms/validation/identity-20261023/venv', 'database': {
            'NAME': 'hms_edge_validation_20261024', 'USER': 'hms_edge_app',
            'PASSWORD': 'Synthetic-configuration-only-value', 'HOST': '127.0.0.1',
            'PORT': '15549', 'OPTIONS': {'sslmode': 'require'}}}

    def test_private_config_is_exact_reviewed_endpoint_and_never_mutated(self):
        runner = self.runner()
        config = self.config()
        original = copy.deepcopy(config)
        runner.validate_config(config)
        self.assertEqual(config, original)

    def test_foreign_database_role_host_port_or_tls_is_rejected(self):
        runner = self.runner()
        for key, value in [('NAME', 'hms_preview'), ('USER', 'postgres'),
                           ('HOST', '187.127.132.106'), ('PORT', '5548'),
                           ('OPTIONS', {'sslmode': 'disable'})]:
            with self.subTest(key=key):
                config = self.config()
                config['database'][key] = value
                with self.assertRaises(ValueError):
                    runner.validate_config(config)

    def test_arbitrary_runtime_paths_and_extra_config_are_rejected(self):
        runner = self.runner()
        for patch in ({'venv': '/opt/hms/releases/venv-20261026'},
                      {'prefix': '/opt/hms'}, {'source': '/opt/hms/current'},
                      {'command': ['systemctl', 'restart', 'nginx']}):
            config = {**self.config(), **patch}
            with self.subTest(patch=tuple(patch)), self.assertRaises(ValueError):
                runner.validate_config(config)

    def test_new_literal_runtime_and_source_do_not_reuse_old_or_live_paths(self):
        runner = self.runner()
        self.assertEqual(str(runner.PREFIX).replace('\\', '/'), '/opt/hms/validation/document-http-edge-20261103')
        self.assertEqual(str(runner.SOURCE).replace('\\', '/'), '/opt/hms/validation/document-http-source-20261103')

    def test_rendered_topology_only_uses_new_prefix_and_candidate_ports(self):
        runner = self.runner()
        rendered = runner.render_document_nginx(ROOT)
        self.assertIn('127.0.0.1:18185', rendered)
        self.assertIn('127.0.0.1:18186', rendered)
        self.assertIn('document-http-edge-20261103', rendered)
        self.assertIn('client_body_timeout 2s;', rendered)
        for forbidden in ('/opt/hms/current', '/etc/letsencrypt',
                          '/opt/hms/validation/network-edge-20261024',
                          '/opt/hms/validation/network-edge-source-20261024', '127.0.0.1:8185'):
            self.assertNotIn(forbidden, rendered)

    def test_report_observation_does_not_expose_arbitrary_header_or_body(self):
        runner = self.runner()
        marker = 'private-synthetic-marker-never-log'
        observed = runner.framing_observation({'CONTENT_LENGTH': marker,
            'HTTP_TRANSFER_ENCODING': marker, 'HTTP_X_HMS_FRAMING_SCENARIO': marker,
            'HTTP_COOKIE': marker, 'wsgi.input': marker, 'HTTP_AUTHORIZATION': marker})
        self.assertNotIn(marker, repr(observed))
        self.assertLessEqual(len(repr(observed)), 512)
        self.assertIsInstance(observed, dict)

    def test_observer_never_reads_the_request_stream(self):
        runner = self.runner()
        class ForbiddenInput:
            def read(self, *args):
                raise AssertionError('Observer read input')
            def readline(self, *args):
                raise AssertionError('Observer read input line')
        observed = runner.framing_observation({'CONTENT_LENGTH': '4096',
            'HTTP_TRANSFER_ENCODING': '', 'HTTP_X_HMS_FRAMING_SCENARIO': 'unknown',
            'wsgi.input': ForbiddenInput()})
        self.assertIsInstance(observed, dict)

    def test_runner_never_calls_historical_broad_validation_prepare(self):
        self.runner()
        source = RUNNER.read_text(encoding='utf-8')
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'prepare' for node in ast.walk(tree)),
            'Do not execute the old wildcard/outage/privileged matrix')

    def test_pg_identity_accepts_inet_text_masks_but_no_foreign_identity(self):
        runner = self.runner()
        identity = getattr(runner, 'isolated_pg_identity', None)
        self.assertTrue(callable(identity), 'Missing normalized PG identity check')
        row = ('hms_edge_validation_20261024', 'hms_edge_app', '172.19.0.2/32', 5432, 170011, True)
        for address in ('172.19.0.2/32', '172.19.0.2'):
            self.assertTrue(identity((*row[:2], address, *row[3:]), self.config()['database'], '172.19.0.2'))
        for index, wrong in enumerate(('hms_preview', 'postgres', '172.19.0.3/32', 15549, 160000, False)):
            with self.subTest(index=index):
                changed = list(row)
                changed[index] = wrong
                self.assertFalse(identity(changed, self.config()['database'], '172.19.0.2'))

    def run_h2(self, missing_length, missing_status, *, effects=True, duplicate=False, stale_only=False,
               strict_curl=False):
        """Pure evaluator regression, NOT actual HTTP2/proxy acceptance."""
        runner = self.runner()
        gate = runner.Gate(self.config())
        gate.base = '/synthetic/'
        gate.command = lambda args: b'curl synthetic HTTP2'
        gate.headers = lambda scenario: {'X-HMS-Framing-Scenario': scenario}
        state = [[], [], [], []]
        observed = [{'scenario': 'h2-missing', 'length': 4096}]
        gate.snapshot = lambda: tuple(tuple(rows) for rows in state)
        gate.observation_rows = lambda: list(observed)
        minute = datetime(2026, 11, 5, tzinfo=timezone.utc)
        gate.rate_sample = lambda: ((minute, len(state[0])), minute)

        def curl(args, **kwargs):
            if strict_curl:
                self.assertEqual(args[:4], ['curl', '-q', '--noproxy', '*'])
            config = (runner.PREFIX / 'curl.conf').read_text()
            scenario = next(s for s in ('h2-list', 'h2-create4096', 'h2-create4097', 'h2-missing', 'h2-mismatch')
                            if 'Scenario: ' + s + '"' in config)
            success = scenario in ('h2-list', 'h2-create4096') or scenario == 'h2-missing' and missing_status == 201
            status = missing_status if scenario == 'h2-missing' else {
                'h2-list': 200, 'h2-create4096': 201, 'h2-create4097': 413, 'h2-mismatch': 400}[scenario]
            if success and (scenario != 'h2-missing' or effects):
                state[0].append('allowance')
                state[3].append('event')
                if scenario != 'h2-list':
                    state[1].append('intent')
                    state[2].append('receipt')
            observed.append({'scenario': 'unrelated', 'length': 1})
            if scenario != 'h2-missing' or not stale_only:
                row = {'scenario': scenario, 'length': missing_length if scenario == 'h2-missing' else 0}
                observed.extend([row] * (2 if scenario == 'h2-missing' and duplicate else 1))
            return SimpleNamespace(stdout=f'2 {status}'.encode(), returncode=0)

        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'PREFIX', Path(directory)), \
                patch.object(runner.subprocess, 'run', side_effect=curl):
            gate.http2(b'{}')
        return gate

    def test_h2_missing_canonical_length_requires_real_success_and_effects(self):
        gate = self.run_h2(4096, 201)
        self.assertIn('h2-missing: exactly one persisted allowance', [row['name'] for row in gate.checks])

    def test_h2_missing_absent_length_requires_400_without_effects(self):
        self.run_h2('absent', 400)

    def test_h2_missing_canonical_cannot_be_rejected_or_omit_effects(self):
        for options in ({'missing_status': 400}, {'missing_status': 201, 'effects': False}):
            with self.subTest(options=options), self.assertRaises(AssertionError):
                self.run_h2(4096, **options)

    def test_h2_missing_invalid_or_ambiguous_observations_do_not_pass(self):
        for length, options in ((4095, {}), ('invalid', {}), ('absent', {'duplicate': True}),
                                ('absent', {'stale_only': True})):
            with self.subTest(length=length, options=options), self.assertRaises(AssertionError):
                self.run_h2(length, 400, **options)

    def test_child_environment_ignores_inherited_command_proxy_and_config(self):
        runner = self.runner()
        env = getattr(runner, 'child_environment', None)
        self.assertTrue(callable(env), 'Missing minimal child environment')
        hostile = {'GUNICORN_CMD_ARGS': '--preload --bind 0.0.0.0:80', 'PYTHONSTARTUP': '/foreign',
            'PYTHONPATH': '/foreign', 'CURL_HOME': '/foreign', 'HTTPS_PROXY': 'http://foreign',
            'PATH': '/foreign', 'HOME': '/foreign', 'HMS_SECRET_KEY': 'foreign'}
        with patch.dict(runner.os.environ, hostile, clear=True):
            actual = env()
        self.assertEqual(actual, {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': str(runner.PREFIX),
                                 'LANG': 'C.UTF-8'})

    def test_curl_ignores_default_config_and_proxies(self):
        self.run_h2('absent', 400, strict_curl=True)

    def test_launch_registers_process_before_pending_interrupt_is_delivered(self):
        runner = self.runner()
        gate = runner.Gate(self.config())
        child = SimpleNamespace(pid=101)
        events = []
        def mask(how, value):
            events.append(how)
            if how == 12:
                self.assertEqual(gate.processes, [child])
                raise KeyboardInterrupt()
            return {'old-mask'}
        with patch.object(runner.signal, 'pthread_sigmask', side_effect=mask, create=True), \
                patch.object(runner.signal, 'SIG_BLOCK', 11, create=True), \
                patch.object(runner.signal, 'SIG_SETMASK', 12, create=True), \
                patch.object(runner.Path, 'open', return_value=Mock()), \
                patch.object(runner.subprocess, 'Popen', return_value=child):
            with self.assertRaises(KeyboardInterrupt):
                gate.launch(['synthetic'])
        self.assertEqual(events, [11, 12])

    def test_runtime_ownership_is_recorded_before_pending_interrupt(self):
        runner = self.runner()
        gate = runner.Gate(self.config())
        claim = getattr(gate, 'claim_runtime', None)
        self.assertTrue(callable(claim), 'Missing interrupt-safe runtime claim')
        def mask(how, value):
            if how == 12:
                self.assertTrue(gate.owns_runtime)
                self.assertEqual(gate.runtime_inode, 123)
                raise KeyboardInterrupt()
            return set()
        with patch.object(runner.signal, 'pthread_sigmask', side_effect=mask, create=True), \
                patch.object(runner.signal, 'SIG_BLOCK', 11, create=True), \
                patch.object(runner.signal, 'SIG_SETMASK', 12, create=True), \
                patch.object(runner.Path, 'mkdir'), \
                patch.object(runner.Path, 'stat', return_value=SimpleNamespace(st_ino=123)):
            with self.assertRaises(KeyboardInterrupt):
                claim()

    def test_child_launcher_unblocks_shutdown_signals_before_same_pid_exec(self):
        runner = self.runner()
        gate = runner.Gate(self.config())
        with patch.object(runner.signal, 'pthread_sigmask', return_value=set(), create=True), \
                patch.object(runner.signal, 'SIG_BLOCK', 11, create=True), \
                patch.object(runner.signal, 'SIG_SETMASK', 12, create=True), \
                patch.object(runner.Path, 'open', return_value=Mock()), \
                patch.object(runner.subprocess, 'Popen', return_value=SimpleNamespace(pid=101)) as popen:
            gate.launch(['/usr/sbin/nginx', '-p', '/fixed-runtime'])
        argv = popen.call_args.args[0]
        self.assertEqual(argv[:2], [sys.executable, '-c'])
        self.assertEqual(argv[3:], ['/usr/sbin/nginx', '-p', '/fixed-runtime'])
        events = []
        env = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin'}
        fake_signal = SimpleNamespace(SIG_UNBLOCK=22, SIGINT=2, SIGTERM=15,
            pthread_sigmask=lambda how, signals: events.append(('unblock', how, signals)))
        fake_os = SimpleNamespace(environ=env, execvpe=lambda program, args, environment:
            events.append(('exec', program, args, environment)))
        with patch.dict(sys.modules, {'signal': fake_signal, 'os': fake_os,
                'sys': SimpleNamespace(argv=['-c', *argv[3:]])}):
            exec(compile(argv[2], '<trusted-child-shim>', 'exec'), {})
        self.assertEqual(events, [('unblock', 22, {2, 15}),
            ('exec', '/usr/sbin/nginx', ['/usr/sbin/nginx', '-p', '/fixed-runtime'], env)])

    def test_source_checks_directory_safety(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'candidate-manifest.json').write_text('{"unused":"' + 'a' * 64 + '"}')
            nested = source / 'unsafe-directory'
            nested.mkdir()
            checked = []
            def safe(path, **kwargs):
                checked.append(path)
                if path == nested:
                    raise ValueError('Unsafe directory')
            with patch.object(runner, 'SOURCE', source), patch.object(runner, 'safe_path', side_effect=safe):
                with self.assertRaises(ValueError):
                    runner.verify_source()
            self.assertIn(nested, checked)

    def test_source_rejects_special_files(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'candidate-manifest.json').write_text('{"unused":"' + 'a' * 64 + '"}')
            special = Mock()
            special.is_symlink.return_value = False
            special.is_file.return_value = False
            special.is_dir.return_value = False
            with patch.object(runner, 'SOURCE', source), patch.object(runner, 'safe_path'), \
                    patch.object(runner.Path, 'rglob', return_value=[special]):
                with self.assertRaisesRegex(ValueError, 'Special'):
                    runner.verify_source()

    def test_finite_rejections_cannot_pass_on_connection_close(self):
        runner = self.runner()
        gate = runner.Gate(self.config())
        gate.snapshot = lambda: ((), (), (), ())
        gate.raw = lambda *args, **kwargs: (None, True)
        for scenario, statuses in (('create4097', (413,)), ('withdraw4097', (413,)), ('get-body', (400,))):
            with self.subTest(scenario=scenario), self.assertRaises(AssertionError):
                gate.no_effect('/synthetic', scenario, '', b'', statuses=statuses, allow_close=False)
        gate.no_effect('/synthetic', 'incomplete', '', b'')

    def test_cleanup_detects_surviving_process_group_after_leader_reap(self):
        runner = self.runner()
        gate = runner.Gate(self.config())
        gate.processes = [Mock(pid=101)]
        with patch.object(runner.os, 'killpg', return_value=None, create=True), \
                patch.object(runner.signal, 'SIGKILL', 9, create=True), \
                patch.object(runner.time, 'monotonic', side_effect=range(100)), \
                patch.object(runner.time, 'sleep'):
            gate.cleanup()
        self.assertIn('owned-process-cleanup', gate.cleanup_errors)

    def test_matrix_uses_nested_service_document_for_detail_and_withdraw(self):
        """Lifecycle path composition only; DB/transport acceptance remains separate."""
        runner = self.runner()
        gate = runner.Gate(self.config())
        gate.base = '/api/v1/patients/synthetic/documents/'
        gate.user = SimpleNamespace(username='synthetic-reception')
        gate.password = 'synthetic-unused'
        document_id = '00000000-0000-4000-8000-000000000001'
        calls = []
        def request(path, scenario, method='GET', body=b''):
            calls.append((scenario, path))
            if scenario == 'csrf':
                gate.cookies['csrftoken'] = 'synthetic'
            if scenario == 'login':
                gate.cookies['sessionid'] = 'synthetic'
            if scenario == 'create4096':
                return 201, runner.json.dumps({'server_time': '2026-11-05T00:00:00Z',
                    'capabilities': {}, 'document': {'id': document_id, 'status': 'registered'}}).encode()
            return 200, b'{}'
        gate.request = request
        gate.admitted = lambda name, operation, **kwargs: operation()
        rejections = []
        gate.no_effect = lambda path, scenario, *args, **kwargs: rejections.append((scenario, kwargs))
        gate.snapshot = lambda: ((), (), (), ())
        gate.raw = lambda *args, **kwargs: (400, True)
        gate.chunked = lambda body: None
        gate.http2 = lambda body: None
        try:
            gate.matrix()
        except KeyError as error:
            self.fail('Matrix misread the closed service result: ' + str(error))
        self.assertIn(('detail', gate.base + document_id + '/'), calls)
        self.assertIn(('withdraw4096', gate.base + document_id + '/withdraw/'), calls)
        for scenario, options in rejections:
            if scenario in ('create4097', 'withdraw4097', 'get-body'):
                self.assertIs(options.get('allow_close'), False)


if __name__ == '__main__':
    unittest.main()
