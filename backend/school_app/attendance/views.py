from school_app.accounts.permissions import require_authenticated
from school_app.core.api import api_view, read_json, json_response
from . import services

@api_view('PATCH')
def attendance(request, attendance_id):
    data,status=services.update_manual(require_authenticated(request),attendance_id,read_json(request),request.headers.get('Idempotency-Key'))
    return json_response(data,status)

@api_view('PATCH')
def uniform(request, attendance_id):
    data,status=services.update_uniform(require_authenticated(request),attendance_id,read_json(request),request.headers.get('Idempotency-Key'))
    return json_response(data,status)
