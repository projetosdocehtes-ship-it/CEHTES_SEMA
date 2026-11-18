import logging
import os

from django.core.files import File
from django.dispatch import receiver

from apps.home.models import LogAssinaturaDigital
from apps.home.signals import documento_assinado_signal

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

RECEIVERS_IMPORTED = True


@receiver(documento_assinado_signal)
def registrar_log_assinatura(sender, **kwargs) -> None:
    fname = kwargs.get("documento")
    usuario = kwargs.get("usuario")
    certificado = kwargs.get("certificado")

    # Abre o arquivo no modo 'rb' para criar um objeto File do Django
    with open(fname, "rb") as f:
        documento_django = File(f)

        # Cria um registro no modelo LogAssinaturaDigital, passando o objeto File para o campo de arquivo
        log = LogAssinaturaDigital(
            usuario=usuario,
            certificado=certificado,
            motivo=certificado.motivo_uso,
        )
        log.documento.save(os.path.basename(fname), documento_django, save=True)
