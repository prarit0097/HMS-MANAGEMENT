"""Real PostgreSQL/session/CSRF HTTP acceptance; existing services own race tests."""
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, OperationalError
from django.utils import timezone
from rest_framework.test import APIClient

from document_http_fixtures import (http_workspace, request, metadata_counts,
    CREATE_BODY, WITHDRAW_BODY, local_headers, one_allowance)

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
    def call(*args, **kwargs):
        from apps.core.models import DocumentAccessEvent
        before = DocumentAccessEvent.objects.count()
        with one_allowance(http_workspace):
            response = request(http_workspace, *args, **kwargs)
        assert response.status_code in (200, 201)
        assert DocumentAccessEvent.objects.count() == before + 1
        local_headers(response)
        return response
    key = str(uuid4())
    created = call('POST', key=key)
    assert created.status_code == 201
    local_headers(created)
    intent = created.json()['document']
    assert set(created.json()) == {'server_time', 'capabilities', 'document'}
    assert not intent['can_upload'] and not intent['can_download']
    http_workspace.document_id = intent['id']
    replay = call('POST', key=key)
    assert replay.status_code == 201 and replay.json()['document'] == intent
    listed = call('GET')
    assert listed.status_code == 200 and listed.json()['results'] == [intent]
    detail = call('GET', 'detail')
    assert detail.status_code == 200 and detail.json()['document'] == intent
    withdrawal_key = str(uuid4())
    withdrawn = call('POST', 'withdraw', key=withdrawal_key)
    assert withdrawn.status_code == 200
    assert withdrawn.json()['document']['status'] == 'withdrawn'
    assert withdrawn.json()['document']['version'] == 2
    repeated = call('POST', 'withdraw', key=withdrawal_key)
    assert repeated.status_code == 200 and repeated.json()['document'] == withdrawn.json()['document']
    assert metadata_counts() == (1, 1, 2, 6)


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


def seed_intent(workspace, **overrides):
    from apps.core.models import PatientDocumentIntent
    now = timezone.now()
    values = dict(patient=workspace.patient, created_by=workspace.user, category='registration',
        declared_filename='synthetic-seeded.png', declared_media_type='image/png',
        declared_size_bytes=128, declared_sha256='a' * 64,
        created_at=now, expires_at=now + timedelta(minutes=30))
    values.update(overrides)
    return PatientDocumentIntent.objects.create(**values)


def assert_error(response, code, status):
    from apps.core.document_authority import _ERRORS
    assert response.status_code == status
    assert response.json() == {'code': code, 'message': _ERRORS[code][1]}
    local_headers(response)


@pytest.mark.parametrize('shape,method', [('collection', 'GET'), ('collection', 'POST'), ('detail', 'GET'), ('withdraw', 'POST')])
def test_disabled_valid_http_never_queries_business_objects(http_workspace, shape, method):
    observed = []
    def inspect(execute, sql, params, many, context):
        observed.append(sql.upper())
        return execute(sql, params, many, context)
    with one_allowance(http_workspace), connection.execute_wrapper(inspect):
        response = request(http_workspace, method, shape)
    assert_error(response, 'document_metadata_unavailable', 503)
    forbidden = ('CORE_PATIENT"', 'CORE_PATIENTDOCUMENTINTENT',
        'CORE_DOCUMENTINTENTRECEIPT', 'CORE_DOCUMENTACCESSEVENT')
    assert observed
    assert not any(table in sql for sql in observed for table in forbidden)


