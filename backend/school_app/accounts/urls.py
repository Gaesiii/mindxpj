from django.urls import path

from school_app.accounts.views import login_view, logout_view, me_view

app_name = "accounts"
urlpatterns = [
    path("auth/login", login_view, name="login"),
    path("auth/logout", logout_view, name="logout"),
    path("auth/me", me_view, name="me"),
]
