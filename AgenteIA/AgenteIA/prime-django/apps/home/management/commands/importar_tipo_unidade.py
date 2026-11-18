import logging

from django.core.management.base import BaseCommand

from apps.home.models import TipoUnidade

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Importar os tipos de tributacao do FB para o banco de dados local."

    def handle(self, *args, **kwargs) -> None:
        try:
            TipoUnidade.objects.importar_do_fb()
        except Exception as e:
            logger.exception(
                f"Erro ao tentar importar os tipos de tributacao do FB. {e}",
            )
