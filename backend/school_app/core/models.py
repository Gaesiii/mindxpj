import uuid
from django.conf import settings
from django.db import models

class IdempotencyRequest(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operation = models.CharField(max_length=160)
    key = models.CharField(max_length=128)
    payload_hash = models.CharField(max_length=64)
    response_json = models.JSONField()
    response_status = models.PositiveSmallIntegerField(default=200)
    expires_at = models.DateTimeField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=['actor','operation','key'], name='unique_actor_operation_key')]

class ChangeLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=64)
    entity_id = models.UUIDField()
    action = models.CharField(max_length=64)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    before = models.JSONField()
    after = models.JSONField()
    reason = models.CharField(max_length=1000, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
