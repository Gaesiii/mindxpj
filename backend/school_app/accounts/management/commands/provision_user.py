"""Provision local accounts without exposing passwords in shell arguments."""
from getpass import getpass
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from school_app.accounts.services import provision_user
from school_app.core.enums import Role


class Command(BaseCommand):
    help = "Create a local MVP account; password is entered privately."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--role", choices=Role.values, default=Role.STUDENT)
        parser.add_argument("--student-id", help="Link an active Student UUID (STUDENT role only).")

    def handle(self, *args, **options):
        student = None
        if options.get("student_id"):
            from school_app.students.models import Student
            try:
                student = Student.objects.filter(pk=UUID(options["student_id"]), active=True).first()
            except (ValueError, TypeError):
                raise CommandError("Student ID must be a valid UUID.") from None
            if student is None or options["role"] != Role.STUDENT:
                raise CommandError("Select an active Student profile for a STUDENT account.")
        password = getpass("Password: ")
        confirmation = getpass("Password again: ")
        if password != confirmation:
            raise CommandError("Passwords do not match.")
        try:
            user = provision_user(username=options["username"], password=password, role=options["role"], student=student)
        except ValidationError:
            raise CommandError("Account was not created. Check username, role and password strength.") from None
        self.stdout.write(self.style.SUCCESS(f"Created account {user.id} ({user.role})."))
