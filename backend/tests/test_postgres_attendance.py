"""Run against an isolated PostgreSQL test database for real lock coverage."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, close_old_connections
from django.test import Client, TransactionTestCase
from tests.test_schedule_api import WorkflowCase
from tests.test_vision_engine import upload, frame, BOX


@skipUnless(connection.vendor == 'postgresql', 'Real PostgreSQL row locks required')
class PostgreSQLAttendanceLockTests(TransactionTestCase):
    request = WorkflowCase.request
    open = WorkflowCase.open

    def setUp(self):
        WorkflowCase.setUp(self)
        self.rule.start_time = '00:00:00'
        self.rule.close_time = '23:59:59'
        self.rule.save()
        self.open()
        from school_app.vision.models import FaceSample
        from school_app.vision.engine import MODEL_KEY
        for i in range(3):
            FaceSample.objects.create(student=self.student,image=b'private',embedding=b'x'*512,
                model_key=MODEL_KEY,digest=str(i),created_by=self.teacher)

    def test_enrollment_revocation_waits_for_validated_scan_commit(self):
        from school_app.vision import auto_attendance, enrollment
        from django.contrib.auth import get_user_model
        checked, deleting, deleted, release = (Event() for _ in range(4))
        revision = auto_attendance._revision
        count = 0

        def hold_after_revision(session):
            nonlocal count
            result = revision(session)
            count += 1
            if count == 2:
                checked.set()
                if not release.wait(15):
                    raise AssertionError('Commit was not released')
            return result

        def scan():
            close_old_connections()
            try:
                client = Client()
                client.force_login(get_user_model().objects.get(pk=self.teacher.pk))
                return client.post(f'/api/v1/sessions/{self.session.pk}/auto-attendance-scans',
                    {'images':[upload(frame(1)),upload(frame(2))],
                     'scan_mode':'AUTO_ATTENDANCE','expected_session_version':'1'},
                    HTTP_IDEMPOTENCY_KEY='real-lock-check')
            finally:
                close_old_connections()

        def revoke():
            close_old_connections()
            try:
                actor=get_user_model().objects.get(pk=self.teacher.pk)
                deleting.set()
                enrollment.delete_samples(actor,self.student.pk)
                deleted.set()
            finally:
                close_old_connections()

        with patch.object(auto_attendance, '_revision', side_effect=hold_after_revision), \
                patch('school_app.vision.engine.extract_face', return_value=(frame()[:112,:112],BOX)), \
                patch('school_app.vision.engine.match_face', return_value={
                    'student_id':str(self.student.pk),'cosine_score':.8,'distance':.2,'reason':None}), \
                ThreadPoolExecutor(max_workers=2) as pool:
            scan_future=pool.submit(scan)
            try:
                self.assertTrue(checked.wait(15),'Scan did not reach commit revision check')
                revoke_future=pool.submit(revoke)
                self.assertTrue(deleting.wait(15))
                self.assertFalse(deleted.wait(.5),'Revocation crossed the validated commit boundary')
            finally:
                release.set()
            result=scan_future.result(timeout=30)
            revoke_future.result(timeout=30)
        self.assertEqual(result.status_code,201,result.content)
        self.assertTrue(deleted.is_set())
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status,'PRESENT')
        self.assertFalse(self.student.face_samples.exists())
