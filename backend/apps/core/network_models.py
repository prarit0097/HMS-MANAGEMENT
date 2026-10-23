"""Durable network policy records; mutation authority and graph validation live in B2 services."""
from datetime import timedelta
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

MAX_SAFE_INTEGER = 9007199254740991


def bounded(field, name, *, nullable=False, minimum=1):
    condition = Q(**{f'{field}__gte': minimum, f'{field}__lte': MAX_SAFE_INTEGER})
    if nullable:
        condition |= Q(**{f'{field}__isnull': True})
    return models.CheckConstraint(condition=condition, name=name)


class NetworkRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class NetworkPolicyState(models.Model):
    id = models.SmallIntegerField(primary_key=True, default=1)
    bound_owner = models.ForeignKey('core.Organisation', null=True, on_delete=models.PROTECT, related_name='+')
    revision = models.BigIntegerField(default=1)
    confirmed_policy = models.JSONField()
    confirmed_policy_digest = models.CharField(max_length=64)
    pending_change = models.ForeignKey('core.NetworkPolicyChange', null=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(id=1), name='network_state_singleton'), bounded('revision', 'network_state_revision')]


class NetworkOperator(NetworkRecord):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    organisation = models.ForeignKey('core.Organisation', on_delete=models.PROTECT, related_name='+')
    active = models.BooleanField(default=True)
    version = models.BigIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'organisation'], name='network_operator_user_org'), bounded('version', 'network_operator_version')]


class NetworkPolicyPreview(NetworkRecord):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    owner = models.ForeignKey('core.Organisation', on_delete=models.PROTECT, related_name='+')
    session_digest = models.CharField(max_length=64)
    epoch = models.BigIntegerField()
    operator_version = models.BigIntegerField()
    verified_ip = models.GenericIPAddressField(unpack_ipv4=True)
    environment_digest = models.CharField(max_length=64)
    base_revision = models.BigIntegerField()
    policy = models.JSONField()
    policy_digest = models.CharField(max_length=64)
    request_digest = models.CharField(max_length=64)
    reason = models.CharField(max_length=500)
    normalisations = models.JSONField()
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    request_key = models.UUIDField()
    result_change = models.OneToOneField('core.NetworkPolicyChange', null=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        indexes = [models.Index(fields=['expires_at'], name='network_preview_expiry')]
        constraints = [
            models.UniqueConstraint(fields=['actor', 'request_key'], name='network_preview_actor_key'),
            bounded('epoch', 'network_preview_epoch', minimum=0),
            bounded('operator_version', 'network_preview_operator_v'),
            bounded('base_revision', 'network_preview_base_rev'),
            models.CheckConstraint(condition=Q(expires_at=F('created_at')+timedelta(seconds=300)), name='network_preview_deadline'),
        ]


class NetworkPolicyChange(NetworkRecord):
    STATUSES = ['pending', 'confirmed', 'reverted', 'expired', 'recovered', 'owner_transferred']
    preview = models.OneToOneField('core.NetworkPolicyPreview', null=True, on_delete=models.PROTECT, related_name='+')
    owner = models.ForeignKey('core.Organisation', on_delete=models.PROTECT, related_name='+')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    session_digest = models.CharField(max_length=64, null=True)
    epoch = models.BigIntegerField(null=True)
    operator_version = models.BigIntegerField(null=True)
    verified_ip = models.GenericIPAddressField(unpack_ipv4=True, null=True)
    environment_digest = models.CharField(max_length=64)
    candidate_policy = models.JSONField()
    candidate_policy_digest = models.CharField(max_length=64)
    fallback_policy = models.JSONField()
    fallback_policy_digest = models.CharField(max_length=64)
    base_revision = models.BigIntegerField()
    activation_revision = models.BigIntegerField(unique=True)
    activated_at = models.DateTimeField()
    rollback_at = models.DateTimeField()
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=[(value, value) for value in STATUSES], default='pending')
    finished_at = models.DateTimeField(null=True)
    terminal_revision = models.BigIntegerField(null=True)
    confirm_expected_revision = models.BigIntegerField(null=True)
    revert_expected_revision = models.BigIntegerField(null=True)

    class Meta:
        constraints = [
            bounded('base_revision', 'network_change_base_rev'),
            bounded('activation_revision', 'network_change_activation_rev'),
            bounded('terminal_revision', 'network_change_terminal_rev', nullable=True),
            bounded('confirm_expected_revision', 'network_change_confirm_rev', nullable=True),
            bounded('revert_expected_revision', 'network_change_revert_rev', nullable=True),
            bounded('epoch', 'network_change_epoch', nullable=True, minimum=0),
            bounded('operator_version', 'network_change_operator_v', nullable=True),
            models.CheckConstraint(condition=Q(activation_revision__gt=F('base_revision')), name='network_change_revision_order'),
            models.CheckConstraint(condition=Q(rollback_at=F('activated_at')+timedelta(seconds=300)), name='network_change_deadline'),
            models.CheckConstraint(condition=Q(status__in=['pending', 'confirmed', 'reverted', 'expired', 'recovered', 'owner_transferred']), name='network_change_status'),
            models.CheckConstraint(condition=(Q(status='pending', finished_at__isnull=True, terminal_revision__isnull=True) | (~Q(status='pending') & Q(finished_at__isnull=False, terminal_revision__isnull=False, finished_at__gte=F('activated_at'), terminal_revision__gt=F('activation_revision')))), name='network_change_terminal_state'),
        ]


