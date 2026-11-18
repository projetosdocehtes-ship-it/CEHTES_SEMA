"""Copyright (c) 2019 - present AppSeed.us."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import include, path

from apps.authentication.views import (
    change_password,
    delete_account,
    login_view,
    register_user,
)

app_name = "authentication"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_user, name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("change_password/", change_password, name="change-password"),
    path("delete_account/", delete_account, name="delete-account"),
    path("social_login/", include("allauth.urls")),
    # Adicione as seguintes URLs para a redefinição de senha
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
