"""Enrollment is separate from profile photos; only crops are retained privately."""
import hashlib

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from school_app.accounts.services import AccountError
from school_app.core.idempotency import record_change
from school_app.students.services import require_student_profile
from . import engine
from .models import FaceSample, VisionScan


def sample_revision(student_id):
    ids = FaceSample.objects.filter(student_id=student_id).order_by('id').values_list('id',flat=True)
    return hashlib.sha256(','.join(map(str, ids)).encode()).hexdigest()


def metadata(user, student_id):
    student = require_student_profile(user, student_id)
    samples = FaceSample.objects.filter(student=student)
    total = samples.count()
    usable = samples.filter(model_key=engine.MODEL_KEY, embedding__isnull=False).count()
    return {'student_id':str(student.pk), 'sample_count':total,
            'usable_sample_count':usable, 'requires_reenrollment':total > 0 and usable < 3,
            'model_key':engine.MODEL_KEY}


def invalidate_samples(student, user):
    VisionScan.objects.filter(roster__student=student, status='PENDING').update(
        status='SUPERSEDED', resolved_at=timezone.now(), resolved_by=user,
        reason='Face enrollment changed', version=F('version')+1)


def replace_samples(user, student_id, uploads):
    student = require_student_profile(user, student_id)
    if not student.active or not student.classroom.active:
        raise AccountError('INVALID_STATE','Only active students may enroll.',409)
    budget = settings.VISION_ENROLLMENT_TOTAL_BYTES
    if not 3 <= len(uploads) <= 10 or sum(file.size for file in uploads) > budget:
        raise AccountError('VALIDATION_ERROR',
                           f'Submit 3–10 images, at most {budget / (1024 * 1024):g} MiB total.',422)
    crops = [engine.extract_face(engine.decode_upload(file,
        max_bytes=settings.VISION_ENROLLMENT_IMAGE_BYTES,
        max_pixels=settings.VISION_ENROLLMENT_MAX_PIXELS))[0] for file in uploads]
    encoded = [engine.encode_face(crop) for crop in crops]
    embeddings = [engine.embed_face(crop) for crop in crops]
    digests = [hashlib.sha256(data).hexdigest() for data in encoded]
    if len(set(digests)) != len(digests):
        raise AccountError('VALIDATION_ERROR','Use distinct face samples.',422)
    with transaction.atomic():
        # First write serializes concurrent replacement before checking fresh scope.
        from school_app.students.models import Student
        Student.objects.filter(pk=student_id).update(active=F('active'))
        student = require_student_profile(user,student_id)
        if not student.active or not student.classroom.active:
            raise AccountError('INVALID_STATE','Only active students may enroll.',409)
        before = metadata(user, student_id)
        FaceSample.objects.filter(student=student).delete()
        FaceSample.objects.bulk_create([FaceSample(student=student,image=data,digest=digest,
            embedding=embedding,model_key=engine.MODEL_KEY,created_by=user)
            for data,digest,embedding in zip(encoded,digests,embeddings)])
        invalidate_samples(student,user)
        after = metadata(user,student_id)
        record_change(user,student,'FACE_ENROLL',before,after)
        return after


def delete_samples(user, student_id):
    require_student_profile(user,student_id)
    with transaction.atomic():
        from school_app.students.models import Student
        Student.objects.filter(pk=student_id).update(active=F('active'))
        student = require_student_profile(user,student_id)
        before = metadata(user,student_id)
        FaceSample.objects.filter(student=student).delete()
        invalidate_samples(student,user)
        after = metadata(user,student_id)
        record_change(user,student,'FACE_DELETE',before,after)
        return after
