import uuid
from django.db import models
from school_app.core.enums import Weekday, Slot, RequiredUniform, SessionStatus

class ScheduleRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey('academics.Classroom', on_delete=models.PROTECT)
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    slot = models.CharField(max_length=16, choices=Slot.choices)
    start_time = models.TimeField()
    close_time = models.TimeField()
    grace_minutes = models.PositiveIntegerField()
    required_uniform = models.CharField(max_length=16, choices=RequiredUniform.choices)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['classroom','weekday','slot'], name='unique_class_weekday_slot'), models.CheckConstraint(condition=models.Q(start_time__lt=models.F('close_time')), name='rule_start_before_close'), models.CheckConstraint(condition=models.Q(weekday__lte=6), name='valid_rule_weekday')]

class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey('academics.Classroom', on_delete=models.PROTECT)
    school_date = models.DateField()
    slot = models.CharField(max_length=16, choices=Slot.choices)
    status = models.CharField(max_length=16, choices=SessionStatus.choices, default=SessionStatus.PLANNED)
    start_at = models.DateTimeField(null=True)
    late_cutoff_at = models.DateTimeField(null=True)
    close_at = models.DateTimeField(null=True)
    required_uniform_snapshot = models.CharField(max_length=16, choices=RequiredUniform.choices, null=True)
    version = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['classroom','school_date','slot'], name='unique_class_date_slot'), models.CheckConstraint(condition=models.Q(status='PLANNED') | models.Q(start_at__isnull=False, late_cutoff_at__isnull=False, close_at__isnull=False, required_uniform_snapshot__isnull=False), name='opened_session_has_snapshot')]

class SessionRoster(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.PROTECT, related_name='roster')
    student = models.ForeignKey('students.Student', on_delete=models.PROTECT)
    student_code_snapshot = models.CharField(max_length=64)
    full_name_snapshot = models.CharField(max_length=255)
    class_code_snapshot = models.CharField(max_length=64)
    class_name_snapshot = models.CharField(max_length=255)
    grade_code_snapshot = models.CharField(max_length=64)
    grade_name_snapshot = models.CharField(max_length=255)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['session','student'], name='unique_session_student')]
