"""A03 role scope is applied in database queries before objects are read."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F, Count, Q
from school_app.core.idempotency import check_version, record_change

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
    rows = Classroom.objects.select_related("grade", "teacher").annotate(
        active_student_count=Count("students", filter=Q(students__active=True)),
        total_student_count=Count("students"))
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
    active_count = (classroom.active_student_count if hasattr(classroom, "active_student_count")
                    else classroom.students.filter(active=True).count())
    total_count = (classroom.total_student_count if hasattr(classroom, "total_student_count")
                   else classroom.students.count())
    return {"id": str(classroom.id), "code": classroom.code, "name": classroom.name,
            "grade_id": str(classroom.grade_id), "teacher_id": str(classroom.teacher_id),
            "capacity": classroom.capacity, "active": classroom.active, "version": classroom.version,
            "active_student_count": active_count,
            "total_student_count": total_count}


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
    payload = dict(payload)
    expected = payload.pop("expected_version", None) if classroom is not None else None
    try:
        with transaction.atomic():
            if classroom is not None:
                # Acquire the SQLite write lock before reading counts or version.
                Classroom.objects.filter(pk=classroom.pk).update(version=F("version"))
                classroom = require_class(user, classroom.pk)
                check_version(classroom, expected)
                baseline = {"code": classroom.code, "name": classroom.name,
                            "grade_id": str(classroom.grade_id), "teacher_id": str(classroom.teacher_id),
                            "capacity": classroom.capacity, "active": classroom.active}
                before = serialize_class(classroom)
            else:
                baseline = {"capacity": 50, "active": True}
                before = {}
            values = form_data(ClassroomForm({**baseline, **payload}))
            grade = Grade.objects.filter(pk=values.pop("grade_id")).first()
            teacher = get_user_model().objects.filter(pk=values.pop("teacher_id"),
                            role=Role.HOMEROOM_TEACHER, is_active=True).first()
            if grade is None or teacher is None:
                raise AccountError("VALIDATION_ERROR", "Select a valid grade and active homeroom teacher.", 422)
            creating = classroom is None
            if creating:
                classroom = Classroom()
            else:
                if classroom.students.filter(active=True).count() > values["capacity"]:
                    raise AccountError("CAPACITY_CONFLICT", "Capacity is below the active student count.", 409)
                if not values["active"]:
                    from school_app.schedules.models import Session
                    if classroom.students.filter(active=True).exists() or Session.objects.filter(classroom=classroom,status="OPEN").exists():
                        raise AccountError("INVALID_STATE", "Archive requires no active students or open sessions.", 409)
            classroom.grade, classroom.teacher = grade, teacher
            for key, value in values.items():
                setattr(classroom, key, value)
            if creating:
                classroom.save()
            else:
                changed = Classroom.objects.filter(pk=classroom.pk,version=expected).update(
                    **values,grade=grade,teacher=teacher,version=F("version")+1)
                if not changed:
                    raise AccountError("VERSION_CONFLICT", "Record changed; reload it.", 409)
                classroom.version = expected+1
            record_change(user,classroom,"CREATE" if creating else "UPDATE",before,serialize_class(classroom))
            return classroom
    except IntegrityError:
        raise AccountError("DUPLICATE", "Classroom code already exists.", 409) from None


def archive_class(user, classroom, payload):
    if set(payload) != {"expected_version"}:
        raise AccountError("VALIDATION_ERROR", "Only expected_version is accepted.", 422)
    return save_class(user,{**payload,"active":False},classroom)
