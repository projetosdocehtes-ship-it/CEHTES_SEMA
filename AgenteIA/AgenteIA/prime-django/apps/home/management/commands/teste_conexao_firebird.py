import logging

import firebirdsql
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options) -> None:
        try:
            conn = firebirdsql.connect(
                host="192.168.1.196",
                database="D:\\---\\DB\\RICS.gdb",
                port=3050,
                user="SYSDBA",
                password="CONFIGURAR_LOCALMENTE",
                charset="ISO8859_1",
            )
            print("Conexão bem-sucedida!")
            conn.close()
        except Exception as e:
            logger.info(f"Erro ao conectar ao banco de dados: {e}")