@pytest.mark.parametrize('scope', ['same_org_other_branch', 'other_org', 'moved_patient', 'revoked_membership'])
def test_current_exact_branch_scope_is_concealed_after_admission(http_workspace, settings, scope):
    from apps.core.models import Branch, Membership, Organisation, Patient
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    document = seed_intent(http_workspace)
    http_workspace.document_id = str(document.pk)
    org = http_workspace.org if scope == 'same_org_other_branch' else Organisation.objects.create(name='Other synthetic hospital')
    branch = Branch.objects.create(organisation=org, name='Other synthetic branch', code='OTHER')
    if scope == 'revoked_membership':
        # Preserve global action authority on another branch; the old target is concealed.
        Membership.objects.create(user=http_workspace.user, branch=branch, role='reception')
        http_workspace.membership.is_active = False
        http_workspace.membership.save(update_fields=['is_active'])
    elif scope == 'moved_patient':
        Patient.objects.filter(pk=http_workspace.patient.pk).update(branch=branch)
    else:
        target = Patient.objects.create(branch=branch, full_name='Other synthetic patient')
        http_workspace.base = f'/api/v1/patients/{target.pk}/documents/'
    before = metadata_counts()[1:]
    with one_allowance(http_workspace):
        response = request(http_workspace, 'GET', 'detail')
    assert_error(response, 'not_found', 404)
    assert metadata_counts()[1:] == before


def test_replay_rechecks_current_membership_instead_of_disclosing_receipt(http_workspace, settings):
    from apps.core.models import Branch, Membership
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    key = str(uuid4())
    assert request(http_workspace, 'POST', key=key).status_code == 201
    branch = Branch.objects.create(organisation=http_workspace.org, name='Synthetic retained global grant', code='GLOBAL')
    Membership.objects.create(user=http_workspace.user, branch=branch, role='reception')
    http_workspace.membership.is_active = False
    http_workspace.membership.save(update_fields=['is_active'])
    before = metadata_counts()[1:]
    with one_allowance(http_workspace):
        response = request(http_workspace, 'POST', key=key)
    assert_error(response, 'not_found', 404)
    assert metadata_counts()[1:] == before


@pytest.mark.parametrize('case,code', [('version', 'version_conflict'), ('withdrawn', 'intent_state_conflict'),
    ('expired', 'intent_state_conflict'), ('noncreator', 'permission_denied')])
def test_withdrawal_preserves_creator_version_and_state_boundaries(http_workspace, settings, case, code):
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    values = {}
    if case == 'noncreator':
        values['created_by'] = get_user_model().objects.create_user(username='synthetic-other-creator')
    if case == 'expired':
        values.update(created_at=timezone.now() - timedelta(minutes=31), expires_at=timezone.now() - timedelta(minutes=1))
        # Use one exact timestamp for the model's expiry equality constraint.
        values['expires_at'] = values['created_at'] + timedelta(minutes=30)
    if case == 'withdrawn':
        created = timezone.now() - timedelta(seconds=1)
        values.update(status='withdrawn', version=2, withdrawn_at=timezone.now(),
            withdrawn_by=http_workspace.user, withdrawal_reason='Synthetic prior correction',
            created_at=created, expires_at=created + timedelta(minutes=30))
    document = seed_intent(http_workspace, **values)
    http_workspace.document_id = str(document.pk)
    before = metadata_counts()[1:]
    body = json.dumps({'expected_version': 2 if case == 'version' else 1,
        'reason': 'Synthetic HTTP correction'}).encode()
    with one_allowance(http_workspace):
        response = request(http_workspace, 'POST', 'withdraw', data=body)
    assert_error(response, code, 403 if case == 'noncreator' else 409)
    assert metadata_counts()[1:] == before
    document.refresh_from_db()
    assert document.version == (2 if case == 'withdrawn' else 1)


def test_cursor_page_and_patient_binding_through_http(http_workspace, settings):
    from apps.core.models import Patient
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    documents = [seed_intent(http_workspace) for _ in range(3)]
    with one_allowance(http_workspace):
        first = request(http_workspace, 'GET', query='?limit=2')
    assert first.status_code == 200
    payload = first.json()
    assert [row['id'] for row in payload['results']] == [str(row.pk) for row in reversed(documents[1:])]
    assert payload['has_more'] is True and payload['next_cursor']
    cursor = payload['next_cursor']
    with one_allowance(http_workspace):
        second = request(http_workspace, 'GET', query='?limit=2&cursor=' + cursor)
    assert second.status_code == 200
    assert [row['id'] for row in second.json()['results']] == [str(documents[0].pk)]
    assert second.json()['has_more'] is False and second.json()['next_cursor'] is None
    other = Patient.objects.create(branch=http_workspace.branch, full_name='Synthetic cursor binding')
    http_workspace.base = f'/api/v1/patients/{other.pk}/documents/'
    before = metadata_counts()
    response = request(http_workspace, 'GET', query='?limit=2&cursor=' + cursor)
    assert_error(response, 'validation_error', 400)
    assert metadata_counts() == before


