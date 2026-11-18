import contextlib

from django.apps import apps
from django.contrib import admin

# Register your models here.
app_models = apps.get_app_config("ged").get_models()
for model in app_models:
    with contextlib.suppress(Exception):
        admin.site.register(model)
