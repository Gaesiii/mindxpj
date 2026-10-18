import uuid
from django.conf import settings
from django.db import models
from school_app.core.enums import AttendanceStatus, AttendanceSource, ObservedUniform, UniformStatus

class Attendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roster = models.OneToOneField('schedules.SessionRoster', on_delete=models.PROTECT, related_name='attendance')
    status = models.CharField(max_length=16, choices=AttendanceStatus.choices, default=AttendanceStatus.UNMARKED)
    arrived_at = models.DateTimeField(null=True)
    source = models.CharField(max_length=16, choices=AttendanceSource.choices, null=True)
    absence_reason = models.CharField(max_length=1000, null=True)
    observed_uniform = models.CharField(max_length=16, choices=ObservedUniform.choices, null=True)
    uniform_status = models.CharField(max_length=16, choices=UniformStatus.choices, default=UniformStatus.NOT_APPLICABLE)
    uniform_reason = models.CharField(max_length=1000, null=True)
    uniform_note = models.CharField(max_length=1000, null=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name='verified_attendances')
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name='checked_attendances')
    verified_at = models.DateTimeField(null=True)
    checked_at = models.DateTimeField(null=True)
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=(models.Q(status='PRESENT', arrived_at__isnull=False, source__isnull=False) & ~models.Q(uniform_status='NOT_APPLICABLE')) | models.Q(status__in=['ABSENT','UNMARKED'], arrived_at__isnull=True, source__isnull=True, observed_uniform__isnull=True, uniform_status='NOT_APPLICABLE'), name='attendance_consistent_state')]
