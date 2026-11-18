import os
from datetime import datetime
from venv import logger

from django.core.management.base import BaseCommand

from apps.home.models import models_home as models

path_dir = os.path.split(os.path.abspath(__file__))[0]
MIN_DATE = datetime.min.date()


# Classe do comando
class Command(BaseCommand):
    help = "Importar os usuarioa do FB para o banco de dados local."

    # Método que será executado ao rodar o comando
    def handle(self, *args, **kwargs) -> None:
        # Loop para criar ou atualizar as pessoas
        try:
            models.Colaborador.objects.importar_do_fb()
        except Exception as e:
            logger.exception(
                f" Erro ao tentar importar os tipos de certidões do FB. {e!s}",
            )
