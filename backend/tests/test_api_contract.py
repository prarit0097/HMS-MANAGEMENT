import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from apps.core.models import Organisation, Branch, Membership, Patient, Appointment, Encounter, Bed, Admission
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

@pytest.fixture
def workspace():
    cache.clear()
    org = Organisation.objects.create(name='Synthetic Hospital')
    branch = Branch.objects.create(organisation=org, code='MAIN', name='Main')
    other = Branch.objects.create(organisation=org, code='SECOND', name='Second')
    foreign = Branch.objects.create(organisation=Organisation.objects.create(name='Other synthetic'), code='FOREIGN', name='Foreign')
    user = get_user_model().objects.create_user(username='reception-test', password='Test-fixture-only-passphrase')
    Membership.objects.create(user=user, branch=branch, role='reception')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic Patient', phone='0000000000')
    client = APIClient()
    client.force_login(user)
    return client, user, branch, other, foreign, patient

def test_me_contains_only_assigned_branch_and_permissions(workspace):
    client, user, branch, *_ = workspace
    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 200
    assert response.json()['roles'] == ['reception']
    assert response.json()['branches'] == [{'id': str(branch.id), 'name': 'Main', 'code': 'MAIN'}]
    assert 'patients.write' in response.json()['permissions']

def test_duplicate_phone_allowed_and_private_ids_concealed(workspace):
    client, _, branch, _, foreign, _ = workspace
    hidden = Patient.objects.create(branch=foreign, full_name='Hidden Synthetic')
    response = client.post('/api/v1/patients/', {'full_name': 'Second Synthetic', 'phone': '0000000000', 'branch': str(branch.id)}, format='json')
    assert response.status_code == 201
    assert Patient.objects.filter(phone='0000000000').count() == 2
    assert client.get(f'/api/v1/patients/{hidden.id}/').status_code == 404
    assert client.get('/api/v1/patients/').json()['count'] == 2

def test_branch_selection_cannot_grant_access(workspace):
    client, _, _, other, foreign, _ = workspace
    for branch in (other, foreign):
        assert client.get(f'/api/v1/patients/?branch={branch.id}').status_code == 403
        assert client.post('/api/v1/patients/', {'full_name': 'Rejected', 'branch': str(branch.id)}, format='json').status_code == 403

def test_master_admin_has_inventory_without_patient_access(workspace):
    client, user, branch, *_ = workspace
    Membership.objects.filter(user=user).update(role='master_admin')
    assert client.get('/api/v1/platform/summary/').status_code == 200
    assert client.get('/api/v1/patients/').status_code == 403
    assert client.post('/api/v1/patients/', {'full_name': 'Rejected', 'branch': str(branch.id)}, format='json').status_code == 403

def test_checkin_retry_creates_one_encounter_and_stale_edit_conflicts(workspace):
    client, _, branch, _, _, patient = workspace
    response = client.post('/api/v1/appointments/', {'branch': str(branch.id), 'patient': str(patient.id), 'doctor_name': 'Synthetic Doctor', 'scheduled_at': '2026-10-23T10:00:00+05:30'}, format='json')
    assert response.status_code == 201
    url = f"/api/v1/appointments/{response.json()['id']}/"
    payload = {'status': 'checked_in', 'expected_version': 1}
    assert client.patch(url, payload, format='json').status_code == 200
    assert client.patch(url, payload, format='json').status_code == 409
    assert Encounter.objects.count() == 1
    assert client.patch(url, {'status': 'checked_in', 'expected_version': 2}, format='json').status_code == 200
    assert Encounter.objects.count() == 1

def test_bed_allocation_is_scoped_and_cannot_double_allocate(workspace):
    client, _, branch, other, _, patient = workspace
    bed = Bed.objects.create(branch=branch, number='A1', room_number='A')
    payload = {'patient': str(patient.id), 'bed': str(bed.id), 'treating_doctor': 'Synthetic Doctor'}
    response = client.post('/api/v1/admissions/', payload, format='json')
    assert response.status_code == 201
    assert client.post('/api/v1/admissions/', payload, format='json').status_code == 409
    assert Admission.objects.count() == 1
    result = client.get('/api/v1/beds/').json()['results'][0]
    assert result['status'] == 'occupied'
    assert result['patient_name'] == 'Synthetic Patient'
    wrong_bed = Bed.objects.create(branch=other, number='A1', room_number='A')
    payload['bed'] = str(wrong_bed.id)
    assert client.post('/api/v1/admissions/', payload, format='json').status_code in (403, 404)

def test_reception_cannot_reassign_patient_branch_or_grant_role(workspace):
    client, _, _, other, _, patient = workspace
    assert client.patch(f'/api/v1/patients/{patient.id}/', {'branch': str(other.id)}, format='json').status_code == 400
    assert client.patch(f'/api/v1/patients/{patient.id}/', {'roles': ['master_admin']}, format='json').status_code == 400

def test_search_pagination_validation_and_dashboard(workspace):
    client, _, branch, *_ = workspace
    assert client.get('/api/v1/patients/?limit=-1').status_code == 400
    assert client.get('/api/v1/patients/?q=' + 'x'*201).status_code == 400
    assert client.get('/api/v1/patients/?q=Synthetic').json()['count'] == 1
    response = client.get(f'/api/v1/dashboard/?branch={branch.id}')
    assert response.status_code == 200
    assert response.json()['patients_total'] == 1
    assert response.json()['therapy_pending'] is None

def test_login_throttles_repeated_attempts():
    cache.clear()
    client = APIClient()
    statuses = [client.post('/api/v1/auth/login/', {'username': 'missing', 'password': 'bad'}, format='json').status_code for _ in range(12)]
    assert statuses[-1] == 429

def test_session_mutation_and_logout_require_csrf(workspace):
    _, user, branch, *_ = workspace
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post('/api/v1/patients/', {'branch': str(branch.id), 'full_name': 'Denied'}, format='json').status_code == 403
    assert client.post('/api/v1/auth/logout/').status_code == 403

def test_related_identifiers_conceal_foreign_and_missing_records(workspace):
    from uuid import uuid4
    client, _, branch, _, foreign, _ = workspace
    hidden = Patient.objects.create(branch=foreign, full_name='Hidden Synthetic')
    responses = [client.post('/api/v1/appointments/', {'branch': str(branch.id), 'patient': str(patient_id), 'doctor_name': 'Synthetic', 'scheduled_at': '2026-10-23T10:00:00+05:30'}, format='json') for patient_id in (hidden.pk, uuid4())]
    assert [r.status_code for r in responses] == [404, 404]
    assert responses[0].json() == responses[1].json()

def test_health_has_no_private_details():
    response = APIClient().get('/api/v1/health/')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}

def test_authentication_requires_csrf_and_conceals_invalid_identity():
    client = APIClient(enforce_csrf_checks=True)
    response = client.post('/api/v1/auth/login/', {'username': 'absent', 'password': 'invalid'}, format='json')
    assert response.status_code == 403
    assert 'code' in response.json()
    assert client.get('/api/v1/auth/csrf/').status_code == 200
    token = client.cookies['csrftoken'].value
    response = client.post('/api/v1/auth/login/', {'username': 'absent', 'password': 'invalid'}, format='json', HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 401
    assert response.json()['code'] == 'invalid_credentials'

@pytest.mark.parametrize('path', ['patients/', 'beds/', 'branches/', 'appointments/', 'admissions/', 'dashboard/', 'platform/summary/'])
def test_anonymous_cannot_access_workspace(path):
    response = APIClient().get('/api/v1/' + path)
    assert response.status_code in (401, 403)
    assert set(response.json()) >= {'code', 'message'}
