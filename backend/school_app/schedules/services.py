from datetime import datetime, timedelta, timezone as datetime_timezone
from django.db import transaction, IntegrityError
from django.db.models import F
from django.utils import timezone
from school_app.accounts.services import AccountError
from school_app.academics.services import scoped_classes, require_class
from school_app.core.api import form_data
from school_app.core.enums import SessionStatus, UniformStatus
from school_app.core.idempotency import check_version, record_change
from .forms import ScheduleRuleForm, SessionCreateForm
from .models import ScheduleRule, Session, SessionRoster


def dt(value):
    return value.astimezone(datetime_timezone.utc).isoformat().replace('+00:00','Z') if value is not None else None


def serialize_rule(rule):
    return {'id':str(rule.id),'class_id':str(rule.classroom_id), **rule_fields(rule)}


def rule_fields(rule):
    return {name: getattr(rule,name).isoformat() if name.endswith('_time') else getattr(rule,name) for name in ['weekday','slot','start_time','close_time','grace_minutes','required_uniform']}


def serialize_session(session):
    return {'id':str(session.id),'class_id':str(session.classroom_id),'school_date':str(session.school_date),'slot':session.slot,'status':session.status,'start_at':dt(session.start_at),'late_cutoff_at':dt(session.late_cutoff_at),'close_at':dt(session.close_at),'required_uniform_snapshot':session.required_uniform_snapshot,'version':session.version}


def scoped_sessions(user):
    return Session.objects.filter(classroom__in=scoped_classes(user)).select_related('classroom__grade')


def require_session(user, session_id):
    result=scoped_sessions(user).filter(pk=session_id).first()
    if result is None:
        raise AccountError('NOT_FOUND','Session not found.',404)
    return result


def save_rule(user, payload, *, classroom_id=None, rule=None):
    if rule is None:
        classroom=require_class(user,classroom_id)
        values=form_data(ScheduleRuleForm(payload))
        rule=ScheduleRule(classroom=classroom)
    else:
        require_class(user,rule.classroom_id)
        values=form_data(ScheduleRuleForm(payload,current=rule_fields(rule)))
    for name,value in values.items():
        setattr(rule,name,value)
    try:
        with transaction.atomic():
            rule.save()
    except IntegrityError:
        raise AccountError('DUPLICATE','Rule already exists for this weekday and slot.',409) from None
    return rule


def find_rule(session):
    result=ScheduleRule.objects.filter(classroom_id=session.classroom_id,weekday=session.school_date.weekday(),slot=session.slot).first()
    if result is None:
        raise AccountError('VALIDATION_ERROR','A schedule rule is required for this date and slot.',422)
    return result


def create_session(user, payload):
    values=form_data(SessionCreateForm(payload))
    classroom=require_class(user,values.pop('class_id'))
    with transaction.atomic():
        existing=Session.objects.filter(classroom=classroom,**values).first()
        if existing is not None:
            return existing,False
        probe=Session(classroom=classroom,**values)
        find_rule(probe)
        return Session.objects.get_or_create(classroom=classroom,**values)


def open_session(user, session_id, expected):
    from school_app.students.models import Student
    from school_app.attendance.models import Attendance
    require_session(user,session_id)
    with transaction.atomic():
        session=require_session(user,session_id)
        if session.status == SessionStatus.OPEN:
            return session
        if session.status == SessionStatus.CLOSED:
            raise AccountError('SESSION_CLOSED','Closed sessions cannot reopen.',409)
        check_version(session,expected)
        rule=find_rule(session)
        start=timezone.make_aware(datetime.combine(session.school_date,rule.start_time))
        close=timezone.make_aware(datetime.combine(session.school_date,rule.close_time))
        before=serialize_session(session)
        changed=Session.objects.filter(pk=session.pk,version=expected,status=SessionStatus.PLANNED).update(status=SessionStatus.OPEN,start_at=start,late_cutoff_at=start+timedelta(minutes=rule.grace_minutes),close_at=close,required_uniform_snapshot=rule.required_uniform,version=F('version')+1)
        if not changed:
            raise AccountError('VERSION_CONFLICT','Session changed; reload it.',409)
        classroom=session.classroom
        students=Student.objects.filter(classroom=classroom,active=True).order_by('student_code')
        roster=[SessionRoster(session=session,student=student,student_code_snapshot=student.student_code,full_name_snapshot=student.full_name,class_code_snapshot=classroom.code,class_name_snapshot=classroom.name,grade_code_snapshot=classroom.grade.code,grade_name_snapshot=classroom.grade.name) for student in students]
        SessionRoster.objects.bulk_create(roster)
        Attendance.objects.bulk_create([Attendance(roster=row) for row in roster])
        session.refresh_from_db()
        record_change(user,session,'OPEN',before,serialize_session(session))
        return session


def close_session(user, session_id, expected):
    from school_app.attendance.models import Attendance
    from school_app.qr.models import QrScan
    require_session(user,session_id)
    with transaction.atomic():
        session=require_session(user,session_id)
        if session.status == SessionStatus.CLOSED:
            return {**serialize_session(session),'converted_unmarked':0,'expired_pending':0,'remaining_not_checked':Attendance.objects.filter(roster__session=session,uniform_status=UniformStatus.NOT_CHECKED).count()}
        if session.status != SessionStatus.OPEN:
            raise AccountError('INVALID_STATE','Open the session before closing.',409)
        check_version(session,expected)
        before=serialize_session(session)
        if not Session.objects.filter(pk=session.pk,version=expected,status=SessionStatus.OPEN).update(status=SessionStatus.CLOSED,version=F('version')+1):
            raise AccountError('VERSION_CONFLICT','Session changed; reload it.',409)
        now=timezone.now()
        # Closing converts only unmarked attendance. PRESENT uniforms remain.
        converted=Attendance.objects.filter(roster__session=session,status='UNMARKED').update(status='ABSENT',version=F('version')+1,updated_at=now)
        expired=QrScan.objects.filter(roster__session=session,status='PENDING').update(status='EXPIRED',resolved_at=now,version=F('version')+1)
        from school_app.vision.models import VisionScan
        expired+=VisionScan.objects.filter(roster__session=session,status='PENDING').update(
            status='EXPIRED',resolved_at=now,version=F('version')+1)
        session.refresh_from_db()
        body={**serialize_session(session),'converted_unmarked':converted,'expired_pending':expired,'remaining_not_checked':Attendance.objects.filter(roster__session=session,uniform_status=UniformStatus.NOT_CHECKED).count()}
        record_change(user,session,'CLOSE',before,body)
        return body
