# app.py
"""Copyright (c) 2019 - present AppSeed.us."""

from django.apps import AppConfig
from django.db import connection


class AccountsConfig(AppConfig):
    name = "apps.accounts"

    def ready(self) -> None:
        # Verifica o tipo de banco de dados
        if connection.vendor == "postgresql":
            self.default_auto_field = "django.db.models.BigAutoField"
        elif connection.vendor == "sqlite":
            self.default_auto_field = "django.db.models.AutoField"
        # Inclua mais condições se suportar outros bancos de dados
