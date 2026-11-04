"""Full-client transport contracts plus explicitly isolated adapter handoff seams.

Injected service results below prove adapter behavior only, never business success.
Adapter imports stay inside tests so absent production code is executable RED.
"""
from importlib import import_module
from uuid import uuid4

import pytest
from django.db import connection
from rest_framework.test import APIClient

from document_http_fixtures import (http_workspace, route, request, metadata_counts,
    local_headers, CREATE_BODY, WITHDRAW_BODY)

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize('shape,allow', [('collection', 'GET, POST'), ('detail', 'GET'), ('withdraw', 'POST')])
@pytest.mark.parametrize('method', ['HEAD', 'OPTIONS', 'PUT', 'PATCH', 'DELETE'])
def test_unsupported_methods_require_authority_then_fixed405_without_admission(http_workspace, shape, allow, method):
    before = metadata_counts()
    response = request(http_workspace, method, shape)
    assert response.status_code == 405
    local_headers(response, allow)
    if method == 'HEAD':
        assert response.content == b''
    else:
        assert response.json() == {'code': 'method_not_allowed', 'message': 'This action is unavailable.'}
    assert metadata_counts() == before


@pytest.mark.parametrize('shape', ['collection', 'detail', 'withdraw'])
@pytest.mark.parametrize('role', ['master_admin', 'doctor', 'nurse', None])
def test_global_action_denial_precedes_unsupported_method_without_object_disclosure(http_workspace, shape, role):
    if role is None:
        http_workspace.membership.delete()
    else:
        http_workspace.membership.role = role
        http_workspace.membership.save(update_fields=['role'])
    before = metadata_counts()
    response = request(http_workspace, 'OPTIONS', shape)
    assert response.status_code == 403
    assert response.json() == {'code': 'permission_denied', 'message': 'You do not have access to this action.'}
    local_headers(response)
    assert metadata_counts() == before


@pytest.mark.parametrize('shape,method', [('collection', 'GET'), ('collection', 'POST'), ('detail', 'GET'), ('withdraw', 'POST')])
def test_anonymous_local403_has_distinct_safe_message(http_workspace, shape, method):
    client = APIClient(enforce_csrf_checks=True)
    before = metadata_counts()
    response = client.generic(method, route(http_workspace, shape), data=CREATE_BODY if method == 'POST' else b'', content_type='application/json')
    assert response.status_code == 403
    assert response.json() == {'code': 'not_authenticated', 'message': 'Sign in to continue.'}
    local_headers(response)
    assert metadata_counts() == before


def test_registered_post_uses_real_csrf_before_admission(http_workspace):
    before = metadata_counts()
    response = request(http_workspace, 'POST', csrf=False)
    assert response.status_code == 403
    assert response.json() == {'code': 'csrf_failed', 'message': 'Refresh the page and try again.'}
    local_headers(response)
    assert metadata_counts() == before


def test_content_subpath_stays_unregistered(http_workspace):
    before = metadata_counts()
    response = http_workspace.client.get(route(http_workspace, 'detail') + 'content/')
    assert response.status_code == 404
    assert metadata_counts() == before


@pytest.mark.parametrize('shape,method,allow', [('detail', 'POST', 'GET'), ('withdraw', 'GET', 'POST')])
def test_other_routes_supported_methods_do_not_cross_dispatch(http_workspace, shape, method, allow):
    before = metadata_counts()
    response = request(http_workspace, method, shape)
    assert response.status_code == 405
    assert response.json() == {'code': 'method_not_allowed', 'message': 'This action is unavailable.'}
    local_headers(response, allow)
    assert metadata_counts() == before


def _send(workspace, method='GET', shape='collection', *, suffix='', headers=None,
          content_type='application/json', body=None, path=None):
    supplied = {'HTTP_X_CSRFTOKEN': workspace.client.cookies['csrftoken'].value,
                'HTTP_IDEMPOTENCY_KEY': str(uuid4())}
    supplied.update(headers or {})
    if supplied.get('HTTP_IDEMPOTENCY_KEY') is None:
        supplied.pop('HTTP_IDEMPOTENCY_KEY')
    if body is None:
        body = (WITHDRAW_BODY if shape == 'withdraw' else CREATE_BODY) if method == 'POST' else b''
    return workspace.client.generic(method, (path or route(workspace, shape)) + suffix,
        data=body, content_type=content_type, **supplied)


