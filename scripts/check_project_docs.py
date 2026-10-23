"""Fail closed on undocumented commits and broken repository Markdown links.

This checks synchronization and link existence, not the truth of implementation claims.
Use --links-only before a commit; use --base <previous-sha> for completed changes.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', 'dist', 'build', '.local',
            '.pytest_cache', '.mypy_cache', '.ruff_cache', '__pycache__', 'coverage'}
LIVING_DOCS = {'HMS.md', 'plan.md'}


def git(root, *arguments):
    result = subprocess.run(['git', '-C', str(root), *arguments], text=True,
                            capture_output=True, check=False, encoding='utf-8')
    if result.returncode:
        raise ValueError('Git check failed: ' + (result.stderr.strip() or 'unknown error'))
    return result.stdout


def check_commits(root, base, head):
    errors = []
    git(root, 'rev-parse', '--verify', base + '^{commit}')
    git(root, 'rev-parse', '--verify', head + '^{commit}')
    # CI pull-request merge commits are synthetic. Check the real source commits.
    commits = git(root, 'rev-list', '--reverse', '--no-merges', f'{base}..{head}').splitlines()
    for commit in commits:
        changed = set(filter(None, git(root, 'diff-tree', '--root', '--no-commit-id',
                                       '--name-only', '-r', commit).splitlines()))
        if not changed:
            continue
        missing = LIVING_DOCS - changed
        for document in LIVING_DOCS & changed:
            # A blank-line or whitespace edit is not a project-reference update.
            try:
                previous = git(root, 'show', f'{commit}^:{document}')
            except ValueError:
                previous = ''
            try:
                current = git(root, 'show', f'{commit}:{document}')
            except ValueError:
                current = ''
            if not current.strip() or ''.join(previous.split()) == ''.join(current.split()):
                missing.add(document)
        if missing:
            subject = git(root, 'show', '-s', '--format=%s', commit).strip()
            errors.append(f'{commit[:12]} {subject}: meaningful updates required in '
                          + ', '.join(sorted(missing)) + ' in the same commit.')
    return errors


def markdown_links(source):
    # Do not interpret planned code paths or fenced example Markdown as real links.
    source = re.sub(r'^\s*(```+|~~~+)[\s\S]*?^\s*\1\s*$', '', source, flags=re.MULTILINE)
    source = re.sub(r'`+[^`]*`+', '', source)
    inline = re.findall(r'!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)', source)
    definitions = re.findall(r'^\s*\[[^\]\n]+\]:\s*(<[^>]+>|\S+)', source, re.MULTILINE)
    return inline + definitions


def check_links(root):
    errors = []
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = [name for name in subdirectories if name not in EXCLUDED]
        for name in files:
            if not name.lower().endswith('.md'):
                continue
            path = Path(directory) / name
            for target in markdown_links(path.read_text(encoding='utf-8-sig')):
                target = target.strip('<>')
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                local = unquote(parts.path)
                destination = ((root / local.lstrip('/')) if local.startswith('/')
                               else (path.parent / local)).resolve()
                if not destination.is_relative_to(root) or not destination.exists():
                    errors.append(f'{path.relative_to(root)}: broken local link {target}')
    return errors


def check_api_mapping(root):
    """Check page-action coverage; schema validity is a separate OpenAPI validator gate."""
    # JSON is used as the YAML 1.2 subset to keep this gate dependency-free.
    contract = json.loads((root / 'docs/api/openapi-v1.yaml').read_text(encoding='utf-8'))
    mapping = json.loads((root / 'docs/api/page-actions-v1.json').read_text(encoding='utf-8'))
    operations = {}
    errors = []
    for path, methods in contract['paths'].items():
        for method, operation in methods.items():
            if method not in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}:
                continue
            identifier = operation.get('operationId')
            if not identifier or identifier in operations:
                errors.append(f'Unique operationId required for {method.upper()} {path}.')
            operations[identifier] = operation.get('x-permission', '')
    mapped = set()
    action_ids = set()
    for action in mapping['actions']:
        if not all(action.get(key) for key in ['id', 'page', 'action', 'operation_id']):
            errors.append('Page actions require id, page, action and operation_id.')
        if action.get('id') in action_ids:
            errors.append(f'Duplicate page action {action.get("id")}.')
        action_ids.add(action.get('id'))
        identifier = action.get('operation_id')
        if identifier not in operations:
            errors.append(f'Page action references unknown operation {identifier}.')
        elif action.get('permission', '') != operations[identifier]:
            errors.append(f'{identifier}: page action permission differs from API contract.')
        mapped.add(identifier)
    for identifier in operations.keys() - mapped:
        errors.append(f'{identifier}: missing page-action mapping.')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--base', default='HEAD^', help='exclusive start of commit range')
    parser.add_argument('--head', default='HEAD', help='inclusive end of commit range')
    parser.add_argument('--links-only', action='store_true', help='pre-commit link check only')
    parser.add_argument('--api-contract', action='store_true', help='check Phase A page-action coverage')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        errors = check_links(root)
        if args.api_contract:
            errors.extend(check_api_mapping(root))
        if not args.links_only:
            errors.extend(check_commits(root, args.base, args.head))
    except (ValueError, OSError, KeyError, TypeError) as error:
        errors = [str(error)]
    if errors:
        print('\n'.join(errors))
        return 1
    print('Project documentation checks passed.' +
          (' Commit synchronization was not checked (--links-only).' if args.links_only else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
