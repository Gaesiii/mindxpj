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

    class Meta:
        ordering = ["code", "id"]
