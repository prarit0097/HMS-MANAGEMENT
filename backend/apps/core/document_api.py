"""Bounded HTTP transport for the existing document metadata services.

Authority and all command validation remain in the public business services.
The opaque parser exists solely to let ordinary CSRF checks inspect headers
without interpreting original command bytes as form or file data.
"""
from io import BytesIO
import json
import re

from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent
from django.http import HttpResponse, RawPostDataException
from django.utils.cache import patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from .document_authority import DocumentServiceError, capture_document_context
from .document_services import (DocumentServiceResult, create_document_intent,
                                get_document_intent, list_document_intents,
                                withdraw_document_intent)


_ERRORS = {
    'not_authenticated': (401, 'Your session ended. Sign in again.'),
    'permission_denied': (403, 'You do not have access to this action.'),
    'network_denied': (403, 'Access is not available from this network. Contact your administrator.'),
    'document_metadata_unavailable': (503, 'Document details are unavailable. Try again later.'),
    'validation_error': (400, 'Check the highlighted details.'),
    'not_found': (404, 'This record is unavailable.'),
    'request_too_large': (413, 'This request is too large.'),
    'rate_limited': (429, 'Too many requests. Try again shortly.'),
    'idempotency_conflict': (409, 'This request could not be repeated. Refresh before continuing.'),
    'version_conflict': (409, 'The record changed. Refresh before continuing.'),
    'intent_state_conflict': (409, 'This request can no longer be withdrawn.'),
    'csrf_failed': (403, 'Refresh the page and try again.'),
    'method_not_allowed': (405, 'This action is unavailable.'),
    'unsupported_media_type': (415, 'Use a supported request format.'),
}
_JSON_MEDIA = re.compile(
    r'[ \t]*application/json[ \t]*(?:;[ \t]*charset[ \t]*=[ \t]*(?:UTF-8|"UTF-8")[ \t]*)?',
    re.IGNORECASE | re.ASCII,
)


class DocumentTransportError(Exception):
    def __init__(self, code, status, message):
        if (type(code) is not str or code not in _ERRORS or type(status) is not int
                or type(message) is not str or (status, message) != _ERRORS[code]):
            raise ValueError('Invalid document transport error')
        self.code, self.status, self.message = code, status, message
        super().__init__(message)


def _fail(code):
    raise DocumentTransportError(code, *_ERRORS[code]) from None


def _capture_body(raw_request):
    """Read only the bounded, server-visible entity; never unwrap WSGI streams."""
    is_get = raw_request.method == 'GET'
    if raw_request.method == 'POST':
        length = raw_request.META.get('CONTENT_LENGTH')
        if type(length) is not str or not re.fullmatch(r'[0-9]+', length, re.ASCII):
            _fail('validation_error')
        # Compare decimal strings, avoiding an unbounded integer conversion.
        significant = length.lstrip('0') or '0'
        if len(significant) > 4 or (len(significant) == 4 and significant > '4096'):
            _fail('request_too_large')
    try:
        if hasattr(raw_request, '_body'):
            body = raw_request._body
        else:
            if getattr(raw_request, '_read_started', False):
                _fail('validation_error')
            body = raw_request.read(1 if is_get else 4097)
        if type(body) is not bytes:
            _fail('validation_error')
        if is_get:
            body = body[:1]
        elif len(body) > 4096:
            _fail('request_too_large')
        raw_request._body = body
        raw_request._stream = BytesIO(body)
        return body
    except RequestDataTooBig:
        _fail('request_too_large')
    except (RawPostDataException, ValueError):
        _fail('validation_error')
    except OSError:
        _fail('document_metadata_unavailable')


