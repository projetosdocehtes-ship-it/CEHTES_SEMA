import logging
from venv import logger

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


# Classe do comando
class Command(BaseCommand):
    help = "Importar os tipos de certidões do FB para o banco de dados local."

    # Método que será executado ao rodar o comando
    def handle(self, *args, **kwargs) -> None:
        # Loop para criar ou atualizar as pessoas
        try:
            from apps.home import models

            models.TipoCertidao.objects.importar_tipos_certidao_fb()
        except Exception as e:
            logger.exception(
                f" Erro ao tentar importar os tipos de certidões do FB. {e!s}",
            )
