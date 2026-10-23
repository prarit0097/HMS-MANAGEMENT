from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.models import Organisation, Branch, Membership, Patient, Bed, Appointment, Admission, AuditEvent

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    org = Organisation.objects.create(name='Synthetic reliability')
    branch = Branch.objects.create(organisation=org, code='MAIN', name='Main')
    other = Branch.objects.create(organisation=org, code='OTHER', name='Other')
    actor = get_user_model().objects.create_user(username='synthetic-reliability')
    Membership.objects.create(user=actor, branch=branch, role='reception')
    client = APIClient()
    client.force_login(actor)
    patient = Patient.objects.create(branch=branch, full_name='Synthetic Patient')
    bed = Bed.objects.create(branch=branch, number='1', room_number='1')
    return client, actor, branch, other, patient, bed


def creation(workspace, kind):
    _, _, branch, _, patient, bed = workspace
    return {
        'patients': {'branch': str(branch.pk), 'full_name': 'Synthetic New', 'phone': '0000000000'},
        'appointments': {'branch': str(branch.pk), 'patient': str(patient.pk), 'doctor_name': 'Synthetic', 'scheduled_at': '2026-10-23T10:00:00+05:30'},
        'admissions': {'patient': str(patient.pk), 'bed': str(bed.pk), 'treating_doctor': 'Synthetic'},
    }[kind]


def post(client, kind, payload, key):
    return client.post(f'/api/v1/{kind}/', payload, format='json', HTTP_IDEMPOTENCY_KEY=key)


@pytest.mark.parametrize('kind,model,action', [('patients', Patient, 'patient.created'), ('appointments', Appointment, 'appointment.created'), ('admissions', Admission, 'admission.created')])
def test_same_key_replays_same_result_without_second_write_or_audit(workspace, kind, model, action):
    client = workspace[0]
    body = creation(workspace, kind)
    key = str(uuid4())
    before = model.objects.count()
    first = post(client, kind, body, key)
    replay = post(client, kind, dict(reversed(list(body.items()))), key)
    assert first.status_code == replay.status_code == 201
    assert replay.json()['id'] == first.json()['id']
    assert model.objects.count() == before + 1
    assert AuditEvent.objects.filter(action=action).count() == 1


@pytest.mark.parametrize('kind', ['patients', 'appointments', 'admissions'])
def test_changed_body_conflicts_and_original_key_still_replays(workspace, kind):
    client = workspace[0]
    body = creation(workspace, kind)
    key = str(uuid4())
    original = post(client, kind, body, key)
    changed = {**body, 'full_name' if kind == 'patients' else 'reason': 'Changed Synthetic'}
    assert post(client, kind, changed, key).status_code == 409
    assert post(client, kind, body, key).json()['id'] == original.json()['id']


@pytest.mark.parametrize('key', ['', 'bad', 'a' * 1000, '{00000000-0000-0000-0000-000000000000}', '0' * 32])
def test_malformed_or_oversized_key_is_rejected_without_write(workspace, key):
    client = workspace[0]
    assert post(client, 'patients', creation(workspace, 'patients'), key).status_code == 400
    assert Patient.objects.count() == 1
    assert AuditEvent.objects.count() == 0


def test_validation_failure_does_not_consume_key(workspace):
    client = workspace[0]
    key = str(uuid4())
    invalid = {**creation(workspace, 'patients'), 'age': 200}
    assert post(client, 'patients', invalid, key).status_code == 400
    corrected = {**invalid, 'age': 50}
    assert post(client, 'patients', corrected, key).status_code == 201
    assert post(client, 'patients', corrected, key).status_code == 201
    assert Patient.objects.count() == 2


@pytest.mark.parametrize('kind', ['patients', 'appointments', 'admissions'])
@pytest.mark.parametrize('revocation', ['membership', 'disabled', 'doctor', 'master_admin'])
def test_replay_rechecks_current_action_and_identity(workspace, kind, revocation):
    client, actor, *_ = workspace
    body = creation(workspace, kind)
    key = str(uuid4())
    assert post(client, kind, body, key).status_code == 201
    if revocation == 'membership':
        Membership.objects.filter(user=actor).delete()
    elif revocation == 'disabled':
        actor.is_active = False
        actor.save(update_fields=['is_active'])
    else:
        Membership.objects.filter(user=actor).update(role=revocation)
    response = post(client, kind, body, key)
    assert response.status_code in (401, 403)
    assert 'id' not in response.json()