def _document_response(body, status):
    response = HttpResponse(body, status=status, content_type='application/json')
    response['Cache-Control'] = 'no-store'
    patch_vary_headers(response, ['Cookie'])
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _error_response(exc):
    code, status, message, retry = 'document_metadata_unavailable', *_ERRORS['document_metadata_unavailable'], None
    if isinstance(exc, DocumentServiceError):
        try:
            # Revalidate even genuine exceptions: callers can mutate attributes.
            checked = DocumentServiceError(exc.code, exc.status, exc.message, exc.retry_after)
            code, status, message, retry = checked.code, checked.status, checked.message, checked.retry_after
        except (AttributeError, ValueError, TypeError):
            pass
    elif isinstance(exc, DocumentTransportError):
        try:
            checked = DocumentTransportError(exc.code, exc.status, exc.message)
            code, status, message = checked.code, checked.status, checked.message
        except (AttributeError, ValueError, TypeError):
            pass
    elif isinstance(exc, NotAuthenticated):
        code, status, message = 'not_authenticated', 403, 'Sign in to continue.'
    elif isinstance(exc, TooManyFieldsSent):
        code, status, message = 'validation_error', *_ERRORS['validation_error']
    response = _document_response(json.dumps({'code': code, 'message': message},
        separators=(',', ':'), ensure_ascii=True).encode('utf-8'), status)
    if retry is not None:
        response['Retry-After'] = str(retry)
    return response


class DocumentOpaqueParser(BaseParser):
    media_type = '*/*'

    def parse(self, stream, media_type=None, parser_context=None):
        return {}


class DocumentSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        try:
            super().enforce_csrf(request)
        except PermissionDenied:
            _fail('csrf_failed')


class DocumentNegotiation(BaseContentNegotiation):
    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], 'application/json'


class DocumentView(APIView):
    authentication_classes = [DocumentSessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [DocumentOpaqueParser]
    renderer_classes = [JSONRenderer]
    content_negotiation_class = DocumentNegotiation
    metadata_class = None
    throttle_classes = []
    allowed = ()
    operation = None

    @property
    def allowed_methods(self):
        return list(self.allowed)

    def get_format_suffix(self, **kwargs):
        return None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.command_body = _capture_body(request)
        except Exception as exc:
            response = _error_response(exc)
            response['Allow'] = ', '.join(self.allowed)
            return response
        return super().dispatch(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        operation = self.operation
        if self.allowed == ('GET', 'POST') and request.method == 'POST':
            operation = 'intent.create'
        self.document_context = capture_document_context(request._request, operation)

    def handle_exception(self, exc):
        return _error_response(exc)

    def http_method_not_allowed(self, request, *args, **kwargs):
        _fail('method_not_allowed')

    def _transport(self, request, *, listing=False):
        if 'HTTP_RANGE' in request.META:
            _fail('validation_error')
        if not listing and request.query_params:
            _fail('validation_error')
        if request.method == 'GET':
            if self.command_body:
                _fail('validation_error')
        else:
            media = request.META.get('CONTENT_TYPE', '')
            if (type(media) is not str or _JSON_MEDIA.fullmatch(media) is None
                    or request.META.get('HTTP_CONTENT_ENCODING', '')):
                _fail('unsupported_media_type')

    def _result(self, result, status):
        if (type(result) is not DocumentServiceResult or type(result.status) is not int
                or result.status != status or type(result.body) is not bytes
                or len(result.body) > 262144):
            _fail('document_metadata_unavailable')
        return _document_response(result.body, result.status)


class DocumentCollectionView(DocumentView):
    http_method_names = ['get', 'post']
    allowed = ('GET', 'POST')
    operation = 'intent.list'

    def get(self, request, patient_id):
        self._transport(request, listing=True)
        pairs = [(key, value) for key, values in request.query_params.lists() for value in values]
        return self._result(list_document_intents(self.document_context, patient_id, pairs), 200)

    def post(self, request, patient_id):
        self._transport(request)
        return self._result(create_document_intent(self.document_context, patient_id,
            request.META.get('HTTP_IDEMPOTENCY_KEY'), self.command_body), 201)


class DocumentDetailView(DocumentView):
    http_method_names = ['get']
    allowed = ('GET',)
    operation = 'intent.detail'

    def get(self, request, patient_id, document_id):
        self._transport(request)
        return self._result(get_document_intent(self.document_context, patient_id, document_id), 200)


class DocumentWithdrawView(DocumentView):
    http_method_names = ['post']
    allowed = ('POST',)
    operation = 'intent.withdraw'

    def post(self, request, patient_id, document_id):
        self._transport(request)
        return self._result(withdraw_document_intent(self.document_context, patient_id,
            document_id, request.META.get('HTTP_IDEMPOTENCY_KEY'), self.command_body), 200)
