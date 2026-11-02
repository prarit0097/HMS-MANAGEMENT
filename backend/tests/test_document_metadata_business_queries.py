"""Explain exact SQL emitted by real services against isolated synthetic history.

This is a bounded PG17 measurement, not a hospital capacity guarantee. No
handwritten quota/list SELECT can substitute for capturing the service query.
"""
import json
from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.db import SessionStore
from django.db import connection, transaction
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.core.document_authority import capture_document_context, DocumentServiceError
from apps.core.models import Branch, Membership, Organisation, Patient, PatientDocumentIntent
from apps.core.network_models import NetworkPolicyState
from apps.security.network_policy import policy_digest

pytestmark = pytest.mark.django_db(transaction=True)
BODY = b'{"category":"registration","filename":"synthetic.png","media_type":"image/png","size_bytes":1,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'


@pytest.fixture(autouse=True)
def actual_pg_only():
    if connection.vendor != 'postgresql' or connection.pg_version < 170000:
        pytest.skip('Actual PostgreSQL>=17 EXPLAIN ANALYZE BUFFERS acceptance required; SQLite cannot substitute.')


def _history(settings, monkeypatch, api):
    # Called only AFTER each test's runtime service import. Missing feature is
    # a test failure, never a fixture setup error or needless 31k-row load.
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.DATABASE_ROUTERS = []
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    now = timezone.now().replace(second=30, microsecond=0)
    monkeypatch.setattr(timezone, 'now', lambda: now)
    user = get_user_model().objects.create_user(username='synthetic-query-worker', password='Synthetic-query-28!')
    patients, organisations, branches = [], [], []
    for number in range(3):
        org = Organisation.objects.create(name=f'Synthetic query org {number}')
        branch = Branch.objects.create(organisation=org, name='Desk', code=f'QUERY{number}')
        organisations.append(org)
        branches.append(branch)
        group = [Patient(branch=branch, full_name=f'Synthetic query patient {number}-{index}') for index in range(60)]
        Patient.objects.bulk_create(group)
        patients.append(group)
    Membership.objects.create(user=user, branch=branches[0], role='reception')
    request = RequestFactory().get('/synthetic-query', REMOTE_ADDR='127.0.0.1')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    allow = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
    NetworkPolicyState.objects.update_or_create(pk=1, defaults={
        'confirmed_policy': allow, 'confirmed_policy_digest': policy_digest(allow), 'pending_change': None})
    rows = []
    # 30,060 retained pending-but-expired rows, spread across all 180 patients.
    for group in patients:
        for patient in group:
            for index in range(167):
                created = now - timedelta(days=2, seconds=index)
                rows.append(_intent(patient, user, created))
    # Exactly 1000 rolling creations in org0. Only 20 active, all on patient0.
    # Withdrawn creation history must still count towards organisation quota.
    for index in range(1000):
        patient = patients[0][0] if index < 20 else patients[0][index % 60]
        created = now - timedelta(seconds=100 + index)
        row = _intent(patient, user, created)
        if index >= 20:
            row.status = 'withdrawn'
            row.version = 2
            row.withdrawn_at = created + timedelta(seconds=1)
            row.withdrawn_by = user
            row.withdrawal_reason = 'Synthetic retained quota history'
        rows.append(row)
    PatientDocumentIntent.objects.bulk_create(rows, batch_size=1000)
    assert PatientDocumentIntent.objects.count() == 31060
    with connection.cursor() as cursor:
        for model in (Organisation, Branch, Patient, PatientDocumentIntent):
            cursor.execute('ANALYZE ' + connection.ops.quote_name(model._meta.db_table))
    return SimpleNamespace(api=api, now=now, request=request, user=user, patient=patients[0][0],
        organisations=organisations, patients=patients, rows=31060)


def _intent(patient, user, created):
    return PatientDocumentIntent(patient=patient, created_by=user, category='registration',
        declared_filename='synthetic.png', declared_media_type='image/png', declared_size_bytes=1,
        declared_sha256='a' * 64, created_at=created, expires_at=created + timedelta(minutes=30))