def test_replay_checks_original_result_visibility_even_with_other_branch_grant(workspace):
    client, actor, branch, other, *_ = workspace
    body = creation(workspace, 'patients')
    key = str(uuid4())
    assert post(client, 'patients', body, key).status_code == 201
    Membership.objects.filter(user=actor, branch=branch).delete()
    Membership.objects.create(user=actor, branch=other, role='reception')
    assert post(client, 'patients', body, key).status_code in (403, 404)


def test_replay_serializes_current_result_without_storing_payload(workspace):
    from apps.core.models import IdempotencyRecord
    client = workspace[0]
    body = creation(workspace, 'patients')
    key = str(uuid4())
    original = post(client, 'patients', body, key)
    Patient.objects.filter(pk=original.json()['id']).update(full_name='Corrected Synthetic')
    assert post(client, 'patients', body, key).json()['full_name'] == 'Corrected Synthetic'
    record = IdempotencyRecord.objects.get()
    assert len(record.fingerprint) == 64
    assert str(record.result_id) == original.json()['id']
    assert body['full_name'] not in str(record.__dict__)
    assert body['phone'] not in str(record.__dict__)


def test_different_users_and_operations_have_independent_keys(workspace):
    client, actor, branch, *_ = workspace
    key = str(uuid4())
    body = creation(workspace, 'patients')
    original = post(client, 'patients', body, key)
    other_actor = get_user_model().objects.create_user(username='synthetic-second')
    Membership.objects.create(user=other_actor, branch=branch, role='reception')
    client.force_login(other_actor)
    second = post(client, 'patients', body, key)
    assert second.status_code == 201
    assert second.json()['id'] != original.json()['id']
    assert post(client, 'appointments', creation(workspace, 'appointments'), key).status_code == 201


def test_service_failure_rolls_back_key_so_corrected_admission_can_retry(workspace):
    client, _, _, _, _, bed = workspace
    key = str(uuid4())
    body = creation(workspace, 'admissions')
    bed.status = 'blocked'
    bed.save()
    assert post(client, 'admissions', body, key).status_code == 409
    bed.status = 'available'
    bed.save()
    assert post(client, 'admissions', body, key).status_code == 201
    assert post(client, 'admissions', body, key).status_code == 201
    assert Admission.objects.count() == 1


def test_omitted_key_preserves_legacy_create(workspace):
    client = workspace[0]
    for _ in range(2):
        assert client.post('/api/v1/patients/', creation(workspace, 'patients'), format='json').status_code == 201
    assert Patient.objects.count() == 3


def test_bed_status_filters_scoped_count_before_pagination(workspace):
    client, _, branch, other, *_ = workspace
    Bed.objects.bulk_create([Bed(branch=branch, number=str(i), room_number='0', status='occupied') for i in range(2, 105)])
    Bed.objects.create(branch=branch, number='105', room_number='1')
    Bed.objects.create(branch=other, number='foreign', room_number='1')
    response = client.get('/api/v1/beds/?status=available&limit=1&offset=1')
    assert response.status_code == 200
    assert response.json()['count'] == 2
    assert len(response.json()['results']) == 1
    assert response.json()['results'][0]['status'] == 'available'
    assert response.json()['results'][0]['branch'] == str(branch.pk)
    assert client.get('/api/v1/beds/?status=reserved').json()['count'] == 0


@pytest.mark.parametrize('status', ['unknown', 'AVAILABLE', ''])
def test_invalid_bed_status_is_rejected(workspace, status):
    assert workspace[0].get('/api/v1/beds/', {'status': status}).status_code == 400

@pytest.mark.parametrize('path,field', [('patients/?limit=-1', 'limit'), ('patients/?q=' + 'x' * 201, 'q'), ('appointments/?date=invalid', 'date')])
def test_validation_field_errors_match_published_array_schema(workspace, path, field):
    response = workspace[0].get('/api/v1/' + path)
    assert response.status_code == 400
    assert isinstance(response.json()['field_errors'][field], list)
    assert all(isinstance(message, str) for message in response.json()['field_errors'][field])


def test_nested_validation_errors_are_plain_message_arrays():
    from rest_framework.exceptions import ValidationError
    from apps.core.api import safe_exception_handler
    response = safe_exception_handler(ValidationError({'field': {'child': ['First message', {'nested': 'Second message'}]}}), {})
    assert response.status_code == 400
    assert response.data['code'] == 'invalid'
    assert response.data['field_errors'] == {'field': ['First message', 'Second message']}