def _error(response, status, code, message):
    assert response.status_code == status
    assert response.json() == {'code': code, 'message': message}
    local_headers(response)
    assert not response.has_header('Retry-After')


@pytest.mark.parametrize('shape,allow', [('collection', 'GET, POST'), ('withdraw', 'POST')])
@pytest.mark.parametrize('length,status', [('', 400), ('invalid', 400), ('4097', 413)])
def test_early_framing_errors_keep_route_specific_allow(http_workspace, shape, allow, length, status):
    before = metadata_counts()
    response = _send(http_workspace, 'POST', shape, headers={'CONTENT_LENGTH': length})
    assert response.status_code == status
    local_headers(response, allow)
    assert metadata_counts() == before


@pytest.mark.parametrize('shape', ['collection', 'detail'])
def test_excess_query_fields_are_input400_not_dependency503(http_workspace, settings, shape):
    settings.DATA_UPLOAD_MAX_NUMBER_FIELDS = 2
    before = metadata_counts()
    response = _send(http_workspace, shape=shape, suffix='?limit=1&category=registration&extra=synthetic')
    _error(response, 400, 'validation_error', 'Check the highlighted details.')
    assert metadata_counts() == before


@pytest.mark.parametrize('shape,method', [('collection', 'GET'), ('collection', 'POST'), ('detail', 'GET'), ('withdraw', 'POST')])
@pytest.mark.parametrize('value', ['', 'bytes=0-0', 'sensitive-header-input'])
def test_range_presence_is_rejected_without_service_allowance(http_workspace, shape, method, value):
    before = metadata_counts()
    response = _send(http_workspace, method, shape, headers={'HTTP_RANGE': value})
    _error(response, 400, 'validation_error', 'Check the highlighted details.')
    assert metadata_counts() == before


@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('media', ['text/plain', 'application/x-www-form-urlencoded',
    'multipart/form-data; boundary=synthetic', 'application/json;',
    'application/json; charset=', 'application/json; charset=utf8',
    'application/json; charset=ascii', 'application/json; x=sensitive-input',
    'application/json; charset=UTF-8; charset=UTF-8', 'application/json, text/plain'])
def test_unsupported_post_media_with_valid_real_csrf_is415(http_workspace, shape, media):
    before = metadata_counts()
    response = _send(http_workspace, 'POST', shape, content_type=media)
    _error(response, 415, 'unsupported_media_type', 'Use a supported request format.')
    assert metadata_counts() == before


@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('encoding', ['gzip', 'identity', 'sensitive-input'])
def test_nonempty_content_encoding_is415(http_workspace, shape, encoding):
    before = metadata_counts()
    response = _send(http_workspace, 'POST', shape, headers={'HTTP_CONTENT_ENCODING': encoding})
    _error(response, 415, 'unsupported_media_type', 'Use a supported request format.')
    assert metadata_counts() == before


@pytest.mark.parametrize('shape,method', [('collection', 'POST'), ('detail', 'GET'), ('withdraw', 'POST')])
@pytest.mark.parametrize('query', ['?limit=1', '?format=xml', '?unknown=sensitive-input', '?limit=1&limit=1'])
def test_nonlist_operations_reject_every_query_without_admission(http_workspace, shape, method, query):
    before = metadata_counts()
    response = _send(http_workspace, method, shape, suffix=query)
    _error(response, 400, 'validation_error', 'Check the highlighted details.')
    assert metadata_counts() == before


@pytest.mark.skipif(connection.vendor != 'postgresql', reason='Service validation requires actual PostgreSQL')
@pytest.mark.parametrize('query', ['?format=xml', '?unknown=sensitive-input', '?limit=1&limit=1',
    '?category=registration&category=registration', '?cursor=a&cursor=b',
    '?limit=01', '?limit=0', '?limit=101', '?limit=+1', '?limit=%D9%A1',
    '?category=clinical', '?cursor=not-a-cursor'])
def test_list_preserves_query_pairs_for_strict_service_validation(http_workspace, query):
    before = metadata_counts()
    response = _send(http_workspace, suffix=query)
    _error(response, 400, 'validation_error', 'Check the highlighted details.')
    assert metadata_counts() == before


