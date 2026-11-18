import logging

from apps.home.models import Configuracao

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def get_mensagens_rodape_recibo():
    linha1 = Configuracao.obter("RODAPE_RECIBO_LINHA01")
    linha2 = Configuracao.obter("RODAPE_RECIBO_LINHA02")
    linha3 = Configuracao.obter("RODAPE_RECIBO_LINHA03")

    return {"linha1": linha1, "linha2": linha2, "linha3": linha3}
