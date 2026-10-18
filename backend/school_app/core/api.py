"""Shared JSON/HTTP boundary. Services keep authorization and business rules."""
import json
import math
import re
import uuid
from functools import wraps

from django.core.exceptions import RequestDataTooBig
from django.db import OperationalError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from school_app.accounts.services import AccountError
from school_app.core.errors import error_response


def api_view(*methods):
    def decorate(view):
        @wraps(view)
        @never_cache
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = error_response(request, "METHOD_NOT_ALLOWED", "Phương thức không hợp lệ", 405)
                response["Allow"] = ", ".join(methods)
                return response
            try:
                return view(request, *args, **kwargs)
            except AccountError as exc:
                response = error_response(request, exc.code, exc.message, exc.status, exc.details)
                if exc.status == 429:
                    response["Retry-After"] = str(exc.details.get("retry_after", 60))
                return response
            except OperationalError as exc:
                if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                    raise
                return error_response(request, "DATABASE_BUSY", "Chưa lưu; thử lại cùng Idempotency-Key", 409)
        return wrapped
    return decorate


def _invalid_constant(value):
    raise ValueError("Non-finite JSON number")


def read_json(request, allowed=None):
    try:
        payload = json.loads(request.body.decode("utf-8"), parse_constant=_invalid_constant)
        # Invalid Unicode scalar values can otherwise crash database and UTF-8
        # error serialization. Check every value/key before echoing any errors.
        pending = [payload]
        while pending:
            value = pending.pop()
            if isinstance(value, str):
                value.encode("utf-8")
            elif isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Non-finite JSON number")
            elif isinstance(value, dict):
                pending.extend(value.keys())
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
    except (ValueError, UnicodeError, RecursionError, RequestDataTooBig):
        raise AccountError("BAD_REQUEST", "JSON hoặc UTF-8 không hợp lệ", 400) from None
    if not isinstance(payload, dict):
        raise AccountError("VALIDATION_ERROR", "Body phải là JSON object", 422)
    if allowed is not None:
        extra = set(payload) - set(allowed)
        if extra:
            raise AccountError("VALIDATION_ERROR", "Trường không được phép", 422,
                               {name: ["Không được phép"] for name in sorted(extra)})
    return payload


def form_data(form):
    if not form.is_valid():
        raise AccountError("VALIDATION_ERROR", "Dữ liệu không hợp lệ", 422,
                           {name: list(errors) for name, errors in form.errors.items()})
    return form.cleaned_data


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def parse_uuid(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value):
        raise AccountError("VALIDATION_ERROR", "ID phải là chuỗi UUID có dấu gạch", 422)
    return uuid.UUID(value)
