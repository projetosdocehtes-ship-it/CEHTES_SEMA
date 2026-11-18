import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.cartorios.models import Usuario as User
from apps.home.models import (
    AtoPratica,
    EmolumentoAno,
    Emolumentos,
    EmolumentoValor,
    EstadoCivil,
    FaseAgenda,
    Livro03Descricao,
    Livro05,
    RegistroVinculado,
    StatusProtocolo,
    TipoAndamento,
    TipoFaseProtocolo,
    TipoLogradouro,
    TipoRegistroAuxiliar,
    TipoTributacao,
    TipoVinculo,
    Titulo,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


# Classe do comando
@transaction.atomic
class Command(BaseCommand):
    help = "Importa as tabelas basicas do FB"

    # Método que será executado ao rodar o comando
    def handle(self, *args, **kwargs) -> None:
        from apps.comum.models import TipoRegistroImobiliario
        from apps.home.models import Livro02, Lote, TipoRegimeCasamento, Unidade

        logger.info("Importanto tabelas basicas do FB: ************************ ")

        with transaction.atomic():
            TipoLogradouro.objects.importar_do_fb()

            TipoVinculo.objects.importar_do_fb()

            Livro03Descricao.objects.importar_do_fb()

            TipoRegistroImobiliario.objects.criar_defaults()

            Livro02.objects.criar_defaults()

            Livro05.objects.criar_defaults()

            Unidade.objects.criar_defaults()

            Lote.objects.criar_defaults()

            TipoRegimeCasamento.objects.criar_defaults()

            RegistroVinculado.objects.importar_do_fb()

            TipoRegistroAuxiliar.objects.importar_do_fb()

            AtoPratica.objects.importar_do_fb()

            EstadoCivil.objects.importar_do_fb()

            Titulo.objects.importar_do_fb()

            User.objects.importar_do_fb()

            StatusProtocolo.objects.criar_defaults()

            TipoFaseProtocolo.objects.criar_defaults()

            EmolumentoAno.objects.importar_do_fb()

            Emolumentos.objects.importar_do_fb()

            EmolumentoValor.objects.importar_do_fb()

            FaseAgenda.objects.criar_defaults()

            TipoAndamento.objects.criar_defaults()

            TipoTributacao.objects.importar_do_fb()