def test_http_patient_quota_and_exact_retry_header(http_workspace, settings):
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    for _ in range(20):
        seed_intent(http_workspace)
    before = metadata_counts()[1:]
    with one_allowance(http_workspace):
        response = request(http_workspace, 'POST')
    assert_error(response, 'rate_limited', 429)
    assert 1 <= int(response['Retry-After']) <= 3600
    assert str(int(response['Retry-After'])) == response['Retry-After']
    assert metadata_counts()[1:] == before


def test_real_allowance_window_resets_without_assuming_whole_lifecycle_one_minute(http_workspace):
    from apps.core.models import DocumentMetadataRateWindow
    previous = timezone.now().replace(second=0, microsecond=0) - timedelta(minutes=1)
    DocumentMetadataRateWindow.objects.create(actor=http_workspace.user,
        window_started_at=previous, admitted_count=58)
    with one_allowance(http_workspace):
        response = request(http_workspace, 'GET')
    assert_error(response, 'document_metadata_unavailable', 503)
    row = DocumentMetadataRateWindow.objects.get(actor=http_workspace.user)
    assert row.window_started_at > previous and row.admitted_count == 1
    assert metadata_counts()[1:] == (0, 0, 0)


def test_http_key_conflict_does_not_create_second_receipt_or_event(http_workspace, settings):
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    key = str(uuid4())
    assert request(http_workspace, 'POST', key=key).status_code == 201
    changed = json.loads(CREATE_BODY)
    changed['filename'] = 'changed-synthetic.png'
    before = metadata_counts()[1:]
    with one_allowance(http_workspace):
        response = request(http_workspace, 'POST', key=key, data=json.dumps(changed).encode())
    assert_error(response, 'idempotency_conflict', 409)
    assert metadata_counts()[1:] == before


