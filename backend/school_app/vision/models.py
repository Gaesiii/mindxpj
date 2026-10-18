import uuid

from django.conf import settings
from django.db import models


class FaceSample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='face_samples')
    image = models.BinaryField(editable=False)
    digest = models.CharField(max_length=64)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['student','digest'], name='unique_student_face_sample')]


class VisionScan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roster = models.ForeignKey('schedules.SessionRoster', on_delete=models.PROTECT, related_name='vision_scans')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vision_scans')
    scanned_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    sample_revision = models.CharField(max_length=64)
    attendance_version = models.PositiveIntegerField()
    distance = models.FloatField()
    observed_uniform = models.CharField(max_length=16)
    color_coverage = models.FloatField()
    status = models.CharField(max_length=16, default='PENDING', choices=[(v,v) for v in (
        'PENDING','CONFIRMED','REJECTED','EXPIRED','SUPERSEDED')])
    version = models.PositiveIntegerField(default=0)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='resolved_vision_scans')
    resolved_at = models.DateTimeField(null=True)
    reason = models.CharField(max_length=1000, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['roster'], condition=models.Q(status='PENDING'), name='unique_pending_vision_roster')]
