"""Synthetic configuration API regressions; no clinical data in admin responses."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient
from apps.core.models import Organisation, Branch, Membership, Bed, Patient, Admission, AuditEvent

pytestmark = pytest.mark.django_db

@pytest.fixture
def config():
    org = Organisation.objects.create(name='Synthetic configuration')
    branch = Branch.objects.create(organisation=org, name='Main', code='MAIN')
    other = Branch.objects.create(organisation=org, name='Other', code='OTHER')
    foreign = Branch.objects.create(organisation=Organisation.objects.create(name='Foreign synthetic'), name='Foreign', code='FOREIGN')
    actor = get_user_model().objects.create_user(username='synthetic-config')
    Membership.objects.create(user=actor, branch=branch, role='master_admin')
    client = APIClient(); client.force_login(actor)
    base = f'/api/v1/platform/organisations/{org.pk}/'
    bed = Bed.objects.create(branch=other, number='A1', room_number='A')
    return client, actor, org, branch, other, foreign, bed, base

def bed_payload(branch, **changes):
    return {'branch': str(branch.pk), 'number': ' b2 ', 'room_number': ' r2 ', 'category': 'general', **changes}

def test_master_create_normalises_and_audits_allowed_snapshots(config):
    client, actor, org, branch, other, foreign, bed, base = config
    response = client.post(base+'branches/', {'name': ' New branch ', 'code': ' new-1 '}, format='json')
    assert response.status_code == 201
    assert response.json()['code'] == 'NEW-1'
    event = AuditEvent.objects.get(action='branch.created')
    assert event.actor == actor
    assert event.details == {'before': {}, 'after': {'name': 'New branch', 'code': 'NEW-1'}}
    response = client.post(base+'beds/', bed_payload(other), format='json')
    assert response.status_code == 201
    assert response.json() == {'id': response.json()['id'], 'branch': str(other.pk), 'number': 'B2', 'room_number': 'R2', 'category': 'general', 'status': 'available', 'version': 1}
    event = AuditEvent.objects.get(action='bed.created')
    assert event.details['before'] == {}
    assert event.details['after']['number'] == 'B2'
    assert 'patient' not in str(event.details)
    assert client.get('/api/v1/patients/').status_code == 403
    assert 'platform.configure' in client.get('/api/v1/auth/me/').json()['permissions']

@pytest.mark.parametrize('method', ['get', 'post'])
def test_scope_denial_and_revocation(config, method):
    client, actor, org, branch, other, foreign, bed, base = config
    assert getattr(client, method)(base.replace(str(org.pk), str(foreign.organisation_id))+'branches/', {}, format='json').status_code == 404
    Membership.objects.filter(user=actor).update(role='reception')
    assert getattr(client, method)(base+'branches/', {}, format='json').status_code == 403
    client.logout()
    assert client.get(base+'beds/').status_code == 403

def test_foreign_related_records_concealed(config):
    client, actor, org, branch, other, foreign, bed, base = config
    hidden = Bed.objects.create(branch=foreign, number='X', room_number='X')
    assert client.post(base+'beds/', bed_payload(foreign), format='json').status_code == 404
    assert client.get(base+f'beds/?branch={foreign.pk}').status_code == 404
    assert client.patch(base+f'beds/{hidden.pk}/', {'expected_version': 1, 'number': 'Y'}, format='json').status_code == 404

def test_case_insensitive_legacy_conflicts_without_partial_audits(config):
    client, actor, org, branch, other, foreign, bed, base = config
    Branch.objects.create(organisation=org, name='Legacy', code='legacy')
    Bed.objects.create(branch=other, number='legacy', room_number='R')
    assert client.post(base+'branches/', {'name': 'Duplicate', 'code': 'LEGACY'}, format='json').status_code == 409
    assert client.post(base+'beds/', bed_payload(other, number='LEGACY'), format='json').status_code == 409
    assert client.patch(base+f'beds/{bed.pk}/', {'expected_version': 1, 'number': 'LEGACY'}, format='json').status_code == 409
    assert AuditEvent.objects.count() == 0

@pytest.mark.parametrize('payload', [[], None, 'bad', {'id': 'forged'}, {'organisation': 'forged'}, {'roles': ['doctor']}, {'name': 'X', 'code': 'BAD_CODE'}])
def test_invalid_branch_payloads(config, payload):
    client, *_, base = config
    assert client.post(base+'branches/', payload, format='json').status_code == 400
    assert AuditEvent.objects.count() == 0

@pytest.mark.parametrize('changes', [{'status': 'occupied'}, {'status': 'reserved'}, {'id': 'forged'}, {'version': 2}, {'number': ''}, {'room_number': 'x'*33}, {'category': 'unknown'}])
def test_invalid_bed_payloads(config, changes):
    client, actor, org, branch, other, foreign, bed, base = config
    assert client.post(base+'beds/', bed_payload(other, **changes), format='json').status_code == 400
    assert AuditEvent.objects.count() == 0

def test_patch_version_and_strict_fields(config):
    client, actor, org, branch, other, foreign, bed, base = config
    url = base+f'beds/{bed.pk}/'
    response = client.patch(url, {'expected_version': 1, 'number': ' a3 ', 'status': 'cleaning'}, format='json')
    assert response.status_code == 200
    assert response.json()['version'] == 2
    event = AuditEvent.objects.get(action='bed.changed')
    assert event.details['before']['number'] == 'A1'
    assert event.details['after']['number'] == 'A3'
    assert client.patch(url, {'expected_version': 1, 'status': 'blocked'}, format='json').status_code == 409
    for changes in ({'branch': str(branch.pk)}, {'id': str(bed.pk)}, {'version': 9}, {'status': 'available', 'expected_version': 0}):
        assert client.patch(url, {'expected_version': 2, **changes}, format='json').status_code == 400
    assert client.delete(url).status_code == 405
    assert AuditEvent.objects.count() == 1

@pytest.mark.parametrize('state', ['occupied', 'reserved', 'active_admission'])
def test_occupied_reserved_and_inconsistent_active_admission_immutable(config, state):
    client, actor, org, branch, other, foreign, bed, base = config
    if state == 'active_admission':
        patient = Patient.objects.create(branch=other, full_name='Synthetic')
        Admission.objects.create(patient=patient, bed=bed, branch=other, treating_doctor='Synthetic')
    else:
        bed.status = state; bed.save()
    assert client.patch(base+f'beds/{bed.pk}/', {'expected_version': 1, 'status': 'available'}, format='json').status_code == 409
    assert AuditEvent.objects.count() == 0

def test_pagination_over_one_hundred_and_read_has_no_audit(config):
    client, actor, org, branch, other, foreign, bed, base = config
    Bed.objects.bulk_create([Bed(branch=other, number=f'B{i:03}', room_number='R') for i in range(120)])
    Branch.objects.bulk_create([Branch(organisation=org, name=f'Extra {i:03}', code=f'E{i}') for i in range(120)])
    for endpoint, count in [('beds/', 121), ('branches/', 122)]:
        result = client.get(base+endpoint+'?limit=100').json()
        assert result['count'] == count and len(result['results']) == 100
        assert len(client.get(base+endpoint+'?limit=100&offset=100').json()['results']) == count-100
        assert len(client.get(base+endpoint).json()['results']) == 25
        assert client.get(base+endpoint+'?offset=-1').status_code == 400
    assert AuditEvent.objects.count() == 0

def test_audit_failure_rolls_back_configuration(config, monkeypatch):
    client, actor, org, branch, other, foreign, bed, base = config
    def fail(*args, **kwargs):
        raise IntegrityError('synthetic audit failure')
    monkeypatch.setattr(AuditEvent.objects, 'create', fail)
    with pytest.raises(IntegrityError):
        client.post(base+'branches/', {'name': 'Rollback', 'code': 'ROLLBACK'}, format='json')
    assert not Branch.objects.filter(code='ROLLBACK').exists()

def test_allocation_increments_bed_version(config):
    client, actor, org, branch, other, foreign, bed, base = config
    Membership.objects.create(user=actor, branch=other, role='reception')
    patient = Patient.objects.create(branch=other, full_name='Synthetic allocation')
    response = client.post('/api/v1/admissions/', {'bed': str(bed.pk), 'patient': str(patient.pk), 'treating_doctor': 'Synthetic'}, format='json')
    assert response.status_code == 201
    bed.refresh_from_db()
    assert bed.version == 2 and bed.status == 'occupied'


@pytest.mark.parametrize('endpoint,payload', [('beds/', []), ('beds/', 'bad'), ('beds/', None), ('patch', []), ('patch', 'bad'), ('patch', None), ('patch', {'status': 'blocked'}), ('patch', {'expected_version': True}), ('patch', {'expected_version': 1.5})])
def test_nonobject_and_invalid_version_requests_fail_safely(config, endpoint, payload):
    client, actor, org, branch, other, foreign, bed, base = config
    if endpoint == 'patch':
        response = client.patch(base+f'beds/{bed.pk}/', payload, format='json')
    else:
        response = client.post(base+endpoint, payload, format='json')
    assert response.status_code == 400
    assert AuditEvent.objects.count() == 0


def test_malformed_filter_and_occupied_projection_are_safe(config):
    client, actor, org, branch, other, foreign, bed, base = config
    assert client.get(base+'beds/?branch=bad').status_code == 400
    bed.status = 'occupied'; bed.save()
    patient = Patient.objects.create(branch=other, full_name='Synthetic private patient')
    Admission.objects.create(patient=patient, bed=bed, branch=other, treating_doctor='Synthetic')
    row = client.get(base+'beds/').json()['results'][0]
    assert set(row) == {'id', 'branch', 'number', 'room_number', 'category', 'status', 'version'}
    assert 'Synthetic private patient' not in str(row)


def test_csrf_and_inactive_master_cannot_mutate(config):
    client, actor, org, branch, other, foreign, bed, base = config
    csrf_client = APIClient(enforce_csrf_checks=True); csrf_client.force_login(actor)
    assert csrf_client.post(base+'branches/', {'name': 'Denied', 'code': 'DENIED'}, format='json').status_code == 403
    assert csrf_client.post(base+'beds/', bed_payload(other), format='json').status_code == 403
    assert csrf_client.patch(base+f'beds/{bed.pk}/', {'expected_version': 1, 'status': 'blocked'}, format='json').status_code == 403
    actor.is_active = False; actor.save()
    assert client.get(base+'beds/').status_code == 403
    assert AuditEvent.objects.count() == 0


@pytest.mark.parametrize('operation', ['create', 'change'])
def test_bed_audit_failure_rolls_back_config_and_version(config, monkeypatch, operation):
    client, actor, org, branch, other, foreign, bed, base = config
    def fail(*args, **kwargs):
        raise IntegrityError('synthetic audit failure')
    monkeypatch.setattr(AuditEvent.objects, 'create', fail)
    with pytest.raises(IntegrityError):
        if operation == 'create':
            client.post(base+'beds/', bed_payload(other), format='json')
        else:
            client.patch(base+f'beds/{bed.pk}/', {'expected_version': 1, 'number': 'CHANGED'}, format='json')
    bed.refresh_from_db()
    assert bed.number == 'A1' and bed.version == 1
    assert Bed.objects.count() == 1


def test_ascii_branch_code_validation_precedes_uppercase(config):
    client, *_, base = config
    assert client.post(base+'branches/', {'name': 'Synthetic', 'code': 'ß'}, format='json').status_code == 400


def test_bed_create_requires_category_in_contract(config):
    client, actor, org, branch, other, foreign, bed, base = config
    payload = bed_payload(other)
    del payload['category']
    assert client.post(base+'beds/', payload, format='json').status_code == 400
