"""Trusted operator CLI; model upload is deliberately absent from HTTP APIs."""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


def validate_review(data,report,review,report_bytes,supervisor_id):
    labels=['SHIRT','SPORTS','OTHER']
    digest=hashlib.sha256(data).hexdigest()
    report_digest=hashlib.sha256(report_bytes).hexdigest()
    metrics=report.get('metrics',{})
    if (len(data)>32*1024*1024 or report.get('model_sha256')!=digest or report.get('labels')!=labels
        or not .8 <= report.get('threshold',0) <= 1 or review.get('report_sha256')!=report_digest
        or review.get('supervisor_id')!=str(supervisor_id) or review.get('approved') is not True
        or review.get('school_logo_shape_reviewed') is not True
        or review.get('wrong_school_hard_negatives_reviewed') is not True
        or review.get('occlusion_unknown_behavior_reviewed') is not True
        or not review.get('evidence_reference')
        or any(not .95 <= metrics.get(label,{}).get('precision',-1) <= 1 for label in labels)):
        raise ValueError('Artifact integrity, minimum precision or school-specific approval evidence missing')
    return digest,report_digest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True,help='Supervisor signed-off JSON; see README')
    parser.add_argument('--classroom',required=True)
    parser.add_argument('--supervisor',required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django
    django.setup()
    import cv2
    import numpy as np
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.db.models import Max, F
    from school_app.academics.services import supervisor_user,require_class
    from school_app.academics.models import Classroom
    from school_app.vision.uniform_models import SchoolUniformProfile
    from school_app.vision.uniform_services import require_active
    from school_app.vision.uniform_model import LABELS,artifact_root
    user=get_user_model().objects.get(pk=args.supervisor)
    supervisor_user(user); classroom=require_class(user,args.classroom)
    require_active(classroom)
    report=json.loads(args.report.read_text(encoding='utf-8'))
    review=json.loads(args.review.read_text(encoding='utf-8'))
    data=args.model.read_bytes()
    digest,report_digest=validate_review(data,report,review,args.report.read_bytes(),user.pk)
    net=cv2.dnn.readNetFromONNX(str(args.model)); net.setInput(np.zeros((1,3,224,224),np.float32))
    output=net.forward().reshape(-1)
    if output.shape != (3,) or not np.isfinite(output).all(): raise ValueError('Invalid inference contract')
    root=artifact_root(); root.mkdir(parents=True,exist_ok=True)
    key=f'{digest}.onnx'; destination=root/key
    if not destination.exists(): shutil.copyfile(args.model,destination)
    with transaction.atomic():
        Classroom.objects.filter(pk=classroom.pk).update(name=F('name'))
        user=get_user_model().objects.get(pk=user.pk)
        supervisor_user(user)
        classroom=require_class(user,classroom.pk)
        require_active(classroom)
        version=(SchoolUniformProfile.objects.filter(classroom=classroom).aggregate(v=Max('version'))['v'] or 0)+1
        profile=SchoolUniformProfile.objects.create(classroom=classroom,version=version,model_key=key,
            model_sha256=digest,labels=LABELS,accepted_labels=['SHIRT','SPORTS'],threshold=report['threshold'],
            metadata={'report':report,'review':review,'report_sha256':report_digest},created_by=user)
    print(json.dumps({'profile_id':str(profile.pk),'version':version,'selected':False}))


if __name__=='__main__': main()
