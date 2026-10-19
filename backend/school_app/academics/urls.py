from django.urls import path
from school_app.academics import views

app_name = "academics"
urlpatterns = [
    path("teachers", views.teachers_view, name="teachers"),
    path("grades", views.grades_view, name="grades"),
    path("classes", views.classes_view, name="classes"),
    path("classes/<uuid:class_id>", views.class_view, name="class"),
]
