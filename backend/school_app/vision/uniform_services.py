"""Private garment dataset, independent of student face enrollment."""
import hashlib
import io
import json
import re
import zipfile
import cv2
from django.db import IntegrityError, transaction
from school_app.accounts.services import AccountError
from school_app.academics.services import require_class, supervisor_user
from .uniform_models import SchoolUniformProfile, SchoolUniformSample, SchoolUniformSelection
from .uniform_model import LABELS
from school_app.core.idempotency import record_change


def require_active(classroom):
    if not classroom.active:
        raise AccountError('INVALID_STATE','Archived classes cannot change uniform data.',409)


def snapshot(profile):
    return {'id':str(profile.pk),'version':profile.version,'model_key':profile.model_key,
            'model_sha256':profile.model_sha256,'labels':profile.labels,
            'accepted_labels':profile.accepted_labels,'threshold':profile.threshold,
            'metadata':profile.metadata}


def snapshot_for_class(classroom_id):
    selection = SchoolUniformSelection.objects.select_related('profile').filter(classroom_id=classroom_id).first()
    return snapshot(selection.profile) if selection else None


def profiles(user, classroom_id):
    require_class(user,classroom_id)
    return {'profile':snapshot_for_class(classroom_id),
            'versions':[snapshot(p) for p in SchoolUniformProfile.objects.filter(classroom_id=classroom_id).order_by('-version')]}


@transaction.atomic
def select_profile(user, classroom_id, payload):
    supervisor_user(user)
    classroom = require_class(user,classroom_id)
    require_active(classroom)
    before = snapshot_for_class(classroom_id)
    if set(payload) != {'profile_id'}:
        raise AccountError('VALIDATION_ERROR','Submit profile_id only.',422)
    if payload['profile_id'] is None:
        SchoolUniformSelection.objects.filter(classroom=classroom).delete()
    else:
        from school_app.core.api import parse_uuid
        profile = SchoolUniformProfile.objects.filter(pk=parse_uuid(payload['profile_id']), classroom=classroom).first()
        if profile is None:
            raise AccountError('NOT_FOUND','Uniform profile not found.',404)
        SchoolUniformSelection.objects.update_or_create(classroom=classroom, defaults={'profile':profile})
    record_change(user,classroom,'UNIFORM_PROFILE',{'profile':before},{'profile':snapshot_for_class(classroom_id)})
    return profiles(user,classroom_id)


def sample_metadata(sample):
    return {'id':str(sample.pk),'label':sample.label,'capture_group':sample.capture_group,
            'split':sample.split,'digest':sample.digest,'created_at':sample.created_at.isoformat()}


def samples(user, classroom_id):
    require_class(user,classroom_id)
    items = [sample_metadata(s) for s in SchoolUniformSample.objects.filter(classroom_id=classroom_id).defer('image').order_by('created_at')]
    return {'items':items,'count':len(items)}


def require_sample(user, sample_id):
    from school_app.academics.services import scoped_classes
    sample = SchoolUniformSample.objects.filter(pk=sample_id,classroom__in=scoped_classes(user)).first()
    if sample is None:
        raise AccountError('NOT_FOUND','Uniform sample not found.',404)
    return sample


