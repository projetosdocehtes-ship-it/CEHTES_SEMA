import logging

from django.conf import settings

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def cfg_assets_root(request):
    return {"ASSETS_ROOT": settings.ASSETS_ROOT}
