import contextlib

from django.apps import AppConfig


class PedidosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mapeamentos"
    label = "mapeamentos"
    verbose_name = "Mapeamentos"

    def ready(self) -> None:
        # Registra todos os models deste app para auditoria (auditlog)
        from auditlog.registry import auditlog

        app_models = self.get_models()
        for model in app_models:
            with contextlib.suppress(Exception):
                auditlog.register(model)

        # Importa os sinais definidos no arquivo signals.py
        from apps.mapeamentos import signals

        if signals.SIGNALS_IMPORTED:
            pass
