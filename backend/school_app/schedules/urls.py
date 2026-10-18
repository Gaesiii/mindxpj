from django.urls import path
from . import views
urlpatterns=[path('classes/<uuid:class_id>/schedule-rules',views.rules),path('schedule-rules/<uuid:rule_id>',views.rule_detail),path('sessions',views.sessions),path('sessions/<uuid:session_id>',views.session_detail),path('sessions/<uuid:session_id>/open',views.session_open),path('sessions/<uuid:session_id>/close',views.session_close),path('sessions/<uuid:session_id>/roster',views.roster)]
