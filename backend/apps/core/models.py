import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta:
        abstract = True

class Organisation(UUIDModel):
    name = models.CharField(max_length=160)

class Branch(UUIDModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=32)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['organisation', 'code'], name='unique_branch_code')]
        ordering = ['name', 'id']

class Membership(UUIDModel):
    ROLES = [(r, r) for r in ['master_admin', 'reception', 'doctor', 'pharmacist', 'accounts', 'nurse', 'therapist']]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    role = models.CharField(max_length=32, choices=ROLES)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'branch', 'role'], name='unique_membership')]

def new_uhid():
    return 'HMS-' + uuid.uuid4().hex.upper()

class Patient(UUIDModel):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    uhid = models.CharField(max_length=36, unique=True, default=new_uhid, editable=False)
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=32, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=32, blank=True)
    city = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at', 'id']
        indexes = [models.Index(fields=['branch', 'full_name']), models.Index(fields=['phone'])]

class Appointment(UUIDModel):
    STATUSES = [(r, r) for r in ['scheduled', 'checked_in', 'completed', 'cancelled', 'no_show']]
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    doctor_name = models.CharField(max_length=160)
    scheduled_at = models.DateTimeField()
    reason = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='scheduled')
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ['scheduled_at', 'id']
        indexes = [models.Index(fields=['branch', 'scheduled_at'])]

class Encounter(UUIDModel):
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT)
    checked_in_at = models.DateTimeField(auto_now_add=True)

class Bed(UUIDModel):
    CATEGORIES = [(r, r) for r in ['general', 'semi_private', 'private', 'private_luxury', 'villa']]
    STATUSES = [(r, r) for r in ['available', 'occupied', 'reserved', 'cleaning', 'blocked']]
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    number = models.CharField(max_length=32)
    room_number = models.CharField(max_length=32)
    category = models.CharField(max_length=32, choices=CATEGORIES, default='general')
    status = models.CharField(max_length=20, choices=STATUSES, default='available')
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ['room_number', 'number', 'id']
        constraints = [models.UniqueConstraint(fields=['branch', 'number'], name='unique_bed_number')]

class Admission(UUIDModel):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='admissions')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    treating_doctor = models.CharField(max_length=160)
    reason = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default='active')
    version = models.PositiveIntegerField(default=1)
    admitted_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-admitted_at', 'id']
        constraints = [models.UniqueConstraint(fields=['bed'], condition=Q(status='active'), name='one_active_bed_allocation'), models.UniqueConstraint(fields=['patient'], condition=Q(status='active'), name='one_active_patient_admission')]

class AuditEvent(UUIDModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_id = models.CharField(max_length=36, blank=True)
    branch = models.ForeignKey(Branch, null=True, on_delete=models.PROTECT)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class IdempotencyRecord(UUIDModel):
    """Create-result pointers only; never store request or response payloads."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operation = models.CharField(max_length=32)
    key = models.UUIDField()
    fingerprint = models.CharField(max_length=64)
    result_id = models.UUIDField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['actor', 'operation', 'key'], name='unique_actor_operation_key')]
