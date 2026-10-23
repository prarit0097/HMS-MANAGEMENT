"""Revocation and optimistic-version snapshots must stay authoritative."""
from uuid import uuid4
import pytest
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient
from apps.core.models import Organisation, Branch, Membership, Patient, Bed, Appointment, Admission, AuditEvent, StaffAccessRevision, IdempotencyRecord
from apps.core import resource_admin, services, staff_access

pytestmark = pytest.mark.django_db

def test_current_user_permissions_are_scoped_to_each_active_branch(context):
    org, branch, _, target = context
    other = Branch.objects.create(organisation=org, name='Synthetic reception', code='RECEPTION')
    membership = Membership.objects.create(user=target, branch=other, role='reception')
    client = APIClient(); client.force_login(target)
    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 200
    permissions = response.data['branch_permissions']
    assert 'patients.read' in permissions[str(branch.pk)]
    assert 'patients.write' not in permissions[str(branch.pk)]
    assert 'patients.write' in permissions[str(other.pk)]
    assert 'patients.write' in response.data['permissions']
    membership.is_active = False; membership.save(update_fields=['is_active'])
    response = client.get('/api/v1/auth/me/')
    assert str(other.pk) not in response.data['branch_permissions']
    assert 'patients.write' not in response.data['permissions']

@pytest.fixture
def context():
    org = Organisation.objects.create(name='Synthetic consistency')
    branch = Branch.objects.create(organisation=org, name='Synthetic', code='CONSISTENT')
    actor = get_user_model().objects.create_user(username='synthetic-consistency-admin')
    target = get_user_model().objects.create_user(username='synthetic-consistency-staff')
    for role in ['master_admin', 'reception']:
        Membership.objects.create(user=actor, branch=branch, role=role)
    Membership.objects.create(user=target, branch=branch, role='doctor')
    return org, branch, actor, target

def revoke_after_lock(monkeypatch, actor, model):
    original = QuerySet.get
    fired = []
    def get(queryset, *args, **kwargs):
        result = original(queryset, *args, **kwargs)
        if queryset.model is model and queryset.query.select_for_update and not fired:
            fired.append(True)
            Membership.objects.filter(user=actor).update(is_active=False)
        return result
    monkeypatch.setattr(QuerySet, 'get', get)

def test_branch_create_reauthorises_after_waiting_organisation_lock(context, monkeypatch):
    org, _, actor, _ = context
    revoke_after_lock(monkeypatch, actor, Organisation)
    with pytest.raises(PermissionDenied):
        resource_admin.create_branch(actor, org.pk, {'name':'Must not be created', 'code':'DENIED'})
    assert not Branch.objects.filter(code='DENIED').exists()
    assert AuditEvent.objects.count() == 0

@pytest.mark.parametrize('action', ['create', 'change'])
def test_bed_configuration_reauthorises_after_organisation_lock(context, monkeypatch, action):
    org, branch, actor, _ = context
    bed = Bed.objects.create(branch=branch, number='C1', room_number='C')
    revoke_after_lock(monkeypatch, actor, Organisation)
    with pytest.raises(PermissionDenied):
        if action == 'create':
            resource_admin.create_bed(actor, org.pk, {'branch':branch, 'number':'C2', 'room_number':'C', 'category':'general', 'status':'available'})
        else:
            resource_admin.change_bed(actor, org.pk, bed.pk, {'expected_version':1, 'number':'C2'})
    assert not Bed.objects.filter(number='C2').exists()

@pytest.mark.parametrize('action', ['appointment', 'admission'])
def test_operational_write_rechecks_scope_after_its_row_lock(context, monkeypatch, action):
    _, branch, actor, _ = context
    patient = Patient.objects.create(branch=branch, full_name='Synthetic')
    if action == 'appointment':
        appointment = Appointment.objects.create(patient=patient, branch=branch, doctor_name='Synthetic', scheduled_at=timezone.now())
        revoke_after_lock(monkeypatch, actor, Appointment)
        with pytest.raises(PermissionDenied):
            services.change_appointment(actor, appointment.pk, {'expected_version':1, 'status':'checked_in'})
        appointment.refresh_from_db()
        assert appointment.status == 'scheduled'
    else:
        bed = Bed.objects.create(branch=branch, number='C1', room_number='C')
        revoke_after_lock(monkeypatch, actor, Bed)
        with pytest.raises(PermissionDenied):
            services.allocate_bed(actor, {'patient':patient, 'bed':bed, 'treating_doctor':'Synthetic'})
        assert Admission.objects.count() == 0

def test_idempotent_replay_rechecks_scope_after_waiting_key(context, monkeypatch):
    _, branch, actor, _ = context
    client = APIClient(); client.force_login(actor)
    key = str(uuid4()); body = {'branch':str(branch.pk), 'full_name':'Synthetic retry'}
    assert client.post('/api/v1/patients/', body, format='json', HTTP_IDEMPOTENCY_KEY=key).status_code == 201
    manager = IdempotencyRecord.objects
    original = manager.get_or_create
    def claim(*args, **kwargs):
        result = original(*args, **kwargs)
        Membership.objects.filter(user=actor).update(is_active=False)
        return result
    monkeypatch.setattr(manager, 'get_or_create', claim)
    response = client.post('/api/v1/patients/', body, format='json', HTTP_IDEMPOTENCY_KEY=key)
    assert response.status_code == 403
    assert Patient.objects.count() == 1
    assert AuditEvent.objects.filter(action='patient.created').count() == 1

def test_staff_snapshot_does_not_pair_old_grants_with_new_version(context, monkeypatch):
    org, branch, actor, target = context
    original = QuerySet.values_list
    fired = []
    def values_list(queryset, *fields, **kwargs):
        if queryset.model is StaffAccessRevision and fields == ('version',) and not fired:
            fired.append(True)
            staff_access.change_staff(actor, org.pk, target.pk, {'expected_version':0, 'assignments':[{'branch':branch.pk, 'role':'nurse'}]})
        return original(queryset, *fields, **kwargs)
    monkeypatch.setattr(QuerySet, 'values_list', values_list)
    result = staff_access.staff_response(target, org)
    assert result['version'] == 1
    assert result['assignments'] == [{'branch':str(branch.pk), 'role':'nurse'}]
