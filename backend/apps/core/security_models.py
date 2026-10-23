import uuid
from django.conf import settings
from django.db import models


class IdentitySecurity(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    auth_epoch = models.PositiveBigIntegerField(default=0)
    active_ciphertext = models.TextField(blank=True)
    device_id = models.UUIDField(null=True)
    last_totp_step = models.BigIntegerField(default=-1)
    failure_started = models.DateTimeField(null=True)
    failure_count = models.PositiveIntegerField(default=0)
    version = models.PositiveBigIntegerField(default=0)
    latest_challenge = models.UUIDField(null=True)


class IdentityEnrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_hash = models.CharField(max_length=64)
    ciphertext = models.TextField()
    auth_epoch = models.PositiveBigIntegerField()
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)


class IdentityChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_hash = models.CharField(max_length=64)
    auth_epoch = models.PositiveBigIntegerField()
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    consumed = models.BooleanField(default=False)


class IdentityBackupCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prefix = models.CharField(max_length=8)
    password_hash = models.CharField(max_length=256)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'prefix'], name='unique_identity_backup_prefix')]


class IdentityNetworkBudget(models.Model):
    ip_hash = models.CharField(max_length=64, primary_key=True)
    started_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
