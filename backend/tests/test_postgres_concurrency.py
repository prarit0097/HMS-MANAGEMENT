"""Runs in PostgreSQL CI, explicitly skipped on SQLite; no SQLite race claim."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from django.db import connection, close_old_connections
from django.contrib.auth import get_user_model
from apps.core.models import Organisation, Branch, Membership, Patient, Bed, Admission
from apps.core.services import allocate_bed, Conflict

@pytest.mark.django_db(transaction=True)
def test_postgres_two_allocators_cannot_claim_the_same_bed():
    if connection.vendor != 'postgresql':
        pytest.skip('Requires PostgreSQL row locks and concurrent connections.')
    org = Organisation.objects.create(name='Synthetic race test')
    branch = Branch.objects.create(organisation=org, code='RACE', name='Synthetic')
    user = get_user_model().objects.create_user(username='synthetic-race')
    Membership.objects.create(user=user, branch=branch, role='reception')
    bed = Bed.objects.create(branch=branch, number='R1', room_number='R')
    patients = [Patient.objects.create(branch=branch, full_name=f'Synthetic {i}') for i in range(2)]
    barrier = Barrier(2)
    def claim(patient_id):
        close_old_connections()
        try:
            actor = get_user_model().objects.get(pk=user.pk)
            patient = Patient.objects.get(pk=patient_id)
            selected_bed = Bed.objects.get(pk=bed.pk)
            barrier.wait(timeout=10)
            try:
                allocate_bed(actor, {'patient': patient, 'bed': selected_bed, 'treating_doctor': 'Synthetic'})
                return 'created'
            except Conflict:
                return 'conflict'
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, [patient.pk for patient in patients]))
    assert sorted(results) == ['conflict', 'created']
    assert Admission.objects.filter(bed=bed, status='active').count() == 1


@pytest.mark.django_db(transaction=True)
def test_postgres_branch_configuration_lock_does_not_deadlock_admission_fk(monkeypatch):
    """Force config's branch lock before allocation's bed lock/FK insert.

    A branch FOR UPDATE lock deadlocks with the admission branch FK's KEY SHARE
    check while config waits for the allocated bed. NO KEY UPDATE serialises
    configuration writers while allowing that FK check to complete.
    """
    if connection.vendor != 'postgresql':
        pytest.skip('Requires PostgreSQL row locks and foreign-key lock checks.')
    from threading import Event, local
    from django.db.models.query import QuerySet
    from apps.core.resource_admin import change_bed
    org = Organisation.objects.create(name='Synthetic deterministic lock test')
    branch = Branch.objects.create(organisation=org, code='FKRACE', name='Synthetic')
    actor = get_user_model().objects.create_user(username='synthetic-fk-race')
    for role in ['master_admin', 'reception']:
        Membership.objects.create(user=actor, branch=branch, role=role)
    bed = Bed.objects.create(branch=branch, number='F1', room_number='F')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic FK race')
    branch_locked, allocation_bed_locked, config_waiting_bed = Event(), Event(), Event()
    phase = local()
    original_get = QuerySet.get

    def ordered_get(queryset, *args, **kwargs):
        locking = queryset.query.select_for_update
        action = getattr(phase, 'action', None)
        if action == 'edit' and queryset.model is Bed and locking:
            config_waiting_bed.set()
        result = original_get(queryset, *args, **kwargs)
        if action == 'edit' and queryset.model is Branch and locking:
            branch_locked.set()
            assert allocation_bed_locked.wait(10), 'Allocation did not acquire bed lock.'
        if action == 'allocate' and queryset.model is Bed and locking:
            allocation_bed_locked.set()
            assert config_waiting_bed.wait(10), 'Configuration did not reach bed lock.'
        return result

    monkeypatch.setattr(QuerySet, 'get', ordered_get)
    def run(action):
        close_old_connections()
        phase.action = action
        try:
            user = get_user_model().objects.get(pk=actor.pk)
            try:
                if action == 'edit':
                    change_bed(user, org.pk, bed.pk, {'expected_version': 1, 'number': 'F2'})
                else:
                    assert branch_locked.wait(10), 'Configuration did not acquire branch lock.'
                    allocate_bed(user, {'patient': Patient.objects.get(pk=patient.pk), 'bed': Bed.objects.get(pk=bed.pk), 'treating_doctor': 'Synthetic'})
                return action, 'success'
            except Conflict:
                return action, 'conflict'
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = dict(executor.map(run, ['edit', 'allocate']))
    assert results == {'edit': 'conflict', 'allocate': 'success'}
    bed.refresh_from_db()
    assert bed.status == 'occupied' and bed.number == 'F1' and bed.version == 2
    bed.refresh_from_db()
    assert bed.status == 'occupied'

@pytest.mark.django_db(transaction=True)
def test_postgres_same_key_concurrent_registration_has_one_result_and_audit():
    from uuid import uuid4
    from rest_framework.test import APIClient
    from apps.core.models import AuditEvent
    if connection.vendor != 'postgresql':
        pytest.skip('Requires PostgreSQL unique-key waits and concurrent connections.')
    org = Organisation.objects.create(name='Synthetic idempotency race')
    branch = Branch.objects.create(organisation=org, code='RETRY', name='Synthetic retry')
    actor = get_user_model().objects.create_user(username='synthetic-retry-race')
    Membership.objects.create(user=actor, branch=branch, role='reception')
    key = str(uuid4())
    barrier = Barrier(2)
    def register(_):
        close_old_connections()
        try:
            client = APIClient()
            client.force_login(get_user_model().objects.get(pk=actor.pk))
            barrier.wait(timeout=10)
            response = client.post('/api/v1/patients/', {'branch': str(branch.pk), 'full_name': 'Synthetic concurrent retry'}, format='json', HTTP_IDEMPOTENCY_KEY=key)
            return response.status_code, response.json()
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(register, range(2)))
    assert [status for status, _ in results] == [201, 201]
    assert results[0][1]['id'] == results[1][1]['id']
    assert Patient.objects.count() == 1
    assert AuditEvent.objects.filter(action='patient.created').count() == 1


@pytest.mark.django_db(transaction=True)
def test_postgres_configuration_edit_racing_allocation_is_serialised():
    """Both service calls use independent connections and compete for the bed lock."""
    if connection.vendor != 'postgresql':
        pytest.skip('Requires PostgreSQL row locks and concurrent connections.')
    from apps.core.resource_admin import change_bed
    from apps.core.models import AuditEvent
    org = Organisation.objects.create(name='Synthetic configuration race')
    branch = Branch.objects.create(organisation=org, code='CONFIGRACE', name='Synthetic')
    actor = get_user_model().objects.create_user(username='synthetic-config-race')
    for role in ['master_admin', 'reception']:
        Membership.objects.create(user=actor, branch=branch, role=role)
    bed = Bed.objects.create(branch=branch, number='R1', room_number='R')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic config race')
    barrier = Barrier(2)
    def compete(action):
        close_old_connections()
        try:
            user = get_user_model().objects.get(pk=actor.pk)
            selected = Bed.objects.get(pk=bed.pk)
            barrier.wait(timeout=10)
            try:
                if action == 'edit':
                    change_bed(user, org.pk, bed.pk, {'expected_version': 1, 'number': 'R2'})
                else:
                    allocate_bed(user, {'patient': Patient.objects.get(pk=patient.pk), 'bed': selected, 'treating_doctor': 'Synthetic'})
                return action, 'success'
            except Conflict:
                return action, 'conflict'
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = dict(executor.map(compete, ['edit', 'allocate']))
    assert results['allocate'] == 'success'
    bed.refresh_from_db()
    assert bed.status == 'occupied'
    if results['edit'] == 'success':
        assert bed.number == 'R2' and bed.version == 3
        assert AuditEvent.objects.filter(action='bed.changed').count() == 1
    else:
        assert bed.number == 'R1' and bed.version == 2
        assert not AuditEvent.objects.filter(action='bed.changed').exists()
    assert Admission.objects.filter(bed=bed, status='active').count() == 1
