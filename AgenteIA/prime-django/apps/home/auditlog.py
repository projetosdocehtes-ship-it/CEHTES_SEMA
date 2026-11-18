import logging

# auditlog.py
from auditlog.registry import auditlog

from apps.home.models import Financeiro, PedidoCertidao

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

# Registre os modelos para auditlog
auditlog.register(Financeiro)
auditlog.register(PedidoCertidao)
