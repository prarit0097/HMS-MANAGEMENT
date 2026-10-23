from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, ValidationError
from .models import Patient, Appointment, Encounter, Bed, Admission, AuditEvent
from .authorization import permitted_branches

class Conflict(APIException):
    status_code = 409
    default_code = 'conflict'
    default_detail = 'This record changed or is no longer available. Refresh and try again.'

def audit(user, action, obj):
    AuditEvent.objects.create(actor=user, action=action, object_id=str(obj.pk), branch_id=getattr(obj, 'branch_id', None))

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
