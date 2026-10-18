from django.urls import path
from . import views
urlpatterns=[path('attendance/<uuid:attendance_id>',views.attendance),path('attendance/<uuid:attendance_id>/uniform',views.uniform)]
