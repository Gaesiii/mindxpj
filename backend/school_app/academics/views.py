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
    classroom = services.save_class(request.user, read_json(request, {"code", "name", "grade_id", "teacher_id", "capacity", "active"}))
    return json_response(services.serialize_class(classroom), 201)


@api_view("GET", "PATCH", "DELETE")
def class_view(request, class_id):
    classroom = services.require_class(request.user, class_id)
    if request.method == "GET":
        return json_response(services.serialize_class(classroom))
    services.supervisor_user(request.user)
    if request.method == "DELETE":
        classroom = services.archive_class(request.user,classroom,read_json(request,{"expected_version"}))
    else:
        classroom = services.save_class(request.user,read_json(request,
            {"code","name","grade_id","teacher_id","capacity","active","expected_version"}),classroom)
    return json_response(services.serialize_class(classroom))


@api_view("GET")
def teachers_view(request):
    from django.contrib.auth import get_user_model
    from school_app.core.enums import Role
    services.supervisor_user(request.user)
    teachers = get_user_model().objects.filter(role=Role.HOMEROOM_TEACHER,is_active=True).order_by("username")
    return json_response({"items":[{"id":str(row.pk),"username":row.username,
        "full_name":row.get_full_name()} for row in teachers]})
