"""Frozen B3 real-CSRF and raw-body RED contracts.

The synthetic stream cases prove adapter bounds only. They deliberately do not
claim Nginx/Gunicorn, WSGI hidden-byte, HTTP/1.1 framing or HTTP/2 acceptance.
No successful business command is asserted on SQLite.
"""
import importlib
from io import BytesIO
from uuid import uuid4

import pytest
from django.core.exceptions import RequestDataTooBig
from django.db import connection
from django.http import HttpRequest, RawPostDataException
from django.http.multipartparser import MultiPartParser as DjangoMultiPartParser
from rest_framework.parsers import MultiPartParser

from document_http_fixtures import (
    CREATE_BODY, WITHDRAW_BODY, http_workspace, local_headers, metadata_counts,
    request, route,
)


def adapter():
    # Literal RED must fail in a test body, never during collection/setup.
    try:
        return importlib.import_module('apps.core.document_api')
    except ModuleNotFoundError as exc:
        if exc.name == 'apps.core.document_api':
            pytest.fail('Frozen document HTTP adapter is not implemented', pytrace=False)
        raise


def post(workspace, shape, body, *, csrf=True, **headers):
    defaults = {'HTTP_IDEMPOTENCY_KEY': str(uuid4())}
    if csrf:
        defaults['HTTP_X_CSRFTOKEN'] = workspace.client.cookies['csrftoken'].value
    defaults.update(headers)
    content_type = defaults.pop('content_type', 'application/json')
    return workspace.client.generic('POST', route(workspace, shape), data=body,
        content_type=content_type, **defaults)


def rejection(response, status, code, message):
    assert response.status_code == status
    assert response.json() == {'code': code, 'message': message}
    local_headers(response)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('failure', [
    'missing-header', 'wrong-header', 'malformed-header', 'missing-cookie',
    'wrong-cookie', 'foreign-origin', 'null-origin', 'https-missing-referer',
    'https-foreign-referer',
])
def test_real_csrf_rejects_cookie_header_and_origin_failures_without_allowance(http_workspace, shape, failure):
    workspace = http_workspace
    token = workspace.client.cookies['csrftoken'].value
    headers = {'HTTP_X_CSRFTOKEN': token}
    if failure == 'missing-header':
        headers.pop('HTTP_X_CSRFTOKEN')
    elif failure == 'wrong-header':
        headers['HTTP_X_CSRFTOKEN'] = 'A' * 32 if token != 'A' * 32 else 'B' * 32
    elif failure == 'malformed-header':
        headers['HTTP_X_CSRFTOKEN'] = 'unsafe-secret-detail!'
    elif failure == 'missing-cookie':
        del workspace.client.cookies['csrftoken']
    elif failure == 'wrong-cookie':
        workspace.client.cookies['csrftoken'] = 'B' * 32 if token != 'B' * 32 else 'C' * 32
    elif failure == 'foreign-origin':
        headers['HTTP_ORIGIN'] = 'https://synthetic-untrusted.invalid'
    elif failure == 'null-origin':
        headers['HTTP_ORIGIN'] = 'null'
    elif failure.startswith('https-'):
        headers['wsgi.url_scheme'] = 'https'
        if failure == 'https-foreign-referer':
            headers['HTTP_REFERER'] = 'https://synthetic-untrusted.invalid/form'
    before = metadata_counts()
    body = WITHDRAW_BODY if shape == 'withdraw' else CREATE_BODY
    response = post(workspace, shape, body, csrf=False, **headers)
    rejection(response, 403, 'csrf_failed', 'Refresh the page and try again.')
    assert metadata_counts() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('multipart', [False, True])
