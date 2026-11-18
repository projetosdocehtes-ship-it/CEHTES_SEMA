import contextlib
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class PedidosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pedidos"
    label = "pedidos"
    verbose_name = "Pedidos"

    def ready(self) -> None:
        # Registra todos os models deste app para auditoria (auditlog)
        from auditlog.registry import auditlog

        app_models = self.get_models()
        for model in app_models:
            with contextlib.suppress(Exception):
                auditlog.register(model)

        # Importa os sinais definidos no arquivo signals.py
        from apps.pedidos import signals

        if signals.SIGNALS_IMPORTED:
            pass
