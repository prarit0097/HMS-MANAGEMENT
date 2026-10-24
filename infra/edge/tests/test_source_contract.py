"""Supplementary source invariants; actual Nginx HTTP validation is separate."""
from pathlib import Path
import re
import unittest
import importlib.util
import sys
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]


class EdgeSourceContract(unittest.TestCase):
    def test_stored_runtime_fixture_policies_are_strictly_canonical(self):
        runner = self.runner()
        with patch.object(sys, 'path', [str(ROOT / 'backend'), *sys.path]):
            from apps.security import network_policy as policy
        for fixture in (runner.OPEN, runner.RESTRICTED):
            self.assertEqual(fixture, policy.canonical_policy(fixture))
            self.assertEqual(len(policy.policy_digest(fixture)), 64)

    def test_runtime_failure_frames_omit_messages_and_locals(self):
        runner = self.runner()
        self.assertTrue(callable(getattr(runner, 'failure_frames', None)), 'Redacted failure frame helper absent')
        try:
            raise ValueError('synthetic-private-detail-must-not-escape')
        except ValueError as error:
            frames = runner.failure_frames(error)
        self.assertTrue(frames)
        self.assertEqual(set(frames[-1]), {'file', 'function', 'line'})
        self.assertNotIn('synthetic-private-detail-must-not-escape', str(frames))

    def runner(self):
        path = ROOT / 'infra/edge/tests/validate_isolated.py'
        self.assertTrue(path.exists(), 'Isolated runner is missing')
        spec = importlib.util.spec_from_file_location('edge_validation', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_runner_rejects_unsafe_database_or_extra_configuration(self):
        runner = self.runner()
        config = {'venv': '/opt/hms/validation/identity-20261023/venv', 'database': {
            'NAME': 'hms_edge_validation_20261024', 'USER': 'hms_edge_app', 'PASSWORD': 'synthetic',
            'HOST': '127.0.0.1', 'PORT': '15549', 'OPTIONS': {'sslmode': 'require'}}}
        runner.validate_config(config)
        for changed in ({**config, 'admin_database': {}}, {**config, 'venv': '/opt/hms/venv'},
                        {**config, 'database': {**config['database'], 'NAME': 'hms_preview'}},
                        {**config, 'database': {**config['database'], 'PORT': '5548'}},
                        {**config, 'database': {**config['database'], 'USER': 'hms_app'}},
                        {**config, 'database': {**config['database'], 'OPTIONS': {'sslmode': 'disable'}}}):
            with self.assertRaises(ValueError):
                runner.validate_config(changed)

    def test_runner_renders_reviewed_source_only_for_loopback_candidate(self):
        runner = self.runner()
        rendered = runner.render_nginx(ROOT)
        self.assertIn('listen 127.0.0.1:18186 ssl;', rendered)
        self.assertNotIn('listen 443', rendered)
        self.assertNotIn('listen 80', rendered)
        self.assertNotIn('/opt/hms/current', rendered)
        self.assertNotIn('/etc/letsencrypt', rendered)
        self.assertIn('proxy_pass http://127.0.0.1:18185/api/v1/network-policy/edge-probe/;', rendered)
        self.assertIn('daemon off;', rendered)

    def test_static_boundary_removes_public_direct_file_paths_and_filters_headers(self):
        nginx = (ROOT / 'infra/hostinger/nginx.conf').read_text()
        self.assertNotIn('try_files', nginx)
        for route in ('location = /index.html', 'location /assets/', 'location /'):
            self.assertIn(route, nginx)
        private = ROOT / 'infra/edge/static-upstream.conf'
        proxy = ROOT / 'infra/edge/static-proxy.conf'
        self.assertTrue(private.exists() and proxy.exists(), 'D2 static boundary is absent')
        private, proxy = private.read_text(), proxy.read_text()
        self.assertIn('listen unix:/opt/hms/run/edge-static.sock;', private)
        self.assertIn('disable_symlinks on;', private)
        self.assertNotRegex(private, r'listen\s+\d')
        self.assertIn('proxy_pass http://hms_private_static;', proxy)
        self.assertIn('proxy_pass_request_headers off;', proxy)
        self.assertIn('proxy_cache off;', proxy)
        self.assertIn('proxy_set_header Range $http_range;', proxy)
        self.assertEqual(set(re.findall(r'proxy_set_header\s+(\S+)', proxy)), {'Host', 'Range', 'Content-Length'})
        self.assertNotIn('add_header', proxy)
        self.assertNotIn('proxy_method', proxy)

    def test_owned_group_cleanup_survives_exited_leader_and_is_not_repeated(self):
        runner = self.runner()
        validation = runner.Validation({}, ROOT)
        process = Mock(pid=987654)
        process.poll.return_value = 0
        validation.processes.append(process)
        signals = []

        def kill_group(pid, action):
            signals.append((pid, action))
            if action == 0:
                raise ProcessLookupError()

        with patch.object(runner.os, 'killpg', side_effect=kill_group, create=True), \
                patch.object(runner.signal, 'SIGCONT', 18, create=True):
            validation.stop(process)
            first = list(signals)
            validation.stop(process)
            self.assertEqual(first, signals)
        self.assertIn((process.pid, 18), signals)
        self.assertIn((process.pid, runner.signal.SIGTERM), signals)
    def test_tls_server_includes_guard_and_retains_security_headers(self):
        source = (ROOT / 'infra/hostinger/nginx.conf').read_text()
        self.assertIn('include /opt/hms/current/infra/edge/network-guard.conf;', source)
        for header in ('Strict-Transport-Security', 'Content-Security-Policy',
                       'X-Content-Type-Options', 'X-Frame-Options', 'Permissions-Policy'):
            self.assertIn(f'add_header {header}', source)
        self.assertNotIn('satisfy any', source)

    def test_ordinary_api_cannot_supply_probe_marker(self):
        source = (ROOT / 'infra/hostinger/proxy.conf').read_text()
        self.assertIn('proxy_set_header X-HMS-Network-Probe "";', source)
        self.assertIn('proxy_set_header X-Forwarded-For $remote_addr;', source)
        self.assertNotIn('$proxy_add_x_forwarded_for', source)

    def test_guard_private_fixed_probe_and_failclosed_policy(self):
        path = ROOT / 'infra/edge/network-guard.conf'
        self.assertTrue(path.exists(), 'Reusable network guard is missing')
        source = path.read_text()
        for directive in ('auth_request /_hms_network_check;', 'satisfy all;',
                          'location = /_hms_network_check {', 'internal;', 'auth_request off;',
                          'auth_basic off;', 'proxy_pass_request_body off;',
                          'proxy_pass_request_headers off;', 'proxy_method GET;',
                          'proxy_set_header Content-Length "";',
                          'proxy_set_header X-HMS-Network-Probe "1";',
                          'proxy_connect_timeout 1s;', 'proxy_read_timeout 3s;',
                          'proxy_next_upstream off;', 'proxy_cache off;', 'proxy_store off;',
                          'proxy_pass http://127.0.0.1:8185/api/v1/network-policy/edge-probe/;'):
            self.assertIn(directive, source)
        self.assertRegex(source, r'location = /api/v1/network-policy/edge-probe/\s*\{\s*return 404;\s*\}')
        self.assertNotIn('error_page', source)
        # Only the frozen allowlist of request headers may enter the internal probe.
        headers = set(re.findall(r'proxy_set_header\s+(\S+)', source))
        self.assertEqual(headers, {'Host', 'X-Forwarded-Proto', 'X-Forwarded-For',
                                 'X-Real-IP', 'X-HMS-Network-Probe', 'Content-Length'})

    def test_guard_disables_protected_static_revalidation(self):
        path = ROOT / 'infra/edge/network-guard.conf'
        self.assertTrue(path.exists(), 'Reusable network guard is missing')
        source = path.read_text()
        self.assertIn('add_header Cache-Control "no-store" always;', source)
        self.assertIn('etag off;', source)
        self.assertIn('if_modified_since off;', source)


if __name__ == '__main__':
    unittest.main()