def test_body_csrf_token_cannot_replace_header_and_multipart_is_never_parsed(http_workspace, monkeypatch, shape, multipart):
    def forbidden_parse(*args, **kwargs):
        pytest.fail('Document transport invoked multipart/file parsing')
    monkeypatch.setattr(MultiPartParser, 'parse', forbidden_parse)
    monkeypatch.setattr(DjangoMultiPartParser, 'parse', forbidden_parse)
    token = http_workspace.client.cookies['csrftoken'].value
    if multipart:
        body = (f'--synthetic\r\nContent-Disposition: form-data; name="csrfmiddlewaretoken"\r\n\r\n{token}'
            '\r\n--synthetic\r\nContent-Disposition: form-data; name="file"; filename="synthetic.png"'
            '\r\nContent-Type: image/png\r\n\r\nsynthetic-file\r\n--synthetic--\r\n').encode()
        media = 'multipart/form-data; boundary=synthetic'
    else:
        body = f'csrfmiddlewaretoken={token}'.encode()
        media = 'application/x-www-form-urlencoded'
    before = metadata_counts()
    response = post(http_workspace, shape, body, csrf=False, content_type=media)
    rejection(response, 403, 'csrf_failed', 'Refresh the page and try again.')
    assert metadata_counts() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
def test_valid_header_multipart_reaches415_without_file_parser_or_allowance(http_workspace, monkeypatch, shape):
    def forbidden_parse(*args, **kwargs):
        pytest.fail('Document transport invoked multipart/file parsing')
    monkeypatch.setattr(MultiPartParser, 'parse', forbidden_parse)
    monkeypatch.setattr(DjangoMultiPartParser, 'parse', forbidden_parse)
    body = (b'--synthetic\r\nContent-Disposition: form-data; name="file"; filename="synthetic.png"'
        b'\r\nContent-Type: image/png\r\n\r\nsynthetic-file\r\n--synthetic--\r\n')
    before = metadata_counts()
    response = post(http_workspace, shape, body, content_type='multipart/form-data; boundary=synthetic')
    rejection(response, 415, 'unsupported_media_type', 'Use a supported request format.')
    assert metadata_counts() == before


class Unreadable:
    """Any parser read, including readline, is a contract violation."""
    def read(self, *args, **kwargs):
        pytest.fail('Opaque document parser read original command bytes')

    def readline(self, *args, **kwargs):
        pytest.fail('Opaque document parser read an original command line')


@pytest.mark.parametrize('view_name', ['DocumentCollectionView', 'DocumentDetailView', 'DocumentWithdrawView'])
@pytest.mark.parametrize('media', ['application/json', 'multipart/form-data; boundary=synthetic', 'application/x-www-form-urlencoded'])
def test_document_local_opaque_parser_returns_empty_without_read_or_readline(view_name, media):
    module = adapter()
    view = getattr(module, view_name)
    parsers = [parser() for parser in view.parser_classes]
    assert len(parsers) == 1
    assert type(parsers[0]) is module.DocumentOpaqueParser
    assert parsers[0].media_type == '*/*'
    assert parsers[0].parse(Unreadable(), media_type=media, parser_context={}) == {}


BAD_JSON = [
    pytest.param(b'', id='empty'),
    pytest.param(b'{', id='truncated'),
    pytest.param(b'{} {}', id='two-json-values'),
    pytest.param(b'[]', id='array-root'),
    pytest.param(b'{"category":"registration","category":"registration"}', id='duplicate-root-key'),
    pytest.param(b'{"nested":{"a":1,"a":2}}', id='duplicate-nested-key'),
    pytest.param(b'{"size_bytes":NaN}', id='nan'),
    pytest.param(b'{"size_bytes":Infinity}', id='infinity'),
    pytest.param(b'{"size_bytes":-Infinity}', id='negative-infinity'),
    pytest.param(b'\xef\xbb\xbf' + CREATE_BODY, id='utf8-bom'),
    pytest.param(b'{"filename":"\xff"}', id='invalid-utf8'),
    pytest.param(b'{"filename":"\\ud800"}', id='escaped-surrogate'),
    pytest.param(b'{"x":' + b'[' * 9 + b'0' + b']' * 9 + b'}', id='depth-nine'),
    pytest.param(b'{"x":' + b'[' * 1200 + b'0' + b']' * 1200 + b'}', id='decoder-recursion'),
]


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != 'postgresql', reason='Strict B1 JSON validation follows the real PostgreSQL dependency guard')
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('body', BAD_JSON)
def test_original_malformed_json_survives_real_csrf_and_rejects_before_admission(http_workspace, shape, body):
    before = metadata_counts()
    # Explicit zero length is important: POST framing remains well-defined.
    response = post(http_workspace, shape, body, CONTENT_LENGTH=str(len(body)))
    rejection(response, 400, 'validation_error', 'Check the highlighted details.')
    assert metadata_counts() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('shape', ['collection', 'detail'])
