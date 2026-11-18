import json

from django.contrib.auth.models import User
from django.db import models
from django_quill.fields import QuillField

# Create your models here.

ROLE_CHOICES = (
    ("admin", "Admin"),
    ("user", "User"),
)


def avatar_with_id(instance, filename) -> str:
    return f"{instance.user.id}/avatar/{filename}"


def convert_to_quill():
    converted_data = {
        "delta": "",
        "html": "Write something #cool about you.",
    }
    return json.dumps(converted_data)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role: str = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    full_name: str = models.CharField(max_length=255, null=True, blank=True)
    country: str = models.CharField(max_length=255, null=True, blank=True)
    city: str = models.CharField(max_length=255, null=True, blank=True)
    zip_code: str = models.CharField(max_length=255, null=True, blank=True)
    address: str = models.CharField(max_length=255, null=True, blank=True)
    phone: str = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.ImageField(upload_to=avatar_with_id, null=True, blank=True)
    dark_mode: bool = models.BooleanField(default=False)
    bio = QuillField(default=convert_to_quill())

    def __str__(self) -> str:
        return self.user.username
