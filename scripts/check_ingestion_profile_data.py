"""Validate synthetic repository documentation, never runtime launch authority."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path('docs/implementation/schemas/ingestion-profile-data-v1.schema.json')
CATALOGUE_PATH = Path('docs/implementation/fixtures/ingestion-profile-data-v1.json')
KINDS = {'root_profile': 'rootProfile', 'supervisor_projection': 'avctlProjection',
         'launch_record': 'launchRecord'}
AVCTL = 'hms-ingest-avctl'
MEMBERS = {
    'hms-preview': ('guard-read',),
    'hms-ingest-bytes': ('guard-read', 'object-read'),
    'hms-ingest-work': ('guard-read', 'object-read', 'scan-ipc'),
    AVCTL: ('guard-read', 'scan-ipc', 'av-ipc', 'signature-read'),
    'hms-ingest-av': ('av-ipc', 'signature-read'),
    'hms-ingest-image': (), 'hms-ingest-update': (),
}


class DataValidationError(ValueError):
    def __init__(self):
        super().__init__('Invalid documentation contract data.')


def _fail(*unused):
    raise DataValidationError()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _canonical(raw, limit):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        _fail()
    value = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs,
                       parse_float=_fail, parse_constant=_fail)
    if type(value) is not dict or _encode(value) != raw:
        _fail()
    return value


def _validators(schema):
    if type(schema) is not dict or schema.get('$schema') != 'https://json-schema.org/draft/2020-12/schema':
        _fail()
    definitions = schema.get('$defs')
    if type(definitions) is not dict or not set(KINDS.values()) <= definitions.keys():
        _fail()

    def inspect(value, depth=0):
        if depth > 64:
            _fail()
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ('$dynamicRef', '$recursiveRef') or (depth and key in ('$id', '$schema')):
                    _fail()
                if key == '$ref':
                    if not isinstance(child, str) or not re.fullmatch(r'#\/\$defs\/[A-Za-z][A-Za-z0-9_]*', child):
                        _fail()
                    if child.removeprefix('#/$defs/') not in definitions:
                        _fail()
                inspect(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                inspect(child, depth + 1)

    inspect(schema)
    Draft202012Validator.check_schema(schema)
    # Drop the document's identifier/base scope: every supported reference is local.
    return {kind: Draft202012Validator({'$defs': definitions, '$ref': '#/$defs/' + name})
            for kind, name in KINDS.items()}


def _validate(profile_raw, projection_raw, launch_raw, validators):
    profile, own, launch = [_canonical(raw, limit) for raw, limit in
                            zip((profile_raw, projection_raw, launch_raw), (8192, 2048, 2048))]
    for kind, value in zip(KINDS, (profile, own, launch)):
        if not validators[kind].is_valid(value):
            _fail()
    groups, services = profile['groups'], profile['services']
    if len(set(groups.values())) != 12 or len({v['uid'] for v in services.values()}) != 7:
        _fail()
    for role, suffixes in MEMBERS.items():
        identity = services[role]
        expected = sorted(groups['hms-ingest-' + name] for name in suffixes)
        if identity['primary_gid'] != groups[role] or identity['supplementary_gids'] != expected:
            _fail()
    projected = {
        'version': 1, 'service': AVCTL, 'source_profile_sha256': sha256(profile_raw).hexdigest(),
        'installation_id': profile['installation_id'], 'host': profile['host'],
        'identity': services[AVCTL],
        'peer_uids': {role: services[role]['uid'] for role in ('hms-ingest-work', 'hms-ingest-av')},
        'execution': profile['execution'][AVCTL],
    }
    if projection_raw != _encode(projected):
        _fail()
    expected = {'installation_id': profile['installation_id'], 'boot_id': profile['host']['boot_id'],
                'uid': own['identity']['uid'], 'gid': own['identity']['primary_gid'],
                'supplementary_gids': own['identity']['supplementary_gids'],
                'unit': own['execution']['unit'], 'cgroup': own['execution']['cgroup']}
    if any(launch[key] != value for key, value in expected.items()):
        _fail()
    if any(launch['namespaces'][key] != value for key, value in profile['host']['namespaces'].items()):
        _fail()
    # PID/start/mount/manifest/epoch facts cannot be authenticated by this developer tool.


def validate_bundle(profile_raw, projection_raw, launch_raw, schema):
    """Reject inconsistent documentation bytes; return no grant or authority object."""
    try:
        _validate(profile_raw, projection_raw, launch_raw, _validators(schema))
    except Exception:
        raise DataValidationError() from None


def _read(root, relative, limit):
    root = Path(root).resolve(strict=True)
    current = root
    for part in relative.parts:
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            _fail()
        if current != root / relative and not stat.S_ISDIR(info.st_mode):
            _fail()
    if not stat.S_ISREG(info.st_mode) or not current.resolve(strict=True).is_relative_to(root):
        _fail()
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(current, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            _fail()
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        if not 0 < len(raw) <= limit:
            _fail()
        return raw
    finally:
        os.close(fd)


def _artifact(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_fail)


def _catalogue(root):
    schema = _artifact(_read(root, SCHEMA_PATH, 65536))
    data = _artifact(_read(root, CATALOGUE_PATH, 262144))
    validators = _validators(schema)
    if data['synthetic_only'] is not True or set(data['bases']) != set(KINDS):
        _fail()
    report = dict(status='passed', structural_cases=0, structural_rejections=0,
                  semantic_cases=0, semantic_rejections=0, wire_examples=0,
                  wire_rejections=0, authority_checks=0)
    cases, wires = data['cases'], data['wire_limit_cases']
    if type(cases) is not list or not 1 <= len(cases) <= 1000 or type(wires) is not list or not 1 <= len(wires) <= 1000:
        _fail()
    identifiers = set()
    for case in cases:
        if type(case['id']) is not str or case['id'] in identifiers:
            _fail()
        identifiers.add(case['id'])
        kind = case['kind']
        if kind not in KINDS or type(case['valid']) is not bool or type(case['semantic_valid']) is not bool:
            _fail()
        values = deepcopy(data['bases'])
        for edit in case['patch']:
            keys = edit['path'].split('/')[1:]
            if not edit['path'].startswith('/') or not keys:
                _fail()
            target = values[kind]
            for key in keys[:-1]:
                target = target[key]
            if edit['op'] == 'remove':
                del target[keys[-1]]
            elif edit['op'] == 'set':
                target[keys[-1]] = edit['value']
            else:
                _fail()
        actual = validators[kind].is_valid(values[kind])
        if actual != case['valid']:
            _fail()
        try:
            _validate(*(_encode(values[kind]) for kind in KINDS), validators)
            semantic = True
        except Exception:
            semantic = False
        if semantic != case['semantic_valid']:
            _fail()
        report['structural_cases'] += 1
        report['structural_rejections'] += not actual
        report['semantic_cases'] += 1
        report['semantic_rejections'] += not semantic
    for case in wires:
        if case['kind'] != 'launch_record' or type(case['valid']) is not bool or type(case['semantic_valid']) is not bool:
            _fail()
        actual = validators['launch_record'].is_valid(json.loads(case['raw']))
        if actual != case['valid']:
            _fail()
        try:
            _validate(_encode(data['bases']['root_profile']), _encode(data['bases']['supervisor_projection']),
                      case['raw'].encode('ascii'), validators)
            semantic = True
        except Exception:
            semantic = False
        if semantic != case['semantic_valid']:
            _fail()
        report['wire_examples'] += 1
        report['wire_rejections'] += not semantic
    return report


def check_catalogue(root):
    try:
        return _catalogue(root)
    except Exception:
        raise DataValidationError() from None


class _Arguments(argparse.ArgumentParser):
    def error(self, message):
        _fail()


def main(argv=None):
    try:
        parser = _Arguments(description=__doc__)
        parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
        args = parser.parse_args(argv)
        result = check_catalogue(args.root)
    except Exception:
        print(json.dumps({'status': 'failed', 'code': 'invalid_contract_data'}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
