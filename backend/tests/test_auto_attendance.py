"""Workflow tests use controlled inference; they do not measure recognition accuracy."""
from datetime import datetime, time
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, override_settings
from django.utils import timezone

from school_app.vision.models import FaceSample, VisionScan
from tests.test_schedule_api import WorkflowCase
from tests.test_vision_engine import upload, frame, BOX


class AutoAttendanceTests(WorkflowCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        now = timezone.make_aware(datetime.combine(self.day, time(7, 4)))
        self.clock_patch = patch('django.utils.timezone.now', return_value=now)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        self.open()
        self.url = f'/api/v1/sessions/{self.session.pk}/auto-attendance-scans'
        self.extract = patch('school_app.vision.engine.extract_face', return_value=(frame()[:112, :112], BOX))
        self.extract.start()
        self.addCleanup(self.extract.stop)
        self.match = patch('school_app.vision.engine.match_face', return_value={
            'student_id': str(self.student.pk), 'cosine_score': .8, 'distance': .2, 'reason': None})
        self.mock_match = self.match.start()
        self.addCleanup(self.match.stop)
        for i in range(3):
            FaceSample.objects.create(student=self.student, image=b'private', embedding=b'x'*512,
                model_key='sface-2021dec-fp32', digest=str(i), created_by=self.teacher)
        # Use the current pinned model key rather than a test-only engine variant.
        from school_app.vision.engine import MODEL_KEY
        FaceSample.objects.update(model_key=MODEL_KEY)

    def scan(self, key='auto', mode='AUTO_ATTENDANCE', **extra):
        return self.client.post(self.url, {'images': [upload(frame(1)), upload(frame(2))],
            'scan_mode': mode, 'expected_session_version': '1', **extra}, HTTP_IDEMPOTENCY_KEY=key)

    def test_records_without_confirmation_and_retry_does_not_repeat_inference(self):
        result = self.scan()
        self.assertEqual(result.status_code, 201, result.content)
        self.assertEqual(result.json()['outcome'], 'RECORDED')
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'PRESENT')
        self.assertEqual(self.attendance.recognition_mode, 'AUTO')
        self.assertIsNone(self.attendance.verified_by_id)
        self.assertIsNone(self.attendance.verified_at)
        self.assertEqual(self.attendance.recorded_by_id, self.teacher.pk)
        self.assertEqual(self.attendance.uniform_status, 'NOT_CHECKED')
        calls = self.mock_match.call_count
        self.assertEqual(self.scan().json(), result.json())
        self.assertEqual(self.mock_match.call_count, calls)
        arrived = self.attendance.arrived_at
        self.assertEqual(self.scan('another').json()['outcome'], 'ALREADY_RECORDED')
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.arrived_at, arrived)
        self.assertEqual(VisionScan.objects.filter(status='AUTO_RECORDED').count(), 1)

    def test_unknown_disagreement_and_duplicate_frames_do_not_record(self):
        good = self.mock_match.return_value
        self.mock_match.side_effect = [good, {**good, 'student_id': str(self.second.pk)}]
        self.assertEqual(self.scan('disagree').json()['outcome'], 'AMBIGUOUS')
        self.mock_match.side_effect = None
        self.mock_match.return_value = {**good, 'student_id': None, 'reason': 'UNKNOWN_FACE'}
        self.assertEqual(self.scan('unknown').json()['outcome'], 'UNKNOWN')
        same = self.client.post(self.url, {'images':[upload(), upload()], 'scan_mode':'AUTO_ATTENDANCE',
            'expected_session_version':'1'}, HTTP_IDEMPOTENCY_KEY='same')
        self.assertEqual(same.status_code, 422)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'UNMARKED')

    def test_blur_and_lost_face_after_success_never_erase_committed_attendance(self):
        from school_app.accounts.services import AccountError
        self.assertEqual(self.scan('first').json()['outcome'], 'RECORDED')
        self.attendance.refresh_from_db()
        saved = (self.attendance.status, self.attendance.arrived_at, self.attendance.version)
        for reason in ('BLURRY_FACE', 'NO_FACE', 'MULTIPLE_FACES', 'FACE_TOO_SMALL'):
            with self.subTest(reason=reason), patch('school_app.vision.engine.extract_face',
                    side_effect=AccountError(reason, 'Uncertain frame', 422)):
                response = self.scan(reason)
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()['reason'], reason)
                self.attendance.refresh_from_db()
                self.assertEqual((self.attendance.status, self.attendance.arrived_at,
                                  self.attendance.version), saved)
        self.assertEqual(VisionScan.objects.filter(status='AUTO_RECORDED').count(), 1)

    def test_server_rechecks_transfer_and_enrollment_after_inference(self):
        good = self.mock_match.return_value
        def transfer(*args, **kwargs):
            self.student.classroom = self.other_class
            self.student.save()
            return good
        self.mock_match.side_effect = transfer
        self.assertEqual(self.scan('transfer').status_code, 409)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'UNMARKED')

    def test_scope_csrf_strict_identity_and_versions(self):
        self.assertEqual(self.scan(student_id=str(self.student.pk)).status_code, 422)
        self.assertEqual(self.scan(expected_session_version='999').status_code, 409)
        for user in (self.other, self.student_user):
            self.client.force_login(user)
            self.assertIn(self.scan().status_code, (403,404))
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.teacher)
        self.assertEqual(secure.post(self.url, {}).status_code, 403)

    def test_uniform_only_does_not_mark_and_manual_absence_is_preserved(self):
        self.assertEqual(self.scan(mode='UNIFORM_ONLY').json()['outcome'], 'NOT_PRESENT')
        self.request('patch', f'/attendance/{self.attendance.pk}',
            {'expected_version':0, 'status':'ABSENT'}, 'manual-absence')
        self.assertEqual(self.scan('after-manual').json()['outcome'], 'ALREADY_RECORDED')
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'ABSENT')

    @override_settings(VISION_ANALYSES_PER_MINUTE=1)
    def test_limit_and_key_payload_conflict(self):
        self.assertEqual(self.scan().status_code, 201)
        self.assertEqual(self.scan(mode='UNIFORM_ONLY').status_code, 409)
        response = self.scan('limited')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_report_includes_auto_source_without_fake_verification(self):
        self.scan()
        response = self.client.get('/api/v1/reports/attendance',
            {'date_from':str(self.day),'date_to':str(self.day)})
        self.assertEqual(response.status_code, 200, response.content)
        row = next(row for row in response.json()['items'] if row['student_id']==str(self.student.pk))
        self.assertIsNotNone(row['scanned_at'])
        self.assertEqual(row['recognition_mode'], 'AUTO')
        self.assertIsNone(row['verified_at'])

    def test_no_write_transaction_during_inference_and_changed_enrollment_rejected(self):
        from django.db import connection
        good=self.mock_match.return_value
        savepoints=list(connection.savepoint_ids)
        def infer(*args,**kwargs):
            self.assertEqual(connection.savepoint_ids,savepoints)
            FaceSample.objects.filter(student=self.student).delete()
            return good
        self.mock_match.side_effect=infer
        self.assertEqual(self.scan().status_code,409)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status,'UNMARKED')

    def test_unknown_replay_has_strict_key_and_no_repeated_inference(self):
        self.mock_match.return_value={'student_id':None,'cosine_score':.1,'distance':.9,'reason':'UNKNOWN_FACE'}
        response=self.scan()
        self.assertEqual(response.json()['outcome'],'UNKNOWN')
        calls=self.mock_match.call_count
        self.assertEqual(self.scan().json(),response.json())
        self.assertEqual(self.mock_match.call_count,calls)
        self.assertEqual(self.scan(mode='UNIFORM_ONLY').status_code,409)

    def test_uniform_review_needs_teacher_reason_and_correction_survives_auto(self):
        model_result={'observed_uniform':'SPORTS','uniform_status':'REVIEW_REQUIRED',
            'confidence':.99,'reason':'WRONG_UNIFORM','profile_version':1}
        with patch('school_app.vision.uniform_model.evaluate_pair',return_value=model_result):
            response=self.scan()
            self.assertEqual(response.status_code,201,response.content)
            self.assertEqual(response.json()['attendance']['uniform_status'],'REVIEW_REQUIRED')
            report=self.client.get('/api/v1/reports/summary',{'date_from':str(self.day),'date_to':str(self.day)})
            self.assertEqual(report.status_code,200,report.content)
            self.assertEqual(report.json()['review_required'],1)
            path=f'/attendance/{self.attendance.pk}/uniform'
            payload={'expected_version':1,'observed_uniform':'SPORTS','uniform_status':'NON_COMPLIANT'}
            self.assertEqual(self.request('patch',path,payload,'no-reason').status_code,422)
            corrected=self.request('patch',path,{**payload,'observed_uniform':'SHIRT','uniform_status':'COMPLIANT'},'correction')
            self.assertEqual(corrected.status_code,200,corrected.content)
            self.scan('again-uniform',mode='UNIFORM_ONLY')
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.uniform_status,'COMPLIANT')
        self.assertEqual(self.attendance.uniform_source,'MANUAL')

    def test_automatic_face_threshold_does_not_reuse_confirm_threshold(self):
        self.mock_match.return_value={**self.mock_match.return_value,'cosine_score':.5}
        self.assertEqual(self.scan().json()['outcome'],'UNKNOWN')
        self.assertEqual(self.mock_match.call_args.kwargs['min_cosine'],.60)
        self.assertEqual(self.mock_match.call_args.kwargs['min_margin'],.15)

    def test_operator_deactivation_during_inference_prevents_recording(self):
        from django.contrib.auth import get_user_model
        good=self.mock_match.return_value
        def revoke(*args,**kwargs):
            get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=False)
            return good
        self.mock_match.side_effect=revoke
        self.assertEqual(self.scan().status_code,401)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status,'UNMARKED')
