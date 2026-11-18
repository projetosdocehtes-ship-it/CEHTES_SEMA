import logging

from celery import shared_task

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


@shared_task
def sync_task():
    # Coloque aqui o código que realiza a sincronização
    print("Sincronização executada!")
    # Exemplo de código de sincronização:
    # Sincronizar dados de um API externa, atualizar banco de dados, etc.
