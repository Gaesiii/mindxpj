from django.urls import path
from school_app.reports import views

urlpatterns = [
    path('reports/attendance', views.attendance_report, name='report-attendance'),
    path('reports/summary', views.summary_report, name='report-summary'),
    path('reports/export', views.export_report, name='report-export'),
]
