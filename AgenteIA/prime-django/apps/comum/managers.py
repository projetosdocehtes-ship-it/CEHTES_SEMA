import logging

from django.db import models

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class TipoRegistroImobiliarioManager(models.Manager):
    def criar_defaults(self) -> None:
        self.update_or_create(id=1, defaults={"nome": "Matrícula"})
        self.update_or_create(id=2, defaults={"nome": "Transcrição"})
        self.update_or_create(id=3, defaults={"nome": "Inscrição"})
        self.update_or_create(id=4, defaults={"nome": "Registro Auxiliar"})

        logger.info("Tipos de Registro Imobiliario adicionados!")
