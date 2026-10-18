from django.urls import path
from . import views
from functools import wraps
from django.conf import settings
from school_app.accounts.permissions import require_authenticated
from school_app.accounts.services import AccountError
from school_app.core.api import api_view


def legacy(view):
    @api_view('GET','POST')
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        require_authenticated(request)
        if not settings.QR_ENABLED:
            raise AccountError('QR_RETIRED','QR was replaced by staff-operated OpenCV scans.',410)
        return view(request,*args,**kwargs)
    return wrapped
urlpatterns=[path('sessions/<uuid:session_id>/qr-challenges',legacy(views.challenge)),path('sessions/<uuid:session_id>/qr-scans',legacy(views.queue)),path('qr-scans',legacy(views.scan)),path('qr-scans/<uuid:scan_id>/confirm',legacy(views.confirm)),path('qr-scans/<uuid:scan_id>/reject',legacy(views.reject)),path('me/today-sessions',legacy(views.today)),path('me/scan-status',legacy(views.own_status))]
