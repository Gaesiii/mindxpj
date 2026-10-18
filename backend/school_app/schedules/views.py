from django import forms
from school_app.accounts.permissions import require_authenticated
from school_app.accounts.services import AccountError
from school_app.academics.services import require_class, assert_class_filter
from school_app.core.api import api_view, read_json, json_response, form_data, parse_uuid
from school_app.core.enums import Slot
from .models import ScheduleRule
from .forms import SessionVersionForm, JsonDateField
from . import services

@api_view('GET','POST')
def rules(request, class_id):
    user=require_authenticated(request)
    classroom=require_class(user,class_id)
    if request.method == 'POST':
        return json_response(services.serialize_rule(services.save_rule(user,read_json(request),classroom_id=class_id)),201)
    return json_response({'items':[services.serialize_rule(row) for row in ScheduleRule.objects.filter(classroom=classroom).order_by('weekday','slot')]})

@api_view('PATCH')
def rule_detail(request, rule_id):
    user=require_authenticated(request)
    from school_app.academics.services import scoped_classes
    rule=ScheduleRule.objects.filter(pk=rule_id,classroom__in=scoped_classes(user)).first()
    if rule is None:
        raise AccountError('NOT_FOUND','Schedule rule not found.',404)
    return json_response(services.serialize_rule(services.save_rule(user,read_json(request),rule=rule)))

@api_view('GET','POST')
def sessions(request):
    user=require_authenticated(request)
    if request.method == 'POST':
        session,created=services.create_session(user,read_json(request))
        return json_response(services.serialize_session(session),201 if created else 200)
    rows=services.scoped_sessions(user)
    if set(request.GET)-{'class_id','date_from','date_to','slot'}:
        raise AccountError('VALIDATION_ERROR','Unsupported filter.',422)
    if 'class_id' in request.GET:
        cid=parse_uuid(request.GET['class_id']); assert_class_filter(user,cid); rows=rows.filter(classroom_id=cid)
    dates={}
    for name in ['date_from','date_to']:
        if name in request.GET:
            field=JsonDateField(input_formats=['%Y-%m-%d'])
            try:
                dates[name]=field.clean(request.GET[name])
            except forms.ValidationError:
                raise AccountError('VALIDATION_ERROR','Invalid date filter.',422) from None
            rows=rows.filter(**{'school_date__gte' if name=='date_from' else 'school_date__lte':dates[name]})
    if len(dates)==2 and dates['date_from']>dates['date_to']:
        raise AccountError('VALIDATION_ERROR','Date range is reversed.',422)
    if 'slot' in request.GET:
        if request.GET['slot'] not in Slot.values:
            raise AccountError('VALIDATION_ERROR','Invalid slot.',422)
        rows=rows.filter(slot=request.GET['slot'])
    return json_response({'items':[services.serialize_session(row) for row in rows.order_by('school_date','slot','classroom__code')]})

@api_view('GET')
def session_detail(request, session_id):
    return json_response(services.serialize_session(services.require_session(require_authenticated(request),session_id)))

@api_view('POST')
def session_open(request, session_id):
    user=require_authenticated(request)
    values=form_data(SessionVersionForm(read_json(request)))
    return json_response(services.serialize_session(services.open_session(user,session_id,values['expected_version'])))

@api_view('POST')
def session_close(request, session_id):
    user=require_authenticated(request)
    values=form_data(SessionVersionForm(read_json(request)))
    return json_response(services.close_session(user,session_id,values['expected_version']))

@api_view('GET')
def roster(request, session_id):
    from school_app.attendance.services import serialize_attendance
    from school_app.qr.services import expire_pending
    session=services.require_session(require_authenticated(request),session_id)
    expire_pending(session_id=session.pk)
    rows=session.roster.select_related('attendance','session').order_by('student_code_snapshot')
    return json_response({'items':[{'id':str(row.pk),'student_id':str(row.student_id), **{name:getattr(row,name) for name in ['student_code_snapshot','full_name_snapshot','class_code_snapshot','class_name_snapshot','grade_code_snapshot','grade_name_snapshot']},'attendance':serialize_attendance(row.attendance)} for row in rows]})
