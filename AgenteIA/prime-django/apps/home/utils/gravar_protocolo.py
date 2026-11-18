# Configurar logging
import logging
from datetime import timedelta

# import comandos
from django.conf import settings
from django.utils import timezone
from sequences import get_next_value

from apps.home.models import (
    GrupoTipoAndamento,
    Livro01Protocolo,
    Livro05,
    PedidoParte,
)

# Importar os protocolos
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)


def get_data_atual(formato=settings.DATE_FORMAT_STR, qtde_dias=0):
    data_resultante = timezone.now().date() + timedelta(qtde_dias)
    return data_resultante.strftime(formato)


# Gravar o SQL do protocolo
def criar_protocolo(pedido_id, titulo_id, observaco, protocolo_sistema) -> None:
    Livro01Protocolo.criar_protocolo(pedido_id, titulo_id, observaco, protocolo_sistema)


# Grava as partes envolvidas
def criar_pedido_partes(
    pedido_id,
    participacao_nome,
    participacao_cpf_cnpj,
    papel,
) -> None:
    """Insere as partes envolvidas em um pedido."""
    pessoa, criado = Livro05.objects.get_or_create(
        nome=participacao_nome,
        cpf=participacao_cpf_cnpj,
    )

    PedidoParte.objects.create(pedido_id=pedido_id, pessoa=pessoa, papel=papel)


# Selecionar Sequence para o Pedido de Certidao
def selecionar_sequence(desc_sequence):
    return get_next_value(desc_sequence)


# Atualizar o colaborador com codigo vazio


# AJUSTAR A SEQUENCE DO DJANGO PARA O PROXIMO ANDAMENTO


# Verificar se existe o grupo de Andamento para o protocolo - FIREBIRD
def atualizar_andamento_no_firebird(
    pedido_id: int,
    protocolo_id: int,
    colaborador_id: int,
    tipo_andamento_id: int,
    colaborador_encaminhado_id: int,
    db: FbConnection,
) -> None:
    from apps.home.utils.importacao_de_protocolo_firebird import criar_andamento_fb

    colaborador_encaminhado_id = colaborador_encaminhado_id or colaborador_id

    grupo_andamento = GrupoTipoAndamento.objects.filter(
        tipo_andamento_principal_id=tipo_andamento_id,
    ).order_by("ordem")

    if grupo_andamento.exists():
        for andamento in grupo_andamento:
            print(
                f"Gravando andamento '{andamento.tipo_andamento_principal.descricao_servico}' no FIREBIRD:",
                f"tipo_andamento_id: {tipo_andamento_id}",
                f"protocolo_id: {protocolo_id}",
                f"colaborador_id: {colaborador_id}",
                f"colaborador_encaminhado_id: {colaborador_encaminhado_id}",
            )

            # Gravar o Andamento auxiliar do Grupo - Firebird
            if tipo_andamento_id:
                criar_andamento_fb(
                    pedido_id=pedido_id,
                    colaborador_id=colaborador_id,
                    tipo_andamento_id=tipo_andamento_id,
                    colaborador_encaminhado_id=colaborador_encaminhado_id,
                    db=db,
                )