def add_sample(user, classroom_id, upload, payload):
    supervisor_user(user)
    classroom = require_class(user,classroom_id)
    require_active(classroom)
    if set(payload) != {'label','capture_group','split','roi'} or payload['label'] not in LABELS or payload['split'] not in ['train','val','test']:
        raise AccountError('VALIDATION_ERROR','Supply label, capture_group, split and garment roi.',422)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',payload['capture_group']):
        raise AccountError('VALIDATION_ERROR','Use a non-identifying capture_group token.',422)
    try:
        roi = json.loads(payload['roi'])
        if not isinstance(roi,list) or len(roi) != 4 or any(type(v) is not int for v in roi):
            raise ValueError()
        x,y,w,h = roi
    except (ValueError,TypeError):
        raise AccountError('VALIDATION_ERROR','roi must be [x,y,width,height] integers.',422) from None
    from .engine import decode_upload, detect_faces
    image = decode_upload(upload)
    if min(x,y) < 0 or min(w,h) < 96 or x+w > image.shape[1] or y+h > image.shape[0]:
        raise AccountError('VALIDATION_ERROR','Garment crop must be inside image and at least 96 pixels.',422)
    faces = detect_faces(image)
    # Fail closed: original context must establish a head above the garment crop.
    if len(faces) != 1 or y < float(faces[0][1]+faces[0][3])*1.0 + 12:
        raise AccountError('INVALID_IMAGE','Show one face above a separate garment ROI; face pixels are never stored.',422)
    crop = image[y:y+h,x:x+w].copy()
    if len(detect_faces(crop)):
        raise AccountError('INVALID_IMAGE','Garment ROI contains a face.',422)
    ok, encoded = cv2.imencode('.png',crop)
    if not ok:
        raise AccountError('INVALID_IMAGE','Cannot encode garment crop.',422)
    data = encoded.tobytes()
    if len(data) > 1024*1024:
        raise AccountError('INVALID_IMAGE','Garment crop must encode to at most 1 MiB.',422)
    with transaction.atomic():
        # Serialize per-class dataset mutations before limits and group checks.
        from school_app.academics.models import Classroom
        from django.db.models import F
        Classroom.objects.filter(pk=classroom.pk).update(name=F('name'))
        # Detection happens outside the write lock; account and class may change.
        from django.contrib.auth import get_user_model
        actor=get_user_model().objects.filter(pk=user.pk,is_active=True).first()
        if actor is None:
            raise AccountError('UNAUTHENTICATED','Operator account is no longer active.',401)
        supervisor_user(actor)
        classroom=require_class(actor,classroom_id)
        require_active(classroom)
        if SchoolUniformSample.objects.filter(classroom=classroom).count() >= 1000:
            raise AccountError('VALIDATION_ERROR','Class dataset limit is 1000 samples.',422)
        from django.db.models import Sum
        from django.db.models.functions import Length
        total = SchoolUniformSample.objects.filter(classroom=classroom).aggregate(size=Sum(Length('image')))['size'] or 0
        if total + len(data) > 32*1024*1024:
            raise AccountError('VALIDATION_ERROR','Class private dataset limit is 32 MiB.',422)
        if SchoolUniformSample.objects.filter(classroom=classroom,capture_group=payload['capture_group']).exclude(split=payload['split']).exists():
            raise AccountError('VALIDATION_ERROR','A capture group must stay in one split.',422)
        try:
            sample = SchoolUniformSample.objects.create(classroom=classroom,image=data,
                digest=hashlib.sha256(data).hexdigest(),label=payload['label'],split=payload['split'],
                capture_group=payload['capture_group'],created_by=actor)
        except IntegrityError:
            raise AccountError('DUPLICATE','This garment image is already stored.',409) from None
        record_change(user,sample,'UNIFORM_SAMPLE_ADD',{},sample_metadata(sample))
    return sample_metadata(sample)


def delete_sample(user,sample_id):
    supervisor_user(user)
    with transaction.atomic():
        sample = require_sample(user,sample_id)
        require_active(sample.classroom)
        record_change(user,sample,'UNIFORM_SAMPLE_DELETE',sample_metadata(sample),{})
        sample.delete()
    return {'deleted':True}


def export_dataset(user, classroom_id):
    supervisor_user(user)
    require_class(user,classroom_id)
    from django.conf import settings
    from django.db.models import Sum
    from django.db.models.functions import Length
    rows=SchoolUniformSample.objects.filter(classroom_id=classroom_id).order_by('id')
    # Leave headroom for the manifest, ZIP headers and platform response envelope.
    # Reject before materializing private BLOBs or allocating the ZIP in memory.
    if getattr(settings,'VERCEL_DEMO',False):
        total=rows.aggregate(size=Sum(Length('image')))['size'] or 0
        if total >= 4*1024*1024 or rows.count()>500:
            raise AccountError('EXPORT_LIMIT_EXCEEDED','Dataset too large for Vercel demo export; use the local private dataset workflow.',422)
    manifest = {'schema_version':1,'classroom_id':str(classroom_id),'labels':LABELS,'samples':[]}
    output = io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for sample in rows.iterator():
            path = f'images/{sample.id}.png'
            archive.writestr(path,bytes(sample.image))
            manifest['samples'].append({**sample_metadata(sample),'path':path,'sha256':sample.digest})
        archive.writestr('manifest.json',json.dumps(manifest,indent=2))
    return output.getvalue()
