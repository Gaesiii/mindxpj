from django.urls import path
from . import views
from . import uniform_views

urlpatterns = [
    path('classes/<uuid:classroom_id>/uniform-profile',uniform_views.uniform_profile),
    path('classes/<uuid:classroom_id>/uniform-samples',uniform_views.uniform_samples),
    path('uniform-samples/<uuid:sample_id>/image',uniform_views.uniform_sample_image),
    path('classes/<uuid:classroom_id>/uniform-dataset-export',uniform_views.uniform_dataset_export),
    path('sessions/<uuid:session_id>/auto-attendance-scans',views.auto_scans),
    path('students/<uuid:student_id>/face-samples',views.samples),
    path('sessions/<uuid:session_id>/vision-scans',views.scans),
    path('vision-scans/<uuid:scan_id>/confirm',views.confirm),
    path('vision-scans/<uuid:scan_id>/reject',views.reject),
]
