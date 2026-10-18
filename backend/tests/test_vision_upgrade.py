"""API migration contracts; synthetic vision inputs never require model assets."""
from datetime import timedelta
from unittest.mock import patch

import cv2
import numpy as np
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from school_app.accounts.services import AccountError
from school_app.vision.models import FaceSample, VisionScan
from school_app.vision.services import serialize_scan
from tests.test_vision_api import VisionApiTests
from tests.test_vision_engine import frame, upload


MODEL_KEY = 'sface-2021dec-fp32'


class VisionUpgradeTests(VisionApiTests):
    def legacy_samples(self, student=None):
        return FaceSample.objects.bulk_create([
            FaceSample(student=student or self.student, image=b'legacy crop',
                       digest=str(index), created_by=self.teacher)
            for index in range(3)
        ])

    def test_legacy_samples_remain_but_require_enrollment_again(self):
        old = self.legacy_samples()
        body = self.client.get(self.samples_url).json()
        self.assertEqual(body['sample_count'], 3)
        self.assertEqual(body.get('usable_sample_count'), 0)
        self.assertIs(body.get('requires_reenrollment'), True)
        self.assertEqual(body.get('model_key'), MODEL_KEY)
        response = self.scan()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['recognition'], 'UNKNOWN')
        self.assertEqual(response.json()['reason'], 'REENROLLMENT_REQUIRED')
        self.assertEqual(FaceSample.objects.filter(pk__in=[s.pk for s in old]).count(), 3)
        self.assertFalse(VisionScan.objects.exists())
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'UNMARKED')

    def test_enrollment_stores_private_color_crops_and_versioned_embeddings(self):
        body = self.enroll().json()
        self.assertEqual(body.get('usable_sample_count'), 3)
        self.assertIs(body.get('requires_reenrollment'), False)
        self.assertEqual(body.get('model_key'), MODEL_KEY)
        for sample in FaceSample.objects.all():
            self.assertEqual(sample.model_key, MODEL_KEY)
            self.assertEqual(len(sample.embedding), 512)
            crop = cv2.imdecode(np.frombuffer(sample.image, np.uint8), cv2.IMREAD_UNCHANGED)
            self.assertEqual(crop.shape, (112, 112, 3))
            self.assertAlmostEqual(float(np.linalg.norm(np.frombuffer(sample.embedding, '<f4'))), 1, places=5)
        self.assertNotIn('embedding', body)
        self.assertNotIn('image', body)

    def test_mixed_legacy_roster_matches_only_versioned_student(self):
        self.legacy_samples(self.second)
        self.enroll()
        response = self.scan()
        self.assertEqual(response.status_code, 201, response.content)
        scan = response.json()['scan']
        self.assertEqual(scan['student_id'], str(self.student.pk))
        self.assertEqual(scan.get('model_key'), MODEL_KEY)
        self.assertEqual(scan.get('metric'), 'cosine')
        self.assertAlmostEqual(scan.get('cosine_score', -100), 1, places=5)
        self.assertAlmostEqual(scan['distance'], 1 - scan['cosine_score'], places=5)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'UNMARKED')

    def test_legacy_scan_serialization_preserves_distance_metric(self):
        scan = self.candidate()
        stored = VisionScan.objects.get(pk=scan['id'])
        stored.model_key = 'lbph'
        stored.cosine_score = None
        stored.distance = 47.5
        stored.save()
        body = serialize_scan(stored)
        self.assertEqual(body.get('metric'), 'lbph_distance')
        self.assertIsNone(body.get('cosine_score'))
        self.assertEqual(body['distance'], 47.5)

    def test_unrecognized_embedding_cannot_mark_attendance(self):
        self.enroll()
        response = self.scan(image=frame(999))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['recognition'], 'UNKNOWN')
        self.assertFalse(VisionScan.objects.exists())
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'UNMARKED')

    def test_other_model_and_missing_embedding_are_not_usable(self):
        self.enroll()
        samples = list(FaceSample.objects.all())
        FaceSample.objects.filter(pk=samples[0].pk).update(model_key='future-model')
        FaceSample.objects.exclude(pk=samples[0].pk).update(embedding=None)
        body = self.client.get(self.samples_url).json()
        self.assertEqual(body['sample_count'], 3)
        self.assertEqual(body['usable_sample_count'], 0)
        self.assertIs(body['requires_reenrollment'], True)
        response = self.scan()
        self.assertEqual(response.json()['reason'], 'REENROLLMENT_REQUIRED')
        self.assertFalse(VisionScan.objects.exists())

    def test_embedding_failure_preserves_enrollment_and_pending_scan(self):
        candidate = self.candidate()
        old_ids = set(FaceSample.objects.values_list('pk', flat=True))
        with patch('school_app.vision.engine.embed_face', side_effect=AccountError(
                'VISION_UNAVAILABLE', 'Local recognition unavailable.', 503)):
            response = self.client.post(self.samples_url, {
                'images':[upload(frame(seed)) for seed in (4, 5, 6)]})
        self.assertEqual(response.status_code, 503, response.content)
        self.assertEqual(set(FaceSample.objects.values_list('pk', flat=True)), old_ids)
        self.assertEqual(VisionScan.objects.get(pk=candidate['id']).status, 'PENDING')


