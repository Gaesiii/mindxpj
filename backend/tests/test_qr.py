from django.test import override_settings
import base64
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from school_app.qr.models import QrScan,QrChallenge
from school_app.core.models import ChangeLog, IdempotencyRequest
from tests.test_schedule_api import WorkflowCase

@override_settings(QR_ENABLED=True)
class QrApiTests(WorkflowCase):
    def setUp(self):
        super().setUp(); cache.clear(); self.open()

    def issue(self):
        self.client.force_login(self.teacher)
        result=self.request('post',f'/sessions/{self.session.pk}/qr-challenges',{})
        self.assertEqual(result.status_code,201,result.content)
        data=result.json()
        self.assertTrue(base64.b64decode(data['qr_image_base64']).startswith(b'\x89PNG'))
        self.assertEqual(data['refresh_after_seconds'],30)
        self.assertFalse(QrChallenge.objects.filter(token_hash=data['token']).exists())
        return data['token']

    def scan(self,token,user=None,key='scan'):
        self.client.force_login(user or self.student_user)
        response=self.request('post','/qr-scans',{'token':token},key)
        self.assertEqual(response.status_code,201,response.content)
        return response.json()

    def confirm(self,scan,**extra):
        self.client.force_login(self.teacher)
        return self.request('post',f"/qr-scans/{scan['id']}/confirm",{'expected_scan_version':0,'expected_attendance_version':0,'identity_confirmed':True,**extra},'confirm')

    def test_two_students_same_token_first_scan_preserved_and_confirmation(self):
        token=self.issue(); first=self.scan(token)
        repeated=self.request('post','/qr-scans',{'token':token},'scan-new-key')
        self.assertEqual(repeated.status_code,200,repeated.content)
        self.assertEqual(repeated.json()['scanned_at'],first['scanned_at'])
        second=self.scan(token,self.second_user,'second-scan')
        self.assertNotEqual(second['id'],first['id'])
        self.attendance.refresh_from_db();self.assertEqual(self.attendance.status,'UNMARKED')
        confirmed=self.confirm(first)
        self.assertEqual(confirmed.status_code,200,confirmed.content)
        self.assertEqual(confirmed.json()['attendance']['arrived_at'],first['scanned_at'])
        self.assertEqual(confirmed.json()['attendance']['uniform_status'],'NOT_CHECKED')
        self.assertEqual(confirmed.json()['scan']['status'],'CONFIRMED')

    def test_invalid_identity_expired_token_and_wrong_class(self):
        token=self.issue();self.client.force_login(self.student_user)
        for body in [{'token':token,'student_id':str(self.second.pk)},{'token':5}]:
            self.assertEqual(self.request('post','/qr-scans',body,'bad').status_code,422)
        challenge=QrChallenge.objects.get();challenge.expires_at=timezone.now()-timedelta(seconds=1);challenge.save()
        self.assertEqual(self.request('post','/qr-scans',{'token':token},'expired').json()['code'],'QR_EXPIRED')
        token=self.issue(); self.student.classroom=self.other_class;self.student.save();self.client.force_login(self.student_user)
        self.assertEqual(self.request('post','/qr-scans',{'token':token},'wrong-class').status_code,422)
        self.client.force_login(self.teacher)
        self.assertEqual(self.request('post','/qr-scans',{'token':token},'teacher').status_code,403)

    def test_expired_pending_cannot_confirm_and_status_expires(self):
        token=self.issue();scan=self.scan(token)
        row=QrScan.objects.get(pk=scan['id']);row.expires_at=timezone.now()-timedelta(seconds=1);row.save()
        self.client.force_login(self.teacher)
        result=self.client.get(f'/api/v1/sessions/{self.session.pk}/qr-scans')
        self.assertEqual(result.status_code,200,result.content)
        self.assertEqual(result.json()['items'],[])
        row.refresh_from_db();self.assertEqual(row.status,'EXPIRED')
        response=self.confirm(scan)
        self.assertEqual(response.status_code,409,response.content)
        self.attendance.refresh_from_db();self.assertEqual(self.attendance.status,'UNMARKED')

    def test_confirm_uniform_rollback_identity_true_and_stale_versions(self):
        scan=self.scan(self.issue());count=ChangeLog.objects.count()
        response=self.confirm(scan,uniform={'observed_uniform':'SPORTS','uniform_status':'COMPLIANT'})
        self.assertEqual(response.status_code,422,response.content)
        self.attendance.refresh_from_db();self.assertEqual(self.attendance.version,0)
        self.assertEqual(QrScan.objects.get(pk=scan['id']).status,'PENDING')
        self.assertEqual(ChangeLog.objects.count(),count)
        self.assertFalse(IdempotencyRequest.objects.filter(key='confirm').exists())
        self.assertEqual(self.confirm(scan,identity_confirmed=1).status_code,422)
        self.assertEqual(self.confirm(scan,expected_scan_version=2).status_code,409)
        self.assertEqual(self.confirm(scan,uniform={'observed_uniform':'SHIRT','uniform_status':'COMPLIANT'}).status_code,200)

    def test_manual_supersedes_pending_and_scan_cannot_overwrite_manual(self):
        token=self.issue();scan=self.scan(token)
        self.client.force_login(self.teacher)
        body={'expected_version':0,'status':'PRESENT','reason':'Manual entry','arrived_at':(timezone.now()-timedelta(seconds=1)).isoformat()}
        response=self.request('patch',f'/attendance/{self.attendance.pk}',body,'manual')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(QrScan.objects.get(pk=scan['id']).status,'SUPERSEDED')
        self.assertEqual(self.confirm(scan).status_code,409)
        self.client.force_login(self.student_user)
        response=self.request('post','/qr-scans',{'token':token},'after-manual')
        self.assertEqual(response.status_code,200,response.content)
        self.attendance.refresh_from_db();self.assertEqual(self.attendance.source,'MANUAL')
        self.assertEqual(QrScan.objects.count(),1)

    def test_reject_retry_and_own_status_and_close_blocks_scan(self):
        token=self.issue();scan=self.scan(token)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/api/v1/sessions/{self.session.pk}/qr-scans').status_code,404)
        self.client.force_login(self.teacher)
        path=f"/qr-scans/{scan['id']}/reject"
        body={'expected_scan_version':0,'reason':'Identity does not match'}
        response=self.request('post',path,body,'reject')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(self.request('post',path,body,'reject').json(),response.json())
        self.client.force_login(self.student_user)
        own=self.client.get('/api/v1/me/scan-status',{'session_id':str(self.session.pk)})
        self.assertEqual(own.status_code,200,own.content)
        self.assertEqual(own.json()['scan']['status'],'REJECTED')
        self.assertEqual(self.client.get('/api/v1/me/today-sessions').status_code,200)
        self.client.force_login(self.teacher)
        self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.client.force_login(self.student_user)
        self.assertEqual(self.request('post','/qr-scans',{'token':token},'closed').status_code,409)


    def test_invalid_tokens_rate_limited_and_successful_replay_exempt(self):
        token=self.issue(); scan=self.scan(token)
        for index in range(29):
            response=self.request('post','/qr-scans',{'token':'invalid-token'},'invalid-'+str(index))
            self.assertEqual(response.status_code,422,response.content)
        limited=self.request('post','/qr-scans',{'token':'invalid-token'},'over-limit')
        self.assertEqual(limited.status_code,429,limited.content)
        self.assertIn('Retry-After',limited)
        replay=self.request('post','/qr-scans',{'token':token},'scan')
        self.assertEqual(replay.status_code,201,replay.content)
        self.assertEqual(replay.json(),scan)

    def test_expiry_persists_when_confirm_is_rejected(self):
        scan=self.scan(self.issue())
        row=QrScan.objects.get(pk=scan['id']);row.expires_at=timezone.now()-timedelta(seconds=1);row.save()
        response=self.confirm(scan)
        self.assertEqual(response.status_code,409,response.content)
        row.refresh_from_db();self.assertEqual(row.status,'EXPIRED')
        self.assertFalse(IdempotencyRequest.objects.filter(key='confirm').exists())

    def test_retry_after_close_and_student_transfer_rechecks_scope(self):
        token=self.issue();scan=self.scan(token)
        first=self.confirm(scan)
        self.assertEqual(first.status_code,200,first.content)
        self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.assertEqual(self.confirm(scan).json(),first.json())
        self.client.force_login(self.student_user)
        self.assertEqual(self.request('post','/qr-scans',{'token':token},'scan').status_code,201)
        self.student.classroom=self.other_class;self.student.save()
        self.assertEqual(self.request('post','/qr-scans',{'token':token},'scan').status_code,422)
        self.assertEqual(self.client.get('/api/v1/me/scan-status',{'session_id':str(self.session.pk)}).status_code,404)


    def test_queue_contains_immutable_class_and_grade_identity(self):
        scanned=self.scan(self.issue())
        self.client.force_login(self.teacher)
        self.classroom.name='Renamed';self.classroom.save()
        response=self.client.get(f'/api/v1/sessions/{self.session.pk}/qr-scans')
        self.assertEqual(response.status_code,200,response.content)
        row=response.json()['items'][0]
        self.assertEqual(row.get('class_code_snapshot'),'10A')
        self.assertEqual(row.get('class_name_snapshot'),'Class A')
        self.assertEqual(row.get('grade_code_snapshot'),'G10')
        self.assertEqual(row.get('grade_name_snapshot'),'Grade 10')
        self.assertEqual(row['scanned_at'],scanned['scanned_at'])


    def test_historical_queue_does_not_read_outside_current_photo_scope(self):
        self.scan(self.issue())
        self.student.classroom=self.other_class;self.student.photo_path='private/transferred.jpg';self.student.save()
        self.client.force_login(self.teacher)
        response=self.client.get(f'/api/v1/sessions/{self.session.pk}/qr-scans')
        self.assertEqual(response.status_code,200,response.content)
        self.assertIsNone(response.json()['items'][0]['photo_url'])
        self.assertEqual(self.client.get(f'/api/v1/students/{self.student.pk}/photo').status_code,404)
        self.client.force_login(self.supervisor)
        response=self.client.get(f'/api/v1/sessions/{self.session.pk}/qr-scans')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['items'][0]['photo_url'],f'/api/v1/students/{self.student.pk}/photo')
        self.classroom.teacher=self.other;self.classroom.save()
        self.client.force_login(self.other)
        response=self.client.get(f'/api/v1/sessions/{self.session.pk}/qr-scans')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['items'][0]['photo_url'],f'/api/v1/students/{self.student.pk}/photo')
