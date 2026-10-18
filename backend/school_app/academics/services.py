"""A03 role scope is applied in database queries before objects are read."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from school_app.accounts.services import AccountError
from school_app.academics.forms import ClassroomForm, GradeForm
from school_app.academics.models import Classroom, Grade
from school_app.core.api import form_data
from school_app.core.enums import Role


def staff_user(user):
    if not user.is_authenticated or not user.is_active:
        raise AccountError("UNAUTHENTICATED", "Authentication is required.", 401)
    if user.role not in (Role.HOMEROOM_TEACHER, Role.SUPERVISOR):
        raise AccountError("FORBIDDEN", "Staff business role is required.", 403)
    return user


def supervisor_user(user):
    staff_user(user)
    if user.role != Role.SUPERVISOR:
        raise AccountError("FORBIDDEN", "Supervisor role is required.", 403)
    return user


def scoped_classes(user):
    staff_user(user)
    rows = Classroom.objects.select_related("grade", "teacher")
    return rows if user.role == Role.SUPERVISOR else rows.filter(teacher_id=user.id)


def require_class(user, class_id):
    classroom = scoped_classes(user).filter(pk=class_id).first()
    if classroom is None:
        raise AccountError("NOT_FOUND", "Classroom was not found.", 404)
    return classroom


def assert_class_filter(user, class_id):
    classroom = scoped_classes(user).filter(pk=class_id).first()
    if classroom is None:
        raise AccountError("FORBIDDEN", "Classroom filter is outside your scope.", 403)
    return classroom


def serialize_grade(grade):
    return {"id": str(grade.id), "code": grade.code, "name": grade.name}


def serialize_class(classroom):
    return {"id": str(classroom.id), "code": classroom.code, "name": classroom.name,
            "grade_id": str(classroom.grade_id), "teacher_id": str(classroom.teacher_id)}


def list_grades(user):
    classes = scoped_classes(user)
    rows = Grade.objects.all()
    if user.role == Role.HOMEROOM_TEACHER:
        rows = rows.filter(classrooms__in=classes).distinct()
    return rows


def create_grade(user, payload):
    supervisor_user(user)
    values = form_data(GradeForm(payload))
    try:
        with transaction.atomic():
            return Grade.objects.create(**values)
    except IntegrityError:
        raise AccountError("DUPLICATE", "Grade code already exists.", 409) from None


def save_class(user, payload, classroom=None):
    supervisor_user(user)
    if classroom is not None:
        baseline = {"code": classroom.code, "name": classroom.name,
                    "grade_id": str(classroom.grade_id), "teacher_id": str(classroom.teacher_id)}
        payload = {**baseline, **payload}
    values = form_data(ClassroomForm(payload))
    grade = Grade.objects.filter(pk=values.pop("grade_id")).first()
    teacher = get_user_model().objects.filter(pk=values.pop("teacher_id"),
                    role=Role.HOMEROOM_TEACHER, is_active=True).first()
    if grade is None or teacher is None:
        raise AccountError("VALIDATION_ERROR", "Select a valid grade and active homeroom teacher.", 422)
    if classroom is None:
        classroom = Classroom()
    classroom.grade, classroom.teacher = grade, teacher
    for key, value in values.items():
        setattr(classroom, key, value)
    try:
        with transaction.atomic():
            classroom.save()
    except IntegrityError:
        raise AccountError("DUPLICATE", "Classroom code already exists.", 409) from None
    return classroom
