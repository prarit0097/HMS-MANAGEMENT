from django.test import override_settings
from rest_framework.test import APIClient

@override_settings(HMS_IP_ALLOWLIST_ONLY=True, HMS_IP_ALLOWLIST=[], HMS_IP_BLOCKLIST=[], HMS_TRUSTED_PROXIES=())
def test_policy_denies_auth_bootstrap_and_spoofed_forwarded_header():
    client = APIClient()
    response = client.get('/api/v1/auth/csrf/', REMOTE_ADDR='198.51.100.4', HTTP_X_FORWARDED_FOR='127.0.0.1')
    assert response.status_code == 403
    assert response.json()['code'] == 'network_denied'
    assert client.get('/api/v1/health/').status_code == 200

@override_settings(HMS_IP_ALLOWLIST_ONLY=True, HMS_IP_ALLOWLIST=['203.0.113.0/24'], HMS_IP_BLOCKLIST=[], HMS_TRUSTED_PROXIES=('10.0.0.0/8',))
def test_trusted_proxy_policy_checks_original_client_and_fails_malformed_chain():
    client = APIClient()
    assert client.get('/api/v1/auth/csrf/', REMOTE_ADDR='10.0.0.2', HTTP_X_FORWARDED_FOR='203.0.113.8').status_code == 200
    assert client.get('/api/v1/auth/csrf/', REMOTE_ADDR='10.0.0.2', HTTP_X_FORWARDED_FOR='malformed').status_code == 403

def test_clickjacking_header_is_present():
    assert APIClient().get('/api/v1/health/')['X-Frame-Options'] == 'DENY'