class NetworkPolicyEvent(NetworkRecord):
    ACTIONS = ['policy.activated', 'policy.confirmed', 'policy.reverted', 'policy.expired', 'policy.recovered', 'operator.granted', 'operator.revoked', 'owner.bound', 'owner.transferred']
    OUTCOMES = ['pending', 'confirmed', 'reverted', 'expired', 'recovered', 'granted', 'revoked', 'bound', 'transferred']
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    os_actor = models.CharField(max_length=150, null=True)
    owner = models.ForeignKey('core.Organisation', on_delete=models.PROTECT, related_name='+')
    change = models.ForeignKey('core.NetworkPolicyChange', null=True, on_delete=models.PROTECT, related_name='+')
    action = models.CharField(max_length=32, choices=[(value, value) for value in ACTIONS])
    outcome = models.CharField(max_length=20, choices=[(value, value) for value in OUTCOMES])
    revision = models.BigIntegerField()
    reason = models.CharField(max_length=500)
    before_policy = models.JSONField(null=True)
    after_policy = models.JSONField(null=True)
    created_at = models.DateTimeField()
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    entitlement_version_before = models.BigIntegerField(null=True)
    entitlement_version_after = models.BigIntegerField(null=True)
    previous_owner = models.ForeignKey('core.Organisation', null=True, on_delete=models.PROTECT, related_name='+')
    new_owner = models.ForeignKey('core.Organisation', null=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        indexes = [models.Index(fields=['owner', '-created_at', '-id'], name='network_event_owner_time_id')]
        constraints = [
            bounded('revision', 'network_event_revision'),
            bounded('entitlement_version_before', 'network_event_entitlement_before', nullable=True, minimum=0),
            bounded('entitlement_version_after', 'network_event_entitlement_after', nullable=True),
            models.CheckConstraint(condition=Q(action__in=['policy.activated', 'policy.confirmed', 'policy.reverted', 'policy.expired', 'policy.recovered', 'operator.granted', 'operator.revoked', 'owner.bound', 'owner.transferred']), name='network_event_action'),
            models.CheckConstraint(condition=Q(outcome__in=['pending', 'confirmed', 'reverted', 'expired', 'recovered', 'granted', 'revoked', 'bound', 'transferred']), name='network_event_outcome'),
        ]
