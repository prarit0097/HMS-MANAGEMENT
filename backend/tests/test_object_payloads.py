"""Malformed object contracts must fail safely before domain writes/fingerprints."""
import json
from uuid import uuid4
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from apps.core.models import Organisation, Branch, Membership, Patient, Appointment, IdempotencyRecord
from django.utils import timezone

pytestmark = pytest.mark.django_db

@pytest.fixture
def context():
    branch = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic object validation'), name='Test', code='TEST')
    actor = get_user_model().objects.create_user(username='synthetic-object-check')
    Membership.objects.create(user=actor, branch=branch, role='reception')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic')
    appointment = Appointment.objects.create(patient=patient, branch=branch, doctor_name='Synthetic', scheduled_at=timezone.now())
    client = APIClient()
    client.force_login(actor)
    return client, branch, patient, appointment

@pytest.mark.parametrize('payload', [[], [{}], None, 'abc', 3, True])
@pytest.mark.parametrize('action', ['login', 'patients', 'appointments', 'admissions', 'patient_patch', 'appointment_patch'])
def test_nonobject_body_returns_structured400(context, action, payload):
    client, _, patient, appointment = context
    method = 'POST'
    path = f'/api/v1/{action}/'
    if action == 'login':
        client.logout()
        path = '/api/v1/auth/login/'
    elif action == 'patient_patch':
        method, path = 'PATCH', f'/api/v1/patients/{patient.id}/'
    elif action == 'appointment_patch':
        method, path = 'PATCH', f'/api/v1/appointments/{appointment.id}/'
    client.raise_request_exception = False
    response = client.generic(method, path, json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    body = response.json()
    assert isinstance(body['message'], str)
    assert isinstance(body['field_errors']['non_field_errors'], list)

def test_keyed_multipart_with_file_returns400_without_claim(context):
    client, branch, *_ = context
    client.raise_request_exception = False
    response = client.post('/api/v1/patients/', {'branch':str(branch.id), 'full_name':'Synthetic', 'unexpected':SimpleUploadedFile('synthetic.txt', b'synthetic')}, format='multipart', HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert response.status_code == 400
    assert IdempotencyRecord.objects.count() == 0
