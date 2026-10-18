"""A13/B13 independent HTTP integration: real CSRF, role boundaries and retries."""
import json
import uuid
from datetime import date, datetime, time, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from school_app.academics.models import Classroom, Grade
from school_app.students.models import Student
from school_app.schedules.models import ScheduleRule
from school_app.attendance.models import Attendance
from school_app.core.models import IdempotencyRequest
from school_app.qr.models import QrScan


@override_settings(QR_ENABLED=True, DEBUG=False, ALLOWED_HOSTS=["testserver"])
class HttpContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user(username="flowteacher", role="HOMEROOM_TEACHER")
        cls.other = User.objects.create_user(username="otherteacher", role="HOMEROOM_TEACHER")
        cls.supervisor = User.objects.create_user(username="flowsupervisor", role="SUPERVISOR")
        grade = Grade.objects.create(code="10", name="Khối 10")
        cls.classroom = Classroom.objects.create(code="10A", name="10A", grade=grade, teacher=cls.teacher)
        cls.students = [Student.objects.create(student_code=f"HS{i}", full_name=f"Nguyễn An {i}",
                       classroom=cls.classroom) for i in range(2)]
        cls.pupil = User.objects.create_user(username="flowpupil", password="K12Demo!7264",
                                             role="STUDENT", student=cls.students[0])
        ScheduleRule.objects.create(classroom=cls.classroom, weekday=0, slot="MORNING",
            start_time=time(7), close_time=time(8), grace_minutes=5, required_uniform="SHIRT")

    def setUp(self):
        cache.clear()
        self.client.force_login(self.teacher)
        response = self.write(self.client, "post", "/api/v1/sessions", {
            "class_id": str(self.classroom.pk), "school_date": "2026-10-12", "slot": "MORNING"})
        self.assertEqual(response.status_code, 201, response.content)
        self.session_id = response.json()["id"]
        self.session_url = "/api/v1/sessions/" + self.session_id
        response = self.write(self.client, "post", self.session_url + "/open", {"expected_version": 0})
        self.assertEqual(response.status_code, 200, response.content)
        rows = self.client.get(self.session_url + "/roster").json()["items"]
        self.rows = sorted(rows, key=lambda item: item["student_code_snapshot"])

    def write(self, client, method, url, body, key=None, csrf=False):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        if csrf:
            headers["HTTP_X_CSRFTOKEN"] = client.cookies["csrftoken"].value
        return getattr(client, method)(url, data=json.dumps(body), content_type="application/json", **headers)

    def test_full_flow_with_csrf_and_retry_after_close(self):
        staff = Client(enforce_csrf_checks=True)
        staff.force_login(self.teacher)
        staff.get("/api/v1/auth/me")
        pupil = Client(enforce_csrf_checks=True)
        self.assertEqual(pupil.get("/api/v1/auth/me").status_code, 401)
        initial_csrf = pupil.cookies["csrftoken"].value
        auth = {"username": "flowpupil", "password": "K12Demo!7264"}
        self.assertEqual(self.write(pupil, "post", "/api/v1/auth/login", auth).status_code, 403)
        self.assertEqual(self.write(pupil, "post", "/api/v1/auth/login", auth, csrf=True).status_code, 200)
        self.assertNotEqual(pupil.cookies["csrftoken"].value, initial_csrf)
        at_scan = datetime(2026, 10, 12, 0, 4, tzinfo=timezone.utc)
        with patch("django.utils.timezone.now", return_value=at_scan):
            challenge = self.write(staff, "post", self.session_url + "/qr-challenges", {}, csrf=True)
            self.assertEqual(challenge.status_code, 201)
            token = challenge.json()["token"]
            scan_response = self.write(pupil, "post", "/api/v1/qr-scans", {"token": token}, "scan-first", True)
            self.assertEqual(scan_response.status_code, 201, scan_response.content)
        scan = scan_response.json()
        self.assertEqual(Attendance.objects.get(pk=self.rows[0]["attendance"]["id"]).status, "UNMARKED")
        confirm_url = "/api/v1/qr-scans/" + scan["id"] + "/confirm"
        body = {"expected_scan_version": 0, "expected_attendance_version": 0,
                "identity_confirmed": True, "uniform": {"observed_uniform": "SPORTS",
                "uniform_status": "NON_COMPLIANT"}}
        with patch("django.utils.timezone.now", return_value=datetime(2026, 10, 12, 0, 8, tzinfo=timezone.utc)):
            bad = self.write(staff, "post", confirm_url, body, "confirm", True)
            self.assertEqual(bad.status_code, 422, bad.content)
            self.assertEqual(QrScan.objects.get(pk=scan["id"]).status, "PENDING")
            self.assertFalse(IdempotencyRequest.objects.filter(key="confirm").exists())
            body["uniform"]["reason"] = "Buổi sáng yêu cầu sơ mi"
            confirmed = self.write(staff, "post", confirm_url, body, "confirm", True)
            self.assertEqual(confirmed.status_code, 200, confirmed.content)
            official = confirmed.json()["attendance"]
            self.assertEqual(official["arrived_at"], scan["scanned_at"])
            self.assertEqual(official["arrival_status"], "ON_TIME")
            self.assertEqual(official["uniform_status"], "NON_COMPLIANT")
        attendance_url = "/api/v1/attendance/" + self.rows[1]["attendance"]["id"]
        with patch("django.utils.timezone.now", return_value=datetime(2026, 10, 12, 0, 12, tzinfo=timezone.utc)):
            manual = self.write(staff, "patch", attendance_url, {"expected_version": 0,
                "status": "PRESENT", "arrived_at": "2026-10-12T07:10:00+07:00",
                "reason": "Không có điện thoại"}, "manual", True)
            self.assertEqual(manual.status_code, 200, manual.content)
            self.assertEqual(manual.json()["arrival_status"], "LATE")
            closed = self.write(staff, "post", self.session_url + "/close", {"expected_version": 1}, csrf=True)
            self.assertEqual(closed.status_code, 200, closed.content)
            self.assertEqual(closed.json()["remaining_not_checked"], 1)
            replay = self.write(staff, "post", confirm_url, body, "confirm", True)
            self.assertEqual(replay.status_code, 200, replay.content)
            self.assertEqual(replay.json(), confirmed.json())
            self.assertEqual(self.write(pupil, "post", "/api/v1/qr-scans", {"token": token}, "newscan", True).status_code, 409)
        filters = {"date_from": "2026-10-12", "date_to": "2026-10-12"}
        summary = staff.get("/api/v1/reports/summary", filters).json()
        self.assertEqual({k: summary[k] for k in ["expected", "present", "on_time", "late", "non_compliant", "not_checked"]},
                         {"expected": 2, "present": 2, "on_time": 1, "late": 1, "non_compliant": 1, "not_checked": 1})
        self.assertEqual(summary["violation_rate"], 1)
        self.assertEqual(summary["check_coverage"], .5)
        for fmt in ["csv", "xlsx"]:
            export = staff.get("/api/v1/reports/export", {**filters, "format": fmt})
            self.assertEqual(export.status_code, 200)
            self.assertIn("no-store", export["Cache-Control"])
        self.assertEqual(self.write(pupil, "post", "/api/v1/auth/logout", {}, csrf=True).status_code, 200)
        self.assertEqual(pupil.get("/api/v1/me/today-sessions").status_code, 401)

    def test_read_write_export_scopes_for_all_roles(self):
        routes = ["/api/v1/grades", "/api/v1/classes", "/api/v1/students", "/api/v1/sessions",
                  self.session_url, self.session_url + "/roster", self.session_url + "/qr-scans",
                  f"/api/v1/students/{self.students[0].id}/photo",
                  "/api/v1/reports/attendance?date_from=2026-10-12&date_to=2026-10-12",
                  "/api/v1/reports/summary?date_from=2026-10-12&date_to=2026-10-12",
                  "/api/v1/reports/export?date_from=2026-10-12&date_to=2026-10-12&format=csv"]
        self.client.logout()
        for url in routes:
            with self.subTest(role="anonymous", url=url):
                self.assertEqual(self.client.get(url).status_code, 401)
        self.client.force_login(self.pupil)
        for url in routes:
            with self.subTest(role="student", url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.other)
        for url in [self.session_url, self.session_url + "/roster", self.session_url + "/qr-scans",
                    f"/api/v1/students/{self.students[0].id}", f"/api/v1/students/{self.students[0].id}/photo"]:
            self.assertEqual(self.client.get(url).status_code, 404)
        for url, payload in [(self.session_url + "/open", {"expected_version": 1}),
                             (self.session_url + "/close", {"expected_version": 1}),
                             (self.session_url + "/qr-challenges", {})]:
            self.assertEqual(self.write(self.client, "post", url, payload).status_code, 404)
        patch_url = "/api/v1/attendance/" + self.rows[0]["attendance"]["id"]
        self.assertEqual(self.write(self.client, "patch", patch_url, {"expected_version": 0,
            "status": "ABSENT"}, "outside").status_code, 404)
        self.assertEqual(self.write(self.client, "patch", patch_url + "/uniform", {"expected_version": 0,
            "observed_uniform": "SHIRT", "uniform_status": "COMPLIANT"}, "outside").status_code, 404)

    def test_replay_rechecks_reassigned_teacher_scope(self):
        url = "/api/v1/attendance/" + self.rows[0]["attendance"]["id"]
        body = {"expected_version": 0, "status": "ABSENT"}
        self.assertEqual(self.write(self.client, "patch", url, body, "reassign").status_code, 200)
        Classroom.objects.filter(pk=self.classroom.pk).update(teacher=self.other)
        self.assertEqual(self.write(self.client, "patch", url, body, "reassign").status_code, 404)
        self.assertEqual(self.client.get(self.session_url + "/roster").status_code, 404)
