from django.urls import path
from . import views

urlpatterns = [
    path('students/<uuid:student_id>/face-samples',views.samples),
    path('sessions/<uuid:session_id>/vision-scans',views.scans),
    path('vision-scans/<uuid:scan_id>/confirm',views.confirm),
    path('vision-scans/<uuid:scan_id>/reject',views.reject),
]