@pytest.mark.skipif(connection.vendor != 'postgresql', reason='Service validation requires actual PostgreSQL')
@pytest.mark.parametrize('shape', ['collection', 'withdraw'])
@pytest.mark.parametrize('key', [None, '', 'not-a-key', '12345678-1234-4234-8234-123456789ABC',
    '12345678123442348234123456789abc', ' 12345678-1234-4234-8234-123456789abc',
    '12345678-1234-4234-8234-123456789abc,12345678-1234-4234-8234-123456789abc'])
def test_original_idempotency_header_reaches_canonical_validation(http_workspace, shape, key):
    before = metadata_counts()
    response = _send(http_workspace, 'POST', shape, headers={'HTTP_IDEMPOTENCY_KEY': key})
    _error(response, 400, 'validation_error', 'Check the highlighted details.')
    assert metadata_counts() == before


@pytest.mark.skipif(connection.vendor != 'postgresql', reason='Service validation requires actual PostgreSQL')
@pytest.mark.parametrize('segment', ['not-a-uuid', '12345678-1234-4234-8234-123456789ABC',
    '12345678123442348234123456789abc'])
@pytest.mark.parametrize('location', ['patient', 'document'])
def test_registered_string_segments_are_concealed_local404(http_workspace, segment, location):
    path = route(http_workspace, 'detail')
    path = path.replace(str(http_workspace.patient.pk) if location == 'patient' else http_workspace.document_id, segment)
    before = metadata_counts()
    response = _send(http_workspace, path=path)
    _error(response, 404, 'not_found', 'This record is unavailable.')
    assert metadata_counts() == before


@pytest.mark.parametrize('shape,allow', [('collection', 'GET, POST'), ('detail', 'GET'), ('withdraw', 'POST')])
def test_unsupported_method_skips_target_media_query_range_and_negotiation(http_workspace, shape, allow):
    path = route(http_workspace, shape).replace(str(http_workspace.patient.pk), 'invalid-patient')
    before = metadata_counts()
    response = _send(http_workspace, 'OPTIONS', shape, path=path, suffix='?format=xml&limit=0',
        content_type='text/plain', headers={'HTTP_RANGE': 'sensitive-input', 'HTTP_ACCEPT': 'text/html'})
    _error(response, 405, 'method_not_allowed', 'This action is unavailable.')
    local_headers(response, allow)
    assert metadata_counts() == before


def _adapter_service(monkeypatch, name, replacement):
    # Root-approved frozen import bindings; no context is forged or injected.
    api = import_module('apps.core.document_api')
    monkeypatch.setattr(api, name, replacement)
    return api


@pytest.mark.parametrize('shape,operation', [('collection', 'intent.list'), ('detail', 'intent.detail'), ('withdraw', 'intent.withdraw')])
@pytest.mark.parametrize('method', ['HEAD', 'OPTIONS'])
def test_unsupported_methods_capture_the_exact_route_operation(http_workspace, monkeypatch, shape, operation, method):
    from apps.core.document_authority import capture_document_context
    api = import_module('apps.core.document_api')
    captured = []
    def capture(raw, selected):
        context = capture_document_context(raw, selected)
        captured.append((selected, context.operation))
        return context
    monkeypatch.setattr(api, 'capture_document_context', capture)
    before = metadata_counts()
    response = _send(http_workspace, method, shape)
    assert response.status_code == 405
    assert captured == [(operation, operation)]
    assert metadata_counts() == before


@pytest.mark.parametrize('shape,method,service,operation,status', [
    ('collection', 'GET', 'list_document_intents', 'intent.list', 200),
    ('detail', 'GET', 'get_document_intent', 'intent.detail', 200),
    ('collection', 'POST', 'create_document_intent', 'intent.create', 201),
    ('withdraw', 'POST', 'withdraw_document_intent', 'intent.withdraw', 200)])
