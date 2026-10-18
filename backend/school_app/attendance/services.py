from django.db.models import F
from django.utils import timezone
from school_app.accounts.services import AccountError
from school_app.academics.services import scoped_classes
from school_app.core.enums import Role, AttendanceStatus, UniformStatus, SessionStatus
from school_app.core.idempotency import run_idempotent, check_version, record_change
from school_app.schedules.services import dt
from .models import Attendance
from .forms import strict_fields, integer, text, arrival, invalid
from .uniform_rules import validate_uniform


def serialize_attendance(attendance):
    present=attendance.status == AttendanceStatus.PRESENT
    arrival_status=('ON_TIME' if attendance.arrived_at <= attendance.roster.session.late_cutoff_at else 'LATE') if present else 'NOT_APPLICABLE'
    data={'id':str(attendance.pk),'roster_id':str(attendance.roster_id),'arrival_status':arrival_status}
    for name in ['status','source','absence_reason','observed_uniform','uniform_status','uniform_reason','uniform_note','version']:
        data[name]=getattr(attendance,name)
    for name in ['arrived_at','verified_at','checked_at','updated_at']:
        data[name]=dt(getattr(attendance,name))
    for name in ['verified_by_id','checked_by_id']:
        value=getattr(attendance,name); data[name]=str(value) if value else None
    return data


def require_attendance(user, attendance_id):
    result=Attendance.objects.filter(pk=attendance_id,roster__session__classroom__in=scoped_classes(user)).select_related('roster__session').first()
    if result is None:
        raise AccountError('NOT_FOUND','Attendance not found.',404)
    return result


def writable_session(user, session, reason):
    if session.status == SessionStatus.PLANNED:
        raise AccountError('INVALID_STATE','Session must be opened.',409)
    if session.status == SessionStatus.CLOSED:
        if user.role != Role.SUPERVISOR:
            raise AccountError('SESSION_CLOSED','Only a supervisor may correct a closed session.',409)
        if not reason:
            invalid('A reason is required to correct a closed session.')


def apply_uniform(attendance, payload, user, now):
    if attendance.status != AttendanceStatus.PRESENT:
        invalid('Uniform checks require PRESENT attendance.')
    values=validate_uniform(payload, attendance.roster.session.required_uniform_snapshot)
    for name,value in values.items():
        setattr(attendance,name,value)
    attendance.checked_by_id=user.pk
    attendance.checked_at=now


def commit_attendance(attendance, expected):
    values={name:getattr(attendance,name) for name in ['status','source','arrived_at','absence_reason','observed_uniform','uniform_status','uniform_reason','uniform_note','verified_by_id','verified_at','checked_by_id','checked_at']}
    values.update(version=F('version')+1,updated_at=timezone.now())
    if not Attendance.objects.filter(pk=attendance.pk,version=expected).update(**values):
        raise AccountError('VERSION_CONFLICT','Attendance changed; reload it.',409)
    attendance.refresh_from_db()


def update_manual(user, attendance_id, payload, key):
    require_attendance(user,attendance_id)  # Scope before replay, including reassignment.
    def perform():
        from school_app.qr.models import QrScan
        from school_app.qr.services import expire_pending, serialize_scan
        attendance=require_attendance(user,attendance_id)
        strict_fields(payload,['expected_version','status','arrived_at','absence_reason','reason'],['expected_version','status'])
        expected=integer(payload,'expected_version')
        reason=text(payload,'reason')
        writable_session(user,attendance.roster.session,reason)
        check_version(attendance,expected)
        status=payload['status']
        if not isinstance(status,str) or status not in ['PRESENT','ABSENT']:
            invalid('Select PRESENT or ABSENT.')
        now=timezone.now()
        before=serialize_attendance(attendance)
        if status == AttendanceStatus.PRESENT:
            if 'arrived_at' not in payload:
                invalid('PRESENT requires arrived_at.')
            arrived=arrival(payload['arrived_at'])
            if arrived > now:
                invalid('arrived_at cannot be in the future.')
            try:
                arrival_date=timezone.localtime(arrived).date()
            except (OverflowError, ValueError):
                invalid('arrived_at is outside the supported date range.')
            if arrival_date != attendance.roster.session.school_date:
                invalid('arrived_at must belong to the session school_date.')
            if 'arrived_at' in payload and arrived < now and not reason:
                invalid('Retrospective arrival requires a reason.')
            if payload.get('absence_reason') is not None:
                invalid('PRESENT cannot have an absence reason.')
            if attendance.status != AttendanceStatus.PRESENT:
                attendance.uniform_status=UniformStatus.NOT_CHECKED
                attendance.observed_uniform=attendance.uniform_reason=attendance.uniform_note=None
                attendance.checked_by_id=attendance.checked_at=None
            attendance.arrived_at=arrived
            attendance.source='MANUAL'
            attendance.absence_reason=None
        else:
            if payload.get('arrived_at') is not None:
                invalid('ABSENT cannot have arrived_at.')
            attendance.arrived_at=attendance.source=None
            attendance.absence_reason=text(payload,'absence_reason')
            attendance.observed_uniform=attendance.uniform_reason=attendance.uniform_note=None
            attendance.uniform_status=UniformStatus.NOT_APPLICABLE
            attendance.checked_by_id=attendance.checked_at=None
        attendance.status=status
        attendance.verified_by_id=user.pk; attendance.verified_at=now
        commit_attendance(attendance,expected)
        from school_app.vision.models import VisionScan
        VisionScan.objects.filter(roster_id=attendance.roster_id,status='PENDING').update(
            status='SUPERSEDED',resolved_at=now,resolved_by=user,
            reason='Manual attendance',version=F('version')+1)
        expire_pending(roster_id=attendance.roster_id)
        for scan in QrScan.objects.filter(roster_id=attendance.roster_id,status='PENDING'):
            scan_before=serialize_scan(scan)
            scan.status='SUPERSEDED';scan.resolved_at=now;scan.resolved_by=user;scan.version+=1
            scan.save(update_fields=['status','resolved_at','resolved_by','version'])
            record_change(user,scan,'SUPERSEDE',scan_before,serialize_scan(scan),reason)
        body=serialize_attendance(attendance)
        record_change(user,attendance,'MANUAL',before,body,reason)
        return body,200
    return run_idempotent(user,'attendance.update:'+str(attendance_id),key,payload,perform)


def update_uniform(user, attendance_id, payload, key):
    require_attendance(user,attendance_id)
    def perform():
        attendance=require_attendance(user,attendance_id)
        strict_fields(payload,['expected_version','observed_uniform','uniform_status','reason','note'],['expected_version','observed_uniform','uniform_status'])
        expected=integer(payload,'expected_version'); reason=text(payload,'reason')
        writable_session(user,attendance.roster.session,reason)
        check_version(attendance,expected)
        before=serialize_attendance(attendance)
        apply_uniform(attendance,{name:value for name,value in payload.items() if name != 'expected_version'},user,timezone.now())
        commit_attendance(attendance,expected)
        body=serialize_attendance(attendance)
        record_change(user,attendance,'UNIFORM',before,body,reason)
        return body,200
    return run_idempotent(user,'attendance.uniform:'+str(attendance_id),key,payload,perform)
