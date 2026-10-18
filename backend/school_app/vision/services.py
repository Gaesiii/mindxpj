"""Scoped, idempotent vision proposals. No raw camera image is persisted."""
import hashlib
import time
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from school_app.accounts.services import AccountError
from school_app.academics.services import scoped_classes
from school_app.attendance.forms import strict_fields, integer, text, invalid
from school_app.attendance.services import serialize_attendance, apply_uniform, commit_attendance
from school_app.core.idempotency import run_idempotent, record_change, check_version
from school_app.schedules.models import SessionRoster
from school_app.schedules.services import require_session, dt
from . import engine
from .enrollment import sample_revision
from .models import FaceSample, VisionScan


def serialize_scan(scan):
    return {'id':str(scan.pk), 'roster_id':str(scan.roster_id),
            'attendance_id':str(scan.roster.attendance.pk),
            'student_id':str(scan.roster.student_id),
            'student_code_snapshot':scan.roster.student_code_snapshot,
            'full_name_snapshot':scan.roster.full_name_snapshot,
            'status':scan.status, 'version':scan.version,
            'expected_attendance_version':scan.attendance_version,
            'scanned_at':dt(scan.scanned_at), 'expires_at':dt(scan.expires_at),
            'resolved_at':dt(scan.resolved_at), 'reason':scan.reason,
            'distance':scan.distance, 'observed_uniform':scan.observed_uniform,
            'model_key':scan.model_key, 'cosine_score':scan.cosine_score,
            'metric':'cosine' if scan.model_key == engine.MODEL_KEY else 'lbph_distance',
            'color_coverage':scan.color_coverage}


def require_scan(user, scan_id):
    scan = VisionScan.objects.filter(pk=scan_id,roster__session__classroom__in=scoped_classes(user)).select_related(
        'roster__session','roster__student','roster__attendance').first()
    if scan is None:
        raise AccountError('NOT_FOUND','Scan not found.',404)
    return scan


def expire_pending(session_id):
    VisionScan.objects.filter(roster__session_id=session_id,status='PENDING',expires_at__lte=timezone.now()).update(
        status='EXPIRED',resolved_at=timezone.now(),version=F('version')+1)


def require_open_today(session):
    if session.status != 'OPEN':
        raise AccountError('SESSION_CLOSED','Vision requires an OPEN session.',409)
    if session.school_date != timezone.localdate():
        raise AccountError('SESSION_DATE','Vision may only record today. Use manual entry for corrections.',409)
    now = timezone.now()
    if session.start_at is None or session.close_at is None or not session.start_at <= now <= session.close_at:
        raise AccountError('SESSION_TIME','Vision requires the scheduled session time window.',409)


def analysis_limit(user):
    now = int(time.time()); window = 60
    key = f'vision:analysis:{user.pk}:{now//window}'
    if cache.add(key,1,timeout=window):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.add(key,1,timeout=window); count=1
    if count > settings.VISION_ANALYSES_PER_MINUTE:
        raise AccountError('RATE_LIMITED','Too many analyses; try later.',429,{'retry_after':window-now%window})


def analyze(user, session_id, upload, key):
    require_session(user,session_id)  # Scope before replay, mutable state inside callback.
    # Hash bounded original bytes for strict request retries; never persist them.
    if upload.size > engine.MAX_BYTES:
        analysis_limit(user)
        raise AccountError('INVALID_IMAGE','Image must be at most 2 MiB.',422)
    raw = upload.read(engine.MAX_BYTES+1)
    upload.seek(0)
    fingerprint = hashlib.sha256(raw).hexdigest()

    def perform():
        session = require_session(user,session_id)
        require_open_today(session)
        captured_at = timezone.now()
        analysis_limit(user)
        roster = list(SessionRoster.objects.filter(session=session,student__active=True,
                       student__classroom_id=session.classroom_id).select_related('student','attendance'))
        if len(roster)>50:
            raise AccountError('VISION_LIMIT','Demo supports at most 50 active roster students.',422)
        image = engine.decode_upload(upload)
        crop, box = engine.extract_face(image)
        samples = defaultdict(list)
        roster_samples = FaceSample.objects.filter(student_id__in=[row.student_id for row in roster])
        for sample in roster_samples.filter(model_key=engine.MODEL_KEY, embedding__isnull=False):
            samples[str(sample.student_id)].append(bytes(sample.embedding))
        samples = {student_id: vectors for student_id, vectors in samples.items() if len(vectors) >= 3}
        uniform = engine.suggest_uniform(image,box)
        if not samples and roster_samples.exists():
            return {'recognition':'UNKNOWN','reason':'REENROLLMENT_REQUIRED','uniform':uniform,'scan':None},200
        match = engine.match_face(crop,samples)
        if match['student_id'] is None:
            return {'recognition':'UNKNOWN','reason':match['reason'],'uniform':uniform,'scan':None},200
        row = next(row for row in roster if str(row.student_id)==match['student_id'])
        if row.attendance.status != 'UNMARKED':
            return {'recognition':'ALREADY_MARKED','scan':None,'attendance':serialize_attendance(row.attendance)},200
        require_open_today(session)
        now = captured_at
        VisionScan.objects.filter(roster=row,status='PENDING').update(status='SUPERSEDED',resolved_at=now,
            resolved_by=user,reason='New capture',version=F('version')+1)
        scan = VisionScan.objects.create(roster=row,created_by=user,scanned_at=now,expires_at=now+timedelta(seconds=120),
            sample_revision=sample_revision(row.student_id),attendance_version=row.attendance.version,
            distance=match['distance'],model_key=engine.MODEL_KEY,cosine_score=match['cosine_score'],**uniform)
        body = serialize_scan(scan)
        record_change(user,scan,'VISION_SCAN',{},body)
        return {'recognition':'CANDIDATE','scan':body,'uniform':uniform},201

    return run_idempotent(user,'vision.analyze:'+str(session_id),key,{'image_sha256':fingerprint},perform)


