"""Student profiles are independent of attendance; transfer affects future rosters."""
import uuid
from django.db import models


class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_code = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=150)
    classroom = models.ForeignKey("academics.Classroom", on_delete=models.PROTECT, related_name="students")
    photo_path = models.CharField(max_length=200, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["student_code", "id"]