def test_adapter_only_one_genuine_context_and_exact_committed_byte_handoff(http_workspace, monkeypatch,
        shape, method, service, operation, status):
    from apps.core.document_authority import capture_document_context
    from apps.core.document_services import DocumentServiceResult
    body = b'{ "z" : "\\u0061", "a":1 }\n'
    captures, calls = [], []
    def capture(raw, requested):
        context = capture_document_context(raw, requested)
        captures.append((raw, requested, context))
        return context
    def supplied(*args):
        calls.append(args)
        return DocumentServiceResult(status, body)
    api = _adapter_service(monkeypatch, service, supplied)
    monkeypatch.setattr(api, 'capture_document_context', capture)
    key = str(uuid4())
    before = metadata_counts()
    response = _send(http_workspace, method, shape, headers={'HTTP_IDEMPOTENCY_KEY': key,
        'HTTP_ACCEPT': 'text/html; indent=8', 'HTTP_IF_NONE_MATCH': '*',
        'HTTP_IF_MODIFIED_SINCE': 'Wed, 21 Oct 2015 07:28:00 GMT'})
    assert response.status_code == status and response.content == body
    local_headers(response)
    assert len(captures) == len(calls) == 1
    raw, requested, context = captures[0]
    assert requested == operation and context.operation == operation
    assert context._request is raw and raw is response.wsgi_request
    assert calls[0][0] is context and calls[0][1] == str(http_workspace.patient.pk)
    if service == 'list_document_intents':
        assert list(calls[0][2]) == []
    elif method == 'GET':
        assert calls[0][2] == http_workspace.document_id
    elif shape == 'collection':
        assert calls[0][2:] == (key, CREATE_BODY)
    else:
        assert calls[0][2:] == (http_workspace.document_id, key, WITHDRAW_BODY)
    assert metadata_counts() == before  # Injected result is not business acceptance.


@pytest.mark.parametrize('media', ['application/json', 'APPLICATION/JSON',
    'application/json; charset=UTF-8', 'application/json; charset="UTF-8"',
    ' \tApplication/JSON \t; \tcharset = "UTF-8" \t'])
def test_adapter_only_valid_media_preserves_original_body(http_workspace, monkeypatch, media):
    from apps.core.document_services import DocumentServiceResult
    calls = []
    original = b' { "unchanged": true } '
    def supplied(*args):
        calls.append(args)
        return DocumentServiceResult(201, b'{}')
    _adapter_service(monkeypatch, 'create_document_intent', supplied)
    response = _send(http_workspace, 'POST', body=original, content_type=media,
        headers={'HTTP_CONTENT_ENCODING': ''})
    assert response.status_code == 201
    assert len(calls) == 1 and calls[0][-1] == original


@pytest.mark.parametrize('query', ['?limit=10&limit=20', '?category=registration&limit=25&cursor=synthetic'])
def test_adapter_only_list_handoff_does_not_collapse_duplicate_query_pairs(http_workspace, monkeypatch, query):
    from apps.core.document_services import DocumentServiceResult
    calls = []
    def supplied(*args):
        calls.append(args)
        return DocumentServiceResult(200, b'{}')
    _adapter_service(monkeypatch, 'list_document_intents', supplied)
    response = _send(http_workspace, suffix=query)
    assert response.status_code == 200 and len(calls) == 1
    expected = [('limit', '10'), ('limit', '20')] if '10' in query else [
        ('category', 'registration'), ('limit', '25'), ('cursor', 'synthetic')]
    assert sorted(calls[0][2]) == sorted(expected)


@pytest.mark.parametrize('code,status,message,retry', [
    ('not_authenticated', 401, 'Your session ended. Sign in again.', None),
    ('permission_denied', 403, 'You do not have access to this action.', None),
    ('network_denied', 403, 'Access is not available from this network. Contact your administrator.', None),
    ('validation_error', 400, 'Check the highlighted details.', None),
    ('not_found', 404, 'This record is unavailable.', None),
    ('request_too_large', 413, 'This request is too large.', None),
    ('document_metadata_unavailable', 503, 'Document details are unavailable. Try again later.', None),
    ('idempotency_conflict', 409, 'This request could not be repeated. Refresh before continuing.', None),
    ('version_conflict', 409, 'The record changed. Refresh before continuing.', None),
    ('intent_state_conflict', 409, 'This request can no longer be withdrawn.', None),
    ('rate_limited', 429, 'Too many requests. Try again shortly.', 1),
    ('rate_limited', 429, 'Too many requests. Try again shortly.', 3600)])
