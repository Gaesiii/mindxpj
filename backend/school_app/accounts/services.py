"""A02 auth and local account provisioning; no public account creation."""
import hashlib
import time

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from school_app.core.enums import Role

# Local demo only: Django's default LocMemCache is per process. This is not
# a distributed limit. Ignore forwarded headers: REMOTE_ADDR is the peer.
LOGIN_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 300


class AccountError(Exception):
    def __init__(self, code, message, status, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


def check_login_limit(request):
    now = int(time.time())
    window = now // LOGIN_WINDOW_SECONDS
    peer_hash = hashlib.sha256(request.META.get("REMOTE_ADDR", "unknown").encode()).hexdigest()
    key = f"accounts:login:{peer_hash}:{window}"
    if cache.add(key, 1, timeout=LOGIN_WINDOW_SECONDS):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:  # Cache eviction/expiry between add and incr.
            cache.add(key, 1, timeout=LOGIN_WINDOW_SECONDS)
            count = 1
    if count > LOGIN_ATTEMPTS:
        raise AccountError("RATE_LIMITED", "Too many login attempts. Try again later.", 429,
                           {"retry_after": LOGIN_WINDOW_SECONDS - now % LOGIN_WINDOW_SECONDS})


def authenticate_user(request, username, password):
    check_login_limit(request)
    user = authenticate(request=request, username=username, password=password)
    if user is None or not user.is_active:
        raise AccountError("INVALID_CREDENTIALS", "Invalid username or password.", 401)
    return user


def serialize_identity(user):
    class_ids = []
    student_id = None
    if user.role in (Role.HOMEROOM_TEACHER, Role.SUPERVISOR):
        from school_app.academics.services import scoped_classes
        class_ids = [str(value) for value in scoped_classes(user).values_list("id", flat=True)]
    elif user.role == Role.STUDENT and user.student_id:
        student_id = str(user.student_id)
        if user.student.active:
            class_ids = [str(user.student.classroom_id)]
    return {"id": str(user.id), "username": user.username, "role": user.role,
            "student_id": student_id, "class_ids": class_ids}


def provision_user(*, username, password, role=Role.STUDENT, student=None):
    """Trusted local setup entrypoint; role must be explicit for staff business use."""
    if not isinstance(username, str) or not username.strip():
        raise ValidationError({"username": ["A nonempty username string is required."]})
    if not isinstance(password, str) or not password.strip():
        raise ValidationError({"password": ["A password string is required."]})
    if not isinstance(role, str) or role not in Role.values:
        raise ValidationError({"role": ["Select an allowed business role."]})
    try:
        username.encode("utf-8")
        password.encode("utf-8")
    except UnicodeError:
        raise ValidationError("Username and password must contain valid Unicode.") from None
    if student is not None:
        from school_app.students.models import Student
        if (role != Role.STUDENT or not isinstance(student, Student) or not student.pk
                or not Student.objects.filter(pk=student.pk, active=True).exists()):
            raise ValidationError({"student": ["Only a student account can link an active student profile."]})
    user = get_user_model()(username=username.strip(), role=role, student=student,
                           is_staff=False, is_superuser=False)
    user.full_clean(exclude=["password"])
    validate_password(password, user=user)
    user.set_password(password)
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError:
        raise ValidationError({"username": ["Username already exists."]}) from None
    return user
