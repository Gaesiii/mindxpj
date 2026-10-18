"""Synchronous challenge issuance and expiry; no worker or distributed cache."""
import base64
import hashlib
import io
import secrets
import time
from datetime import timedelta
import qrcode
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.db.models import F
from django.utils import timezone
from school_app.accounts.services import AccountError
from school_app.core.enums import Role, SessionStatus
from school_app.core.idempotency import run_idempotent, check_version, record_change
from school_app.schedules.models import SessionRoster
from school_app.schedules.services import require_session, dt, serialize_session
from school_app.attendance.services import serialize_attendance, require_attendance, apply_uniform, commit_attendance
from school_app.attendance.forms import strict_fields, text, integer, invalid
from .models import QrChallenge, QrScan


def serialize_scan(scan):
    return {'id':str(scan.pk),'roster_id':str(scan.roster_id),'status':scan.status,'scanned_at':dt(scan.scanned_at),'expires_at':dt(scan.expires_at),'version':scan.version,'resolved_by_id':str(scan.resolved_by_id) if scan.resolved_by_id else None,'resolved_at':dt(scan.resolved_at),'reason':scan.reason}


def expire_pending(*, session_id=None, roster_id=None):
    rows=QrScan.objects.filter(status='PENDING',expires_at__lte=timezone.now())
    if session_id is not None:
        rows=rows.filter(roster__session_id=session_id)
    elif roster_id is not None:
        rows=rows.filter(roster_id=roster_id)
    else:
        raise ValueError('Expiry requires a scoped session or roster.')
    return rows.update(status='EXPIRED',resolved_at=timezone.now(),version=F('version')+1)


def student_for_user(user):
    if not user.is_authenticated or not user.is_active:
        raise AccountError('UNAUTHENTICATED','Authentication is required.',401)
    if user.role != Role.STUDENT:
        raise AccountError('FORBIDDEN','Only a student may scan.',403)
    if not user.student_id:
        raise AccountError('STUDENT_NOT_LINKED','Student account has no profile.',403)
    from school_app.students.models import Student
    student=Student.objects.get(pk=user.student_id)
    if not student.active:
        raise AccountError('FORBIDDEN','Student profile is inactive.',403)
    return student


def scan_limit(user):
    now=int(time.time()); window=60; key=f'qr:scan:{user.pk}:{now//window}'
    if cache.add(key,1,timeout=window):
        count=1
    else:
        try:
            count=cache.incr(key)
        except ValueError:
            cache.add(key,1,timeout=window);count=1
    if count > 30:
        raise AccountError('RATE_LIMITED','Too many scans; try later.',429,{'retry_after':window-now%window})


def issue_challenge(user, session_id):
    require_session(user,session_id)
    token=secrets.token_urlsafe(32)
    with transaction.atomic():
        # A write fence serializes issuance against close on SQLite as well.
        from school_app.schedules.models import Session
        session=require_session(user,session_id)
        if session.status != SessionStatus.OPEN:
            raise AccountError('SESSION_CLOSED' if session.status == SessionStatus.CLOSED else 'INVALID_STATE','QR requires an OPEN session.',409)
        if not Session.objects.filter(pk=session.pk,status='OPEN').update(status='OPEN'):
            raise AccountError('SESSION_CLOSED','Session was closed.',409)
        now=timezone.now()
        challenge=QrChallenge.objects.create(session=session,token_hash=hashlib.sha256(token.encode()).hexdigest(),issued_by=user,issued_at=now,expires_at=now+timedelta(seconds=60))
        output=io.BytesIO();qrcode.make(token).save(output,format='PNG')
        return {'id':str(challenge.pk),'session_id':str(session.pk),'token':token,'issued_at':dt(now),'expires_at':dt(challenge.expires_at),'refresh_after_seconds':30,'qr_image_base64':base64.b64encode(output.getvalue()).decode()}


def scan_token(user, payload, key):
    student=student_for_user(user)
    try:
        strict_fields(payload,['token'],['token'])
        token=payload['token']
        if not isinstance(token,str) or not token or len(token)>512:
            invalid('token must be a nonempty string of at most 512 characters.')
        fingerprint=hashlib.sha256(token.encode()).hexdigest()
        challenge=QrChallenge.objects.filter(token_hash=fingerprint).select_related('session').first()
        if challenge is None:
            raise AccountError('QR_INVALID','Invalid QR token.',422)
        roster=SessionRoster.objects.filter(session=challenge.session,student=student,session__classroom_id=student.classroom_id).select_related('session','attendance').first()
        if roster is None:
            raise AccountError('ROSTER_REQUIRED','Current classroom and session roster must match.',422)
    except AccountError:
        # Invalid token/schema/roster attempts still consume quota. Valid
        # requests count inside the callback so successful retries can replay.
        scan_limit(user)
        raise
    expire_pending(roster_id=roster.pk)
    def perform():
        scan_limit(user)
        # Reload state after unique idempotency claim obtained the write lock.
        roster.refresh_from_db(); session=roster.session
        if session.status != SessionStatus.OPEN:
            raise AccountError('SESSION_CLOSED' if session.status == SessionStatus.CLOSED else 'INVALID_STATE','Scan requires an OPEN session.',409)
        now=timezone.now()
        if challenge.expires_at <= now:
            raise AccountError('QR_EXPIRED','QR token expired.',422)
        attendance=roster.attendance
        if attendance.status != 'UNMARKED':
            latest=QrScan.objects.filter(roster=roster).order_by('-scanned_at').first()
            if latest and latest.status == 'CONFIRMED' and attendance.source == 'QR':
                return serialize_scan(latest),200
            return {'scan':serialize_scan(latest) if latest else None,'attendance':serialize_attendance(attendance)},200
        pending=QrScan.objects.filter(roster=roster,status='PENDING').first()
        if pending:
            return serialize_scan(pending),200
        scan=QrScan.objects.create(roster=roster,challenge=challenge,student_user=user,scanned_at=now,expires_at=now+timedelta(minutes=15))
        body=serialize_scan(scan)
        record_change(user,scan,'SCAN',{},body)
        return body,201
    return run_idempotent(user,'qr.scan',key,{'token_fingerprint':fingerprint},perform)


