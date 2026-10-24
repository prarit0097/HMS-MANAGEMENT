from django.http import JsonResponse, HttpResponse
from django.conf import settings
from apps.security import normalise_client_ip, evaluate_ip

class NetworkPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        from .network_environment import network_decision
        from .network_snapshot import NetworkStateUnavailable
        from .network_api import PROBE_PATH
        probe = request.path == PROBE_PATH
        if probe:
            from apps.security.ip_policy import _address
            try:
                peers = getattr(settings, 'HMS_NETWORK_PROBE_PEERS', ())
                if not isinstance(peers, (tuple, list)) or not peers or any(not _address(peer).is_loopback for peer in peers):
                    raise ValueError()
                if str(_address(request.META.get('REMOTE_ADDR', ''))) not in {str(_address(peer)) for peer in peers} or request.META.get('HTTP_X_HMS_NETWORK_PROBE') != '1' or request.META.get('QUERY_STRING') or request.read(1):
                    raise ValueError()
                request._hms_validated_network_probe = True
            except (ValueError, TypeError):
                response = HttpResponse(status=404)
                response['Cache-Control'] = 'no-store'
                return response
            if request.method not in {'GET', 'HEAD'}:
                response = HttpResponse(status=405)
                response['Allow'] = 'GET, HEAD'
                response['Cache-Control'] = 'no-store'
                return response
        if request.path.startswith('/api/') and request.path != '/api/v1/health/':
            try:
                decision = network_decision(request.META.get('REMOTE_ADDR', ''), request.META.get('HTTP_X_FORWARDED_FOR'))
                request.verified_client_ip = decision.verified_ip
                status = 204 if decision.allowed else 403
            except NetworkStateUnavailable:
                status = 503
            if probe or status != 204:
                if probe:
                    response = HttpResponse(status=status)
                else:
                    response = JsonResponse({'code': 'network_policy_unavailable' if status == 503 else 'network_denied', 'message': 'Network settings are temporarily unavailable.' if status == 503 else 'Access is not available from this network. Contact your administrator.'}, status=status)
                response['Cache-Control'] = 'no-store'
                return response
        response = self.get_response(request)
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-store'
        return response

def csrf_failure(request, reason=''):
    return JsonResponse({'code': 'csrf_failed', 'message': 'Your session could not be verified. Refresh and try again.'}, status=403)


class IdentitySessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/api/v1/network-policy/edge-probe/' and getattr(request, '_hms_validated_network_probe', False):
            return self.get_response(request)
        if request.path.startswith('/api/') and request.user.is_authenticated:
            from .identity_security import epoch_valid, require_platform, SecurityError
            request.user._hms_auth_epoch = request.session.get('auth_epoch')
            request.user._hms_factor_verified_at = request.session.get('factor_verified_at')
            if request.path != '/api/v1/auth/logout/':
                if not epoch_valid(request.user):
                    from django.contrib.auth import logout
                    logout(request)
                    return JsonResponse({'code':'not_authenticated','message':'Your session ended. Sign in again.'},status=401)
                if request.path.startswith('/api/v1/platform/') and request.method not in {'GET','HEAD','OPTIONS'}:
                    try:
                        require_platform(request.user)
                    except SecurityError as exc:
                        return JsonResponse({'code':exc.default_code,'message':str(exc.detail)},status=exc.status_code)
        return self.get_response(request)
