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
    bed.refresh_from_db()
    assert bed.status == 'occupied'
