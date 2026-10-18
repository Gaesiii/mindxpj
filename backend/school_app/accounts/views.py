"""JSON session endpoints protected by Django CSRF middleware."""
import json
from functools import wraps

from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from school_app.accounts.forms import LoginForm, validate_payload
from school_app.accounts.permissions import require_authenticated
from school_app.accounts.services import AccountError, authenticate_user, serialize_identity
from school_app.core.errors import error_response


def endpoint(method):
    def decorate(view):
        @wraps(view)
        @never_cache
        def wrapped(request):
            if request.method != method:
                response = error_response(request, "METHOD_NOT_ALLOWED", "Method is not allowed.", 405)
                response["Allow"] = method
                return response
            try:
                return view(request)
            except AccountError as exc:
                response = error_response(request, exc.code, exc.message, exc.status, exc.details)
                if exc.status == 429:
                    response["Retry-After"] = str(exc.details["retry_after"])
                return response
        return wrapped
    return decorate


def read_payload(request, fields):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    except (ValueError, UnicodeError):
        raise AccountError("BAD_REQUEST", "Invalid JSON body.", 400) from None
    errors = validate_payload(payload, fields)
    if errors:
        raise AccountError("VALIDATION_ERROR", "Invalid request fields.", 422, errors)
    return payload


@ensure_csrf_cookie
@endpoint("GET")
def me_view(request):
    return JsonResponse(serialize_identity(require_authenticated(request)))


@endpoint("POST")
def login_view(request):
    form = LoginForm(read_payload(request, {"username", "password"}))
    if not form.is_valid():
        raise AccountError("VALIDATION_ERROR", "Invalid request fields.", 422,
                           {key: list(values) for key, values in form.errors.items()})
    user = authenticate_user(request, **form.cleaned_data)
    request.session.flush()
    login(request, user)
    return JsonResponse(serialize_identity(user))


@endpoint("POST")
def logout_view(request):
    require_authenticated(request)
    read_payload(request, set())
    logout(request)
    return JsonResponse({"ok": True})
