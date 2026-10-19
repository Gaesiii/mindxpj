"""A03 grade/class definitions. Current teacher controls historical class scope."""
import uuid
from django.conf import settings
from django.db import models


class Grade(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["code", "id"]


class Classroom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="classrooms")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="classrooms")
    capacity = models.PositiveSmallIntegerField(default=50)
    active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["code", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(capacity__gte=1, capacity__lte=50), name="class_capacity_1_50")]
