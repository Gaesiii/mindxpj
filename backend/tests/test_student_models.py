"""A04/A05 relational constraints and provisioning identities."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from school_app.core.enums import Role


class StudentModelTests(TestCase):
    def setUp(self):
        from school_app.students.models import Student
        from school_app.academics.models import Grade, Classroom
        self.Student = Student
        self.teacher = get_user_model().objects.create_user(username="teacher", role=Role.HOMEROOM_TEACHER)
        grade = Grade.objects.create(code="10", name="Khối 10")
        self.classroom = Classroom.objects.create(code="10A", name="10A", grade=grade, teacher=self.teacher)

    def test_student_unique_code_duplicate_names_and_protected_classroom(self):
        from django.db.models.deletion import ProtectedError
        first = self.Student.objects.create(student_code="HS01", full_name="Nguyễn An", classroom=self.classroom)
        second = self.Student.objects.create(student_code="HS02", full_name="Nguyễn An", classroom=self.classroom)
        self.assertNotEqual(first.id, second.id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.Student.objects.create(student_code="HS01", full_name="Other", classroom=self.classroom)
        with self.assertRaises(ProtectedError):
            self.classroom.delete()

    def test_account_provision_links_only_active_student_one_to_one(self):
        from school_app.accounts.services import provision_user
        student = self.Student.objects.create(student_code="HS01", full_name="An", classroom=self.classroom)
        user = provision_user(username="pupil", password="Rivers!Purple92", student=student)
        self.assertEqual(user.student_id, student.id)
        from school_app.accounts.services import serialize_identity
        self.assertEqual(serialize_identity(user)["student_id"], str(student.id))
        self.assertEqual(serialize_identity(user)["class_ids"], [str(self.classroom.id)])
        for kwargs in ({"username": "duplicate", "student": student},
                       {"username": "staff", "student": student, "role": Role.HOMEROOM_TEACHER}):
            with self.assertRaises(ValidationError):
                provision_user(password="Rivers!Purple92", **kwargs)
        student.active = False
        student.save()
        with self.assertRaises(ValidationError):
            provision_user(username="inactive", password="Rivers!Purple92", student=student)

    def test_student_link_is_protected_and_scan_identity_comes_from_user(self):
        from django.db.models.deletion import ProtectedError
        from django.test import RequestFactory
        from school_app.accounts.permissions import require_student
        from school_app.accounts.services import provision_user, AccountError
        student = self.Student.objects.create(student_code="HS01", full_name="An", classroom=self.classroom)
        user = provision_user(username="pupil", password="Rivers!Purple92", student=student)
        request = RequestFactory().post("/", {"student_id": "somebody-else"})
        request.user = user
        self.assertEqual(require_student(request), student)
        with self.assertRaises(ProtectedError):
            student.delete()
        student.active = False
        student.save()
        user.refresh_from_db()
        with self.assertRaises(AccountError) as caught:
            require_student(request)
        self.assertEqual(caught.exception.status, 403)
