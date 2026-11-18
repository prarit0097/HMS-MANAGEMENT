"""Check synthetic documentation consistency without creating runtime authority."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import check_ingestion_profile_data as checker

SCHEMA_PATH = Path('docs/implementation/schemas/ingestion-profile-data-v1.schema.json')
CATALOGUE_PATH = Path('docs/implementation/fixtures/ingestion-profile-data-v1.json')
SCHEMA = json.loads((ROOT / SCHEMA_PATH).read_text(encoding='utf-8'))
CATALOGUE = json.loads((ROOT / CATALOGUE_PATH).read_text(encoding='utf-8'))
BASES = CATALOGUE['bases']


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def projection(profile):
    """Independent oracle for the published ProjectAvctl data mapping."""
    return {
        'version': 1,
        'service': 'hms-ingest-avctl',
        'source_profile_sha256': sha256(raw(profile)).hexdigest(),
        'installation_id': profile['installation_id'],
        'host': deepcopy(profile['host']),
        'identity': deepcopy(profile['services']['hms-ingest-avctl']),
        'peer_uids': {
            'hms-ingest-work': profile['services']['hms-ingest-work']['uid'],
            'hms-ingest-av': profile['services']['hms-ingest-av']['uid'],
        },
        'execution': deepcopy(profile['execution']['hms-ingest-avctl']),
    }


def coherent(profile=None):
    profile = deepcopy(profile if profile is not None else BASES['root_profile'])
    own = projection(profile)
    launch = deepcopy(BASES['launch_record'])
    launch.update(
        installation_id=profile['installation_id'], boot_id=profile['host']['boot_id'],
        uid=own['identity']['uid'], gid=own['identity']['primary_gid'],
        supplementary_gids=deepcopy(own['identity']['supplementary_gids']),
        unit=own['execution']['unit'], cgroup=own['execution']['cgroup'],
    )
    for name in ('user', 'pid', 'cgroup'):
        launch['namespaces'][name] = profile['host']['namespaces'][name]
    return profile, own, launch


class IngestionProfileDataTests(unittest.TestCase):
    def validate(self, bundle=None, schema=None):
        return checker.validate_bundle(*(raw(value) for value in (bundle or coherent())),
                                       deepcopy(SCHEMA) if schema is None else schema)

    def rejected(self, bundle=None, schema=None):
        with self.assertRaises(ValueError) as caught:
            self.validate(bundle, schema)
        return str(caught.exception)

    def temporary_catalogue(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for relative in (SCHEMA_PATH, CATALOGUE_PATH):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / relative).read_bytes())
        return root

    def cli(self, root, timeout=None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / 'check_ingestion_profile_data.py'),
            '--root', str(root)], capture_output=True, text=True, check=False,
            timeout=timeout,
        )

    def test_coherent_bundle_returns_no_authority(self):
        self.assertIsNone(self.validate())

    def test_noncanonical_wire_is_rejected_for_each_document(self):
        documents = [raw(value) for value in coherent()]
        for index, original in enumerate(documents):
            mutations = [b' ' + original, original + b'\n', b'\xef\xbb\xbf' + original,
                         original.replace(b'"version":1', b'"version":1,"version":1'),
                         original.replace(b'"version":1', b'"version":1.0'),
                         original.replace(b'"version":1', b'"version":1e0'),
                         original.replace(b'"version":1', b'"version":NaN'),
                         original.replace(b'"version":1', b'"version":Infinity'),
                         original.replace(b'"version"', b'"\\u0076ersion"'),
                         json.dumps(json.loads(original), sort_keys=False, indent=1).encode()]
            for mutation in mutations:
                with self.subTest(document=index, wire=mutations.index(mutation)):
                    supplied = documents.copy()
                    supplied[index] = mutation
                    with self.assertRaises(ValueError):
                        checker.validate_bundle(*supplied, deepcopy(SCHEMA))

    def test_negative_zero_and_non_ascii_are_rejected(self):
        profile, own, launch = coherent()
        encoded = raw(launch)
        for changed in (encoded.replace(b'"start_ticks":56789', b'"start_ticks":-0'),
                        encoded.replace(b'"version":1', b'"version":\xff')):
            with self.assertRaises(ValueError):
                checker.validate_bundle(raw(profile), raw(own), changed, deepcopy(SCHEMA))

    def test_raw_byte_limits_reject_before_unbounded_parsing(self):
        documents = [raw(value) for value in coherent()]
        for index, limit in enumerate((8192, 2048, 2048)):
            for bad in (b'', b' ' * (limit + 1)):
                with self.subTest(document=index, length=len(bad)):
                    supplied = documents.copy()
                    supplied[index] = bad
                    with self.assertRaises(ValueError):
                        checker.validate_bundle(*supplied, deepcopy(SCHEMA))

    def test_deep_json_recursion_becomes_generic_validation_failure(self):
        _, own, launch = coherent()
        with self.assertRaises(ValueError):
            checker.validate_bundle(b'[' * 1500 + b'0' + b']' * 1500,
                                    raw(own), raw(launch), deepcopy(SCHEMA))

    def test_distinct_role_uids_checked_with_correct_rederived_hash(self):
        profile = deepcopy(BASES['root_profile'])
        profile['services']['hms-ingest-image']['uid'] = profile['services']['hms-ingest-update']['uid']
        self.rejected(coherent(profile))

    def test_named_gid_alias_checked_with_consistent_primary_mapping(self):
        profile = deepcopy(BASES['root_profile'])
        gid = profile['groups']['hms-ingest-guard-read']
        profile['groups']['hms-ingest-image'] = gid
        profile['services']['hms-ingest-image']['primary_gid'] = gid
        self.rejected(coherent(profile))

    def test_primary_gid_and_exact_supplementary_membership(self):
        for mode in ('wrong-primary', 'wrong-member', 'unsorted'):
            profile = deepcopy(BASES['root_profile'])
            identity = profile['services']['hms-ingest-bytes']
            if mode == 'wrong-primary':
                identity['primary_gid'] = profile['groups']['hms-ingest-image']
            elif mode == 'wrong-member':
                identity['supplementary_gids'] = sorted([
                    profile['groups']['hms-ingest-object-read'],
                    profile['groups']['hms-ingest-signature-read'],
                ])
            else:
                identity['supplementary_gids'].reverse()
            with self.subTest(mode=mode):
                self.rejected(coherent(profile))

    def test_every_projection_copy_and_raw_source_hash_are_checked(self):
        for field in ('source_profile_sha256', 'installation_id', 'host',
                      'identity', 'peer_uids', 'execution'):
            bundle = list(coherent())
            own = bundle[1]
            if field == 'source_profile_sha256':
                own[field] = 'd' * 64
            elif field == 'installation_id':
                own[field] = '99999999-9999-4999-8999-999999999999'
            elif field == 'host':
                own[field]['namespaces']['user'] += 1
            elif field == 'identity':
                own[field]['uid'] += 100
            elif field == 'peer_uids':
                own[field]['hms-ingest-work'] = own['identity']['uid']
            else:
                own[field]['mount_policy'] = 'host'
            with self.subTest(field=field):
                self.rejected(tuple(bundle))

    def test_launch_copies_match_projection_and_profile(self):
        for field in ('installation_id', 'boot_id', 'uid', 'gid',
                      'supplementary_gids', 'unit', 'cgroup', 'namespaces'):
            bundle = list(coherent())
            launch = bundle[2]
            if field in ('installation_id', 'boot_id'):
                launch[field] = '99999999-9999-4999-8999-999999999999'
            elif field in ('uid', 'gid'):
                launch[field] += 100
            elif field == 'supplementary_gids':
                launch[field] = list(reversed(launch[field]))
            elif field == 'namespaces':
                launch[field]['cgroup'] += 1
            elif field == 'unit':
                launch[field] = 'another.service'
            else:
                launch[field] = '/system.slice/another.service'
            with self.subTest(field=field):
                self.rejected(tuple(bundle))

    def test_coherent_forged_os_facts_are_not_authenticated(self):
        profile, own, launch = coherent()
        launch.update(pid=2147483647, start_ticks=0,
                      runtime_manifest_sha256='f' * 64,
                      restore_epoch='99999999-9999-4999-8999-999999999999',
                      supervisor_launch_instance='88888888-8888-4888-8888-888888888888')
        launch['namespaces']['mnt'] = 18446744073709551615
        self.assertIsNone(self.validate((profile, own, launch)))

    def test_schema_rejects_resolution_overrides_without_network(self):
        bad_schemas = []
        for keyword, target in (('$ref', 'https://private.invalid/secret'),
                                ('$ref', 'file:///private/secret'),
                                ('$dynamicRef', '#/$defs/rootProfile'),
                                ('$recursiveRef', '#/$defs/rootProfile'),
                                ('$id', 'https://private.invalid/scope'),
                                ('$schema', 'https://private.invalid/meta')):
            schema = deepcopy(SCHEMA)
            schema['$defs']['unreferenced_override'] = {keyword: target}
            bad_schemas.append(schema)
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')) as fetch:
            for schema in bad_schemas:
                with self.subTest(schema=len(bad_schemas)):
                    self.rejected(schema=schema)
            fetch.assert_not_called()

    def test_schema_recursion_is_bounded_failure(self):
        schema = deepcopy(SCHEMA)
        schema['$defs']['rootProfile'] = {'$ref': '#/$defs/rootProfile'}
        self.rejected(schema=schema)

    def test_failures_do_not_reflect_values_or_low_level_paths(self):
        messages = []
        for secret in ('DO_NOT_ECHO_SYNTHETIC_SECRET', '/private/DO_NOT_ECHO'):
            profile, own, launch = coherent()
            own['secret'] = secret
            messages.append(self.rejected((profile, own, launch)))
            self.assertNotIn(secret, messages[-1])
        self.assertEqual(messages[0], messages[1])

    def test_real_catalogue_report_is_closed_and_has_no_authority(self):
        report = checker.check_catalogue(ROOT)
        self.assertEqual(set(report), {'status', 'structural_cases', 'structural_rejections',
                                     'semantic_cases', 'semantic_rejections', 'wire_examples',
                                     'wire_rejections', 'authority_checks'})
        self.assertNotEqual(report['status'], 'failed')
        for key, expected in {'structural_cases': 71, 'structural_rejections': 55,
                              'semantic_cases': 71, 'semantic_rejections': 63,
                              'wire_examples': 5, 'wire_rejections': 5,
                              'authority_checks': 0}.items():
            self.assertEqual(report[key], expected, key)

    def test_catalogue_semantic_expectations_cannot_be_silently_ignored(self):
        root = self.temporary_catalogue()
        data = json.loads((root / CATALOGUE_PATH).read_text(encoding='utf-8'))
        data['cases'][0]['semantic_valid'] = False
        (root / CATALOGUE_PATH).write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            checker.check_catalogue(root)

    def test_fixed_document_reads_are_bounded(self):
        for relative, limit in ((SCHEMA_PATH, 65536), (CATALOGUE_PATH, 262144)):
            root = self.temporary_catalogue()
            (root / relative).write_bytes(b' ' * (limit + 1))
            with self.subTest(path=relative):
                with self.assertRaises(ValueError):
                    checker.check_catalogue(root)

    def test_fixed_inputs_cannot_escape_through_symlink(self):
        root = self.temporary_catalogue()
        outside = root / 'outside-schema.json'
        outside.write_bytes((root / SCHEMA_PATH).read_bytes())
        target = root / SCHEMA_PATH
        target.unlink()
        try:
            target.symlink_to(outside)
        except OSError:
            self.skipTest('Platform cannot create a synthetic symlink.')
        with self.assertRaises(ValueError):
            checker.check_catalogue(root)

    def test_fixed_input_ancestor_cannot_link_outside_selected_root(self):
        root = self.temporary_catalogue()
        outside_directory = tempfile.TemporaryDirectory()
        self.addCleanup(outside_directory.cleanup)
        outside = Path(outside_directory.name)
        self.assertFalse(outside.resolve().is_relative_to(root.resolve()))
        target = root / SCHEMA_PATH
        (outside / target.name).write_bytes(target.read_bytes())
        target.unlink()
        target.parent.rmdir()
        try:
            target.parent.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Platform cannot create a synthetic directory symlink.')
        with self.assertRaises(ValueError):
            checker.check_catalogue(root)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'Platform has no POSIX FIFO primitive.')
    def test_nonregular_fifo_is_rejected_with_bounded_cli(self):
        root = self.temporary_catalogue()
        target = root / SCHEMA_PATH
        target.unlink()
        os.mkfifo(target, 0o600)
        result = self.cli(root, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout), {
            'status': 'failed', 'code': 'invalid_contract_data',
        })
        self.assertEqual(result.stderr, '')

    def test_cli_success_and_fixed_private_failure(self):
        success = self.cli(ROOT)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(success.stdout), checker.check_catalogue(ROOT))
        root = self.temporary_catalogue()
        (root / CATALOGUE_PATH).write_text('{"DO_NOT_ECHO_SECRET":', encoding='utf-8')
        failure = self.cli(root)
        self.assertEqual(failure.returncode, 1)
        output = failure.stdout + failure.stderr
        self.assertNotIn('DO_NOT_ECHO_SECRET', output)
        self.assertNotIn(str(root), output)
        self.assertNotIn('Traceback', output)
        parsed = json.loads(output)
        self.assertEqual(parsed, {'status': 'failed', 'code': 'invalid_contract_data'})


if __name__ == '__main__':
    unittest.main()
