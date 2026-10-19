"""Two-frame automatic recording, with inference outside the write transaction.

No frames are retained. Consistency between images is not a liveness check.
"""
import hashlib
import json
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from school_app.accounts.services import AccountError
from school_app.attendance.services import serialize_attendance, commit_attendance
from school_app.core.idempotency import lookup_idempotent, run_idempotent, check_version, record_change
from school_app.schedules.models import SessionRoster
from school_app.schedules.services import require_session
from . import engine
from .enrollment import sample_revision
from .models import FaceSample, VisionScan
from .services import analysis_limit, require_open_today

MAX_FRAME_BYTES = 1024 * 1024


def _roster(session):
    return list(SessionRoster.objects.filter(session=session, student__active=True,
        student__classroom_id=session.classroom_id).select_related('student','attendance','session'))


def _current_session(user,session_id):
    # Inference may outlive a concurrent account lock or business-role change.
    from django.contrib.auth import get_user_model
    actor=get_user_model().objects.filter(pk=user.pk,is_active=True).first()
    if actor is None:
        raise AccountError('UNAUTHENTICATED','Operator account is no longer active.',401)
    return require_session(actor,session_id)


def _revision(session):
    """Include all candidates; changing another student's samples can change ambiguity."""
    rows = SessionRoster.objects.filter(session=session).order_by('id').values_list(
        'id','student_id','student__active','student__classroom_id','student__version')
    samples = FaceSample.objects.filter(student__sessionroster__session=session).order_by('id').values_list(
        'id','student_id','model_key','digest')
    return hashlib.sha256(json.dumps([list(rows),list(samples)],default=str).encode()).hexdigest()


def _response(outcome, *, row=None, uniform=None, reason=None):
    body = {'outcome':outcome, 'recognition':outcome, 'reason':reason, 'uniform':uniform}
    if row is not None:
        body.update(student_id=str(row.student_id), full_name_snapshot=row.full_name_snapshot,
                    attendance=serialize_attendance(row.attendance))
    return body


def _apply_uniform(attendance, result, now):
    # A teacher's decision (including a false-alarm correction) always wins.
    if attendance.checked_by_id is not None or attendance.uniform_status != 'NOT_CHECKED':
        return False
    if result['uniform_status'] not in ('COMPLIANT','REVIEW_REQUIRED'):
        return False
    attendance.uniform_status = result['uniform_status']
    attendance.observed_uniform = result['observed_uniform']
    attendance.uniform_source = 'AUTO'
    attendance.uniform_reason = attendance.uniform_note = None
    attendance.checked_by_id = None
    attendance.checked_at = now
    return True


