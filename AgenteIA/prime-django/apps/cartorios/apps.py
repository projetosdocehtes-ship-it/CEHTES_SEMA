"""Configuração da aplicação de Cartórios."""

import contextlib
import logging

from django.apps import AppConfig

from apps.cartorios import signals

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class CartoriosConfig(AppConfig):
    """
    Configuração da aplicação de Cartórios.

    Esta classe define as configurações da aplicação de Cartórios, incluindo o nome, rótulo e o campo de chave primária automática padrão.
    Também registra todos os modelos da aplicação para auditoria usando o pacote auditlog.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cartorios"
    label = "cartorios"
    verbose_name = "Cartórios"

    def ready(self) -> None:
        """
        Método chamado quando a aplicação está pronta.

        Este método é chamado quando a aplicação está pronta para ser usada.
        Ele registra todos os modelos da aplicação para auditoria usando o pacote auditlog.
        Também importa o sinal somente quando os modelos estiverem prontos.
        """
        app_models = self.get_models()
        for model in app_models:
            from auditlog.registry import auditlog

            with contextlib.suppress(Exception):
                auditlog.register(model)

        if signals.SIGNALS_IMPORTED:
            pass
