import logging

from import_export import resources

from apps.home.models import Livro01Andamento

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class AndamentosResource(resources.ModelResource):
    class Meta:
        model = Livro01Andamento
