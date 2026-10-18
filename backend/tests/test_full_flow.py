from django.test import override_settings
import json
from datetime import timedelta
from django.test import Client
from django.core.cache import cache
from django.utils import timezone
from school_app.attendance.models import Attendance
from school_app.qr.models import QrScan
from school_app.schedules.models import SessionRoster
from tests.test_schedule_api import WorkflowCase

@override_settings(QR_ENABLED=True)
class FullFlowTests(WorkflowCase):
    def test_scan_verify_uniform_close_and_counts(self):
        cache.clear();self.open()
        issued=self.request('post',f'/sessions/{self.session.pk}/qr-challenges',{}).json()
        self.client.force_login(self.student_user)
        scanned=self.request('post','/qr-scans',{'token':issued['token']},'scan').json()
        self.client.force_login(self.teacher)
        result=self.request('post',f"/qr-scans/{scanned['id']}/confirm",{'expected_scan_version':0,'expected_attendance_version':0,'identity_confirmed':True,'uniform':{'observed_uniform':'SPORTS','uniform_status':'NON_COMPLIANT','reason':'Shirt required'}},'confirm')
        self.assertEqual(result.status_code,200,result.content)
        self.assertEqual(result.json()['attendance']['uniform_status'],'NON_COMPLIANT')
        self.client.force_login(self.second_user)
        pending=self.request('post','/qr-scans',{'token':issued['token']},'second-scan').json()
        self.client.force_login(self.teacher)
        roster=self.client.get(f'/api/v1/sessions/{self.session.pk}/roster')
        self.assertEqual(roster.status_code,200,roster.content)
        self.assertEqual(len(roster.json()['items']),2)
        closed=self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.assertEqual(closed.status_code,200,closed.content)
        self.assertEqual(closed.json()['converted_unmarked'],1)
        self.assertEqual(closed.json()['expired_pending'],1)
        self.assertEqual(QrScan.objects.get(pk=pending['id']).status,'EXPIRED')
        self.assertEqual(Attendance.objects.filter(roster__session=self.session,status='PRESENT').count(),1)
        self.assertEqual(Attendance.objects.filter(roster__session=self.session,status='ABSENT').count(),1)
        self.assertEqual(SessionRoster.objects.filter(session=self.session).count(),2)
        self.assertEqual(self.request('post',f'/sessions/{self.session.pk}/qr-challenges',{}).status_code,409)

    def test_write_endpoints_require_csrf_and_do_not_accept_identity(self):
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.teacher)
        csrf.get('/api/v1/auth/me')
        path=f'/api/v1/sessions/{self.session.pk}/open'
        response=csrf.post(path,data=json.dumps({'expected_version':0}),content_type='application/json')
        self.assertEqual(response.status_code,403)
        response=csrf.post(path,data=json.dumps({'expected_version':0,'student_id':str(self.student.pk)}),content_type='application/json',HTTP_X_CSRFTOKEN=csrf.cookies['csrftoken'].value)
        self.assertEqual(response.status_code,422,response.content)
        self.session.refresh_from_db();self.assertEqual(self.session.status,'PLANNED')
        response=csrf.post(path,data=json.dumps({'expected_version':0}),content_type='application/json',HTTP_X_CSRFTOKEN=csrf.cookies['csrftoken'].value)
        self.assertEqual(response.status_code,200,response.content)
