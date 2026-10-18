"""Custom User from the first migration; protected Student linkage added in A05."""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from school_app.core.enums import Role


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    student = models.OneToOneField("students.Student", null=True, blank=True,
                                  on_delete=models.PROTECT, related_name="user")

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(role__in=Role.values), name="accounts_user_valid_role"
        )]
