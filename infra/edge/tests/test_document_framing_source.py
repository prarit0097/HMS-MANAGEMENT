"""First framing-runner safety RED; never starts a process or opens a socket."""
import ast
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

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


if __name__ == '__main__':
    unittest.main()
