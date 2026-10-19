"""A03 current-teacher scope and grade/class API boundaries."""
import json
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from school_app.core.enums import Role


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class AcademicsTests(TestCase):
    def setUp(self):
        from school_app.academics.models import Grade, Classroom
        self.Grade, self.Classroom = Grade, Classroom
        User = get_user_model()
        self.supervisor = User.objects.create_user(username="supervisor", role=Role.SUPERVISOR)
        self.teacher = User.objects.create_user(username="teacher", role=Role.HOMEROOM_TEACHER)
        self.other = User.objects.create_user(username="other", role=Role.HOMEROOM_TEACHER)
        self.pupil = User.objects.create_user(username="pupil")
        self.grade = Grade.objects.create(code="10", name="Khối 10")
        self.classroom = Classroom.objects.create(code="10A", name="Lớp 10A", grade=self.grade, teacher=self.teacher)
        self.foreign = Classroom.objects.create(code="10B", name="Lớp 10B", grade=self.grade, teacher=self.other)
        self.client.force_login(self.supervisor)

    def write(self, method, url, payload):
        return getattr(self.client, method)(url, json.dumps(payload), content_type="application/json")

    def test_models_protect_relations_and_unique_codes(self):
        from django.db.models.deletion import ProtectedError
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.Grade.objects.create(code="10", name="Duplicate")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.Classroom.objects.create(code="10A", name="Duplicate", grade=self.grade, teacher=self.teacher)
        with self.assertRaises(ProtectedError):
            self.grade.delete()
        with self.assertRaises(ProtectedError):
            self.teacher.delete()

    def test_scoped_helpers_for_current_teacher_and_explicit_filter(self):
        from school_app.academics.services import scoped_classes, require_class, assert_class_filter
        from school_app.accounts.services import AccountError
        self.assertEqual(list(scoped_classes(self.teacher)), [self.classroom])
        self.assertEqual(scoped_classes(self.supervisor).count(), 2)
        self.assertEqual(require_class(self.teacher, self.classroom.id), self.classroom)
        with self.assertRaises(AccountError) as caught:
            require_class(self.teacher, self.foreign.id)
        self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(AccountError) as caught:
            assert_class_filter(self.teacher, self.foreign.id)
        self.assertEqual(caught.exception.status, 403)
        for user in (self.pupil, get_user_model().objects.create_superuser(username="operator")):
            with self.assertRaises(AccountError) as caught:
                scoped_classes(user)
            self.assertEqual(caught.exception.status, 403)
        self.teacher.is_active = False
        with self.assertRaises(AccountError) as caught:
            scoped_classes(self.teacher)
        self.assertEqual(caught.exception.status, 401)

    def test_supervisor_creates_grade_and_class_and_duplicate_is_conflict(self):
        response = self.write("post", "/api/v1/grades", {"code": "11", "name": "Khối 11"})
        self.assertEqual(response.status_code, 201)
        payload = {"code": "11A", "name": "Lớp 11A", "grade_id": response.json()["id"], "teacher_id": str(self.teacher.id)}
        created = self.write("post", "/api/v1/classes", payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["teacher_id"], str(self.teacher.id))
        self.assertEqual(self.write("post", "/api/v1/classes", payload).status_code, 409)
        self.assertEqual(self.write("post", "/api/v1/grades", {"code": "11", "name": "Khối 11"}).status_code, 409)

    def test_classroom_teacher_must_be_active_homeroom_teacher(self):
        payload = {"code": "bad", "name": "Bad", "grade_id": str(self.grade.id)}
        for user in (self.pupil, self.supervisor):
            self.assertEqual(self.write("post", "/api/v1/classes", {**payload, "teacher_id": str(user.id)}).status_code, 422)
        self.teacher.is_active = False
        self.teacher.save()
        self.assertEqual(self.write("post", "/api/v1/classes", {**payload, "teacher_id": str(self.teacher.id)}).status_code, 422)
        self.assertEqual(self.Classroom.objects.count(), 2)

    def test_teacher_reads_only_assigned_classes_and_grades_and_cannot_write(self):
        unrelated = self.Grade.objects.create(code="12", name="Khối 12")
        self.client.force_login(self.teacher)
        self.assertEqual([row["id"] for row in self.client.get("/api/v1/classes").json()["items"]], [str(self.classroom.id)])
        self.assertEqual([row["id"] for row in self.client.get("/api/v1/grades").json()["items"]], [str(self.grade.id)])
        self.assertEqual(self.write("post", "/api/v1/grades", {"code": "9", "name": "Khối 9"}).status_code, 403)
        self.assertEqual(self.write("patch", f"/api/v1/classes/{self.classroom.id}", {"name": "Changed"}).status_code, 403)
        self.assertNotEqual(unrelated.id, self.grade.id)

    def test_reassignment_changes_scope_and_auth_me_immediately(self):
        response = self.write("patch", f"/api/v1/classes/{self.classroom.id}", {"teacher_id": str(self.other.id), "expected_version": 0})
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/api/v1/auth/me").json()["class_ids"], [])
        self.assertEqual(self.client.get("/api/v1/classes").json()["items"], [])
        self.client.force_login(self.other)
        self.assertEqual(set(self.client.get("/api/v1/auth/me").json()["class_ids"]), {str(self.classroom.id), str(self.foreign.id)})

    def test_student_and_anonymous_cannot_list_classes_or_grades(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/classes").status_code, 401)
        self.client.force_login(self.pupil)
        for url in ("/api/v1/classes", "/api/v1/grades"):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_class_create_and_patch_reject_wrong_types_extra_fields_and_bad_uuid(self):
        valid = {"code": "new", "name": "New", "grade_id": str(self.grade.id), "teacher_id": str(self.teacher.id)}
        for payload in ({**valid, "name": 1}, {**valid, "role": "SUPERVISOR"}, {**valid, "grade_id": "bad"}, {**valid, "name": " "}):
            self.assertEqual(self.write("post", "/api/v1/classes", payload).status_code, 422)
        self.assertEqual(self.write("patch", f"/api/v1/classes/{self.classroom.id}", {"teacher_id": None}).status_code, 422)
        self.assertEqual(self.write("patch", f"/api/v1/classes/{self.classroom.id}", {"id": "spoof"}).status_code, 422)

    def test_class_reference_ids_require_dashed_uuid_strings(self):
        valid = {"code": "new", "name": "New", "grade_id": str(self.grade.id), "teacher_id": str(self.teacher.id)}
        for field, value in (("grade_id", self.grade.id.hex), ("teacher_id", "{" + str(self.teacher.id) + "}")):
            with self.subTest(field=field):
                self.assertEqual(self.write("post", "/api/v1/classes", {**valid, field: value}).status_code, 422)

    def test_unauthenticated_writes_remain_csrf_protected(self):
        from django.test import Client
        response = Client(enforce_csrf_checks=True).post("/api/v1/grades", "{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "CSRF_FAILED")
