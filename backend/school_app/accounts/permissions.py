"""Role boundaries; classroom checks belong to A03/A07 after models exist."""
from school_app.core.enums import Role
from school_app.accounts.services import AccountError


def require_authenticated(request):
    user = request.user
    if not user.is_authenticated or not user.is_active:
        raise AccountError("UNAUTHENTICATED", "Authentication is required.", 401)
    return user


def require_roles(request, *roles):
    user = require_authenticated(request)
    if user.role not in roles:
        raise AccountError("FORBIDDEN", "You do not have permission.", 403)
    return user


def require_student(request):
    user = require_roles(request, Role.STUDENT)
    if not getattr(user, "student_id", None):
        raise AccountError("STUDENT_NOT_LINKED", "Student account has no linked profile.", 403)
    student = user.student
    if not student.active:
        raise AccountError("FORBIDDEN", "Student profile is inactive.", 403)
    return student
