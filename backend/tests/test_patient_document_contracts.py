"""Pure declaration rules; synthetic values, deliberately no database fixture/mark."""
import base64
import copy
import importlib
import json

import pytest


P = '00000000-0000-0000-0000-000000000001'
D = '00000000-0000-0000-0000-000000000002'
T = '2024-02-29T12:34:56.123456Z'
CREATE = dict(category='registration', filename='sample.png', media_type='image/png',
              size_bytes=1, sha256='a' * 64)
WITHDRAW = dict(expected_version=1, reason='Wrong request')
CURSOR_JSON = ('{"v":1,"patient_id":"00000000-0000-0000-0000-000000000001",'
               '"category":"registration","created_at":"2024-02-29T12:34:56.123456Z",'
               '"id":"00000000-0000-0000-0000-000000000002"}')
CURSOR = ('eyJ2IjoxLCJwYXRpZW50X2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAx'
          'IiwiY2F0ZWdvcnkiOiJyZWdpc3RyYXRpb24iLCJjcmVhdGVkX2F0IjoiMjAyNC0wMi0yOVQx'
          'MjozNDo1Ni4xMjM0NTZaIiwiaWQiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDIifQ')
CONTROLS = list(range(32)) + list(range(127, 160)) + [0x61C, 0x200E, 0x200F] + list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A)) + [0xD800, 0xDFFF]


@pytest.fixture
def contract():
    # Import inside fixture leaves the installed pytest environment independently visible at RED.
    return importlib.import_module('apps.core.document_contracts')


