import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Importar os tipos de Andamento do FB para o banco de dados local."

    def handle(self, *args, **kwargs) -> None:
        from apps.home.models import TipoAndamento

        try:
            TipoAndamento.objects.importar_do_fb()
        except Exception as e:
            logger.exception(
                f" Erro ao tentar importar os Tipos de Andamento do FB. {e}",
            )
