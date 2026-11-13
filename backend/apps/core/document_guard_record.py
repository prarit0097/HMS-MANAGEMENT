"""Bounded JSON facts only; no trusted observation or access authority."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from uuid import UUID


_FIELDS = {'version', 'installation_id', 'epoch', 'mode', 'reason',
           'recorded_at', 'manifest_sha256'}
_TIMESTAMP = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z')
_HASH = re.compile(r'[0-9a-f]{64}')


@dataclass(frozen=True)
class GuardRecordFacts:
    version: int
    installation_id: UUID
    epoch: UUID
    mode: str
    reason: str
    recorded_at: datetime
    manifest_sha256: str | None


def _invalid():
    raise ValueError('Invalid guard record.') from None


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _constant(_value):
    _invalid()


def _uuid(value):
    if type(value) is not str or len(value) != 36:
        _invalid()
    try:
        parsed = UUID(value)
    except ValueError:
        parsed = None
    if parsed is None or str(parsed) != value:
        _invalid()
    return parsed


def parse_guard_record(raw: bytes) -> GuardRecordFacts:
    """Decode canonical facts; even active+restore conveys no permission."""
    if type(raw) is not bytes or not 1 <= len(raw) <= 4096:
        _invalid()
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                           parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        value = None
    if type(value) is not dict or set(value) != _FIELDS:
        _invalid()
    if type(value['version']) is not int or value['version'] != 1:
        _invalid()
    installation = _uuid(value['installation_id'])
    epoch = _uuid(value['epoch'])
    if type(value['mode']) is not str or value['mode'] not in ('active', 'closed'):
        _invalid()
    if type(value['reason']) is not str or value['reason'] not in ('fresh', 'maintenance', 'restore'):
        _invalid()
    stamp = value['recorded_at']
    if type(stamp) is not str or _TIMESTAMP.fullmatch(stamp) is None:
        _invalid()
    try:
        recorded = datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
    except ValueError:
        recorded = None
    if recorded is None:
        _invalid()
    manifest = value['manifest_sha256']
    if manifest is not None and (type(manifest) is not str or _HASH.fullmatch(manifest) is None):
        _invalid()
    return GuardRecordFacts(1, installation, epoch, value['mode'], value['reason'],
                            recorded, manifest)
