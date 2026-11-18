"""Copyright (c) 2019 - present AppSeed.us."""

from django.urls import path, re_path

from apps.samples import views

urlpatterns = [
    # The samples page
    path("", views.index, name="samples"),
    # Matches any html file
    # re_path(r"^.*\.*", views.pages, name="pages"),
    re_path(r"^.+\.html$", views.pages, name="pages"),
]