@pytest.mark.parametrize('shape,method', [('collection', 'GET'), ('collection', 'POST'), ('detail', 'GET'), ('withdraw', 'POST')])
def test_real_audit_insert_failure_never_discloses_or_keeps_business_writes(http_workspace, settings, shape, method):
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    document = seed_intent(http_workspace)
    http_workspace.document_id = str(document.pk)
    before = metadata_counts()[1:]
    attempted = []
    def fail_event(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith('INSERT') and 'CORE_DOCUMENTACCESSEVENT' in sql.upper():
            attempted.append(True)
            # Actual PostgreSQL statement error poisons and rolls back phase B.
            return execute('SELECT 1/0', (), False, context)
        return execute(sql, params, many, context)
    with one_allowance(http_workspace), connection.execute_wrapper(fail_event):
        response = request(http_workspace, method, shape)
    assert attempted == [True]
    assert_error(response, 'document_metadata_unavailable', 503)
    assert metadata_counts()[1:] == before
    document.refresh_from_db()
    assert (document.status, document.version) == ('pending', 1)


@pytest.mark.parametrize('outcome', ['commit', 'rollback'])
def test_labelled_real_business_outcome_simulated_lost_ack_http_reconciliation(http_workspace, settings, monkeypatch, outcome):
    """Driver ACK fault after real outcome; no claim of a real network outage."""
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    key = str(uuid4())
    original_commit, original_rollback = connection.commit, connection.rollback
    business, faults = [], []
    def observe(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.lstrip().upper().startswith('INSERT') and 'CORE_DOCUMENTINTENTRECEIPT' in sql.upper():
            business.append(True)
            if outcome == 'rollback':
                raise OperationalError('Synthetic phase B failure before actual rollback')
        return result
    def commit():
        original_commit()
        if business and outcome == 'commit':
            faults.append('commit')
            raise OperationalError('Synthetic lost ACK after actual phase B commit')
    def rollback():
        original_rollback()
        if business and outcome == 'rollback':
            faults.append('rollback')
            raise OperationalError('Synthetic lost ACK after actual phase B rollback')
    with monkeypatch.context() as patch:
        patch.setattr(connection, 'commit', commit)
        patch.setattr(connection, 'rollback', rollback)
        with one_allowance(http_workspace), connection.execute_wrapper(observe):
            response = request(http_workspace, 'POST', key=key)
    assert faults == [outcome] and business == [True]
    assert_error(response, 'document_metadata_unavailable', 503)
    assert metadata_counts()[1:] == ((1, 1, 1) if outcome == 'commit' else (0, 0, 0))
    with one_allowance(http_workspace):
        reconciled = request(http_workspace, 'POST', key=key)
    assert reconciled.status_code == 201
    assert metadata_counts()[1:] == (1, 1, 2 if outcome == 'commit' else 1)


@pytest.mark.parametrize('code,status,message,retry', [
    ('not_authenticated', 401, 'Your session ended. Sign in again.', None),
    ('permission_denied', 403, 'You do not have access to this action.', None),
    ('network_denied', 403, 'Access is not available from this network. Contact your administrator.', None),
    ('document_metadata_unavailable', 503, 'Document details are unavailable. Try again later.', None),
    ('validation_error', 400, 'Check the highlighted details.', None),
    ('not_found', 404, 'This record is unavailable.', None),
    ('request_too_large', 413, 'This request is too large.', None),
    ('rate_limited', 429, 'Too many requests. Try again shortly.', 1),
    ('rate_limited', 429, 'Too many requests. Try again shortly.', 3600),
    ('idempotency_conflict', 409, 'This request could not be repeated. Refresh before continuing.', None),
    ('version_conflict', 409, 'The record changed. Refresh before continuing.', None),
    ('intent_state_conflict', 409, 'This request can no longer be withdrawn.', None),
])
def test_typed_service_error_exact_vocabulary_over_real_session_csrf(http_workspace, monkeypatch, code, status, message, retry):
    from importlib import import_module
    from apps.core.document_authority import DocumentServiceError
    adapter = import_module('apps.core.document_api')  # absent module is test RED, never collection/setup
    invoked = []
    def fail(*args, **kwargs):
        invoked.append((args, kwargs))
        raise DocumentServiceError(code, status, message, retry)
    monkeypatch.setattr(adapter, 'create_document_intent', fail)
    before = metadata_counts()
    response = request(http_workspace, 'POST')
    assert len(invoked) == 1
    assert response.status_code == status
    assert response.json() == {'code': code, 'message': message}
    assert response.get('Retry-After') == (str(retry) if retry is not None else None)
    local_headers(response)
    assert metadata_counts() == before  # this typed-failure injection never admits


@pytest.mark.parametrize('malformation', ['unknown_code', 'status', 'message', 'retry_bool', 'retry_large', 'unexpected'])
def test_untrusted_service_failure_tuple_cannot_leak_or_set_retry_header(http_workspace, monkeypatch, malformation):
    from importlib import import_module
    from apps.core.document_authority import DocumentServiceError
    adapter = import_module('apps.core.document_api')
    error = DocumentServiceError('rate_limited', 429, 'Too many requests. Try again shortly.', 1)
    if malformation == 'unknown_code':
        error.code = 'synthetic_sensitive_code'
    elif malformation == 'status':
        error.status = 200
    elif malformation == 'message':
        error.message = 'Synthetic sensitive SQL/body detail'
    elif malformation == 'retry_bool':
        error.retry_after = True
    elif malformation == 'retry_large':
        error.retry_after = 3601
    else:
        error = RuntimeError('Synthetic sensitive SQL/body detail')
    invoked = []
    def fail(*args, **kwargs):
        invoked.append(True)
        raise error
    monkeypatch.setattr(adapter, 'create_document_intent', fail)
    before = metadata_counts()
    response = request(http_workspace, 'POST')
    assert invoked == [True]
    assert_error(response, 'document_metadata_unavailable', 503)
    assert not response.has_header('Retry-After')
    assert metadata_counts() == before