def test_adapter_only_expected_service_errors_have_closed_envelope(http_workspace, monkeypatch, code, status, message, retry):
    from apps.core.document_authority import DocumentServiceError
    def supplied(*args):
        error = DocumentServiceError(code, status, message, retry)
        error.field_errors = {'patient': 'sensitive-input'}
        error.request_id = 'sensitive-input'
        raise error
    _adapter_service(monkeypatch, 'list_document_intents', supplied)
    before = metadata_counts()
    response = _send(http_workspace)
    assert response.status_code == status and response.json() == {'code': code, 'message': message}
    local_headers(response)
    assert response.get('Retry-After') == (str(retry) if retry is not None else None)
    assert metadata_counts() == before


@pytest.mark.parametrize('damage', ['code', 'status', 'message', 'retry_zero', 'retry_large', 'retry_bool', 'retry_unrelated'])
def test_adapter_only_mutated_service_error_is_fixed503(http_workspace, monkeypatch, damage):
    from apps.core.document_authority import DocumentServiceError
    error = DocumentServiceError('rate_limited', 429, 'Too many requests. Try again shortly.', 1)
    changes = {'code': ('code', 'sensitive-input'), 'status': ('status', 418),
        'message': ('message', 'sensitive-input'), 'retry_zero': ('retry_after', 0),
        'retry_large': ('retry_after', 3601), 'retry_bool': ('retry_after', True),
        'retry_unrelated': ('code', 'not_found')}
    setattr(error, *changes[damage])
    def supplied(*args):
        raise error
    _adapter_service(monkeypatch, 'list_document_intents', supplied)
    _error(_send(http_workspace), 503, 'document_metadata_unavailable',
        'Document details are unavailable. Try again later.')


@pytest.mark.parametrize('result_kind', ['wrong_type', 'wrong_status', 'bool_status', 'text_body', 'bytearray_body', 'oversize'])
def test_adapter_only_invalid_service_result_never_discloses_partial_body(http_workspace, monkeypatch, result_kind):
    from apps.core.document_services import DocumentServiceResult
    results = {'wrong_type': {'status': 200, 'body': b'sensitive-input'},
        'wrong_status': DocumentServiceResult(202, b'sensitive-input'),
        'bool_status': DocumentServiceResult(True, b'sensitive-input'),
        'text_body': DocumentServiceResult(200, 'sensitive-input'),
        'bytearray_body': DocumentServiceResult(200, bytearray(b'sensitive-input')),
        'oversize': DocumentServiceResult(200, b'x' * 262145)}
    _adapter_service(monkeypatch, 'list_document_intents', lambda *args: results[result_kind])
    _error(_send(http_workspace), 503, 'document_metadata_unavailable',
        'Document details are unavailable. Try again later.')


@pytest.mark.parametrize('exception_type', [RuntimeError, OSError, PermissionError])
def test_adapter_only_unknown_service_failures_do_not_leak_details(http_workspace, monkeypatch, exception_type):
    def supplied(*args):
        raise exception_type('sensitive-input SQL patient payload')
    _adapter_service(monkeypatch, 'list_document_intents', supplied)
    _error(_send(http_workspace), 503, 'document_metadata_unavailable',
        'Document details are unavailable. Try again later.')


def test_adapter_only_response_at_exact_byte_ceiling_has_no_postservice_queries(http_workspace, monkeypatch):
    from apps.core.document_services import DocumentServiceResult
    body = b'{"padding":"' + b'x' * (262144 - len(b'{"padding":""}')) + b'"}'
    assert len(body) == 262144
    returned = False
    def supplied(*args):
        nonlocal returned
        returned = True
        return DocumentServiceResult(200, body)
    def guard(execute, sql, params, many, context):
        assert not returned, 'SQL executed after detached service result'
        return execute(sql, params, many, context)
    _adapter_service(monkeypatch, 'list_document_intents', supplied)
    with connection.execute_wrapper(guard):
        response = _send(http_workspace)
    assert returned and response.status_code == 200 and response.content == body
    local_headers(response)


@pytest.mark.parametrize('exception_type', [SystemExit, KeyboardInterrupt])
def test_adapter_only_process_control_exceptions_are_not_translated(http_workspace, monkeypatch, exception_type):
    def supplied(*args):
        raise exception_type('synthetic-process-control')
    _adapter_service(monkeypatch, 'list_document_intents', supplied)
    with pytest.raises(exception_type, match='synthetic-process-control'):
        _send(http_workspace)
