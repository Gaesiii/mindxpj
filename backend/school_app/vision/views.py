from school_app.accounts.services import AccountError
from school_app.core.api import api_view, json_response, read_json
from school_app.students.services import require_student_profile
from school_app.schedules.services import require_session


@api_view('POST')
def auto_scans(request, session_id):
    require_session(request.user,session_id)
    if (request.GET or set(request.POST) != {'scan_mode','expected_session_version'}
            or any(len(request.POST.getlist(name)) != 1 for name in request.POST)
            or set(request.FILES) != {'images'}):
        raise AccountError('VALIDATION_ERROR','Submit two images, scan_mode and expected_session_version only.',422)
    version = request.POST['expected_session_version']
    if not version.isascii() or not version.isdigit() or len(version)>10:
        raise AccountError('VALIDATION_ERROR','Expected session version must be an integer.',422)
    from .auto_attendance import analyze_auto
    body,status = analyze_auto(request.user,session_id,request.FILES.getlist('images'),
        request.POST['scan_mode'],int(version),request.headers.get('Idempotency-Key'))
    return json_response(body,status)


@api_view('GET','POST','DELETE')
def samples(request, student_id):
    require_student_profile(request.user,student_id)
    from . import enrollment
    if request.method == 'GET':
        if request.GET:
            raise AccountError('VALIDATION_ERROR','No filters are accepted.',422)
        return json_response(enrollment.metadata(request.user,student_id))
    if request.method == 'DELETE':
        if request.body or request.GET:
            raise AccountError('VALIDATION_ERROR','DELETE takes no body or query.',422)
        return json_response(enrollment.delete_samples(request.user,student_id))
    if request.GET or set(request.POST) or set(request.FILES) != {'images'}:
        raise AccountError('VALIDATION_ERROR','Submit only repeated images fields.',422)
    return json_response(enrollment.replace_samples(request.user,student_id,request.FILES.getlist('images')),201)


@api_view('GET','POST')
def scans(request, session_id):
    require_session(request.user,session_id)
    from . import services
    if request.GET:
        raise AccountError('VALIDATION_ERROR','No filters are accepted.',422)
    if request.method == 'GET':
        return json_response(services.queue(request.user,session_id))
    if set(request.POST) or set(request.FILES) != {'image'} or len(request.FILES.getlist('image')) != 1:
        raise AccountError('VALIDATION_ERROR','Submit one image and no extra fields.',422)
    body,status = services.analyze(request.user,session_id,request.FILES['image'],request.headers.get('Idempotency-Key'))
    return json_response(body,status)


@api_view('POST')
def confirm(request, scan_id):
    from . import services
    services.require_scan(request.user,scan_id)
    body,status = services.resolve(request.user,scan_id,read_json(request),request.headers.get('Idempotency-Key'),confirm=True)
    return json_response(body,status)


@api_view('POST')
def reject(request, scan_id):
    from . import services
    services.require_scan(request.user,scan_id)
    body,status = services.resolve(request.user,scan_id,read_json(request),request.headers.get('Idempotency-Key'),confirm=False)
    return json_response(body,status)