class VisionMigrationTests(TransactionTestCase):
    def test_upgrade_retains_legacy_samples_scans_and_confirmed_attendance(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        executor.migrate([('vision', '0001_initial')])
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        old_apps = executor.loader.project_state([('vision', '0001_initial')]).apps
        User = old_apps.get_model('accounts', 'User')
        Grade = old_apps.get_model('academics', 'Grade')
        Classroom = old_apps.get_model('academics', 'Classroom')
        Student = old_apps.get_model('students', 'Student')
        Session = old_apps.get_model('schedules', 'Session')
        Roster = old_apps.get_model('schedules', 'SessionRoster')
        # Attendance may not be in vision's dependency graph, so use its latest model.
        from school_app.attendance.models import Attendance
        user = User.objects.create(username='history', role='HOMEROOM_TEACHER')
        grade = Grade.objects.create(code='history', name='History')
        classroom = Classroom.objects.create(code='history', name='History', grade_id=grade.pk,
                                             teacher_id=user.pk)
        student = Student.objects.create(student_code='history', full_name='History', classroom_id=classroom.pk)
        session = Session.objects.create(classroom_id=classroom.pk, school_date=timezone.localdate(), slot='MORNING')
        roster = Roster.objects.create(session_id=session.pk, student_id=student.pk,
            student_code_snapshot='history', full_name_snapshot='History', class_code_snapshot='history',
            class_name_snapshot='History', grade_code_snapshot='history', grade_name_snapshot='History')
        now = timezone.now()
        attendance = Attendance.objects.create(roster_id=roster.pk, status='PRESENT', source='VISION',
            arrived_at=now, uniform_status='NOT_CHECKED', verified_by_id=user.pk, verified_at=now, version=2)
        sample = old_apps.get_model('vision', 'FaceSample').objects.create(student_id=student.pk,
            image=b'private old grayscale png', digest='history', created_by_id=user.pk)
        scan = old_apps.get_model('vision', 'VisionScan').objects.create(roster_id=roster.pk,
            created_by_id=user.pk, scanned_at=now, expires_at=now+timedelta(seconds=120),
            sample_revision='history', attendance_version=0, distance=47.5, observed_uniform='UNKNOWN',
            color_coverage=0, status='CONFIRMED', version=1, resolved_at=now, resolved_by_id=user.pk)
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        retained_sample = FaceSample.objects.get(pk=sample.pk)
        self.assertEqual(bytes(retained_sample.image), b'private old grayscale png')
        self.assertEqual(retained_sample.model_key, '')
        self.assertIsNone(retained_sample.embedding)
        retained_scan = VisionScan.objects.get(pk=scan.pk)
        self.assertEqual((retained_scan.status, retained_scan.version, retained_scan.distance), ('CONFIRMED', 1, 47.5))
        self.assertEqual(retained_scan.model_key, 'lbph')
        self.assertIsNone(retained_scan.cosine_score)
        attendance.refresh_from_db()
        self.assertEqual((attendance.status, attendance.source, attendance.version), ('PRESENT', 'VISION', 2))
        self.assertEqual(attendance.arrived_at, now)