def queue(user, session_id):
    require_session(user,session_id)
    expire_pending(session_id)
    return {'items':[serialize_scan(scan) for scan in VisionScan.objects.filter(roster__session_id=session_id,
                    status='PENDING').select_related('roster__attendance').order_by('scanned_at')]}


def resolve(user, scan_id, payload, key, *, confirm):
    scan = require_scan(user,scan_id)
    expire_pending(scan.roster.session_id)

    def perform():
        scan = require_scan(user,scan_id)
        session, student, attendance = scan.roster.session, scan.roster.student, scan.roster.attendance
        require_open_today(session)
        allowed = ['expected_scan_version','expected_attendance_version','identity_confirmed','uniform'] if confirm else ['expected_scan_version','reason']
        required = allowed[:3] if confirm else allowed
        strict_fields(payload,allowed,required)
        if confirm and payload['identity_confirmed'] is not True:
            invalid('Staff must explicitly confirm identity.')
        check_version(scan,integer(payload,'expected_scan_version'))
        now = timezone.now()
        if scan.status != 'PENDING' or scan.expires_at <= now:
            raise AccountError('SCAN_NOT_PENDING','Scan has expired or been resolved.',409)
        before = serialize_scan(scan)
        if confirm:
            if not student.active or student.classroom_id != session.classroom_id:
                raise AccountError('ROSTER_CHANGED','Student is no longer active in this class.',409)
            if scan.sample_revision != sample_revision(student.pk):
                raise AccountError('ENROLLMENT_CHANGED','Face enrollment changed; rescan.',409)
            expected = integer(payload,'expected_attendance_version')
            check_version(attendance,expected)
            if expected != scan.attendance_version or attendance.status != 'UNMARKED':
                raise AccountError('ATTENDANCE_CHANGED','Attendance changed; reload it.',409)
            attendance_before = serialize_attendance(attendance)
            attendance.status,attendance.source = 'PRESENT','VISION'
            attendance.arrived_at = scan.scanned_at
            attendance.absence_reason = None
            attendance.uniform_status = 'NOT_CHECKED'
            attendance.observed_uniform = attendance.uniform_reason = attendance.uniform_note = None
            attendance.checked_by_id = attendance.checked_at = None
            attendance.verified_by_id,attendance.verified_at = user.pk,now
            if 'uniform' in payload:
                if isinstance(payload['uniform'],dict) and payload['uniform'].get('observed_uniform') == 'UNKNOWN':
                    invalid('UNKNOWN uniform must remain NOT_CHECKED; inspect before deciding.')
                apply_uniform(attendance,payload['uniform'],user,now)
            commit_attendance(attendance,expected)
            record_change(user,attendance,'VISION_CONFIRM',attendance_before,serialize_attendance(attendance))
            scan.status = 'CONFIRMED'
        else:
            scan.reason = text(payload,'reason',required=True)
            scan.status = 'REJECTED'
        scan.resolved_by,scan.resolved_at,scan.version = user,now,scan.version+1
        scan.save(update_fields=['status','reason','resolved_by','resolved_at','version'])
        record_change(user,scan,'CONFIRM' if confirm else 'REJECT',before,serialize_scan(scan),scan.reason)
        return ({'scan':serialize_scan(scan),'attendance':serialize_attendance(attendance)} if confirm else serialize_scan(scan)),200

    return run_idempotent(user,'vision.resolve:'+str(scan_id),key,{'confirm':confirm,**payload},perform)
