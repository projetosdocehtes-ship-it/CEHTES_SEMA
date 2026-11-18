"""Copyright (c) 2019 - present AppSeed.us."""

from django.urls import path

from apps.accounts.views import profile, user_list

app_name = "accounts"

urlpatterns = [
    path("user_list/", user_list),
    path("user/<str:username>/", user_list),
    path("user_profile/", profile),
]
