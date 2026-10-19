import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class SchoolUniformProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey('academics.Classroom', on_delete=models.PROTECT, related_name='uniform_profiles')
    version = models.PositiveIntegerField()
    model_key = models.CharField(max_length=150)
    model_sha256 = models.CharField(max_length=64)
    labels = models.JSONField(default=list)
    accepted_labels = models.JSONField(default=list)
    threshold = models.FloatField(default=.95)
    metadata = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['classroom','version'], name='unique_class_uniform_version')]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Uniform profile versions are immutable. Import a new version.')
        return super().save(*args, **kwargs)


class SchoolUniformSelection(models.Model):
    classroom = models.OneToOneField('academics.Classroom', primary_key=True, on_delete=models.CASCADE)
    profile = models.ForeignKey(SchoolUniformProfile, on_delete=models.PROTECT)


class SchoolUniformSample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey('academics.Classroom', on_delete=models.CASCADE, related_name='uniform_samples')
    image = models.BinaryField(editable=False)
    digest = models.CharField(max_length=64)
    label = models.CharField(max_length=10, choices=[(s,s) for s in ['SHIRT','SPORTS','OTHER']])
    capture_group = models.CharField(max_length=80)
    split = models.CharField(max_length=10, choices=[(s,s) for s in ['train','val','test']])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['classroom','digest'], name='unique_class_uniform_digest')]
