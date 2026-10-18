import uuid
from django.conf import settings
from django.db import models
from school_app.core.enums import QrScanStatus

class QrChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey('schedules.Session', on_delete=models.PROTECT)
    token_hash = models.CharField(max_length=64, unique=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()

class QrScan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roster = models.ForeignKey('schedules.SessionRoster', on_delete=models.PROTECT, related_name='scans')
    challenge = models.ForeignKey(QrChallenge, on_delete=models.PROTECT)
    student_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='qr_scans')
    scanned_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=QrScanStatus.choices, default=QrScanStatus.PENDING)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name='resolved_scans')
    resolved_at = models.DateTimeField(null=True)
    version = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=1000, null=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['roster'], condition=models.Q(status='PENDING'), name='unique_pending_roster')]
