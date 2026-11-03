"""Initial real PostgreSQL HTTP RED batch; later framing/CSRF/fault matrix pending."""
import json
from uuid import uuid4

import pytest
from django.db import connection
from rest_framework.test import APIClient

from document_http_fixtures import (http_workspace, request, metadata_counts,
    CREATE_BODY, WITHDRAW_BODY, local_headers)

pytestmark = [pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(connection.vendor != 'postgresql', reason='Actual PostgreSQL HTTP business acceptance only')]


@pytest.mark.parametrize('shape,method', [('collection', 'GET'), ('collection', 'POST'), ('detail', 'GET'), ('withdraw', 'POST')])
def test_valid_disabled_http_commits_only_allowance_then503(http_workspace, shape, method):
    from apps.core.models import DocumentMetadataRateWindow
    before = metadata_counts()
    response = request(http_workspace, method, shape)
    assert response.status_code == 503
    assert response.json() == {'code': 'document_metadata_unavailable', 'message': 'Document details are unavailable. Try again later.'}
    local_headers(response)
    after = metadata_counts()
    assert after == (before[0] + 1, *before[1:])
    assert DocumentMetadataRateWindow.objects.get(actor=http_workspace.user).admitted_count == 1


def test_http_four_operation_lifecycle_and_keyed_replays(http_workspace, settings):
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    key = str(uuid4())
    created = request(http_workspace, 'POST', key=key)
    assert created.status_code == 201
    local_headers(created)
    intent = created.json()['document']
    assert set(created.json()) == {'server_time', 'capabilities', 'document'}
    assert not intent['can_upload'] and not intent['can_download']
    http_workspace.document_id = intent['id']
    replay = request(http_workspace, 'POST', key=key)
    assert replay.status_code == 201 and replay.json()['document'] == intent
    listed = request(http_workspace, 'GET')
    assert listed.status_code == 200 and listed.json()['results'] == [intent]
    detail = request(http_workspace, 'GET', 'detail')
    assert detail.status_code == 200 and detail.json()['document'] == intent
    withdrawal_key = str(uuid4())
    withdrawn = request(http_workspace, 'POST', 'withdraw', key=withdrawal_key)
    assert withdrawn.status_code == 200
    assert withdrawn.json()['document']['status'] == 'withdrawn'
    assert withdrawn.json()['document']['version'] == 2
    repeated = request(http_workspace, 'POST', 'withdraw', key=withdrawal_key)
    assert repeated.status_code == 200 and repeated.json()['document'] == withdrawn.json()['document']
    assert metadata_counts() == (1, 1, 2, 6)
    from apps.core.models import DocumentMetadataRateWindow
    assert DocumentMetadataRateWindow.objects.get(actor=http_workspace.user).admitted_count == 6


def test_real_password_login_then_document_command(http_workspace, settings):
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    client = APIClient(enforce_csrf_checks=True)
    assert client.get('/api/v1/auth/csrf/').status_code == 200
    headers = {'HTTP_X_CSRFTOKEN': client.cookies['csrftoken'].value}
    login = client.post('/api/v1/auth/login/', {'username': http_workspace.user.username,
        'password': 'Synthetic-http-passphrase'}, format='json', **headers)
    assert login.status_code == 200
    assert client.get('/api/v1/auth/me/').status_code == 200
    response = client.post(http_workspace.base, data=CREATE_BODY, content_type='application/json',
        HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value, HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert response.status_code == 201
    assert response.json()['document']['patient_id'] == str(http_workspace.patient.pk)
