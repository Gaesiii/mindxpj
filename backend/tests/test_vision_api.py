from datetime import timedelta
from datetime import datetime, time
from unittest.mock import patch
import json

from django.core.cache import cache
from django.test import Client, override_settings
from django.utils import timezone

from school_app.core.models import ChangeLog
from school_app.vision.models import FaceSample, VisionScan
from tests.test_schedule_api import WorkflowCase
from tests.test_vision_engine import BOX, frame, upload


class VisionApiTests(WorkflowCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        now=timezone.make_aware(datetime.combine(self.day,time(7,4)))
        clock_patch=patch('django.utils.timezone.now',return_value=now)
        self.clock=clock_patch.start();self.addCleanup(clock_patch.stop)
        self.open()
        self.detector = patch('school_app.vision.engine.detect_faces', return_value=[BOX])
        self.detector.start()
        self.addCleanup(self.detector.stop)
        self.samples_url = f'/api/v1/students/{self.student.pk}/face-samples'
        self.scans_url = f'/api/v1/sessions/{self.session.pk}/vision-scans'

    def enroll(self, student=None):
        url = f'/api/v1/students/{(student or self.student).pk}/face-samples'
        result = self.client.post(url, {'images':[upload(frame(seed)) for seed in (1,2,3)]})
        self.assertEqual(result.status_code, 201, result.content)
        return result

    def scan(self, key='scan', image=None):
        return self.client.post(self.scans_url, {'image':upload(image)}, HTTP_IDEMPOTENCY_KEY=key)

    def candidate(self):
        self.enroll()
        result = self.scan()
        self.assertEqual(result.status_code, 201, result.content)
        return result.json()['scan']

    def confirm(self, scan, key='confirm', **extra):
        return self.request('post', f"/vision-scans/{scan['id']}/confirm", {
            'expected_scan_version':scan['version'], 'expected_attendance_version':0,
            'identity_confirmed':True, **extra}, key)

    def test_enrollment_metadata_replaces_atomically_and_deletes_private_crops(self):
        result = self.enroll()
        self.assertEqual(result.json()['sample_count'], 3)
        self.assertNotIn('image', result.json())
        self.assertEqual(FaceSample.objects.count(), 3)
        ids = list(FaceSample.objects.values_list('pk',flat=True))
        self.assertEqual(self.client.post(self.samples_url, {'images':[upload()]}).status_code,422)
        self.assertEqual(list(FaceSample.objects.values_list('pk',flat=True)), ids)
        self.enroll()
        self.assertEqual(FaceSample.objects.count(),3)
        self.assertFalse(FaceSample.objects.filter(pk__in=ids).exists())
        self.assertEqual(self.client.get(self.samples_url).json()['sample_count'],3)
        self.assertEqual(self.client.delete(self.samples_url).status_code,200)
        self.assertEqual(FaceSample.objects.count(),0)

    def test_pending_confirm_retry_and_report_source(self):
        scan = self.candidate()
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status,'UNMARKED')
        response = self.confirm(scan, uniform={'observed_uniform':'SHIRT','uniform_status':'COMPLIANT'})
        self.assertEqual(response.status_code,200,response.content)
        attendance = response.json()['attendance']
        self.assertEqual(attendance['source'],'VISION')
        self.assertEqual(attendance['arrived_at'],scan['scanned_at'])
        self.assertEqual(attendance['uniform_status'],'COMPLIANT')
        logs=ChangeLog.objects.count()
        again=self.confirm(scan, uniform={'observed_uniform':'SHIRT','uniform_status':'COMPLIANT'})
        self.assertEqual(again.json(),response.json())
        self.assertEqual(ChangeLog.objects.count(),logs)
        report=self.client.get('/api/v1/reports/attendance', {'date_from':str(self.day),'date_to':str(self.day)})
        self.assertEqual(report.status_code,200,report.content)
        row=next(row for row in report.json()['items'] if row['student_id']==str(self.student.pk))
        self.assertEqual(row['source'],'VISION')
        self.assertIsNotNone(row['scanned_at'])

    def test_unknown_and_ambiguous_never_create_proposals(self):
        response=self.scan()
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['recognition'],'UNKNOWN')
        self.assertEqual(VisionScan.objects.count(),0)
        self.enroll(); self.enroll(self.second)
        response=self.scan('ambiguous')
        self.assertEqual(response.json()['reason'],'AMBIGUOUS_FACE')
        self.assertEqual(VisionScan.objects.count(),0)

    def test_scope_and_student_role_every_endpoint(self):
        scan=self.candidate()
        for user in (self.other,self.student_user):
            self.client.force_login(user)
            for response in (self.client.get(self.samples_url),self.client.delete(self.samples_url),
                             self.client.post(self.samples_url,{'images':[upload()]}),
                             self.scan('forbidden'),self.client.get(self.scans_url),self.confirm(scan)):
                self.assertIn(response.status_code,(403,404),response.content)
        self.client.logout()
        self.assertEqual(self.client.get(self.scans_url).status_code,401)

    def test_confirm_requires_identity_versions_and_atomic_uniform_validation(self):
        scan=self.candidate(); logs=ChangeLog.objects.count()
        for extra,status in [({'identity_confirmed':1},422),({'expected_scan_version':4},409),
                             ({'expected_attendance_version':4},409),
                             ({'student_id':str(self.second.pk)},422),
                             ({'uniform':{'observed_uniform':'SPORTS','uniform_status':'COMPLIANT'}},422)]:
            self.assertEqual(self.confirm(scan,**extra).status_code,status)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status,'UNMARKED')
        self.assertEqual(VisionScan.objects.get().status,'PENDING')
        self.assertEqual(ChangeLog.objects.count(),logs)

    def test_expiry_and_close_disallow_confirmation(self):
        scan=self.candidate()
        VisionScan.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.confirm(scan).status_code,409)
        self.assertEqual(self.client.get(self.scans_url).json()['items'],[])
        result=self.scan('new')
        self.assertEqual(result.status_code,201,result.content)
        self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.assertEqual(self.confirm(result.json()['scan'],'closed').status_code,409)
        self.assertEqual(VisionScan.objects.filter(status='PENDING').count(),0)

    def test_manual_entry_supersedes_scan(self):
        scan=self.candidate()
        result=self.request('patch',f'/attendance/{self.attendance.pk}',{
            'expected_version':0,'status':'PRESENT','arrived_at':(timezone.now()-timedelta(seconds=1)).isoformat(),
            'reason':'Manual fallback'},'manual')
        self.assertEqual(result.status_code,200,result.content)
        self.assertEqual(VisionScan.objects.get().status,'SUPERSEDED')
        self.assertEqual(self.confirm(scan).status_code,409)

    def test_sample_revocation_and_transfer_invalidate_pending(self):
        scan=self.candidate()
        self.client.delete(self.samples_url)
        self.assertEqual(self.confirm(scan).status_code,409)
        scan=self.candidate()
        self.student.classroom=self.other_class;self.student.save()
        self.assertEqual(self.confirm(scan).status_code,409)
        self.assertEqual(self.scan('transfer').json()['recognition'],'UNKNOWN')

    def test_reenrollment_and_reassignment_checked_before_replay(self):
        scan=self.candidate(); self.enroll()
        self.assertEqual(self.confirm(scan).status_code,409)
        self.classroom.teacher=self.other;self.classroom.save()
        self.assertEqual(self.scan().status_code,404)
        self.assertEqual(self.client.get(self.samples_url).status_code,404)

    def test_retry_and_conflicting_image_key(self):
        self.enroll()
        first=self.scan()
        again=self.scan()
        self.assertEqual(first.json(),again.json())
        self.assertEqual(VisionScan.objects.count(),1)
        self.assertEqual(self.scan(image=frame(2)).status_code,409)

    def test_successful_analysis_retry_after_close_replays_without_new_write(self):
        scan=self.candidate()
        self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        result=self.scan()
        self.assertEqual(result.status_code,201,result.content)
        self.assertEqual(result.json()['scan']['id'],scan['id'])
        self.assertEqual(VisionScan.objects.count(),1)
        self.assertEqual(self.scan('new-key').status_code,409)

    def test_duplicate_enrollment_rejected_and_unknown_uniform_needs_inspection(self):
        result=self.client.post(self.samples_url,{'images':[upload(),upload(),upload()]})
        self.assertEqual(result.status_code,422,result.content)
        self.assertEqual(FaceSample.objects.count(),0)
        scan=self.candidate()
        result=self.confirm(scan,uniform={'observed_uniform':'UNKNOWN','uniform_status':'NON_COMPLIANT','reason':'Unknown'})
        self.assertEqual(result.status_code,422,result.content)
        self.attendance.refresh_from_db();self.assertEqual(self.attendance.status,'UNMARKED')

    def test_oversized_roster_rejected_before_processing(self):
        from school_app.schedules.models import SessionRoster
        from school_app.students.models import Student
        for index in range(49):
            student=Student.objects.create(student_code=f'large{index}',full_name='Extra',classroom=self.classroom)
            SessionRoster.objects.create(session=self.session,student=student,student_code_snapshot=student.student_code,
                full_name_snapshot=student.full_name,class_code_snapshot='10A',class_name_snapshot='A',
                grade_code_snapshot='G10',grade_name_snapshot='10')
        self.assertEqual(self.scan().status_code,422)

    def test_frame_schema_reject_and_csrf(self):
        self.enroll()
        self.assertEqual(self.client.post(self.scans_url,{'image':upload(),'student_id':str(self.student.pk)},HTTP_IDEMPOTENCY_KEY='x').status_code,422)
        self.assertEqual(self.client.post(self.scans_url,{'image':[upload(),upload()]},HTTP_IDEMPOTENCY_KEY='x').status_code,422)
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.teacher)
        self.assertEqual(secure.post(self.scans_url,{'image':upload()},HTTP_IDEMPOTENCY_KEY='x').status_code,403)

    def test_reject_requires_reason_and_no_attendance_write(self):
        scan=self.candidate()
        path=f"/vision-scans/{scan['id']}/reject"
        self.assertEqual(self.request('post',path,{'expected_scan_version':0},'reject').status_code,422)
        result=self.request('post',path,{'expected_scan_version':0,'reason':'Wrong candidate'},'reject')
        self.assertEqual(result.status_code,200,result.content)
        self.assertEqual(result.json()['status'],'REJECTED')
        self.attendance.refresh_from_db();self.assertEqual(self.attendance.status,'UNMARKED')

    def test_default_qr_path_is_retired(self):
        self.assertEqual(self.request('post',f'/sessions/{self.session.pk}/qr-challenges',{}).status_code,410)

    def test_scan_rate_limit_and_session_date(self):
        with override_settings(VISION_ANALYSES_PER_MINUTE=1):
            self.assertEqual(self.scan().status_code,200)
            self.assertEqual(self.scan('next').status_code,429)
        self.session.school_date=self.day-timedelta(days=1);self.session.save()
        self.assertEqual(self.scan('yesterday').status_code,409)

    def test_analysis_and_confirmation_require_session_time_window(self):
        self.enroll()
        for when in (self.session.start_at-timedelta(seconds=1), self.session.close_at+timedelta(seconds=1)):
            self.clock.return_value = when
            self.assertEqual(self.scan('outside-'+str(when)).status_code,409)
        self.clock.return_value = self.session.close_at-timedelta(seconds=30)
        result=self.scan('just-in-time')
        self.assertEqual(result.status_code,201,result.content)
        self.clock.return_value = self.session.close_at+timedelta(seconds=1)
        self.assertEqual(self.confirm(result.json()['scan']).status_code,409)
        self.attendance.refresh_from_db();self.assertEqual(self.attendance.status,'UNMARKED')
