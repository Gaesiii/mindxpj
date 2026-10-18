from django.urls import path
from school_app.students import views

app_name = "students"
urlpatterns = [
    path("students", views.students_view, name="students"),
    path("students/<uuid:student_id>", views.student_view, name="student"),
    path("students/<uuid:student_id>/photo", views.photo_view, name="photo"),
]
