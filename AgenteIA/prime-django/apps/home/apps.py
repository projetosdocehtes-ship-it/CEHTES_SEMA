import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.home"
    label = "home"
    verbose_name = "Home"

    def ready(self) -> None:
        # app_models = self.get_models()
        # for model in app_models:
        #     with contextlib.suppress(Exception):
        #         auditlog.register(model)

        import apps.home.auditlog  # noqa: F401
        from apps.home import receivers  # noqa: F401
        from apps.home.signals import (
            signals_migrate,  # noqa: F401
            signals_save,  # noqa: F401
        )


class FotovoltaicoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fotovoltaico"
    verbose_name = "Agente Fotovoltaico"
