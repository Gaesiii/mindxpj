"""Local fictional demo accounts/profiles/rules; never resets historical sessions."""
import os
from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from school_app.accounts.services import provision_user, AccountError
from school_app.academics.models import Grade, Classroom
from school_app.students.models import Student
from school_app.schedules.models import ScheduleRule
from school_app.schedules.services import save_rule
from school_app.core.enums import Role, Slot, RequiredUniform


def validation_codes(error):
    errors = ([item for items in error.error_dict.values() for item in items]
              if hasattr(error, 'error_dict') else error.error_list)
    return ','.join(sorted({str(item.code or 'invalid') for item in errors}))


def validate_demo_password(password):
    """Precheck every seeded username; never expose input values in errors."""
    if not isinstance(password, str) or not password.strip():
        raise CommandError('DEMO_PASSWORD rejected [blank]. Set a nonempty strong demo password.')
    usernames = ['demo_supervisor', 'demo_teacher_a', 'demo_teacher_b',
                 *[f'demo_student_{index:02}' for index in range(1, 21)]]
    for username in usernames:
        try:
            validate_password(password, user=get_user_model()(username=username))
        except ValidationError as error:
            raise CommandError(f'DEMO_PASSWORD rejected for {username} [{validation_codes(error)}]. '
                               'Set a strong random password in the matching Vercel environment and redeploy.') from None


def seed_account(username, role, password, student=None):
    email = f"{username}@example.invalid"
    user = get_user_model().objects.filter(username=username).first()
    if user is not None:
        expected_student = student.pk if student is not None else None
        if user.email != email or user.role != role or user.student_id != expected_student:
            raise CommandError("Demo username collision: existing account is not a compatible demo account.")
        return user
    user = provision_user(username=username, role=role, password=password, student=student)
    user.email = email
    user.save(update_fields=["email"])
    return user


def seed_objects(password):
    grade = Grade.objects.filter(code="DEMO10").first()
    if grade is not None and grade.name != "Khối demo 10":
        raise CommandError("Demo grade collision; existing data was preserved.")
    if grade is None:
        grade = Grade.objects.create(code="DEMO10", name="Khối demo 10")
    supervisor = seed_account("demo_supervisor", Role.SUPERVISOR, password)
    classrooms = []
    for letter in ("A", "B"):
        teacher = seed_account(f"demo_teacher_{letter.lower()}", Role.HOMEROOM_TEACHER, password)
        code, name = f"DEMO10{letter}", f"Lớp demo 10{letter}"
        classroom = Classroom.objects.filter(code=code).first()
        if classroom is not None and (classroom.name != name or classroom.grade_id != grade.pk
                                      or classroom.teacher_id != teacher.pk):
            raise CommandError("Demo classroom collision; existing data was preserved.")
        if classroom is None:
            classroom = Classroom.objects.create(code=code, name=name, grade=grade, teacher=teacher)
        classrooms.append(classroom)
    for index in range(1, 21):
        code, name = f"DEMOHS{index:02}", f"Học sinh demo {index:02}"
        classroom = classrooms[0 if index <= 10 else 1]
        student = Student.objects.filter(student_code=code).first()
        if student is not None and (student.full_name != name or student.classroom_id != classroom.pk):
            raise CommandError("Demo student collision; existing data was preserved.")
        if student is None:
            student = Student.objects.create(student_code=code, full_name=name, classroom=classroom)
        seed_account(f"demo_student_{index:02}", Role.STUDENT, password, student)
    for classroom in classrooms:
        for weekday in range(5):
            for slot, start, close, uniform in (
                    (Slot.MORNING, "07:00:00", "08:00:00", RequiredUniform.SHIRT),
                    (Slot.AFTERNOON, "13:00:00", "14:00:00", RequiredUniform.SPORTS)):
                if not ScheduleRule.objects.filter(classroom=classroom, weekday=weekday, slot=slot).exists():
                    save_rule(supervisor, {"weekday": weekday, "slot": slot, "start_time": start,
                              "close_time": close, "grace_minutes": 5, "required_uniform": uniform},
                              classroom_id=classroom.pk)


class Command(BaseCommand):
    help = "Seed 2 demo classes, 20 fictional students and weekday rules; preserve existing passwords."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD")
        if password is None:
            password = getpass("Demo password: ")
            if password != getpass("Demo password again: "):
                raise CommandError("Passwords do not match.")
        validate_demo_password(password)
        try:
            with transaction.atomic():
                seed_objects(password)
        except ValidationError as error:
            raise CommandError(f'Demo data validation failed [{validation_codes(error)}]. Existing data was preserved.') from None
        except AccountError as error:
            raise CommandError(f'Demo data creation rejected [{error.code}]. Existing data was preserved.') from None
        except IntegrityError:
            raise CommandError('Demo database constraint failed. Existing data was preserved.') from None
        self.stdout.write(self.style.SUCCESS(
            "Demo ready: DEMO10A/DEMO10B, 20 fictional students, weekday morning/afternoon rules. "
            "Accounts: demo_supervisor, demo_teacher_a/b, demo_student_01..20. "
            "Existing passwords and historical sessions were preserved."))
