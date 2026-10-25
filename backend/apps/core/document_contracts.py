"""Pure, bounded declarations for the planned patient-document metadata API.

These helpers provide no authentication, persistence, transport or file handling.
"""
import base64
import binascii
import datetime
import hashlib
import json
import re
import uuid


class DocumentContractError(Exception):
    def __init__(self, code: str, status: int, message: str):
        self.code = code
        self.status = status
        self.message = message
        super().__init__(message)


def _invalid():
    raise DocumentContractError('validation_error', 400, 'Check the highlighted details.') from None


def _reject_constant(_value):
    _invalid()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _scalar_string(value):
    if type(value) is not str or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        _invalid()


def _walk(value, depth=0):
    if type(value) is str:
        _scalar_string(value)
    elif type(value) in (dict, list):
        depth += 1
        if depth > 8:
            _invalid()
        if type(value) is dict:
            for key, item in value.items():
                _scalar_string(key)
                _walk(item, depth)
        else:
            for item in value:
                _walk(item, depth)


def _json_object(body):
    try:
        text = body.decode('utf-8', errors='strict')
        result = json.loads(text, object_pairs_hook=_object, parse_constant=_reject_constant)
        if type(result) is not dict:
            _invalid()
        _walk(result)
        return result
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        _invalid()


def _body(body):
    if type(body) is not bytes:
        _invalid()
    if len(body) > 4096:
        raise DocumentContractError('request_too_large', 413, 'This request is too large.') from None
    return _json_object(body)


def _shape(value, keys):
    if type(value) is not dict or set(value) != keys:
        _invalid()


def _integer(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        _invalid()
    return value


def _text(value, minimum, maximum, filename=False):
    _scalar_string(value)
    for char in value:
        point = ord(char)
        if (point < 32 or 127 <= point <= 159 or point in (0x061C, 0x200E, 0x200F)
                or 0x202A <= point <= 0x202E or 0x2066 <= point <= 0x2069):
            _invalid()
    result = value.strip()
    if not minimum <= len(result) <= maximum:
        _invalid()
    if filename and ('/' in result or '\\' in result or result in ('.', '..')):
        _invalid()
    return result


def _create(payload):
    _shape(payload, {'category', 'filename', 'media_type', 'size_bytes', 'sha256'})
    if type(payload['category']) is not str or payload['category'] != 'registration':
        _invalid()
    if type(payload['media_type']) is not str or payload['media_type'] not in ('image/jpeg', 'image/png'):
        _invalid()
    digest = payload['sha256']
    if type(digest) is not str or re.fullmatch('[0-9a-f]{64}', digest) is None:
        _invalid()
    return {'category': 'registration', 'filename': _text(payload['filename'], 1, 120, filename=True),
            'media_type': payload['media_type'], 'size_bytes': _integer(payload['size_bytes'], 10485760),
            'sha256': digest}


def _withdraw(payload):
    _shape(payload, {'expected_version', 'reason'})
    return {'expected_version': _integer(payload['expected_version'], 2147483647),
            'reason': _text(payload['reason'], 10, 500)}


def parse_create(body: bytes) -> dict:
    return _create(_body(body))


def parse_withdraw(body: bytes) -> dict:
    return _withdraw(_body(body))


def canonical_uuid(value: str) -> str:
    if type(value) is not str:
        _invalid()
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        _invalid()
    if str(parsed) != value:
        _invalid()
    return value


def _timestamp(value):
    if type(value) is not str or re.fullmatch(
            '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{6}Z', value) is None:
        _invalid()
    try:
        datetime.datetime(int(value[:4]), int(value[5:7]), int(value[8:10]),
                          int(value[11:13]), int(value[14:16]), int(value[17:19]), int(value[20:26]),
                          tzinfo=datetime.timezone.utc)
    except (ValueError, OverflowError):
        _invalid()
    return value


def encode_cursor(patient_id: str, created_at: str, document_id: str) -> str:
    cursor = {'v': 1, 'patient_id': canonical_uuid(patient_id), 'category': 'registration',
              'created_at': _timestamp(created_at), 'id': canonical_uuid(document_id)}
    data = json.dumps(cursor, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def _cursor(value, patient_id):
    if type(value) is not str or not 1 <= len(value) <= 512 or re.fullmatch('[A-Za-z0-9_-]+', value) is None:
        _invalid()
    try:
        data = base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)
    except (ValueError, binascii.Error):
        _invalid()
    result = _json_object(data)
    _shape(result, {'v', 'patient_id', 'category', 'created_at', 'id'})
    if type(result['v']) is not int or result['v'] != 1 or result['category'] != 'registration':
        _invalid()
    if result['patient_id'] != patient_id:
        _invalid()
    if encode_cursor(result['patient_id'], result['created_at'], result['id']) != value:
        _invalid()
    return result


def parse_list_query(pairs: list[tuple[str, str]] | tuple[tuple[str, str], ...], patient_id: str) -> dict:
    canonical_uuid(patient_id)
    if type(pairs) not in (list, tuple) or len(pairs) > 3:
        _invalid()
    query = {}
    for pair in pairs:
        if type(pair) is not tuple or len(pair) != 2 or any(type(item) is not str for item in pair):
            _invalid()
        key, value = pair
        if key not in ('limit', 'category', 'cursor') or key in query:
            _invalid()
        query[key] = value
    limit = 25
    if 'limit' in query:
        value = query['limit']
        # A three-digit ceiling also avoids invoking Python's large-integer conversion limit.
        if len(value) > 3 or re.fullmatch('[1-9][0-9]*', value) is None:
            _invalid()
        limit = _integer(int(value), 100)
    if 'category' in query and query['category'] != 'registration':
        _invalid()
    return {'limit': limit, 'category': 'registration',
            'cursor': _cursor(query['cursor'], patient_id) if 'cursor' in query else None}


def command_fingerprint(operation: str, patient_id: str, document_id: str | None, payload: dict) -> str:
    canonical_uuid(patient_id)
    if type(operation) is not str:
        _invalid()
    if operation == 'intent.create' and document_id is None:
        normalized = _create(payload)
    elif operation == 'intent.withdraw':
        canonical_uuid(document_id)
        normalized = _withdraw(payload)
    else:
        _invalid()
    preimage = {'operation': operation, 'patient_id': patient_id, 'document_id': document_id, 'payload': normalized}
    data = json.dumps(preimage, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
