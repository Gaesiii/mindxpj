from school_app.academics import services
from school_app.core.api import api_view, json_response, read_json


@api_view("GET", "POST")
def grades_view(request):
    if request.method == "GET":
        return json_response({"items": [services.serialize_grade(row) for row in services.list_grades(request.user)]})
    services.supervisor_user(request.user)
    grade = services.create_grade(request.user, read_json(request, {"code", "name"}))
    return json_response(services.serialize_grade(grade), 201)


@api_view("GET", "POST")
def classes_view(request):
    if request.method == "GET":
        return json_response({"items": [services.serialize_class(row) for row in services.scoped_classes(request.user)]})
    services.supervisor_user(request.user)
    classroom = services.save_class(request.user, read_json(request, {"code", "name", "grade_id", "teacher_id"}))
    return json_response(services.serialize_class(classroom), 201)


@api_view("PATCH")
def class_view(request, class_id):
    services.supervisor_user(request.user)
    classroom = services.require_class(request.user, class_id)
    classroom = services.save_class(request.user, read_json(request, {"code", "name", "grade_id", "teacher_id"}), classroom)
    return json_response(services.serialize_class(classroom))
