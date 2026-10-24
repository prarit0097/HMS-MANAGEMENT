"""Strict HTTP adapters for the frozen deployment network contract."""
import json
from io import BytesIO
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist, RequestDataTooBig
from django.http import HttpResponse
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError
from .network_authority import capture_network_context, require_network_operator, NetworkError
from .network_snapshot import NetworkStateUnavailable
from .network_access import read_network_state, preview_network_policy, activate_network_preview, finish_network_change
from .network_history import network_history

PROBE_PATH = '/api/v1/network-policy/edge-probe/'
BODY_LIMIT = 32768


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Repeated field')
        result[key] = value
    return result


def bounded_body(raw_request):
    """Capture bytes before session CSRF parsing can consume the raw stream."""
    try:
        length = raw_request.META.get('CONTENT_LENGTH', '')
        if length and (not str(length).isascii() or not str(length).isdigit()):
            raise NetworkError('validation_error', 400)
        if length and int(length) > BODY_LIMIT:
            raise NetworkError('request_too_large', 413, 'Use a smaller request.')
        data = raw_request._body if hasattr(raw_request, '_body') else raw_request.read(BODY_LIMIT+1)
        if type(data) is not bytes:
            raise NetworkError('validation_error', 400)
        if len(data) > BODY_LIMIT:
            raise NetworkError('request_too_large', 413, 'Use a smaller request.')
        return data
    except RequestDataTooBig:
        raise NetworkError('request_too_large', 413, 'Use a smaller request.') from None
    except (ValueError, TypeError):
        raise NetworkError('validation_error', 400) from None


def body(request, fields):
    if request.content_type != 'application/json':
        raise NetworkError('unsupported_media_type', 415, 'Send this request as JSON.')
    data = getattr(request._request, '_hms_network_raw_body', None)
    if type(data) is not bytes or len(data) > BODY_LIMIT:
        raise NetworkError('validation_error', 400)
    try:
        parsed = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RequestDataTooBig, RecursionError):
        raise NetworkError('validation_error', 400) from None
    if type(parsed) is not dict or set(parsed) != set(fields):
        raise NetworkError('validation_error', 400)
    return parsed


class NetworkView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    action = 'read'
    http_method_names = ['get', 'head', 'post']

    def initial(self, request, *args, **kwargs):
        if request.method == 'POST' and self.action in ('preview', 'activate', 'confirm', 'revert'):
            raw = request._request
            data = bounded_body(raw)
            raw._hms_network_raw_body = data
            # Both Django's cache and the replay stream contain only bytes that
            # have passed our independent limit. No unbounded body read occurs.
            raw._body = data
            raw._stream = BytesIO(data)
            try:
                return super().initial(request, *args, **kwargs)
            except RecursionError:
                # Session CSRF checks can parse this bounded JSON replay before
                # body() gets its own opportunity to reject excessive nesting.
                raise NetworkError('validation_error', 400) from None
        return super().initial(request, *args, **kwargs)

    def handle_exception(self, exc):
        if isinstance(exc, ParseError):
            exc = NetworkError('validation_error', 400)
        if isinstance(exc, (NetworkStateUnavailable, DatabaseError, ObjectDoesNotExist)):
            exc = NetworkError('network_policy_unavailable', 503)
        response = super().handle_exception(exc)
        if response.status_code == 403 and 'CSRF' in str(getattr(exc, 'detail', '')):
            response.data = {'code': 'csrf_failed', 'message': 'Your session could not be verified. Refresh and try again.'}
        response['Cache-Control'] = 'no-store'
        return response

    def _context(self, request):
        context = capture_network_context(request)
        require_network_operator(context)
        return context

    def get(self, request, **kwargs):
        if self.action not in ('read', 'history'):
            return Response({'code': 'method_not_allowed', 'message': 'Use the supported request method.'}, status=405)
        context = self._context(request)
        if request._request.read(1):
            raise NetworkError('validation_error', 400)
        if self.action == 'history':
            result = network_history(context, request.query_params)
        else:
            if request.query_params:
                raise NetworkError('validation_error', 400)
            result = read_network_state(context)
        return Response(result)

    def post(self, request, **kwargs):
        if self.action not in ('preview', 'activate', 'confirm', 'revert'):
            return Response({'code': 'method_not_allowed', 'message': 'Use the supported request method.'}, status=405)
        context = self._context(request)
        if request.query_params:
            raise NetworkError('validation_error', 400)
        if self.action == 'preview':
            data = body(request, ('expected_revision', 'policy', 'reason'))
            result, created = preview_network_policy(context, data['expected_revision'], data['policy'], data['reason'], request.headers.get('Idempotency-Key'))
            return Response(result, status=201 if created else 200)
        data = body(request, ('expected_revision',))
        if self.action == 'activate':
            result = activate_network_preview(context, kwargs['preview_id'], data['expected_revision'])
        else:
            result = finish_network_change(context, kwargs['change_id'], data['expected_revision'], self.action)
        return Response(result)


class EdgeProbe(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        # Normally answered before sessions by NetworkPolicyMiddleware.
        response = HttpResponse(status=204 if getattr(request._request, '_hms_validated_network_probe', False) else 404)
        response['Cache-Control'] = 'no-store'
        return response
