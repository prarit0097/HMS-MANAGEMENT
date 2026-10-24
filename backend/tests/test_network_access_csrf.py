"""Real CSRF-enabled clients must retain exact bounded raw JSON validation."""
import uuid
import io
import json
import pytest
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from apps.core.models import NetworkPolicyState, NetworkPolicyPreview, NetworkPolicyChange, NetworkPolicyEvent
from tests.test_network_access_api import manager, ROOT, OPEN

pytestmark = pytest.mark.django_db


@pytest.fixture
def csrf_manager(manager):
    original, *_ = manager
    client = APIClient(enforce_csrf_checks=True)
    client.cookies = original.cookies.copy()
    response = client.get('/api/v1/auth/csrf/')
    assert response.status_code == 200
    return client, client.cookies['csrftoken'].value


@pytest.mark.parametrize('finish,outcome', [('confirm', 'confirmed'), ('revert', 'reverted')])
def test_valid_csrf_json_management_writes_keep_exact_raw_body(csrf_manager, finish, outcome):
    client, token = csrf_manager
    response = client.post(ROOT+'previews/', {'expected_revision': 1, 'policy': OPEN, 'reason': 'Synthetic valid CSRF preview'}, format='json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 201
    activation = client.post(ROOT+f"previews/{response.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json', HTTP_X_CSRFTOKEN=token)
    assert activation.status_code == 200 and activation.json()['outcome'] == 'pending'
    terminal = client.post(ROOT+f"changes/{activation.json()['change_id']}/{finish}/", {'expected_revision': 2}, format='json', HTTP_X_CSRFTOKEN=token)
    assert terminal.status_code == 200 and terminal.json()['outcome'] == outcome
    assert NetworkPolicyState.objects.get(pk=1).revision == 3


@pytest.mark.parametrize('token', [None, 'A'*32])
def test_missing_or_wrong_csrf_remains_denied_without_mutation(csrf_manager, token):
    client, valid = csrf_manager
    headers = {'HTTP_X_CSRFTOKEN': token} if token is not None else {}
    response = client.post(ROOT+'previews/', {'expected_revision': 1, 'policy': OPEN, 'reason': 'Synthetic invalid CSRF request'}, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()), **headers)
    assert response.status_code == 403 and response.json()['code'] == 'csrf_failed'
    assert not NetworkPolicyPreview.objects.exists() and not NetworkPolicyEvent.objects.exists()


@pytest.mark.parametrize('raw', ['{"expected_revision":1,"expected_revision":1,"policy":{"allowlist_only":false,"allowlist":[],"blocklist":[]},"reason":"Synthetic duplicate request"}', '{"expected_revision":1,"policy":{"allowlist_only":false,"allowlist_only":false,"allowlist":[],"blocklist":[]},"reason":"Synthetic nested duplicate request"}', '{invalid-json'])
def test_valid_csrf_does_not_relax_duplicate_or_malformed_json(csrf_manager, raw):
    client, token = csrf_manager
    response = client.post(ROOT+'previews/', raw, content_type='application/json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 400 and response.json()['code'] == 'validation_error'
    assert not NetworkPolicyPreview.objects.exists()


@pytest.mark.parametrize('opening,closing,depth', [('[', ']', 12000), ('{"x":', '}', 4000)])
def test_valid_csrf_deep_json_is_generic_400_without_writes(csrf_manager, opening, closing, depth):
    client, token = csrf_manager
    client.raise_request_exception = False
    raw = '{"x":' + opening*depth + '"synthetic-depth-marker"' + closing*depth + '}'
    assert len(raw.encode('utf-8')) < 32768
    state_before = NetworkPolicyState.objects.values().get(pk=1)
    response = client.post(ROOT+'previews/', raw, content_type='application/json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 400
    assert response.json() == {'code': 'validation_error', 'message': 'Please check the supplied fields.'}
    assert b'synthetic-depth-marker' not in response.content
    assert response['Cache-Control'] == 'no-store'
    assert NetworkPolicyState.objects.values().get(pk=1) == state_before
    assert not NetworkPolicyPreview.objects.exists()
    assert not NetworkPolicyChange.objects.exists()
    assert not NetworkPolicyEvent.objects.exists()
    normal = client.post(ROOT+'previews/', {'expected_revision': 1, 'policy': OPEN, 'reason': 'Synthetic recovery after deep JSON'}, format='json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert normal.status_code == 201


def test_csrf_path_preserves_backend_32k_limit(csrf_manager):
    client, token = csrf_manager
    response = client.post(ROOT+'previews/', ' '*32769, content_type='application/json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 413 and response.json()['code'] == 'request_too_large'
    assert not NetworkPolicyPreview.objects.exists()


def test_exact_32k_original_json_is_accepted_with_csrf(csrf_manager):
    client, token = csrf_manager
    raw = json.dumps({'expected_revision': 1, 'policy': OPEN, 'reason': 'Synthetic exact boundary preview'}, separators=(',', ':'))
    raw += ' '*(32768-len(raw))
    response = client.post(ROOT+'previews/', raw, content_type='application/json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 201
    assert NetworkPolicyPreview.objects.count() == 1


def test_valid_header_without_csrf_cookie_remains_denied(csrf_manager):
    client, token = csrf_manager
    del client.cookies['csrftoken']
    response = client.post(ROOT+'previews/', {'expected_revision': 1, 'policy': OPEN, 'reason': 'Synthetic missing cookie request'}, format='json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 403 and response.json()['code'] == 'csrf_failed'
    assert not NetworkPolicyPreview.objects.exists()


def test_valid_csrf_multipart_file_is_still_unsupported(csrf_manager):
    client, token = csrf_manager
    response = client.post(ROOT+'previews/', {'file': io.BytesIO(b'Synthetic attachment')}, HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 415
    assert not NetworkPolicyPreview.objects.exists() and not NetworkPolicyEvent.objects.exists()


@pytest.mark.parametrize('declared_length', ['', '1'])
def test_raw_stream_limit_is_independent_of_missing_or_understated_length(csrf_manager, manager, declared_length):
    from apps.core.network_api import NetworkView
    client, token = csrf_manager
    _, user, *_ = manager
    payload = b' '*32769
    reads = []
    class BoundedStream(io.BytesIO):
        def read(self, size=-1):
            reads.append(size)
            assert 0 <= size <= 32769, 'Authentication/parser tried an unbounded raw body read'
            return super().read(size)
    raw = APIRequestFactory(enforce_csrf_checks=True).post(ROOT+'previews/', payload, content_type='application/json', HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    raw.META['CONTENT_LENGTH'] = declared_length
    raw._stream = BoundedStream(payload)
    raw.user = user
    raw.session = client.session
    raw.COOKIES['csrftoken'] = token
    response = NetworkView.as_view(action='preview')(raw)
    assert response.status_code == 413 and response.data['code'] == 'request_too_large'
    assert reads and all(0 <= size <= 32769 for size in reads)
    assert not NetworkPolicyPreview.objects.exists()
