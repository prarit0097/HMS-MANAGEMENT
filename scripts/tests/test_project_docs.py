"""Exercise documentation checks through their CLI against temporary Git repositories."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'check_project_docs.py'


class ProjectDocsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Synthetic Fixture')
        self.write('HMS.md', '# HMS\n\nInitial state.\n')
        self.write('plan.md', '# Plan\n\nInitial tasks.\n')
        self.commit('baseline')
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *arguments):
        return subprocess.run(['git', '-C', str(self.root), *arguments], check=True,
                              capture_output=True, text=True).stdout

    def write(self, path, content):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding='utf-8')

    def commit(self, subject):
        self.git('add', '.')
        self.git('commit', '-qm', subject)

    def check(self, *arguments):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root),
                               *arguments], capture_output=True, text=True)

    def test_changed_source_requires_both_living_documents_in_same_commit(self):
        self.write('backend/new.py', 'value = 1\n')
        self.commit('source without reference updates')
        result = self.check('--base', self.base)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('HMS.md', result.stdout)
        self.assertIn('plan.md', result.stdout)

    def test_source_with_both_document_updates_passes(self):
        self.write('backend/new.py', 'value = 1\n')
        self.write('HMS.md', '# HMS\n\nImplemented new value with no permissions change.\n')
        self.write('plan.md', '# Plan\n\n- [x] New value implemented and checked.\n')
        self.commit('coherent source and docs')
        result = self.check('--base', self.base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_later_doc_commit_does_not_hide_undocumented_source_commit(self):
        self.write('frontend/new.ts', 'export const version = 1;\n')
        self.commit('undocumented source')
        self.write('HMS.md', '# HMS\n\nLater docs.\n')
        self.write('plan.md', '# Plan\n\nLater plan.\n')
        self.commit('later docs')
        result = self.check('--base', self.base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('undocumented source', result.stdout)

    def test_whitespace_only_doc_changes_do_not_satisfy_gate(self):
        self.write('backend/new.py', 'value = 1\n')
        self.write('HMS.md', '# HMS\n\nInitial state.\n\n')
        self.write('plan.md', '# Plan\n\nInitial tasks.   \n')
        self.commit('source with cosmetic doc edits')
        result = self.check('--base', self.base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_checks_real_links_but_not_future_paths_inside_code(self):
        self.write('docs/guide.md', '[Reference](../HMS.md#status)\n`backend/future.py`\n'
                   '```markdown\n[example](future-file.md)\n```\n')
        result = self.check('--links-only')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write('docs/guide.md', '[Missing](missing.md)\n')
        result = self.check('--links-only')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('docs/guide.md', result.stdout.replace('\\', '/'))
        self.assertIn('missing.md', result.stdout)

    def test_reference_and_escaped_space_links_are_checked(self):
        self.write('docs/file with spaces.md', '# Existing\n')
        self.write('README.md', '[Existing](docs/file%20with%20spaces.md)\n'
                   '[Guide][guide]\n\n[guide]: docs/missing.md\n')
        result = self.check('--links-only')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('docs/missing.md', result.stdout)
        self.assertNotIn('file%20with%20spaces.md', result.stdout)

    def test_ignores_dependency_and_environment_markdown(self):
        for directory in ['node_modules', '.venv', 'venv', '.git', 'dist']:
            self.write(f'{directory}/guide.md', '[missing](not-present.md)\n')
        self.write('README.md', '[External](https://example.invalid/not-downloaded)\n')
        result = self.check('--links-only')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_git_base_fails_instead_of_skipping_change_gate(self):
        result = self.check('--base', 'missing-ref')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Git', result.stdout)

    def contract_fixture(self, actions):
        self.write('docs/api/openapi-v1.yaml', json.dumps({'paths': {'/patients/': {'get': {
            'operationId': 'listPatients', 'x-permission': 'patients.read'}}}}))
        self.write('docs/api/page-actions-v1.json', json.dumps({'actions': actions}))

    def test_contract_requires_page_action_mapping_for_each_operation(self):
        self.contract_fixture([])
        result = self.check('--links-only', '--api-contract')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('listPatients', result.stdout)

    def test_mapping_rejects_unknown_operation_and_wrong_permission(self):
        self.contract_fixture([{'id': 'R01.search', 'page': 'R01', 'action': 'Search',
                               'operation_id': 'listPatients', 'permission': 'patients.write'},
                              {'id': 'R01.delete', 'page': 'R01', 'action': 'Delete',
                               'operation_id': 'deletePatient', 'permission': 'patients.write'}])
        result = self.check('--links-only', '--api-contract')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('permission', result.stdout)
        self.assertIn('deletePatient', result.stdout)

    def test_valid_page_action_mapping_passes(self):
        self.contract_fixture([{'id': 'R01.search', 'page': 'R01', 'action': 'Search',
                               'operation_id': 'listPatients', 'permission': 'patients.read'}])
        result = self.check('--links-only', '--api-contract')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
