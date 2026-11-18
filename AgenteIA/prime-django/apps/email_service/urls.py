# email_service/urls.py
from django.urls import path

from apps.email_service import views

urlpatterns = [
    path("send_email/", views.send_email, name="send_email"),
]
