"""Dormant registration metadata; no file storage or runtime authority is supplied."""
from datetime import timedelta
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, router
from django.db.models import F, Q, Value
from django.db.models.functions import Length
from django.db.models.lookups import Exact, GreaterThanOrEqual, LessThanOrEqual
from django.db.utils import NotSupportedError
from django.utils import timezone


def length_between(field, minimum, maximum):
    return GreaterThanOrEqual(Length(field), Value(minimum)) & LessThanOrEqual(Length(field), Value(maximum))


def sha256_shape(field):
    # Length is explicit: regex '$' alone can match before a trailing newline.
    return Exact(Length(field), Value(64)) & Q(**{f'{field}__regex': r'^[0-9a-f]{64}$'})


class DocumentMetadataActorField(models.OneToOneField):
    """Permanent migration type: a required actor must not become a SQLite rowid."""
    def db_type(self, connection):
        parent = super().db_type(connection)
        if connection.vendor == 'sqlite' and isinstance(parent, str) and parent.lower() == 'integer':
            return 'bigint'
        return parent


class DocumentMetadataMinuteAligned(models.Func):
    """Permanent migration expression for finite, exact UTC-minute instants."""
    arity = 1
    output_field = models.BooleanField()

    def as_postgresql(self, compiler, connection, **extra_context):
        sql, params = compiler.compile(self.source_expressions[0])
        return f"((isfinite({sql}) AND {sql} = DATE_TRUNC('minute', {sql}, 'UTC')) IS TRUE)", list(params) * 3

    def as_sqlite(self, compiler, connection, **extra_context):
        sql, params = compiler.compile(self.source_expressions[0])
        return f"(({sql} = django_datetime_trunc('minute', {sql}, 'UTC', 'UTC')) IS TRUE)", list(params) * 2

    def as_sql(self, compiler, connection, **extra_context):
        raise NotSupportedError('Document metadata minute constraints require PostgreSQL or SQLite.')


class DocumentMetadataRateWindow(models.Model):
    actor = DocumentMetadataActorField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.PROTECT, related_name='+')
    window_started_at = models.DateTimeField()
    admitted_count = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(admitted_count__gte=1, admitted_count__lte=60), name='doc_metadata_rate_count'),
            models.CheckConstraint(condition=DocumentMetadataMinuteAligned(F('window_started_at')), name='doc_metadata_rate_minute'),
        ]


class PatientDocumentIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('core.Patient', on_delete=models.PROTECT, related_name='+')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    category = models.CharField(max_length=32, choices=[('registration', 'registration')])
    declared_filename = models.CharField(max_length=120)
    declared_media_type = models.CharField(max_length=32, choices=[('image/jpeg', 'image/jpeg'), ('image/png', 'image/png')])
    declared_size_bytes = models.PositiveBigIntegerField()
    declared_sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=[('pending', 'pending'), ('withdrawn', 'withdrawn')], default='pending')
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField()
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    withdrawal_reason = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['patient', '-created_at', '-id'], name='doc_intent_patient_time_id'),
                   models.Index(fields=['status', 'expires_at', 'id'], name='doc_intent_status_expiry_id')]
        constraints = [
            models.CheckConstraint(condition=Q(category='registration'), name='doc_intent_category'),
            models.CheckConstraint(condition=Q(declared_media_type__in=['image/jpeg', 'image/png']), name='doc_intent_media'),
            models.CheckConstraint(condition=Q(declared_size_bytes__gte=1, declared_size_bytes__lte=10485760), name='doc_intent_size'),
            models.CheckConstraint(condition=Q(version__gte=1, version__lte=2147483647), name='doc_intent_version'),
            models.CheckConstraint(condition=sha256_shape('declared_sha256'), name='doc_intent_digest'),
            models.CheckConstraint(condition=length_between('declared_filename', 1, 120), name='doc_intent_filename_length'),
            models.CheckConstraint(condition=Q(expires_at=F('created_at')+timedelta(minutes=30)), name='doc_intent_expiry'),
            models.CheckConstraint(condition=Q(status__in=['pending', 'withdrawn']), name='doc_intent_status'),
            models.CheckConstraint(condition=(
                Q(status='pending', withdrawn_at__isnull=True, withdrawn_by__isnull=True, withdrawal_reason='') |
                (Q(status='withdrawn', withdrawn_at__isnull=False, withdrawn_by__isnull=False, withdrawn_at__gte=F('created_at')) &
                 length_between('withdrawal_reason', 10, 500))
            ), name='doc_intent_withdrawal_shape'),
        ]


class DocumentIntentReceipt(models.Model):
    """Metadata command identity, not receipt of uploaded bytes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    operation = models.CharField(max_length=32, choices=[('intent.create', 'intent.create'), ('intent.withdraw', 'intent.withdraw')])
    key = models.UUIDField()
    fingerprint = models.CharField(max_length=64)
    result = models.ForeignKey(PatientDocumentIntent, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['actor', 'operation', 'key'], name='doc_receipt_actor_operation_key'),
            models.CheckConstraint(condition=Q(operation__in=['intent.create', 'intent.withdraw']), name='doc_receipt_operation'),
            models.CheckConstraint(condition=sha256_shape('fingerprint'), name='doc_receipt_fingerprint'),
        ]


class DocumentAccessEvent(models.Model):
    OPERATIONS = ['intent.list', 'intent.detail', 'intent.create_result', 'intent.withdraw_result']
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    patient = models.ForeignKey('core.Patient', on_delete=models.PROTECT, related_name='+')
    document = models.ForeignKey(PatientDocumentIntent, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    operation = models.CharField(max_length=32, choices=[(op, op) for op in OPERATIONS])
    result_count = models.PositiveSmallIntegerField()
    projection_sha256 = models.CharField(max_length=64)
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def clean(self):
        super().clean()
        if self.document_id and self.patient_id:
            # Match Django's constraint-validation routing and compare persisted
            # scope, never an unsaved/cached related object's mutable patient.
            alias = router.db_for_write(type(self), instance=self)
            try:
                document_patient_id = PatientDocumentIntent._base_manager.using(alias).values_list('patient_id', flat=True).get(pk=self.document_id)
            except PatientDocumentIntent.DoesNotExist:
                raise ValidationError({'document': 'Document does not exist.'}) from None
            if document_patient_id != self.patient_id:
                raise ValidationError({'document': 'Document must belong to the event patient.'})

    class Meta:
        indexes = [models.Index(fields=['patient', '-created_at', '-id'], name='doc_event_patient_time_id'),
                   models.Index(fields=['actor', '-created_at', '-id'], name='doc_event_actor_time_id')]
        constraints = [
            models.CheckConstraint(condition=Q(operation__in=['intent.list', 'intent.detail', 'intent.create_result', 'intent.withdraw_result']), name='doc_event_operation'),
            models.CheckConstraint(condition=Q(result_count__gte=0, result_count__lte=100), name='doc_event_count'),
            models.CheckConstraint(condition=sha256_shape('projection_sha256'), name='doc_event_projection_digest'),
            models.CheckConstraint(condition=(Q(operation='intent.list', document__isnull=True) |
                Q(operation__in=['intent.detail', 'intent.create_result', 'intent.withdraw_result'], document__isnull=False, result_count=1)), name='doc_event_result_shape'),
        ]
