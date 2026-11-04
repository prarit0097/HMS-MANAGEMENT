"""Synthetic genuine-session setup; supplies no document authority shortcuts."""
from types import SimpleNamespace
import json
from contextlib import contextmanager
from datetime import timezone as datetime_timezone
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Branch, Membership, Organisation, Patient

CREATE_BODY = json.dumps(dict(category='registration', filename='synthetic-http.png',
    media_type='image/png', size_bytes=128, sha256='a' * 64)).encode()
WITHDRAW_BODY = b'{"expected_version":1,"reason":"Synthetic HTTP correction"}'


@pytest.fixture
def http_workspace(settings):
    cache.clear()
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.HMS_DOCUMENT_METADATA_ENABLED = False
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    org = Organisation.objects.create(name='Synthetic HTTP hospital')
    branch = Branch.objects.create(organisation=org, name='Synthetic HTTP desk', code='H01')
    user = get_user_model().objects.create_user(username='synthetic-http', password='Synthetic-http-passphrase')
    membership = Membership.objects.create(user=user, branch=branch, role='reception')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic HTTP patient')
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    session = client.session
    session['auth_epoch'] = 0
    session.save()
    csrf = client.get('/api/v1/auth/csrf/')
    assert csrf.status_code == 200
    assert client.get('/api/v1/auth/me/').status_code == 200
    base = f'/api/v1/patients/{patient.pk}/documents/'
    return SimpleNamespace(client=client, user=user, branch=branch, org=org,
        membership=membership, patient=patient, base=base, document_id=str(uuid4()))


def route(workspace, shape):
    if shape == 'collection':
        return workspace.base
    detail = workspace.base + workspace.document_id + '/'
    return detail if shape == 'detail' else detail + 'withdraw/'


def request(workspace, method, shape='collection', *, data=None, key=None, csrf=True, query=''):
    headers = {'HTTP_IDEMPOTENCY_KEY': key or str(uuid4())}
    if csrf:
        headers['HTTP_X_CSRFTOKEN'] = workspace.client.cookies['csrftoken'].value
    body = data if data is not None else (WITHDRAW_BODY if shape == 'withdraw' else CREATE_BODY)
    if method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        body = b''
    return workspace.client.generic(method, route(workspace, shape) + query, data=body,
        content_type='application/json', **headers)


@contextmanager
def one_allowance(workspace):
    """Observe real persisted admission, including a UTC minute reset per call.

    No authority/rate decision or clock is replaced. Callers separately check
    response and business/audit effects; a reset must still persist exactly one.
    """
    from apps.core.models import DocumentMetadataRateWindow
    rows = DocumentMetadataRateWindow.objects.filter(actor=workspace.user)
    before = rows.values_list('window_started_at', 'admitted_count').first()
    started = timezone.now().astimezone(datetime_timezone.utc).replace(second=0, microsecond=0)
    yield
    finished = timezone.now().astimezone(datetime_timezone.utc).replace(second=0, microsecond=0)
    window, count = rows.values_list('window_started_at', 'admitted_count').get()
    assert started <= window <= finished
    assert count == (before[1] + 1 if before and before[0] == window else 1)


def metadata_counts():
    from apps.core.models import (DocumentMetadataRateWindow, PatientDocumentIntent,
        DocumentIntentReceipt, DocumentAccessEvent)
    return tuple(model.objects.count() for model in (DocumentMetadataRateWindow,
        PatientDocumentIntent, DocumentIntentReceipt, DocumentAccessEvent))


def local_headers(response, allow=None):
    assert response['Cache-Control'] == 'no-store'
    assert 'Cookie' in [value.strip() for value in response.get('Vary', '').split(',')]
    assert response['X-Content-Type-Options'] == 'nosniff'
    assert response['Content-Type'].split(';')[0] == 'application/json'
    assert not response.has_header('ETag') and not response.has_header('Last-Modified')
    if allow is not None:
        assert response['Allow'] == allow
