"""A14 local fictional seed, repeatability and collision safety."""
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from school_app.academics.models import Grade, Classroom
from school_app.students.models import Student
from school_app.schedules.models import ScheduleRule, Session
from school_app.core.enums import Role, RequiredUniform, Slot


class SeedDemoTests(TestCase):
    def run_seed(self):
        output = StringIO()
        with patch.dict("os.environ", {"DEMO_PASSWORD": "Rivers!Purple92"}):
            call_command("seed_demo", stdout=output)
        return output.getvalue()

    def test_seed_creates_fake_roles_links_and_weekday_uniform_rules_without_sessions(self):
        output = self.run_seed()
        User = get_user_model()
        self.assertEqual(User.objects.filter(role=Role.SUPERVISOR).count(), 1)
        self.assertEqual(User.objects.filter(role=Role.HOMEROOM_TEACHER).count(), 2)
        self.assertEqual(User.objects.filter(role=Role.STUDENT).count(), 20)
        self.assertEqual(Classroom.objects.count(), 2)
        self.assertEqual(Student.objects.count(), 20)
        self.assertEqual(ScheduleRule.objects.count(), 20)
        self.assertFalse(Session.objects.exists())
        for user in User.objects.all():
            self.assertTrue(user.check_password("Rivers!Purple92"))
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            self.assertNotIn(user.password, output)
            if user.role == Role.STUDENT:
                self.assertIsNotNone(user.student_id)
                self.assertTrue(user.student.active)
        self.assertNotIn("Rivers!Purple92", output)
        self.assertEqual(set(ScheduleRule.objects.filter(slot=Slot.MORNING).values_list("required_uniform", flat=True)), {RequiredUniform.SHIRT})
        self.assertEqual(set(ScheduleRule.objects.filter(slot=Slot.AFTERNOON).values_list("required_uniform", flat=True)), {RequiredUniform.SPORTS})

    def test_repeat_seed_preserves_objects_passwords_and_unrelated_data(self):
        unrelated = get_user_model().objects.create_user(username="real_teacher", role=Role.HOMEROOM_TEACHER)
        unrelated_grade = Grade.objects.create(code="REAL", name="Existing")
        self.run_seed()
        ids = set(Student.objects.values_list("id", flat=True))
        pupil = get_user_model().objects.get(username="demo_student_01")
        pupil.set_password("Changed!Secret95")
        pupil.save()
        from django.utils import timezone
        from datetime import timedelta
        from school_app.core.enums import SessionStatus
        classroom = Classroom.objects.get(code="DEMO10A")
        now = timezone.now()
        history = Session.objects.create(classroom=classroom, school_date=now.date(), slot=Slot.MORNING,
            status=SessionStatus.CLOSED, start_at=now - timedelta(hours=2),
            late_cutoff_at=now - timedelta(hours=2) + timedelta(minutes=5),
            close_at=now - timedelta(hours=1), required_uniform_snapshot=RequiredUniform.SHIRT, version=4)
        rule = ScheduleRule.objects.filter(classroom=classroom, weekday=0, slot=Slot.MORNING).get()
        rule.grace_minutes = 7
        rule.save()
        self.run_seed()
        self.assertEqual(set(Student.objects.values_list("id", flat=True)), ids)
        pupil.refresh_from_db()
        self.assertTrue(pupil.check_password("Changed!Secret95"))
        self.assertTrue(get_user_model().objects.filter(pk=unrelated.pk).exists())
        self.assertTrue(Grade.objects.filter(pk=unrelated_grade.pk).exists())
        self.assertEqual(Classroom.objects.count(), 2)
        self.assertEqual(ScheduleRule.objects.count(), 20)
        history.refresh_from_db()
        rule.refresh_from_db()
        self.assertEqual(history.status, SessionStatus.CLOSED)
        self.assertEqual(history.version, 4)
        self.assertEqual(rule.grace_minutes, 7)

    def test_username_collision_is_rejected_atomically_without_overwriting(self):
        existing = get_user_model().objects.create_user(username="demo_teacher_a", role=Role.HOMEROOM_TEACHER)
        with self.assertRaises(CommandError):
            self.run_seed()
        existing.refresh_from_db()
        self.assertEqual(existing.email, "")
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(Grade.objects.exists())
        self.assertFalse(Student.objects.exists())

    def test_grade_collision_rejected_without_mutation(self):
        existing = Grade.objects.create(code="DEMO10", name="Real Grade")
        with self.assertRaises(CommandError):
            self.run_seed()
        existing.refresh_from_db()
        self.assertEqual(existing.name, "Real Grade")
        self.assertFalse(get_user_model().objects.exists())

    def test_no_password_argument_and_private_prompt_support(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", "--password", "secret")
        with patch.dict("os.environ", {}, clear=True), patch(
                "school_app.management_app.management.commands.seed_demo.getpass",
                side_effect=["Rivers!Purple92", "Rivers!Purple92"]):
            call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Student.objects.count(), 20)
