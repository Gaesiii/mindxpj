"""MVP API routes; no frontend or public private-media routes."""
from django.urls import include, path
from school_app.demo_ui.views import index

urlpatterns = [path("api/v1/", include("school_app.accounts.urls")),
               path("api/v1/", include("school_app.academics.urls")),
               path("api/v1/", include("school_app.schedules.urls")),
               path("api/v1/", include("school_app.reports.urls")),
               path("api/v1/", include("school_app.students.urls")),
               path("api/v1/", include("school_app.attendance.urls")),
               path("api/v1/", include("school_app.qr.urls")),
               path("api/v1/", include("school_app.vision.urls"))]
urlpatterns += [path('',index,name='demo-ui')]
handler400 = "school_app.core.errors.bad_request"
handler403 = "school_app.core.errors.permission_denied"
handler404 = "school_app.core.errors.not_found"
handler500 = "school_app.core.errors.server_error"