@pytest.mark.parametrize('role,expected', [('reception', 400), ('doctor', 403)])
def test_nonempty_get_body_is_rejected_after_original_action_authority(http_workspace, shape, role, expected):
    http_workspace.membership.role = role
    http_workspace.membership.save(update_fields=['role'])
    before = metadata_counts()
    response = http_workspace.client.generic('GET', route(http_workspace, shape),
        data=b'x', content_type='application/json')
    if expected == 400:
        rejection(response, 400, 'validation_error', 'Check the highlighted details.')
    else:
        rejection(response, 403, 'permission_denied', 'You do not have access to this action.')
    assert metadata_counts() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('length', ['', '-1', '+2', ' 2', '2 ', '2,2', '2.0', 'two', '\u0662'])
def test_invalid_post_content_length_is_pre_auth400_and_never_admits(http_workspace, shape, length):
    before = metadata_counts()
    # No valid CSRF header: framing safety explicitly takes precedence.
    response = post(http_workspace, shape, b'{}', csrf=False, CONTENT_LENGTH=length)
    rejection(response, 400, 'validation_error', 'Check the highlighted details.')
    assert metadata_counts() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
def test_4097_declared_body_rejects413_before_csrf_and_without_allowance(http_workspace, shape):
    before = metadata_counts()
    response = post(http_workspace, shape, b' ' * 4097, csrf=False)
    rejection(response, 413, 'request_too_large', 'This request is too large.')
    assert metadata_counts() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != 'postgresql', reason='Actual PostgreSQL 17+ business command acceptance only')
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('size', [4095, 4096, 4097])
def test_original_padded_payload_boundaries_with_real_csrf_and_business_effects(http_workspace, settings, shape, size):
    assert connection.pg_version >= 170000
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    if shape == 'withdraw':
        created = request(http_workspace, 'POST')
        assert created.status_code == 201
        http_workspace.document_id = created.json()['document']['id']
    from apps.core.models import DocumentMetadataRateWindow
    def allowance():
        return DocumentMetadataRateWindow.objects.filter(actor=http_workspace.user).values_list(
            'window_started_at', 'admitted_count').first()
    before, count = metadata_counts(), allowance()
    raw = WITHDRAW_BODY if shape == 'withdraw' else CREATE_BODY
    raw += b' ' * (size - len(raw))
    assert len(raw) == size
    response = post(http_workspace, shape, raw)
    if size == 4097:
        rejection(response, 413, 'request_too_large', 'This request is too large.')
        assert metadata_counts() == before and allowance() == count
    else:
        assert response.status_code == (201 if shape == 'collection' else 200)
        local_headers(response)
        current = allowance()
        assert current is not None
        if count is not None and current[0] == count[0]:
            assert current[1] == count[1] + 1
        else:
            assert current[1] == 1  # A genuine minute reset cannot be a failure.
        after = metadata_counts()
        assert after[1:] == (before[1] + (shape == 'collection'), before[2] + 1, before[3] + 1)
        assert response.json()['document']['status'] == ('pending' if shape == 'collection' else 'withdrawn')


class BoundedStream(BytesIO):
    """Visible synthetic entity; does not emulate hidden WSGI framing bytes."""
    def __init__(self, body, *, fault=None):
        super().__init__(body)
        self.reads, self.lines, self.fault = [], [], fault

    def read(self, size=-1):
        self.reads.append(size)
        assert 0 <= size <= 4097, 'Adapter attempted unbounded/oversized stream read'
        if self.fault:
            raise self.fault
        return super().read(size)

    def readline(self, size=-1):
        self.lines.append(size)
        pytest.fail('Body capture must never request stream lines')


def raw_request(body=b'{}', *, method='POST', length='2', fault=None):
    raw = HttpRequest()
    raw.method = method
    raw.META = {} if length is None else {'CONTENT_LENGTH': length}
    raw._stream = BoundedStream(body, fault=fault)
    raw._read_started = False
    return raw


def transport_error(error, status, code, message):
    assert (error.status, error.code, error.message) == (status, code, message)


