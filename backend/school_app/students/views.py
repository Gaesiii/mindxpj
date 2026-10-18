from django.http import FileResponse
from school_app.students import services
from school_app.academics.services import scoped_classes
from school_app.core.api import api_view, read_json, json_response
from school_app.core.enums import Role
from school_app.accounts.services import AccountError


@api_view("GET", "POST")
def students_view(request):
    if request.method == "GET":
        return json_response({"items": [services.serialize_student(row)
                             for row in services.list_students(request.user, request.GET)]})
    scoped_classes(request.user)
    student = services.create_student(request.user, read_json(request, {"student_code", "full_name", "class_id"}))
    return json_response(services.serialize_student(student), 201)


@api_view("GET", "PATCH")
def student_view(request, student_id):
    if request.method == "GET":
        student = services.require_student_profile(request.user, student_id, allow_self=True)
        return json_response(services.serialize_student(student, minimal=request.user.role == Role.STUDENT))
    services.require_student_profile(request.user, student_id)
    student = services.update_student(request.user, student_id, read_json(request, {"full_name", "active", "class_id"}))
    return json_response(services.serialize_student(student))


@api_view("GET", "POST")
def photo_view(request, student_id):
    services.require_student_profile(request.user, student_id)
    if request.method == "GET":
        response = FileResponse(services.open_photo(request.user, student_id), content_type="image/png")
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
    if set(request.POST) or set(request.FILES) != {"photo"} or len(request.FILES.getlist("photo")) != 1:
        raise AccountError("VALIDATION_ERROR", "Submit one photo and no extra fields.", 422)
    student = services.replace_photo(request.user, student_id, request.FILES["photo"])
    return json_response(services.serialize_student(student))
