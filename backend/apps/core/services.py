import hashlib
import json
from uuid import UUID

from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, ValidationError
from .models import Patient, Appointment, Encounter, Bed, Admission, AuditEvent, IdempotencyRecord
from .authorization import permitted_branches

class Conflict(APIException):
    status_code = 409
    default_code = 'conflict'
    default_detail = 'This record changed or is no longer available. Refresh and try again.'

def audit(user, action, obj):
    AuditEvent.objects.create(actor=user, action=action, object_id=str(obj.pk), branch_id=getattr(obj, 'branch_id', None))


def idempotent_create(user, operation, key, payload, create, replay):
    """The unique claim, domain write and audit share one commit.

    A concurrent insert waits on the unique constraint. get_or_create's
    savepoint recovers its loser, which then locks and reads the committed
    result. A failed create rolls back its claim, allowing corrected retries.
    Both callbacks retain the normal API validation/permission ceiling.
    """
    if key is None:
        return create()
    try:
        if len(key) != 36:
            raise ValueError
        parsed_key = UUID(key)
        if str(parsed_key) != key.lower():
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValidationError({'Idempotency-Key': 'Use a UUID idempotency key.'})
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')).hexdigest()
    with transaction.atomic():
        record, created = IdempotencyRecord.objects.get_or_create(
            actor=user, operation=operation, key=parsed_key,
            defaults={'fingerprint': fingerprint},
        )
        if not created:
            record = IdempotencyRecord.objects.select_for_update().get(pk=record.pk)
            if record.fingerprint != fingerprint:
                raise Conflict('This request key was used with different details. Verify the previous result before trying a new request.')
            return replay(record.result_id)
        result = create()
        record.result_id = result.pk
        record.save(update_fields=['result_id'])
        return result

@transaction.atomic
def register_patient(user, validated):
    permitted_branches(user, 'patients.write', validated['branch'].pk)
    patient = Patient.objects.create(**validated)
    audit(user, 'patient.created', patient)
    return patient

@transaction.atomic
def create_appointment(user, validated):
    permitted_branches(user, 'appointments.write', validated['branch'].pk)
    if validated['patient'].branch_id != validated['branch'].pk:
        raise ValidationError({'patient': 'Select a patient registered at this branch.'})
    result = Appointment.objects.create(**validated)
    audit(user, 'appointment.created', result)
    return result

@transaction.atomic
def change_appointment(user, appointment_id, validated):
    branches = permitted_branches(user, 'appointments.write')
    appointment = get_object_or_404(Appointment.objects.select_for_update().filter(branch_id__in=branches), pk=appointment_id)
    if appointment.version != validated.pop('expected_version'):
        raise Conflict()
    status = validated.get('status', appointment.status)
    allowed = {'scheduled': {'scheduled', 'checked_in', 'cancelled', 'no_show'}, 'checked_in': {'checked_in', 'completed', 'cancelled'}, 'completed': {'completed'}, 'cancelled': {'cancelled'}, 'no_show': {'no_show', 'scheduled'}}
    if status not in allowed[appointment.status]:
        raise Conflict('This appointment cannot move to that status.')
    if appointment.status in {'completed', 'cancelled'} and any(key != 'status' for key in validated):
        raise Conflict('Completed or cancelled appointments cannot be rescheduled.')
    for key, value in validated.items():
        setattr(appointment, key, value)
    appointment.version += 1
    appointment.save()
    if status == 'checked_in':
        Encounter.objects.get_or_create(appointment=appointment)
    audit(user, 'appointment.changed', appointment)
    return appointment

def allocate_bed(user, validated):
    branches = permitted_branches(user, 'admissions.write')
    try:
        with transaction.atomic():
            bed = get_object_or_404(Bed.objects.select_for_update().filter(branch_id__in=branches), pk=validated['bed'].pk)
            patient = get_object_or_404(Patient.objects.select_for_update().filter(branch_id=bed.branch_id), pk=validated['patient'].pk)
            if bed.status != 'available' or Admission.objects.filter(patient=patient, status='active').exists():
                raise Conflict()
            admission = Admission.objects.create(branch=bed.branch, **{**validated, 'patient': patient, 'bed': bed})
            bed.status = 'occupied'
            bed.save(update_fields=['status'])
            audit(user, 'admission.created', admission)
            return admission
    except IntegrityError:
        raise Conflict()
