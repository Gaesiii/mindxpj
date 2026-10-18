"""Profile and photo writes enforce current classroom scope at the service boundary."""
from django.db import IntegrityError, transaction
from django.db.models import Q

from school_app.accounts.services import AccountError
from school_app.academics.services import scoped_classes, assert_class_filter, require_class
from school_app.students.forms import StudentCreateForm, StudentUpdateForm
from school_app.students.models import Student
from school_app.core.api import form_data, parse_uuid
from school_app.core.enums import Role
from school_app.core.storage import normalize_photo, store_photo, remove_photo, photo_file


def scoped_students(user):
    return Student.objects.filter(classroom__in=scoped_classes(user)).select_related("classroom__grade")


def require_student_profile(user, student_id, allow_self=False):
    if not user.is_authenticated or not user.is_active:
        raise AccountError("UNAUTHENTICATED", "Authentication is required.", 401)
    if allow_self and user.role == Role.STUDENT:
        if not user.student_id:
            raise AccountError("STUDENT_NOT_LINKED", "Student account has no linked profile.", 403)
        rows = Student.objects.filter(pk=user.student_id).select_related("classroom__grade")
    else:
        rows = scoped_students(user)
    student = rows.filter(pk=student_id).first()
    if student is None:
        raise AccountError("NOT_FOUND", "Student was not found.", 404)
    if user.role == Role.STUDENT and not student.active:
        raise AccountError("FORBIDDEN", "Student profile is inactive.", 403)
    return student


def serialize_student(student, minimal=False):
    result = {"id": str(student.id), "student_code": student.student_code,
              "full_name": student.full_name, "class_id": str(student.classroom_id),
              "grade_id": str(student.classroom.grade_id)}
    if not minimal:
        result.update(active=student.active, has_photo=bool(student.photo_path))
    return result


def list_students(user, query):
    rows = scoped_students(user)
    if set(query) - {"class_id", "active", "search"}:
        raise AccountError("VALIDATION_ERROR", "Unsupported student filter.", 422)
    if hasattr(query, "getlist") and any(len(query.getlist(key)) != 1 for key in query):
        raise AccountError("VALIDATION_ERROR", "Each student filter must occur once.", 422)
    if "class_id" in query:
        classroom = assert_class_filter(user, parse_uuid(query["class_id"]))
        rows = rows.filter(classroom=classroom)
    if "active" in query:
        if query["active"] not in ("true", "false"):
            raise AccountError("VALIDATION_ERROR", "Active filter must be true or false.", 422)
        rows = rows.filter(active=query["active"] == "true")
    if "search" in query:
        search = query["search"].strip()
        if len(search) > 150:
            raise AccountError("VALIDATION_ERROR", "Search is too long.", 422)
        rows = rows.filter(Q(student_code__icontains=search) | Q(full_name__icontains=search))
    return rows


def create_student(user, payload):
    scoped_classes(user)  # Reject unauthorized actors before form/object reads.
    values = form_data(StudentCreateForm(payload))
    classroom = assert_class_filter(user, values.pop("class_id"))
    try:
        with transaction.atomic():
            return Student.objects.create(classroom=classroom, **values)
    except IntegrityError:
        raise AccountError("DUPLICATE", "Student code already exists.", 409) from None


def update_student(user, student_id, payload):
    student = require_student_profile(user, student_id)
    if "class_id" in payload and user.role != Role.SUPERVISOR:
        raise AccountError("FORBIDDEN", "Only supervisors can transfer a student.", 403)
    merged = {"full_name": student.full_name, "active": student.active,
              "class_id": str(student.classroom_id), **payload}
    values = form_data(StudentUpdateForm(merged))
    classroom = require_class(user, values.pop("class_id"))
    student.classroom = classroom
    for key, value in values.items():
        setattr(student, key, value)
    with transaction.atomic():
        student.save(update_fields=["full_name", "active", "classroom"])
    return student


def _remove_old_photo(path):
    try:
        remove_photo(path)
    except OSError:
        # Windows may retain a file handle for an in-flight protected download.
        # The database write is already committed. Keep this private orphan
        # rather than returning a failed write after it has succeeded.
        pass


def replace_photo(user, student_id, upload):
    require_student_profile(user, student_id)
    normalized = normalize_photo(upload)
    new_path = None
    try:
        with transaction.atomic():
            student = require_student_profile(user, student_id)
            old_path = student.photo_path
            new_path = store_photo(student.id, normalized)
            student.photo_path = new_path
            student.save(update_fields=["photo_path"])
            if old_path:
                transaction.on_commit(lambda: _remove_old_photo(old_path))
    except Exception:
        if new_path:
            remove_photo(new_path)
        raise
    return student


def open_photo(user, student_id):
    student = require_student_profile(user, student_id)
    if not student.photo_path:
        raise AccountError("NOT_FOUND", "Photo was not found.", 404)
    try:
        return photo_file(student.photo_path).open("rb")
    except FileNotFoundError:
        raise AccountError("NOT_FOUND", "Photo was not found.", 404) from None
