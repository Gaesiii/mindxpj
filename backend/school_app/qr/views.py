from school_app.accounts.permissions import require_authenticated, require_student
from school_app.accounts.services import AccountError
from school_app.core.api import api_view, read_json, json_response, parse_uuid
from school_app.core.enums import QrScanStatus
from school_app.schedules.services import require_session
from . import services
from .models import QrScan

@api_view('POST')
def challenge(request,session_id):
    user=require_authenticated(request); require_session(user,session_id)
    read_json(request,allowed=[])
    return json_response(services.issue_challenge(user,session_id),201)

@api_view('POST')
def scan(request):
    require_student(request)
    data,status=services.scan_token(request.user,read_json(request),request.headers.get('Idempotency-Key'))
    return json_response(data,status)

@api_view('POST')
def confirm(request,scan_id):
    data,status=services.resolve_scan(require_authenticated(request),scan_id,read_json(request),request.headers.get('Idempotency-Key'),confirm=True)
    return json_response(data,status)

@api_view('POST')
def reject(request,scan_id):
    data,status=services.resolve_scan(require_authenticated(request),scan_id,read_json(request),request.headers.get('Idempotency-Key'),confirm=False)
    return json_response(data,status)

@api_view('GET')
def queue(request,session_id):
    user=require_authenticated(request)
    session=require_session(user,session_id)
    if set(request.GET)-{'status'}:
        raise AccountError('VALIDATION_ERROR','Unsupported filter.',422)
    status=request.GET.get('status','PENDING')
    if status not in QrScanStatus.values:
        raise AccountError('VALIDATION_ERROR','Invalid scan status.',422)
    services.expire_pending(session_id=session.pk)
    rows=list(QrScan.objects.filter(roster__session=session,status=status).select_related('roster').order_by('scanned_at'))
    from school_app.academics.services import scoped_classes
    from school_app.students.models import Student
    # Historical identities remain snapshots; current photo metadata is read
    # only after independently scoping current Student profiles.
    photos={student.pk for student in Student.objects.filter(pk__in=[row.roster.student_id for row in rows],classroom__in=scoped_classes(user)).only('id','photo_path') if student.photo_path}
    return json_response({'items':[{**services.serialize_scan(row),'student_id':str(row.roster.student_id),'student_code_snapshot':row.roster.student_code_snapshot,'full_name_snapshot':row.roster.full_name_snapshot,**{name:getattr(row.roster,name) for name in ['class_code_snapshot','class_name_snapshot','grade_code_snapshot','grade_name_snapshot']},'photo_url':f'/api/v1/students/{row.roster.student_id}/photo' if row.roster.student_id in photos else None} for row in rows]})

@api_view('GET')
def today(request):
    require_student(request)
    if request.GET:
        raise AccountError('VALIDATION_ERROR','No filters are accepted.',422)
    return json_response({'items':services.today_sessions(request.user)})

@api_view('GET')
def own_status(request):
    require_student(request)
    if set(request.GET) != {'session_id'}:
        raise AccountError('VALIDATION_ERROR','Only session_id is required.',422)
    return json_response(services.own_status(request.user,parse_uuid(request.GET['session_id'])))