def wire(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode()


def reject(contract, function, *args, large=False):
    with pytest.raises(contract.DocumentContractError) as caught:
        function(*args)
    error = caught.value
    expected = ('request_too_large', 413, 'This request is too large.') if large else (
        'validation_error', 400, 'Check the highlighted details.')
    assert (error.code, error.status, error.message) == expected
    assert str(error) == expected[2]
    assert 'PRIVATE_MARKER' not in str(error)
    assert error.__cause__ is None


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


@pytest.mark.parametrize('media,size', [('image/png', 1), ('image/jpeg', 10485760)])
def test_create_valid_normalizes_without_mutating(contract, media, size):
    payload = dict(CREATE, filename='\u2003 synthetic  name \u00a0', media_type=media, size_bytes=size)
    original = copy.deepcopy(payload)
    result = contract.parse_create(wire(payload))
    assert result == dict(payload, filename='synthetic  name')
    assert payload == original
    assert result is not payload
    assert contract.parse_create(wire(dict(CREATE, filename='noextension')))['filename'] == 'noextension'


@pytest.mark.parametrize('length', [4095, 4096, 4097])
def test_body_boundaries(contract, length):
    body = wire(CREATE)
    body += b' ' * (length - len(body))
    if length == 4097:
        reject(contract, contract.parse_create, body, large=True)
    else:
        assert contract.parse_create(body) == CREATE


@pytest.mark.parametrize('body', [b'\xff', b'\xef\xbb\xbf{}', '', None, {}, bytearray(b'{}'), memoryview(b'{}'), 4097])
def test_body_types_and_encoding(contract, body):
    reject(contract, contract.parse_create, body)
    reject(contract, contract.parse_withdraw, body)


@pytest.mark.parametrize('body', [b'{"filename":1,"filename":2}', b'{"a":{"x":1,"x":2}}',
    b'{"filename":1,"file\\u006eame":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
    b'[]', b'1', b'null', b'true', b'"PRIVATE_MARKER"', b'{}{}', b'{"x":"\\q"}', b'{"x":',
    b'{"x":' + b'1' * 4000 + b'}'])
def test_strict_json(contract, body):
    reject(contract, contract.parse_create, body)


@pytest.mark.parametrize('alias', ['filename', 'file\\u006eame'])
def test_duplicate_field_in_otherwise_valid_create(contract, alias):
    # Without decoded-key duplicate rejection this complete declaration would succeed.
    body = wire(CREATE)[:-1] + (',"' + alias + '":"other.png"}').encode()
    reject(contract, contract.parse_create, body)


def test_duplicate_field_in_otherwise_valid_withdraw(contract):
    reject(contract, contract.parse_withdraw, wire(WITHDRAW)[:-1] + b',"expected_version":2}')


@pytest.mark.parametrize('depth', [8, 9, 1500])
def test_depth_and_surrogates_nested_containers(contract, depth):
    body = b'{"x":' + b'[' * (depth - 1) + b'0' + b']' * (depth - 1) + b'}'
    reject(contract, contract.parse_create, body)


@pytest.mark.parametrize('body', [b'{"\\ud800":"x"}', b'{"x":["\\udfff"]}', b'{"x":{"y":"\\ud800"}}'])
def test_depth_and_surrogates_lone_recursive(contract, body):
    reject(contract, contract.parse_create, body)


def test_valid_surrogate_pair_is_one_scalar(contract):
    assert contract.parse_create(wire(dict(CREATE, filename='\U0001f600' * 120)))['filename'] == '\U0001f600' * 120
    assert contract.parse_withdraw(wire(dict(WITHDRAW, reason='\U0001f600' * 10)))['reason'] == '\U0001f600' * 10


@pytest.mark.parametrize('key', list(CREATE))
def test_create_missing_fields(contract, key):
    value = dict(CREATE)
    del value[key]
    reject(contract, contract.parse_create, wire(value))


@pytest.mark.parametrize('key', ['creator', 'status', 'version', 'created_at', 'branch', 'encounter', 'scanner', 'storage', 'file', 'Category'])
def test_create_extra_fields(contract, key):
    reject(contract, contract.parse_create, wire(dict(CREATE, **{key: 'PRIVATE_MARKER'})))


@pytest.mark.parametrize('key,value', [('size_bytes', x) for x in [True, False, 1.0, '1', 0, 10485761, None, []]] +
    [('sha256', x) for x in ['a' * 63, 'a' * 65, 'A' * 64, 'g' * 64, 'a' * 64 + '\n', None, []]] +
    [('media_type', x) for x in ['application/pdf', 'IMAGE/PNG', None, []]] +
    [('category', x) for x in ['clinical', 'Registration', None, []]] + [('filename', x) for x in [None, [], True, 12]])
def test_create_shape_and_numbers(contract, key, value):
    reject(contract, contract.parse_create, wire(dict(CREATE, **{key: value})))


@pytest.mark.parametrize('codepoint', CONTROLS)
@pytest.mark.parametrize('position', ['start', 'middle', 'end'])
def test_filename_controls_before_trim(contract, codepoint, position):
    char = chr(codepoint)
    value = {'start': char + 'safe', 'middle': 'sa' + char + 'fe', 'end': 'safe' + char}[position]
    reject(contract, contract.parse_create, wire(dict(CREATE, filename=value)))


@pytest.mark.parametrize('name', ['', ' ', '\u2003', '.', '..', ' ../ ', 'a/b', 'a\\b', 'x' * 121])
def test_filename_path_and_length(contract, name):
    reject(contract, contract.parse_create, wire(dict(CREATE, filename=name)))


def test_filename_codepoints_not_normalized(contract):
    name = 'e\u0301' * 60
    assert contract.parse_create(wire(dict(CREATE, filename=' ' + name + ' ')))['filename'] == name


@pytest.mark.parametrize('reason', ['x' * 10, 'x' * 500, ' path/to\\wrong request '])
@pytest.mark.parametrize('version', [1, 2147483647])
def test_withdraw_valid(contract, reason, version):
    assert contract.parse_withdraw(wire(dict(reason=reason, expected_version=version))) == dict(reason=reason.strip(), expected_version=version)


@pytest.mark.parametrize('value', [0, 2147483648, True, False, 1.0, '1', None, []])
def test_withdraw_version_validation(contract, value):
    reject(contract, contract.parse_withdraw, wire(dict(WITHDRAW, expected_version=value)))


@pytest.mark.parametrize('value', ['x' * 9, 'x' * 501, '', None, [], 10])
def test_withdraw_reason_validation(contract, value):
    reject(contract, contract.parse_withdraw, wire(dict(WITHDRAW, reason=value)))


@pytest.mark.parametrize('codepoint', CONTROLS)
@pytest.mark.parametrize('edge', [True, False])
def test_withdraw_controls_before_trim(contract, codepoint, edge):
    char = chr(codepoint)
    reason = char + 'Wrong request' if edge else 'Wrong request' + char
    reject(contract, contract.parse_withdraw, wire(dict(WITHDRAW, reason=reason)))


@pytest.mark.parametrize('value', [{}, {'reason': 'Wrong request'}, {'expected_version': 1}, dict(WITHDRAW, extra=1)])
def test_withdraw_exact_shape(contract, value):
    reject(contract, contract.parse_withdraw, wire(value))


def test_uuid_is_exact_canonical(contract):
    assert contract.canonical_uuid(P) == P
    assert contract.canonical_uuid('ffffffff-ffff-ffff-ffff-ffffffffffff') == 'ffffffff-ffff-ffff-ffff-ffffffffffff'


@pytest.mark.parametrize('value', ['AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA', '{' + P + '}', 'urn:uuid:' + P, P.replace('-', ''), ' ' + P, P + '\n', '/PRIVATE_MARKER', '', None, 1, True])
def test_uuid_aliases_rejected(contract, value):
    reject(contract, contract.canonical_uuid, value)


def test_query_defaults_and_bounds(contract):
    assert contract.parse_list_query([], P) == dict(limit=25, category='registration', cursor=None)
    for value in ['1', '100']:
        assert contract.parse_list_query((('limit', value), ('category', 'registration')), P) == dict(limit=int(value), category='registration', cursor=None)
    reject(contract, contract.parse_list_query, [], P.upper().replace('000000000001', 'AAAAAAAAAAAA'))


@pytest.mark.parametrize('value', ['0', '101', '01', '+1', ' 1', '1 ', '١', '１', '1e1', '1.0', '', '1\n', '9' * 5000])
def test_query_limit_aliases(contract, value):
    reject(contract, contract.parse_list_query, [('limit', value)], P)


@pytest.mark.parametrize('pairs', [{}, 'limit=1', b'', None, 1, [('limit', '1'), ('limit', '2')], [('x', '1')],
    [('category', '')], [('category', 'Registration')], [('cursor', '')], [('limit', 1)], [(1, '1')],
    [['limit', '1']], [('limit',)], [('limit', '1', '2')], [('limit', '1')] * 4])
def test_query_bounds_and_types(contract, pairs):
    reject(contract, contract.parse_list_query, pairs, P)


def test_query_generator_is_rejected(contract):
    reject(contract, contract.parse_list_query, iter([('limit', '1')]), P)


def test_cursor_golden_vector(contract):
    assert contract.encode_cursor(P, T, D) == CURSOR
    assert base64.urlsafe_b64decode(CURSOR + '==').decode() == CURSOR_JSON
    assert contract.parse_list_query([('cursor', CURSOR)], P) == dict(limit=25, category='registration', cursor=dict(v=1, patient_id=P, category='registration', created_at=T, id=D))


@pytest.mark.parametrize('timestamp', ['0001-01-01T00:00:00.000000Z', '9999-12-31T23:59:59.999999Z', T])
def test_cursor_calendar_valid(contract, timestamp):
    encoded = contract.encode_cursor(P, timestamp, D)
    assert contract.parse_list_query([('cursor', encoded)], P)['cursor']['created_at'] == timestamp


@pytest.mark.parametrize('timestamp', ['2023-02-29T12:34:56.123456Z', '2024-13-01T00:00:00.000000Z', '2024-04-31T00:00:00.000000Z',
    '0000-01-01T00:00:00.000000Z', '2024-01-01T24:00:00.000000Z', '2024-01-01T00:60:00.000000Z', '2024-01-01T00:00:60.000000Z',
    T.replace('.123456', '.1'), T.replace('.123456', ''), T.replace('Z', '+00:00'), T.lower(), T + ' ', T.replace('2', '２'), None, 1])
def test_cursor_calendar_invalid(contract, timestamp):
    reject(contract, contract.encode_cursor, P, timestamp, D)


@pytest.mark.parametrize('text', [CURSOR_JSON.replace('"v":1', '"v":true'), CURSOR_JSON.replace('"v":1', '"v":1.0'),
    CURSOR_JSON.replace('"v":1', '"v":1,"v":1'), CURSOR_JSON.replace('"v":1', '"v":1,"extra":0'),
    CURSOR_JSON.replace('"v":1,', ''), CURSOR_JSON.replace('{', '{ ', 1), CURSOR_JSON.replace('registration', '\\u0072egistration'),
    CURSOR_JSON.replace(P, D), CURSOR_JSON.replace('registration', 'clinical'), CURSOR_JSON.replace('2024-02-29', '2023-02-29'),
    CURSOR_JSON.replace('"v":1,', '')[:-1] + ',"v":1}', '{"x":NaN}', '{"x":"\\ud800"}', '[]'])
def test_cursor_canonical_json(contract, text):
    reject(contract, contract.parse_list_query, [('cursor', b64(text.encode()))], P)


@pytest.mark.parametrize('cursor', [CURSOR + '=', ' ' + CURSOR, CURSOR + '\n', '+', '/', '-' * 513, 'é', b'abc', b64(b'\xff'), CURSOR[:-1] + 'R'])
def test_cursor_canonical_base64(contract, cursor):
    reject(contract, contract.parse_list_query, [('cursor', cursor)], P)


def test_cursor_uppercase_uuid_is_not_canonical(contract):
    text = CURSOR_JSON.replace(D, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    valid = b64(text.encode())
    assert contract.parse_list_query([('cursor', valid)], P)['cursor']['id'] == 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    reject(contract, contract.parse_list_query, [('cursor', b64(text.replace('aaaaaaaa', 'AAAAAAAA').encode()))], P)


def test_fingerprint_golden_vectors(contract):
    # Independently checked compact sorted ASCII preimages: no helper-generated expectations.
    assert contract.command_fingerprint('intent.create', P, None, CREATE) == '0823b6218f5fd9e860b24dd83f3f53f63f6b46f447fb6eac55c98570b0bd0b51'
    assert contract.command_fingerprint('intent.withdraw', P, D, WITHDRAW) == 'c16607ddaf2b6be0f2c834cd5dd9106493fa9eadc6e3d835e672bbeb3af58d8f'
    reordered = dict(reversed(list(CREATE.items())))
    reordered['filename'] = '\u2003sample.png\u00a0'
    assert contract.command_fingerprint('intent.create', P, None, reordered) == '0823b6218f5fd9e860b24dd83f3f53f63f6b46f447fb6eac55c98570b0bd0b51'
    assert contract.command_fingerprint('intent.withdraw', P, D, dict(WITHDRAW, reason=' Wrong request ')) == 'c16607ddaf2b6be0f2c834cd5dd9106493fa9eadc6e3d835e672bbeb3af58d8f'


@pytest.mark.parametrize('operation,patient,document,payload', [('intent.create', D, None, CREATE), ('intent.create', P, None, dict(CREATE, sha256='b' * 64)),
    ('intent.withdraw', P, P, WITHDRAW), ('intent.withdraw', D, D, WITHDRAW), ('intent.withdraw', P, D, dict(WITHDRAW, reason='Other request')),
    ('intent.withdraw', P, D, dict(WITHDRAW, expected_version=2))])
def test_fingerprint_changed_command(contract, operation, patient, document, payload):
    golden = '0823b6218f5fd9e860b24dd83f3f53f63f6b46f447fb6eac55c98570b0bd0b51' if operation == 'intent.create' else 'c16607ddaf2b6be0f2c834cd5dd9106493fa9eadc6e3d835e672bbeb3af58d8f'
    assert contract.command_fingerprint(operation, patient, document, payload) != golden


@pytest.mark.parametrize('operation,patient,document,payload', [('bad', P, None, CREATE), (None, P, None, CREATE), ('intent.create', P, D, CREATE),
    ('intent.withdraw', P, None, WITHDRAW), ('intent.create', 'PRIVATE_MARKER', None, CREATE), ('intent.withdraw', P, 'PRIVATE_MARKER', WITHDRAW),
    ('intent.create', P, None, dict(CREATE, operation='intent.create')), ('intent.create', P, None, {}), ('intent.create', P, None, []),
    ('intent.create', P, None, dict(CREATE, size_bytes=True)), ('intent.withdraw', P, D, dict(WITHDRAW, expected_version=True)),
    ('intent.create', P, None, dict(CREATE, filename='\tPRIVATE_MARKER')), ('intent.withdraw', P, D, dict(WITHDRAW, reason='PRIVATE_MARKER\ud800'))])
def test_fingerprint_revalidates(contract, operation, patient, document, payload):
    reject(contract, contract.command_fingerprint, operation, patient, document, payload)


def test_fingerprint_unicode_expansion_and_no_mutation(contract):
    payload = dict(WITHDRAW, reason=' ' + '\U0001f600' * 500 + ' ')
    original = copy.deepcopy(payload)
    assert len(wire(payload)) > 4096
    result = contract.command_fingerprint('intent.withdraw', P, D, payload)
    assert len(result) == 64 and set(result) <= set('0123456789abcdef')
    assert payload == original
    # A UTF8 wire representation remains valid even when canonical ASCII expansion is larger.
    utf8 = json.dumps(payload, ensure_ascii=False).encode()
    assert len(utf8) < 4096
    normalized = contract.parse_withdraw(utf8)
    assert contract.command_fingerprint('intent.withdraw', P, D, normalized) == result


def test_fixed_errors_and_purity(contract):
    # All real helper calls run under pytest-django's unmarked no-query guard.
    error = contract.DocumentContractError('validation_error', 400, 'Check the highlighted details.')
    assert (error.code, error.status, error.message, str(error)) == ('validation_error', 400, 'Check the highlighted details.', 'Check the highlighted details.')
    reject(contract, contract.parse_create, b'{PRIVATE_MARKER')
    assert contract.parse_create(wire(CREATE)) == CREATE
    assert contract.parse_withdraw(wire(WITHDRAW)) == WITHDRAW
