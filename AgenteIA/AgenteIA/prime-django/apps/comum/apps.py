import contextlib
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class ComumConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comum"
    label = "comum"
    verbose_name = "Comum"

    def ready(self) -> None:
        # Registra todos os models deste app para auditoria (auditlog)
        from auditlog.registry import auditlog

        app_models = self.get_models()
        for model in app_models:
            with contextlib.suppress(Exception):
                auditlog.register(model)
