from school_app.accounts.permissions import require_roles
from school_app.core.api import api_view, json_response
from school_app.core.enums import Role
from school_app.reports.forms import read_filters
from school_app.reports.services import report


def read_report(request, export=False):
    user = require_roles(request, Role.HOMEROOM_TEACHER, Role.SUPERVISOR)
    filters = read_filters(request.GET, export=export)
    return report(user, filters, export=export)


@api_view('GET')
def attendance_report(request):
    result = read_report(request)
    return json_response({'items': result['items'], 'metadata': result['metadata']})


@api_view('GET')
def summary_report(request):
    return json_response(read_report(request)['summary'])


@api_view('GET')
def export_report(request):
    result = read_report(request, export=True)
    from school_app.reports.exporters import export_response
    return export_response(result, request.GET['format'])