@pytest.mark.parametrize('size', [0, 4095, 4096])
def test_capture_reads_only_bounded_original_bytes_and_replays_exact_cache(size):
    raw = raw_request(b' ' * size, length=str(size))
    stream = raw._stream
    result = adapter()._capture_body(raw)
    assert result == b' ' * size
    assert raw._body == result and type(raw._body) is bytes
    assert raw.read() == result
    assert stream.lines == [] and sum(stream.reads) <= 4097


@pytest.mark.parametrize('length', [None, '', '-1', '+2', '\u0662', '2,2', '4097'])
def test_capture_framing_or_declared_oversize_rejects_without_any_stream_read(length):
    module = adapter()
    raw = raw_request(length=length)
    stream = raw._stream
    with pytest.raises(module.DocumentTransportError) as caught:
        module._capture_body(raw)
    if length == '4097':
        transport_error(caught.value, 413, 'request_too_large', 'This request is too large.')
    else:
        transport_error(caught.value, 400, 'validation_error', 'Check the highlighted details.')
    assert stream.reads == [] and stream.lines == []


def test_capture_observed_oversize_rejects_even_if_visible_stream_declares_short():
    module = adapter()
    raw = raw_request(b'x' * 4097, length='2')
    stream = raw._stream
    with pytest.raises(module.DocumentTransportError) as caught:
        module._capture_body(raw)
    transport_error(caught.value, 413, 'request_too_large', 'This request is too large.')
    assert stream.reads and sum(stream.reads) <= 4097 and stream.lines == []


@pytest.mark.parametrize('cached', [b'{}', b' ' * 4096])
def test_capture_accepts_complete_exact_bytes_cache_without_consuming_old_stream(cached):
    raw = raw_request(length=str(len(cached)))
    raw._body, raw._read_started = cached, True
    stream = raw._stream
    assert adapter()._capture_body(raw) == cached
    assert stream.reads == [] and stream.lines == []


@pytest.mark.parametrize('cached', [bytearray(b'{}'), '{}', b'x' * 4097])
def test_capture_rejects_nonbytes_or_oversize_cache_without_stream_consumption(cached):
    module = adapter()
    raw = raw_request(length='2')
    raw._body, raw._read_started = cached, True
    stream = raw._stream
    with pytest.raises(module.DocumentTransportError) as caught:
        module._capture_body(raw)
    if type(cached) is bytes:
        transport_error(caught.value, 413, 'request_too_large', 'This request is too large.')
    else:
        transport_error(caught.value, 400, 'validation_error', 'Check the highlighted details.')
    assert stream.reads == [] and stream.lines == []


def test_capture_read_started_without_complete_body_cache_fails_without_consumption():
    module = adapter()
    raw = raw_request()
    raw._read_started = True
    stream = raw._stream
    with pytest.raises(module.DocumentTransportError) as caught:
        module._capture_body(raw)
    transport_error(caught.value, 400, 'validation_error', 'Check the highlighted details.')
    assert stream.reads == [] and stream.lines == []


@pytest.mark.parametrize('fault,status,code,message', [
    (RequestDataTooBig('synthetic-detail'), 413, 'request_too_large', 'This request is too large.'),
    (RawPostDataException('synthetic-detail'), 400, 'validation_error', 'Check the highlighted details.'),
    (OSError('synthetic-detail'), 503, 'document_metadata_unavailable', 'Document details are unavailable. Try again later.'),
])
def test_capture_expected_resource_readstate_and_io_failures_are_typed(fault, status, code, message):
    module = adapter()
    raw = raw_request(fault=fault)
    stream = raw._stream
    with pytest.raises(module.DocumentTransportError) as caught:
        module._capture_body(raw)
    transport_error(caught.value, status, code, message)
    assert stream.reads and sum(stream.reads) <= 4097 and stream.lines == []


@pytest.mark.parametrize('body', [b'', b'x' * 4097])
def test_capture_supported_get_inspects_at_most_one_visible_byte(body):
    raw = raw_request(body, method='GET', length=str(len(body)))
    stream = raw._stream
    assert adapter()._capture_body(raw) == body[:1]
    assert stream.reads == [1] and stream.lines == []


def test_capture_post_accepts_ascii_leading_zero_length_without_changing_body():
    raw = raw_request(b'{}', length='0002')
    stream = raw._stream
    assert adapter()._capture_body(raw) == b'{}'
    assert sum(stream.reads) <= 4097 and stream.lines == []
