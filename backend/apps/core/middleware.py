from django.http import JsonResponse
from django.conf import settings
from apps.security import normalise_client_ip, evaluate_ip

class NetworkPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.path.startswith('/api/') and request.path != '/api/v1/health/':
            try:
                request.verified_client_ip = normalise_client_ip(request.META.get('REMOTE_ADDR', ''), request.META.get('HTTP_X_FORWARDED_FOR'), settings.HMS_TRUSTED_PROXIES)
                allowed = evaluate_ip(request.verified_client_ip, settings.HMS_IP_ALLOWLIST, settings.HMS_IP_BLOCKLIST, settings.HMS_IP_ALLOWLIST_ONLY)
            except ValueError:
                allowed = False
            if not allowed:
                return JsonResponse({'code': 'network_denied', 'message': 'Access is not available from this network. Contact your administrator.'}, status=403)
        response = self.get_response(request)
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-store'
        return response

def csrf_failure(request, reason=''):
    return JsonResponse({'code': 'csrf_failed', 'message': 'Your session could not be verified. Refresh and try again.'}, status=403)
