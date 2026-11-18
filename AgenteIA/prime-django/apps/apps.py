import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class AppsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps"
    label = "apps"
    verbose_name = "Apps"