def require_scan(user, scan_id):
    from school_app.academics.services import scoped_classes
    scan=QrScan.objects.filter(pk=scan_id,roster__session__classroom__in=scoped_classes(user)).select_related('roster__session','roster__attendance').first()
    if scan is None:
        raise AccountError('NOT_FOUND','Scan not found.',404)
    return scan


def resolve_scan(user, scan_id, payload, key, *, confirm):
    scoped=require_scan(user,scan_id)
    # Persist lazy expiry independently so a rejected confirm cannot roll it back.
    expire_pending(roster_id=scoped.roster_id)
    def perform():
        scan=require_scan(user,scan_id)
        allowed=['expected_scan_version','expected_attendance_version','identity_confirmed','uniform'] if confirm else ['expected_scan_version','reason']
        required=['expected_scan_version','expected_attendance_version','identity_confirmed'] if confirm else ['expected_scan_version','reason']
        strict_fields(payload,allowed,required)
        expected=integer(payload,'expected_scan_version')
        if scan.roster.session.status != SessionStatus.OPEN:
            raise AccountError('SESSION_CLOSED','Only OPEN sessions accept scan verification.',409)
        if scan.status != 'PENDING':
            raise AccountError('INVALID_STATE','Scan is no longer pending.',409)
        check_version(scan,expected)
        if scan.expires_at <= timezone.now():
            raise AccountError('INVALID_STATE','Pending scan expired.',409)
        before=serialize_scan(scan);now=timezone.now()
        if confirm:
            if payload['identity_confirmed'] is not True:
                invalid('identity_confirmed must be JSON true.')
            att_expected=integer(payload,'expected_attendance_version')
            attendance=scan.roster.attendance
            check_version(attendance,att_expected)
            if attendance.status != 'UNMARKED':
                raise AccountError('INVALID_STATE','Attendance was already recorded.',409)
            att_before=serialize_attendance(attendance)
            attendance.status='PRESENT';attendance.source='QR';attendance.arrived_at=scan.scanned_at
            attendance.verified_by_id=user.pk;attendance.verified_at=now
            attendance.uniform_status='NOT_CHECKED';attendance.absence_reason=None
            if 'uniform' in payload:
                apply_uniform(attendance,payload['uniform'],user,now)
            commit_attendance(attendance,att_expected)
            scan.status='CONFIRMED';reason=None
        else:
            reason=text(payload,'reason',required=True)
            scan.status='REJECTED'
        if not QrScan.objects.filter(pk=scan.pk,status='PENDING',version=expected).update(status=scan.status,resolved_at=now,resolved_by=user,version=F('version')+1,reason=reason):
            raise AccountError('VERSION_CONFLICT','Scan changed; reload it.',409)
        scan.refresh_from_db();scan_body=serialize_scan(scan)
        record_change(user,scan,'CONFIRM' if confirm else 'REJECT',before,scan_body,reason)
        if confirm:
            attendance_body=serialize_attendance(attendance)
            record_change(user,attendance,'QR_CONFIRM',att_before,attendance_body)
            return {'scan':scan_body,'attendance':attendance_body},200
        return scan_body,200
    return run_idempotent(user,('qr.confirm:' if confirm else 'qr.reject:')+str(scan_id),key,payload,perform)


def own_roster(user, session_id):
    student=student_for_user(user)
    roster=SessionRoster.objects.filter(session_id=session_id,student=student,session__classroom_id=student.classroom_id).select_related('session','attendance').first()
    if roster is None:
        raise AccountError('NOT_FOUND','Own session not found.',404)
    return roster


def own_status(user, session_id):
    roster=own_roster(user,session_id)
    expire_pending(roster_id=roster.pk)
    latest=roster.scans.order_by('-scanned_at').first()
    return {'scan':serialize_scan(latest) if latest else None,'attendance':serialize_attendance(roster.attendance)}


def today_sessions(user):
    student=student_for_user(user)
    rows=SessionRoster.objects.filter(student=student,session__classroom_id=student.classroom_id,session__school_date=timezone.localdate(),session__status__in=['OPEN','CLOSED']).select_related('session','attendance').order_by('session__slot')
    result=[]
    for roster in rows:
        expire_pending(roster_id=roster.pk)
        result.append({**serialize_session(roster.session),'attendance':serialize_attendance(roster.attendance)})
    return result