def _selects(queries):
    return [item['sql'] for item in queries if item['sql'].lstrip().upper().startswith('SELECT')
            and 'CORE_PATIENTDOCUMENTINTENT' in item['sql'].upper()]


def _explain(sql, bound, record_property, label):
    # EXPLAIN the captured SQL verbatim, including its actual WHERE/order/LIMIT.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='3s'")
            cursor.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + sql)
            value = cursor.fetchone()[0]
    document = json.loads(value) if isinstance(value, str) else value
    plan = document[0]
    assert plan['Plan']['Node Type'] == 'Limit', 'Service failed to bound its outer query'
    assert plan['Plan']['Actual Rows'] <= bound
    assert plan['Execution Time'] < 3000
    assert 'Shared Hit Blocks' in plan['Plan']
    record_property(label, json.dumps({'dataset': {'organisations': 3, 'patients_per_organisation': 60,
        'retained_rows': 31060, 'expired_rows': 30060}, 'sql': sql, 'measurement': plan}, default=str))
    return plan


def test_actual_service_active20_and_rolling1000_quota_queries_under_three_seconds(settings, monkeypatch, record_property):
    api = import_module('apps.core.document_services')
    history = _history(settings, monkeypatch, api)
    context = capture_document_context(history.request, 'intent.create')
    with CaptureQueriesContext(connection) as captured, pytest.raises(DocumentServiceError) as denied:
        history.api.create_document_intent(context, str(history.patient.pk), str(uuid4()), BODY)
    assert (denied.value.code, denied.value.status) == ('rate_limited', 429)
    selects = _selects(captured.captured_queries)
    active = [sql for sql in selects if 'LIMIT 20' in sql.upper() and 'EXPIRES_AT' in sql.upper()]
    rolling = [sql for sql in selects if 'LIMIT 1000' in sql.upper() and 'CORE_ORGANISATION' in sql.upper()]
    # An ORM relation predicate may compare branch.organisation_id without an
    # organisation-table join; accept that exact emitted SQL as well.
    if not rolling:
        rolling = [sql for sql in selects if 'LIMIT 1000' in sql.upper() and 'ORGANISATION_ID' in sql.upper()]
    assert len(active) == len(rolling) == 1, selects
    assert _explain(active[0], 20, record_property, 'active20')['Plan']['Actual Rows'] == 20
    assert _explain(rolling[0], 1000, record_property, 'rolling1000')['Plan']['Actual Rows'] == 1000


def test_actual_service_descending_keyset101_query_and_no_total_count(settings, monkeypatch, record_property):
    api = import_module('apps.core.document_services')
    history = _history(settings, monkeypatch, api)
    context = capture_document_context(history.request, 'intent.list')
    with CaptureQueriesContext(connection) as first_queries:
        first = history.api.list_document_intents(context, str(history.patient.pk), [('limit', '100')])
    body = json.loads(first.body)
    assert first.status == 200 and len(body['results']) == 100 and body['has_more'] is True
    assert type(body['next_cursor']) is str
    next_context = capture_document_context(history.request, 'intent.list')
    with CaptureQueriesContext(connection) as next_queries:
        second = history.api.list_document_intents(next_context, str(history.patient.pk),
            [('limit', '100'), ('cursor', body['next_cursor'])])
    next_body = json.loads(second.body)
    assert next_body['results']
    assert not {row['id'] for row in body['results']} & {row['id'] for row in next_body['results']}
    for label, captured in [('first_keyset101', first_queries), ('next_keyset101', next_queries)]:
        selects = _selects(captured.captured_queries)
        assert not any('COUNT(' in sql.upper() for sql in selects)
        bounded = [sql for sql in selects if 'LIMIT 101' in sql.upper()]
        assert len(bounded) == 1, selects
        assert 'ORDER BY' in bounded[0].upper() and 'DESC' in bounded[0].upper()
        _explain(bounded[0], 101, record_property, label)
