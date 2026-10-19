"""Profile and photo writes enforce current classroom scope at the service boundary."""
from django.db import IntegrityError, transaction
from django.db.models import Q, F
from django.utils import timezone
from school_app.core.idempotency import check_version, record_change
from school_app.academics.models import Classroom

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
        result.update(active=student.active, has_photo=bool(student.photo_path), version=student.version)
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


def _lock_class(class_id):
    Classroom.objects.filter(pk=class_id).update(version=F("version"))


def _check_destination(classroom, active, exclude=None):
    if not classroom.active:
        raise AccountError("INVALID_STATE", "Classroom is archived.", 409)
    if active and classroom.students.filter(active=True).exclude(pk=exclude).count() >= classroom.capacity:
        raise AccountError("CAPACITY_CONFLICT", "Classroom capacity has been reached.", 409)


def _invalidate_scans(student, user):
    from school_app.vision.models import VisionScan
    VisionScan.objects.filter(roster__student=student,status="PENDING").update(
        status="SUPERSEDED",resolved_at=timezone.now(),resolved_by=user,
        reason="Student profile changed",version=F("version")+1)


def create_student(user, payload):
    scoped_classes(user)
    values = form_data(StudentCreateForm({"active":True,**payload}))
    class_id = values.pop("class_id")
    assert_class_filter(user,class_id)
    try:
        with transaction.atomic():
            _lock_class(class_id)
            classroom = assert_class_filter(user,class_id)
            _check_destination(classroom,values["active"])
            student = Student.objects.create(classroom=classroom,**values)
            record_change(user,student,"CREATE",{},serialize_student(student))
            return student
    except IntegrityError:
        raise AccountError("DUPLICATE", "Student code already exists.", 409) from None


def update_student(user, student_id, payload):
    student = require_student_profile(user, student_id)
    if {"class_id","student_code"} & set(payload) and user.role != Role.SUPERVISOR:
        raise AccountError("FORBIDDEN", "Only supervisors can change student code or classroom.", 403)
    payload = dict(payload)
    expected = payload.pop("expected_version",None)
    try:
        with transaction.atomic():
            Student.objects.filter(pk=student_id).update(version=F("version"))
            student = require_student_profile(user,student_id)
            check_version(student,expected)
            before = serialize_student(student)
            values = form_data(StudentUpdateForm({"student_code":student.student_code,
                "full_name":student.full_name,"active":student.active,
                "class_id":str(student.classroom_id),**payload}))
            class_id = values.pop("class_id")
            _lock_class(class_id)
            classroom = require_class(user,class_id)
            # Deactivation stays available for cleanup; other writes require an active class.
            if values["active"] or class_id != student.classroom_id or payload.get("active") is not False:
                _check_destination(classroom,values["active"],student.pk)
            invalidate = class_id != student.classroom_id or (student.active and not values["active"])
            changed = Student.objects.filter(pk=student_id,version=expected).update(
                **values,classroom=classroom,version=F("version")+1)
            if not changed:
                raise AccountError("VERSION_CONFLICT", "Record changed; reload it.", 409)
            student.refresh_from_db()
            if invalidate:
                _invalidate_scans(student,user)
            record_change(user,student,"UPDATE",before,serialize_student(student))
            return student
    except IntegrityError:
        raise AccountError("DUPLICATE", "Student code already exists.", 409) from None


def archive_student(user, student_id, payload):
    require_student_profile(user,student_id)
    if set(payload) != {"expected_version"}:
        raise AccountError("VALIDATION_ERROR", "Only expected_version is accepted.", 422)
    return update_student(user,student_id,{**payload,"active":False})


def _remove_old_photo(path):
    try:
        remove_photo(path)
    except OSError:
        # Windows may retain a file handle for an in-flight protected download.
        # The database write is already committed. Keep this private orphan
        # rather than returning a failed write after it has succeeded.
        pass


def replace_photo(user, student_id, upload):
    student = require_student_profile(user, student_id)
    if not student.classroom.active:
        raise AccountError("INVALID_STATE", "Classroom is archived.", 409)
    normalized = normalize_photo(upload)
    new_path = None
    try:
        with transaction.atomic():
            Student.objects.filter(pk=student_id).update(version=F("version"))
            student = require_student_profile(user, student_id)
            _lock_class(student.classroom_id)
            student = require_student_profile(user, student_id)
            if not student.classroom.active:
                raise AccountError("INVALID_STATE", "Classroom is archived.", 409)
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
