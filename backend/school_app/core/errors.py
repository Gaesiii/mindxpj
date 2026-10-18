"""Shared JSON error shape; business error handling is added with each API."""
import uuid

from django.http import JsonResponse


def error_response(request, code, message, status, details=None):
    return JsonResponse({
        "code": code, "message": message,
        "details": details if details is not None else {},
        "request_id": getattr(request, "request_id", str(uuid.uuid4())),
    }, status=status, json_dumps_params={"ensure_ascii": False})


def bad_request(request, exception):
    return error_response(request, "BAD_REQUEST", "Yêu cầu không hợp lệ", 400)


def permission_denied(request, exception):
    return error_response(request, "FORBIDDEN", "Không có quyền thực hiện", 403)


def not_found(request, exception):
    return error_response(request, "NOT_FOUND", "Không tìm thấy tài nguyên", 404)


def server_error(request):
    return error_response(request, "INTERNAL_ERROR", "Không thể xử lý yêu cầu", 500)


def csrf_failure(request, reason=""):
    return error_response(request, "CSRF_FAILED", "Token CSRF thiếu hoặc không hợp lệ", 403)
