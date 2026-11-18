import logging

from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

SIGNALS_IMPORTED = True


@receiver(post_migrate)
def criar_cartorio(sender, **kwargs):
    if sender.name == "apps.cartorios":
        cartorio_model = apps.get_model("cartorios", "Cartorio")

        try:
            cartorio_model.objects.get_or_create_cartorio_padrao()
        except Exception as e:
            logger.info(f"Erro ao criar cartório padrão: {e}")
            raise
