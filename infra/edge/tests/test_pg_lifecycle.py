"""Ownership/partial-create regressions; no Docker or database is called here."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]


class PgLifecycleOwnership(unittest.TestCase):
    def helper(self):
        path = ROOT / 'infra/edge/tests/prepare_isolated_pg.py'
        self.assertTrue(path.exists(), 'Dedicated PG lifecycle helper is absent')
        spec = importlib.util.spec_from_file_location('edge_pg', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def examples(self, helper):
        receipt = helper.new_receipt()
        receipt['container_id'] = 'synthetic-container-id'
        receipt['network_id'] = 'synthetic-network-id'
        network = {'Id': receipt['network_id'], 'Name': helper.NETWORK,
                   'Labels': helper.labels(receipt), 'Containers': {}}
        container = {'Id': receipt['container_id'], 'Name': '/' + helper.CONTAINER,
            'Image': helper.IMAGE_ID, 'Config': {'Labels': helper.labels(receipt)},
            'Mounts': helper.expected_mounts(), 'HostConfig': {
                'PortBindings': {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '15549'}]},
                'NetworkMode': helper.NETWORK}}
        return receipt, network, container

    def test_exact_owned_resource_is_accepted(self):
        helper = self.helper()
        receipt, network, container = self.examples(helper)
        helper.validate_resource(receipt, network, 'network')
        helper.validate_resource(receipt, container, 'container')

    def test_partial_create_recovers_only_matching_unique_run(self):
        helper = self.helper()
        receipt, network, container = self.examples(helper)
        receipt['container_id'] = None  # Crash after create before recording returned ID.
        helper.validate_resource(receipt, container, 'container')
        for mutate in ('token', 'mount', 'port', 'image', 'id'):
            altered_receipt, altered = copy.deepcopy(receipt), copy.deepcopy(container)
            if mutate == 'token':
                altered['Config']['Labels']['hms.validation.run'] = 'foreign'
            elif mutate == 'mount':
                altered['Mounts'][0]['Source'] = '/opt/hms/data/postgres'
            elif mutate == 'port':
                altered['HostConfig']['PortBindings']['5432/tcp'][0]['HostIp'] = '0.0.0.0'
            elif mutate == 'image':
                altered['Image'] = 'foreign-image'
            else:
                altered_receipt['container_id'] = 'stale-receipt-id'
            with self.assertRaises(ValueError, msg=mutate):
                helper.validate_resource(altered_receipt, altered, 'container')

    def test_stale_network_or_unowned_receipt_is_rejected(self):
        helper = self.helper()
        receipt, network, container = self.examples(helper)
        for changed in ({**network, 'Id': 'foreign-id'}, {**network, 'Labels': {}},
                        {**network, 'Name': 'shared-network'}, {**network, 'Containers': {'other': {}}}):
            with self.assertRaises(ValueError):
                helper.validate_resource(receipt, changed, 'network')
        with self.assertRaises(ValueError):
            helper.validate_resource({**receipt, 'prefix': '/opt/hms'}, container, 'container')

    def test_down_refuses_renamed_recorded_id_before_any_mutation(self):
        helper = self.helper()
        receipt, network, container = self.examples(helper)
        container['Name'] = '/renamed-owned-container'
        lifecycle = helper.Lifecycle()
        lifecycle.require_paths = Mock()
        lifecycle.save = Mock()
        lifecycle.command = Mock()
        lifecycle.inspect = Mock(side_effect=lambda kind, identity: container
                                 if kind == 'container' and identity == receipt['container_id'] else None)
        with patch.object(helper.Path, 'read_text', return_value=__import__('json').dumps(receipt)), \
                patch.object(helper.Path, 'stat', return_value=Mock(st_uid=0, st_mode=0o600)), \
                patch.object(helper.Path, 'is_symlink', return_value=False), \
                patch.object(helper.shutil, 'rmtree') as remove:
            with self.assertRaises(ValueError):
                lifecycle.down()
            lifecycle.command.assert_not_called()
            remove.assert_not_called()
        self.assertEqual(lifecycle.inspect.call_args_list[0].args, ('container', receipt['container_id']))

    def test_down_refuses_foreign_named_resource_when_recorded_id_absent(self):
        helper = self.helper()
        receipt, network, container = self.examples(helper)
        container['Id'] = 'different-container'
        container['Config']['Labels'] = {}
        lifecycle = helper.Lifecycle()
        lifecycle.require_paths = Mock()
        lifecycle.save = Mock()
        lifecycle.command = Mock()
        lifecycle.inspect = Mock(side_effect=lambda kind, identity: container
                                 if kind == 'container' and identity == helper.CONTAINER else None)
        with patch.object(helper.Path, 'read_text', return_value=__import__('json').dumps(receipt)), \
                patch.object(helper.Path, 'stat', return_value=Mock(st_uid=0, st_mode=0o600)), \
                patch.object(helper.Path, 'is_symlink', return_value=False), \
                patch.object(helper.shutil, 'rmtree') as remove:
            with self.assertRaises(ValueError):
                lifecycle.down()
            lifecycle.command.assert_not_called()
            remove.assert_not_called()
        self.assertEqual(lifecycle.inspect.call_args_list[0].args, ('container', receipt['container_id']))


if __name__ == '__main__':
    unittest.main()