def analyze_auto(user, session_id, uploads, mode, expected_session_version, key):
    session = require_session(user,session_id)  # Scope before cached response or image reads.
    if mode not in ('AUTO_ATTENDANCE','UNIFORM_ONLY'):
        raise AccountError('VALIDATION_ERROR','Select a valid scan mode.',422)
    if type(expected_session_version) is not int or expected_session_version < 0:
        raise AccountError('VALIDATION_ERROR','Expected session version is required.',422)
    if len(uploads) != 2 or any(upload.size > MAX_FRAME_BYTES for upload in uploads):
        raise AccountError('INVALID_IMAGE','Submit two images, at most 1 MiB each.',422)
    raw = [upload.read(MAX_FRAME_BYTES+1) for upload in uploads]
    for upload in uploads:
        upload.seek(0)
    if any(len(data)>MAX_FRAME_BYTES for data in raw):
        raise AccountError('INVALID_IMAGE','Image exceeds the frame limit.',422)
    hashes = [hashlib.sha256(data).hexdigest() for data in raw]
    if hashes[0] == hashes[1]:
        raise AccountError('INVALID_IMAGE','Capture two distinct frames.',422)
    payload = {'images':hashes,'scan_mode':mode,'expected_session_version':expected_session_version}
    operation = 'vision.auto:'+str(session_id)
    replay = lookup_idempotent(user,operation,key,payload)
    if replay is not None:
        return replay
    require_open_today(session)
    check_version(session,expected_session_version)
    if not session.classroom.active:
        raise AccountError('CLASS_ARCHIVED','Classroom is archived.',409)
    analysis_limit(user)  # One bounded pair counts as one analysis.
    captured_at = timezone.now()
    signature = _revision(session)
    class_version = session.classroom.version
    profile = session.uniform_profile_snapshot

    def unknown(outcome,reason):
        def remember():
            current=_current_session(user,session_id)
            require_open_today(current)
            check_version(current,expected_session_version)
            if _revision(current) != signature or not current.classroom.active:
                raise AccountError('ROSTER_CHANGED','Roster changed; rescan.',409)
            return _response(outcome,reason=reason),200
        return run_idempotent(user,operation,key,payload,remember)

    roster = _roster(session)
    if len(roster) > 50:
        raise AccountError('VISION_LIMIT','Demo supports at most 50 active roster students.',422)
    grouped = defaultdict(list)
    for student_id, embedding in FaceSample.objects.filter(
            student_id__in=[row.student_id for row in roster],model_key=engine.MODEL_KEY,
            embedding__isnull=False).values_list('student_id','embedding'):
        grouped[str(student_id)].append(bytes(embedding))
    samples = {sid:vectors for sid,vectors in grouped.items() if len(vectors)>=3}
    images, boxes, matches = [], [], []
    recoverable = {'NO_FACE','MULTIPLE_FACES','FACE_TOO_SMALL','BLURRY_FACE'}
    for upload in uploads:
        image = engine.decode_upload(upload)
        try:
            crop,box = engine.extract_face(image)
        except AccountError as exc:
            if exc.code not in recoverable:
                raise
            return unknown('AMBIGUOUS' if exc.code=='MULTIPLE_FACES' else 'UNKNOWN',exc.code)
        images.append(image)
        boxes.append(box)
        matches.append(engine.match_face(crop,samples,
            min_cosine=settings.VISION_AUTO_MIN_COSINE,min_margin=settings.VISION_AUTO_MIN_MARGIN))
    ids = [match['student_id'] for match in matches]
    if any(sid is None for sid in ids):
        reason = next(match['reason'] for match in matches if match['student_id'] is None)
        return unknown('AMBIGUOUS' if reason=='AMBIGUOUS_FACE' else 'UNKNOWN',reason)
    if ids[0] != ids[1]:
        return unknown('AMBIGUOUS','INCONSISTENT_IDENTITY')
    # Defensive validation even if a future matcher implementation changes.
    if min(match['cosine_score'] for match in matches) < settings.VISION_AUTO_MIN_COSINE:
        return unknown('UNKNOWN','AUTO_THRESHOLD')
    row = next((row for row in roster if str(row.student_id)==ids[0]),None)
    if row is None:
        return unknown('UNKNOWN','NOT_IN_ROSTER')
    attendance_version = row.attendance.version
    from .uniform_model import evaluate_pair
    uniform_profile = {**profile,'required_uniform':session.required_uniform_snapshot} if profile else None
    uniform = evaluate_pair(images,boxes,uniform_profile)

    def commit():
        current = _current_session(user,session_id)
        require_open_today(current)
        check_version(current,expected_session_version)
        if (not current.classroom.active or current.classroom.version != class_version
                or current.uniform_profile_snapshot != profile or _revision(current) != signature):
            raise AccountError('ROSTER_CHANGED','Class, roster or face enrollment changed; rescan.',409)
        live = SessionRoster.objects.select_related('student','attendance','session').get(pk=row.pk)
        if not live.student.active or live.student.classroom_id != current.classroom_id:
            raise AccountError('ROSTER_CHANGED','Student changed; rescan.',409)
        attendance = live.attendance
        if mode == 'UNIFORM_ONLY' and attendance.status != 'PRESENT':
            return _response('NOT_PRESENT',row=live,uniform=uniform),200
        if mode == 'AUTO_ATTENDANCE' and attendance.status != 'UNMARKED':
            return _response('ALREADY_RECORDED',row=live,uniform=uniform),200
        check_version(attendance,attendance_version)
        before = serialize_attendance(attendance)
        now = timezone.now()
        if mode == 'AUTO_ATTENDANCE':
            attendance.status,attendance.source,attendance.recognition_mode = 'PRESENT','VISION','AUTO'
            attendance.arrived_at = captured_at
            attendance.absence_reason = None
            attendance.verified_by_id = attendance.verified_at = None
            attendance.recorded_by_id = user.pk
            attendance.uniform_status = 'NOT_CHECKED'
            attendance.uniform_source = None
        updated = _apply_uniform(attendance,uniform,now)
        if mode == 'UNIFORM_ONLY' and not updated:
            return _response('ALREADY_RECORDED',row=live,uniform=uniform),200
        commit_attendance(attendance,attendance_version)
        if mode == 'AUTO_ATTENDANCE':
            VisionScan.objects.filter(roster=live,status='PENDING').update(status='SUPERSEDED',
                resolved_at=now,reason='Automatic attendance',version=F('version')+1)
            VisionScan.objects.create(roster=live,created_by=user,scanned_at=captured_at,
                expires_at=captured_at+timedelta(seconds=120),sample_revision=sample_revision(live.student_id),
                attendance_version=attendance_version,distance=max(m['distance'] for m in matches),
                model_key=engine.MODEL_KEY,cosine_score=min(m['cosine_score'] for m in matches),
                observed_uniform=uniform['observed_uniform'],color_coverage=0,
                status='AUTO_RECORDED',resolved_at=now)
        record_change(user,attendance,'AUTO_ATTENDANCE' if mode=='AUTO_ATTENDANCE' else 'AUTO_UNIFORM',
            before,serialize_attendance(attendance))
        return _response('RECORDED' if mode=='AUTO_ATTENDANCE' else 'UNIFORM_UPDATED',
                         row=live,uniform=uniform),201 if mode=='AUTO_ATTENDANCE' else 200

    return run_idempotent(user,operation,key,payload,commit)
