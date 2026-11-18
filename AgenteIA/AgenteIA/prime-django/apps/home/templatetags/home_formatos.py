import decimal
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import markdown as md
import phonenumbers
from django import template
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db.models import Max, Q, Sum
from django.template.defaultfilters import stringfilter
from django.utils import timezone

from apps.comum.utils import formatar_moeda
from apps.home.helpers import (
    decimal_ou_zero,
    formatar_numero_registro,
    formatar_protocolo,
    get_data_util_em_x_dias,
)
from apps.home.models import (
    Event,
    FichaAuxiliar,
    Financeiro,
    Lembrete,
    Livro01Protocolo,
    Livro02,
    Livro02Texto,
    Livro03,
    Livro03Garantia,
    Livro03Ligacao,
    Livro05,
    Lote,
    NivelAlerta,
    Pedido,
    PedidoCertidao,
    PedidoItem,
    PedidoParteAto,
    Rua,
    Rural,
    RuralNome,
    SeloEletronico,
    TipoAndamento,
    TipoRegimeCasamento,
    TipoRegistroProtocolo,
    TipoTributacao,
    Unidade,
    User,
    Vinculo,
    get_ruas,
)
from apps.home.tipos import TipoEvento, TipoParte
from core.utils.formatacoes import (
    formatar_documento,
    formatar_nome,
    formatar_valor_real_br,
    somente_numeros,
)

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

register = template.Library()

MONTHS = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]


# Retornar a data por extenso e outros formatos
@register.filter
def formatar_data_hora(data):
    if not data:
        return ""
    else:
        return data.strftime(settings.DATE_FORMAT_STR)


# Retornar a data por extenso e outros formatos
@register.filter(name="formatar_data")
def formatar_data(data, opcao=1):
    from apps.home.utils import formatar_data

    return formatar_data(data, opcao)


@register.filter
@stringfilter
def formatar_sim_nao(value) -> str:
    # Converte o valor para string para garantir compatibilidade com diferentes tipos de entrada
    value_str = str(value).lower().strip()
    # Define os valores que correspondem a "sim"
    sim_values = ["true", "1", "sim", "s", "yes", "y"]
    # Define os valores que correspondem a "não"
    nao_values = ["false", "0", "não", "n", "no"]

    if value_str in sim_values:
        return "Sim"
    elif value_str in nao_values or value_str == "":
        return "Não"
    else:
        # Trata casos onde o valor não é reconhecido especificamente como "sim" ou "não"
        # Pode-se optar por logar um erro ou simplesmente retornar uma string vazia
        return ""


# Retornar os dados do imovel lote
@register.filter
@stringfilter
def formatar_situacao(value) -> str | None:
    try:
        if value == "T":
            return " (*) "
        else:
            return ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar o tipo_registro
@register.filter
def tipo_registro(value):
    if not value:
        return ""
    try:
        pedido_item = PedidoItem.objects.filter(pk=value).first()
    except PedidoItem.DoesNotExist:
        return ""

    return pedido_item.tipo_registro if pedido_item.tipo_registro else ""


# Retornar os dados da PESSOA - Nome
@register.filter
@stringfilter
def get_nome_da_pessoa_pelo_id(pessoa_id) -> str:
    if pessoa_id:
        try:
            return Livro05.objects.get(id=pessoa_id).nome or ""
        except Livro05.DoesNotExist:
            return ""
    return ""


# Retornar os dados das PARTES DO ATO
@register.filter
@stringfilter
def get_partes_do_pedido(pedido_item_id):
    pedido_partes = (
        PedidoParteAto.objects.filter(pedido_item_id=pedido_item_id)
        if pedido_item_id
        else None
    )

    return pedido_partes if pedido_partes else ""


@register.filter
@stringfilter
def exibir_pedidos_partes_ato_02(pedido_item_id):
    """Exibe uma string formatada com informações sobre pedidos e partes de um ato."""
    descricao_pedidos_partes_ato = ""

    try:
        pedido_items_partes_ato = (
            PedidoParteAto.objects.filter(pedido_item_id=pedido_item_id)
            .select_related("vinculos", "pessoa")
            .first()
        )

        if pedido_items_partes_ato and pedido_items_partes_ato.vinculos:
            tipo_ato = pedido_items_partes_ato.vinculos.tipo_ato
            numero_ato = str(pedido_items_partes_ato.vinculos.numero_ato).split(".")[0]
            area_pecentual = str(
                pedido_items_partes_ato.vinculos.area_pecentual,
            ).replace(".", ",")
            documento_formatado = pedido_items_partes_ato.pessoa.documento_formatado
            nome_pessoa = pedido_items_partes_ato.pessoa.nome

            descricao_pedidos_partes_ato = f"{tipo_ato}.{numero_ato} {area_pecentual} {documento_formatado} {nome_pessoa}"

    except Exception:
        logger.exception("ERRO")

    return descricao_pedidos_partes_ato


# Retornar os dados dos itens do pedido
@register.filter
@stringfilter
def get_total_valor_emolumento_do_item(pedido_item_id):
    pedido_id = get_pedido_id(pedido_item_id)

    try:
        # Valor total dos emolumentos do protocolo
        resultado = PedidoItem.objects.filter(pedido=pedido_id).aggregate(
            Sum("valor_emolumento"),
        )
        return resultado["valor_emolumento__sum"]

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados dos itens do pedido
@register.filter
@stringfilter
def get_total_tfj(pedido_item_id):
    pedido_id = get_pedido_id(pedido_item_id)

    try:
        # Valor total do TFJ do protocolo
        valor_total_tfj = PedidoItem.objects.filter(pedido=pedido_id).aggregate(
            Sum("valor_tfj"),
        )
        return valor_total_tfj["valor_tfj__sum"]

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados dos itens do pedido
@register.filter
@stringfilter
def get_total_issqn(pedido_item_id):
    pedido_id = get_pedido_id(pedido_item_id)

    try:
        # Valor total do ISSQN do protocolo
        valor_total_issqn = PedidoItem.objects.filter(pedido=pedido_id).aggregate(
            Sum("issqn"),
        )
        return valor_total_issqn["issqn__sum"]

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados dos itens do pedido
@register.filter
@stringfilter
def get_valor_total_recompe_do_item_do_protocolo(pedido_item_id) -> Decimal:
    pedido_id = get_pedido_id(pedido_item_id)

    try:
        # Valor total do ISSQN do protocolo
        valor_total_recompe = PedidoItem.objects.filter(Q(pedido=pedido_id)).aggregate(
            Sum("issqn"),
        )
        return valor_total_recompe["issqn__sum"]

    except Exception:
        logger.exception("ERRO")
        return decimal_ou_zero()


# Retornar os dados dos itens do pedido
@register.filter
def get_total_do_protocolo(pedido_item_id) -> Decimal:
    pedido_id = get_pedido_id(pedido_item_id)

    try:
        # Valor total do protocolo
        valor_total_protocolo = PedidoItem.objects.filter(
            pedido_id=pedido_id,
        ).aggregate(
            Sum("valor_total"),
        )
        return valor_total_protocolo["valor_total__sum"]

    except Exception:
        logger.exception("ERRO")
        return decimal_ou_zero()


# Retornar os dados dos itens do pedido
@register.filter
@stringfilter
def get_total_no_caixa(pedido_item_id: int) -> Decimal:
    pedido_id = get_pedido_id(pedido_item_id)

    try:
        # Valor total caixa
        valor_total_caixa = Financeiro.objects.filter(pedido=pedido_id).aggregate(
            Sum("valor_transacao"),
        )
        return valor_total_caixa["valor_pago__sum"]

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados dos itens do pedido
@register.filter
def get_diferenca_do_caixa(pedido_item_id: int) -> Decimal:
    try:
        valor_total_protocolo = get_total_do_protocolo(pedido_item_id)
        valor_total_caixa = get_total_no_caixa(pedido_item_id)

        return valor_total_protocolo - valor_total_caixa
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados dos itens do pedido
@register.filter
@stringfilter
def get_pedidos_itens(pedido_item_id):
    pedido_id = get_pedido_id(pedido_item_id)

    try:
        # Filtrando o PEDIDO ITEM
        return list(
            PedidoItem.objects.filter(pedido=pedido_id)
            .values_list(
                "pk",
                "ato",
                "codigo_tabela",
                "valor_itbi",
                "tipo_registro",
                "numero_registro",
                "numero_ato",
                "cdhu",
                "custas",
                "valor_total",
            )
            .order_by("pk"),
        )

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados do numero do ato
@register.filter
@stringfilter
def exibir_numero_vinculos_protocolo(numero_registro, tipo_registro, numero_ri):
    from apps.home.utils.importacao_de_protocolo_firebird import (
        get_ultimo_numero_ato_fb,
    )

    try:
        # Filtrando o PEDIDO ITEM
        lista_numero_ato = [
            pedido_item.numero_ato
            for pedido_item in PedidoItem.objects.filter(
                numero_registro=numero_registro,
                tipo_registro=tipo_registro,
                numero_ri=numero_ri,
            )
        ]
        # Filtrar apenas os numeros inteiros
        lista_numero_ato_inteiro = [apenas_numeros(item) for item in lista_numero_ato]

        # Maior Numero POSTEGRESQL
        try:
            numero_ato_inteiro = max(lista_numero_ato_inteiro)
        except Exception:
            logger.exception("ERRO")
            numero_ato_inteiro = 0

        # NUMERO VAZIO
        if str(numero_ato_inteiro) == "":
            numero_ato_inteiro = 0

        # Obter o numero do ato

        numero_ato_inteiro_firebird = (
            get_ultimo_numero_ato_fb(
                numero_registro=numero_registro,
                tipo_registro=tipo_registro,
                numero_ri=numero_ri,
            )
            or 0
        )

        # VERIFICA SE O NUMERO E MAIOR QUE O POSTGRESQL
        if int(numero_ato_inteiro_firebird) > int(numero_ato_inteiro):
            numero_ato_inteiro = numero_ato_inteiro_firebird

        return numero_ato_inteiro
    except Exception:
        logger.exception("ERRO")
        return 0


# Retornar os dados do imovel lote
@register.filter
@stringfilter
def get_vinculos_livro02(pedido_item_id):
    try:
        # Filtrando o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        imovel_id = pedido_item.imovel.pk or 0

        return Vinculo.objects.get_lista_proprietarios_do_imovel(imovel_id)

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados do proprietario
@register.simple_tag
def get_vinculos_de_proprietarios_atuais_com_percentual(
    value,
    imovel_id: int,
    as_var=None,
) -> list:
    try:
        # Proprietarios Atuais
        vinculos_de_propriedade = Vinculo.objects.get_vinculos_de_proprietarios_atuais(
            imovel_id,
        )

        # Proprietarios Atuais
        retornos = []
        percentual_total = 0

        # Filtrando os vinculos - PROPRIETARIO
        for vinculo in vinculos_de_propriedade:
            percentual_total += vinculo.percentual

            # Filtrando o nome das pessoas
            retornos.append(
                [
                    vinculo.numero_ato_formatado,
                    vinculo.percentual_formatado,
                    vinculo.pessoa.documento_formatado,
                    vinculo.pessoa.nome,
                    percentual_total,
                    vinculo.pessoa_id,
                ],
            )

        return retornos
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar da hipoteca
@register.filter
@stringfilter
def get_hipotecas_por_pedido_item(pedido_item_id):
    try:
        # Filtrando o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        hipotecas = pedido_item.imovel.hipotecas

        # Hipotecas Atuais
        hipotecas_atuais = []

        # Filtrando os vinculos HIPOTECA
        ordem_penhor = 0
        nro_ato_atual = ""

        percentual_hipoteca_atual = 0
        # Filtrando os vinculos - HIPOTECAS
        for hipoteca in hipotecas:
            pessoa = hipoteca.pessoa

            # Formatar o percentual
            try:
                percentual_hipoteca_atual += hipoteca.percentual
            except Exception:
                logger.exception("ERRO")
                percentual_hipoteca_atual = 0

            numero_ato_formatado = (
                str(hipoteca.tipo_ato) + "." + str(hipoteca.numero_ato)
            )
            nome = str(pessoa[0].nome)
            cpf = str(formatar_documento(pessoa[0].cpf))
            percentual = (
                "(" + str(percentual_hipoteca_atual).replace(".", ",") + "%" + ")"
            )

            # Se mudar o numero do ato a ordem do penhor e acrescida de 1
            if str(nro_ato_atual) != str(hipoteca.numero_ato):
                nro_ato_atual = str(hipoteca.numero_ato)
                ordem_penhor = int(ordem_penhor) + 1

            grau_penhor = "(Grau: " + str(ordem_penhor) + ")"

            # Filtrando o nome das pessoas
            hipotecas_atuais.append(
                [numero_ato_formatado, grau_penhor, cpf, nome, percentual],
            )

        return hipotecas_atuais
    except Exception:
        logger.exception("ERRO")
        return None


# Retornar os lembretes imovel
@register.simple_tag
def get_lembretes_do_registro(value, imovel_id: int, as_var=None) -> list:
    try:
        # Hipotecas Atuais
        lembretes = Lembrete.objects.filter(imovel_id=imovel_id).order_by("id")

        return [
            [
                lembrete.id,
                lembrete.imovel,
                lembrete.created_at,
                lembrete.updated_at,
                lembrete.descricao,
                lembrete.funcionarios_create_id,
                lembrete.funcionarios_update_id,
                lembrete.nivel_alerta_id,
            ]
            for lembrete in lembretes
        ]

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar da hipoteca
@register.simple_tag
def get_hipotecas_por_imovel(value, imovel_id: int, as_var=None) -> list:
    try:
        # Hipotecas Atuais
        hipotecas = Vinculo.objects.get_hipotecas_do_imovel(imovel_id)

        # Hipotecas Atuais
        hipotecas_atuais = []

        # Filtrando os vinculos HIPOTECA
        ordem_penhor = 0
        nro_ato_atual = ""

        # Filtrando os vinculos - HIPOTECAS
        for hipoteca in hipotecas:
            # Se mudar o numero do ato a ordem do penhor e acrescida de 1
            if str(nro_ato_atual) != str(hipoteca.numero_ato):
                nro_ato_atual = str(hipoteca.numero_ato)
                ordem_penhor = int(ordem_penhor) + 1

            grau_penhor = "(Grau: " + str(ordem_penhor) + ")"

            # Filtrando o nome das pessoas
            hipotecas_atuais.append(
                [
                    hipoteca.numero_ato_formatado,
                    grau_penhor,
                    hipoteca.pessoa.documento_formatado,
                    hipoteca.pessoa.nome,
                    hipoteca.percentual_formatado,
                    hipoteca.pessoa.id,
                ],
            )

        return hipotecas_atuais
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar da Alienacao
@register.filter
@stringfilter
def get_alienacoes_por_pedido_item(pedido_item_id: int) -> list:
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        alienacoes = pedido_item.imovel.alienacoes

        return [
            [
                alienacao.numero_ato_formatado,
                None,
                alienacao.pessoa.documento_formatado,
                alienacao.pessoa.nome,
                None,
            ]
            for alienacao in alienacoes
        ]

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar da Alienacao
@register.simple_tag
def filtrar_alienacoes_do_imovel(value, imovel_id: int, as_var=None) -> list:
    try:
        alienacoes = Vinculo.objects.filtrar_alienacoes_do_imovel(imovel_id)

        # Filtrando os vinculos - HIPOTECAS
        return [
            [
                alienacao.numero_ato_formatado,
                None,
                alienacao.pessoa.documento_formatado,
                alienacao.pessoa.nome,
                None,
                alienacao.pessoa.id,
            ]
            for alienacao in alienacoes
        ]

    except Exception:
        logger.exception("ERRO")
        return None


# Retornar da Livro 3 Vinculados
@register.filter
def get_livro03_por_pedido_item(pedido_item_id: int) -> list:
    """
    Busca os dados associados ao LIVRO 03 para um pedido específico.

    Args:
    ----
        pedido_item_id (int): Chave identificadora do pedido de itens.

    Returns:
    -------
        list: Lista contendo os dados associados ao LIVRO 03.
        str: String vazia em caso de erro.

    """
    try:
        # Filtrando o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        # Filtrando o IMOVEL
        # imovel = Livro02.objects.get(
        #     numero=pedido_item.numero_registro,
        #     tipo=pedido_item.tipo_registro,
        #     cartorio=pedido_item.numero_ri,
        # )

        # Obtendo garantias vinculadas ao imóvel
        garantias = pedido_item.garantias

        # Coletando os dados das garantias
        registros_garantia = []
        for garantia in garantias:
            registro_auxiliar = garantia.registro_auxiliar

            envolvidos = [
                [
                    envolvido.pessoa.nome,
                    envolvido.pessoa.cpf,
                    envolvido.figuras.tipo_figura,
                ]
                for envolvido in Livro03Ligacao.objects.filter(
                    registro_auxiliar_id=garantia.registro_auxiliar,
                )
            ]

            registros_garantia.append(
                [
                    registro_auxiliar.numero_registro_formatado,
                    registro_auxiliar.tipo_registro_auxiliar.nome,
                    registro_auxiliar.numero_cedula,
                    garantia.grau_penhor,
                    formatar_data(registro_auxiliar.data_abertura, 1),
                    formatar_data(registro_auxiliar.cancelado_em, 1),
                    formatar_data(registro_auxiliar.data_vencimento, 1),
                    registro_auxiliar.descricao,
                    garantia.area,
                    envolvidos,
                ],
            )

        return registros_garantia

    except Exception:
        logger.exception("ERRO")
        return ""


@register.simple_tag
def get_id_livro03_por_numero(numero_registro):
    try:
        numero_registro = str(numero_registro).split(".")[0]

        livro03 = Livro03.objects.get(numero=numero_registro)
    except Exception:
        logger.exception("ERRO")

    return livro03.pk


# Retornar da Livro 3 Vinculados
# Buscar Nome Rua pelo ID IMOVEL
@register.simple_tag
def get_detalhes_livro03_por_numero(numero_registro: int) -> list:
    """
    Busca os detalhes do LIVRO 03 com base no número fornecido.

    Args:
    ----
        numero_registro (str): Número do imóvel para busca.

    Returns:
    -------
        list: Lista contendo os detalhes do LIVRO 03 para o número fornecido.
        str: String vazia em caso de erro.

    """
    try:
        registro_auxiliar = Livro03.objects.get(numero=numero_registro)

        ligacoes = Livro03Ligacao.objects.filter(
            registro_auxiliar_id=registro_auxiliar.id,
        )
        envolvidos = [
            [
                ligacao.pessoa.nome,
                ligacao.pessoa.cpf,
                ligacao.figuras.tipo_figura,
            ]
            for ligacao in ligacoes
        ]

        qtde_credor = sum(
            1 for ligacao in ligacoes if ligacao.figuras.tipo_figura == "Credor"
        )
        qtde_devedor = sum(
            1 for ligacao in ligacoes if ligacao.figuras.tipo_figura == "Devedor"
        )
        qtde_avalistas = sum(
            1 for ligacao in ligacoes if ligacao.figuras.tipo_figura == "Avalista"
        )

        garantias = Livro03Garantia.objects.filter(
            registro_auxiliar_id=registro_auxiliar.id,
        )
        detalhes_garantias = [
            [
                garantia.especie,
                garantia.numero,
                garantia.descricao,
                garantia.grau_penhor,
                garantia.tipo_registro,
                garantia.numero_registro,
                garantia.valor,
                garantia.fazenda,
                garantia.tipo_ato,
                garantia.area,
                garantia.quantidade,
                garantia.imovel_vinculado.descricao,
            ]
            for garantia in garantias
        ]

        return [
            [
                formatar_numero_registro(registro_auxiliar.numero),
                registro_auxiliar.tipo_registro_auxiliar.nome,
                registro_auxiliar.numero_cedula,
                "",
                formatar_data(registro_auxiliar.data_abertura, 1),
                formatar_data(registro_auxiliar.cancelado_em, 1),
                formatar_data(registro_auxiliar.data_vencimento, 1),
                registro_auxiliar.descricao,
                "",
                envolvidos,
                detalhes_garantias,
                qtde_credor,
                qtde_devedor,
                qtde_avalistas,
                ligacoes.count(),
                garantias.count(),
                registro_auxiliar.cnm,
            ],
        ]
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados dos proprietarios
@register.filter
def get_proprietarios_atuais_separados_por_virgula(pedido_item_id):
    """
    Obtém os proprietários atuais do imóvel com base na chave fornecida.

    :param pedido_item_id: Chave para identificar os itens de pedidos.
    :return: Uma string com os nomes dos proprietários atuais ou string vazia em caso de erro.
    """
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        # Proprietarios Atuais separados por vírgula
        return ",".join(
            vinculo.pessoa.nome
            for vinculo in pedido_item.imovel.vinculos_de_proprietarios_atuais
        )
    except Exception as e:
        logger.exception(f"ERRO ao obter proprietário atual: {e!s}")
        return ""


# Retornar a descricao do origem_evento
@register.filter
@stringfilter
def origem_evento(value):
    return TipoEvento.get_descricao(value)


# Retornar a descricao do imovel
@register.filter
@stringfilter
def get_descricao_tipo_registro(value):
    return Livro02.get_descricao_tipo_registro(value)


# Retornar a descricao do imovel
@register.filter
@stringfilter
def descricao_tipo_livro(value):
    try:
        tipo_livro = {
            "M": "Livro 02",
            "T": "Transcrição",
            "I": "Inscrição",
            "A": "Livro 03",
        }
        return tipo_livro.get(value, "")
    except Exception:
        logger.exception("ERRO")
        return ""


@register.filter("formatar_numero_registro")
@stringfilter
def formatar_numero_registro_filter(numero_registro):
    return formatar_numero_registro(numero_registro)


@register.filter("formatar_numero_registro_inteiro")
@stringfilter
def formatar_numero_registro_inteiro(numero_registro):
    if not numero_registro:
        return ""

    if len(numero_registro) <= 3:
        return numero_registro

    return numero_registro[:-3] + "." + numero_registro[-3:]


# Retornar o sexo da pessoa
@register.filter
@stringfilter
def lista_sexo(value):
    return (
        ("M", "Masculino"),
        ("F", "Feminino"),
        ("N", "Não informado"),
    )


# Retornar o sexo da pessoa
@register.filter
@stringfilter
def formato_sexo(value):
    try:
        sexos = {
            "M": "Masculino",
            "F": "Feminino",
            "N": "Não informado",
        }
        return sexos.get(value, "")
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar o valor Financeiro
@register.filter
@stringfilter
def mensagem_acessar_ato(value):
    return "Acessar os detalhes checklist do Ato: " + str(value)


# Retornar o valor Financeiro
@register.filter
@stringfilter
def status_parte(value):
    return TipoParte.get_descricao(value)


# Retornar o valor Financeiro
@register.filter
@stringfilter
def real_br_money_mask(value):
    return formatar_valor_real_br(value)


# Retornar Apenas o tipo de cobranca
@register.filter
@stringfilter
def formatar_transacao(transacao: str) -> str:
    # Remove a parte decimal e tenta converter para inteiro
    transacao = transacao.split(".")[0]

    try:
        transacao = int(transacao)
    except ValueError:
        logger.exception("Erro ao converter transacao para inteiro")
        return ""

    tipo_transacao = {"-1": "", "0": "", "1": "Crédito", "2": "Débito"}

    # Verifica se a transação está no dicionário
    return tipo_transacao.get(str(transacao), "")


@register.filter
def formatar_tipo_cobranca(cobranca):
    try:
        cobranca_str = str(cobranca)
        cobranca_key = int(cobranca_str.split(".")[0])
    except ValueError:
        return "Não identificado"

    tipo_cobranca_dict = {
        -1: "",
        0: "10 - Justiça Gratuita",
        1: "Normal",
        2: "2 - 80% Tabela Cartoraria",
        5: "3 - 50% SFH",
        8: "9 - Lei Municipal",
        9: "Cédula Rural 167-67",
        10: "7 - 10% MCMV",
        12: "8 - 20% MCMV",
        14: "6 - 75% FAR/FDS",
        16: "4 - 50% MCMV",
        20: "24 - 100% Devedor",
        24: "25 - Isento TFJ",
        34: "21 - 90% Promorar",
        35: "35 - Isento TFJ",
        36: "22 - 80% Promorar",
        40: "40 - Isento TFJ-Canc.",
        42: "42 - Prenotação - Ordem Judicial - Autoridade Judiciária",
        43: "43 - Prenotação - Ordem Judicial - Parte Interessada",
        47: "47 - Desconto - 75% Registro cédula/nota de crédito rural",
        50: "50 - Registro/Av. de CRP",
        54: "54 - Registro de hipoteca/alienação fiduciária",
        58: "58 - Prenotação - mandado judicial - Autoridade",
        59: "59 - Prenotação - mandado judicial - Parte Interessada",
        60: "60 - Prenotação - indisponibilidade de bens - Autoridade",
        61: "61 - Prenotação - indisponibilidade de bens - Parte Interessada",
        88: "28 - Erro Imputável ao cartório",
        91: "31 - Erro Imputável ao cartório c/decisão",
        97: "37 - 50% PAR",
        98: "38 - Reg/Av Jurídico",
        99: "34 - Reg/Av cédulas",
        100: "10 - Isento Justiça Gratuita",
    }

    return tipo_cobranca_dict.get(cobranca_key, "Não identificado")


@register.filter
@stringfilter
def retornar_estado(numero) -> None:
    """Converte o número do estado em seu nome correspondente."""
    from apps.comum.models import UnidadeFederativa

    UnidadeFederativa.retornar_estado(numero)


# Retornar Apenas Numero
@register.filter
def apenas_numeros_depois_do_ponto(numero) -> str:
    """
    Esta função recebe um número no formato de string, que pode conter pontos como separadores.
    Ela retorna apenas a parte do número após o primeiro ponto.
    Se o número não contiver um ponto, a função retorna o número original.

    Args:
    ----
        numero (str): O número original como uma string.

    Returns:
    -------
        str: O número após o primeiro ponto, ou o número original se não houver ponto.

    """
    try:
        # Tenta dividir o número em partes usando o ponto como separador.
        # Em seguida, concatena a segunda e terceira partes (índices 1 e 2) com um ponto entre elas.
        numero = str(numero).split(".")[1] + "." + str(numero).split(".")[2]
    except Exception:
        # Se a divisão falhar (por exemplo, se não houver ponto no número), retorna o número original.
        return numero

    return numero


# Retornar Apenas Numero
@register.filter
@stringfilter
def apenas_numeros(value):
    return re.sub("[^0-9]", "", value)


# Formatar CPF para exibir corretamente
@register.filter(name="formatar_documento")
def formatar_documento_filter(value):
    return formatar_documento(value)


# Formatar numero de protocolo corretamente
@register.filter
def protocolo_formatado(numero):
    return formatar_protocolo(numero)


@register.filter(name="formatar_moeda")
def formatar_moeda_filter(valor, incluir_simbolo=True) -> str:
    return formatar_moeda(valor, incluir_simbolo)


def get_data_atual() -> str:
    data_atual = timezone.now().date()
    return data_atual.strftime(settings.DATE_FORMAT_STR)


def get_data_atual_separada_por_pontos() -> str:
    data_atual = timezone.now().date()
    return data_atual.strftime(settings.DATE_FORMAT_STR).replace("/", ".")


def get_data_atual_separada_por_tracos() -> str:
    return timezone.now().date().strftime(settings.DATE_FORMAT_STR).replace("/", "-")


@register.filter
@stringfilter
def verificar_data_fase(data) -> int:
    """
    Compara a data fornecida com a data atual e retorna:
    - 0 se a data fornecida é maior que a data atual
    - 1 se a data fornecida é igual à data atual
    - 2 se a data fornecida é menor que a data atual.

    Args:
    ----
        data (str): Data em formato de string para ser convertida e comparada.

    Returns:
    -------
        int: Resultado da comparação da data.

    """
    data = convert_data_str_to_date(data)

    if not data:
        return -1

    hoje = timezone.now().date()

    # Retorna 0, 1 ou 2 baseado na comparação da data fornecida com a data atual
    return 0 if data > hoje else 1 if data == hoje else 2


def convert_data_str_to_date(data: str) -> date:
    try:
        return datetime.strptime(data, settings.DATE_FORMAT_STR).date()
    except ValueError:
        try:
            return datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError:
            return None


# Formatar data gravar BANCO DE DADOS POSTGRESQL
@register.filter
@stringfilter
def data_formato_modelo_gravar_bd(data):
    try:
        data_temp = datetime.strptime(data, settings.DATE_FORMAT_STR).date()
        # print(data_temp)
    except Exception:
        logger.exception("ERRO")
        return ""
    return data_temp


# Formatar data


@register.filter
@stringfilter
def converter_data_para_formato_de_modelo(data: str) -> str:
    if not data or data.strip() == "" or data == "None":
        return ""

    try:
        data_objeto = datetime.strptime(data.split(" ")[0], "%Y-%m-%d")
        data_formatada = data_objeto.strftime(settings.DATE_FORMAT_STR)

        # Verificação de data vazia
        if data_formatada == "01/01/1899":
            return ""

        return data_formatada
    except ValueError:
        logger.exception("ERRO ao converter data: ")
        return ""


# Formatar data e hora
@register.filter(name="data_formato_modelo_hora")
def data_formato_modelo_hora_filter(data) -> str:
    from apps.home.helpers import data_formato_modelo_hora

    return data_formato_modelo_hora(data)


@register.filter
def remover_numero_texto(valor):
    numero = protocolo_formatado(apenas_numeros(valor))
    """Remover pontos de uma string."""
    return str(valor).replace(numero, "")


@register.filter
def remover_pontuacao(valor) -> str:
    """Remover ponto ou vírgula de uma string, bem como sufixos ".00" e ",00"."""
    return (
        str(valor)
        .replace(".00", "")
        .replace(",00", "")
        .replace(".", "")
        .replace(",", "")
    )


# Formatar para retornar o numero inteiro
@register.filter
@stringfilter
def numero_inteiro(valor):
    try:
        value = int(str(valor).split(".")[0])
    except Exception:
        logger.exception("ERRO")
        value = 0

    return value


# Formatar o CODIGO DE SEGURANCA
@register.filter
@stringfilter
def formatar_codigo_seguranca(numero) -> str:
    numero = somente_numeros(numero)

    return numero[0:4] + "." + numero[4:8] + "." + numero[8:12] + "." + numero[12:16]


# Retornar o estado civil com regime da pessoa
@register.filter
@stringfilter
def lista_tipo_regime_casamento(value) -> list:
    tipo_casamento_model = apps.get_model("home", "TipoRegimeCasamento")
    return tipo_casamento_model.objects.lista_tipo_regime_casamento()


# Retornar se existe texto
@register.filter
@stringfilter
def get_texto_imovel(value) -> int:
    # Verifica se o valor é None ou não é um dígito
    if value is None or not str(value).isdigit():
        return 0  # Retorna 0 se o valor não é adequado para a consulta

    # Realiza a consulta assumindo que value é um ID válido
    return Livro02Texto.objects.filter(pedido_item_id=value).count()


@register.filter
@stringfilter
def pedido_item_possui_nota_devolucao(pedido_item_id: int) -> bool:
    nota_devolucao_texto_model = apps.get_model("home", "NotaDevolucaoTexto")
    return nota_devolucao_texto_model.objects.filter(
        pedido_item_id=pedido_item_id,
    ).exists()


# Retornar a lista de tipos de imovel
@register.filter
@stringfilter
def lista_tipo_registro(value):
    # Converter queryset para uma list
    return list(
        TipoRegistroProtocolo.objects.all()
        .values_list("id", "descricao")
        .order_by("id"),
    )


# Retornar a lista de tipos de tributacoes
@register.filter
@stringfilter
def lista_tipo_tributacao(value):
    # Converter queryset para uma list
    return list(
        TipoTributacao.objects.filter(Q(utilizado="S"))
        .values_list("id", "descricao")
        .order_by("outros_codigo_trib_tj"),
    )


# Retornar a lista de Emolumentos Complementares
@register.filter
@stringfilter
def lista_emolumentos_complementares(value):
    from apps.home.models import Emolumentos

    # Converter queryset para uma list
    return list(
        Emolumentos.objects.filter(Q(ato_complementar="S"))
        .values_list("id", "nome")
        .order_by("nome"),
    )


# Retornar o estado civil da pessoa
@register.filter
@stringfilter
def lista_estado_civil(value):
    from apps.home.models import EstadoCivil

    # Converter queryset para uma list
    return list(
        EstadoCivil.objects.filter(Q(exibir="S"))
        .values_list("id", "descricao_estado_civil")
        .order_by("descricao_estado_civil"),
    )


@register.filter
def get_id_regime_bens_filter(descricao_regime):
    from apps.home.models import get_regime_bens

    return get_regime_bens(descricao_regime)


# Retornar o estado_civil PESSOA
@register.filter
def get_descricao_estado_civil(estado_civil_id) -> str:
    from apps.home.models import EstadoCivil

    """
    Obtém a descrição da estado_civil com base no ID fornecido.

    :param estado_civil_id: ID da estado_civil desejada.
    :return: Descrição da estado_civil. Retorna uma string vazia se o estado_civil não for encontrada.
    """
    if not estado_civil_id:
        return ""
    try:
        # Garantindo que o ID seja um inteiro
        estado_civil_id = int(str(estado_civil_id.id).split(".")[0])
    except ValueError:
        logger.exception("ID de estado_civil inválido: %s", estado_civil_id)
        estado_civil_id = 1  # Valor padrão em caso de erro

    estado_civil = EstadoCivil.objects.filter(id=estado_civil_id).first()

    if estado_civil:
        return estado_civil.descricao_estado_civil

    return ""


# Retornar o estado_civil PESSOA
@register.filter
@stringfilter
def get_estado_civil_pela_descricao(descricao_estado_civil):
    from apps.home.models import EstadoCivil

    return EstadoCivil.objects.filter(
        tipoestado_civil__iexact=descricao_estado_civil,
    ).first()


# Retornar o Servico de Andamento
@register.filter(name="get_tipos_andamentos")
def get_tipos_andamentos_filter(tipo_andamento):
    from apps.home.models import get_tipos_andamentos

    return get_tipos_andamentos(tipo_andamento)


@register.filter
def get_nome_colaborador_pelo_id(pk: int) -> str:
    from apps.home.models import Colaborador

    """Obtém o nome do funcionário com base na chave fornecida."""
    try:
        if pk in ["", "None", "home"]:
            return ""

        cache_key = f"funcionario_nome_{pk}"
        nome = cache.get(cache_key)

        if nome is None:
            funcionario = Colaborador.objects.get(id=pk)
            nome = funcionario.nome
            # Armazenar no cache por 300 segundos
            cache.set(cache_key, nome, 300)

        return nome
    except Colaborador.DoesNotExist:
        logger.exception(f"Funcionário não encontrado: {pk}")
        return ""
    except Exception:
        logger.exception("ERRO ao buscar nome do funcionário: ")
        return ""


@register.filter
def mapear_nome_colaborador(nome) -> str:
    from apps.home.models import Colaborador

    """
    Mapeia o nome do funcionário usando o dicionário NOME_MAP.
    Retorna o nome original se não houver mapeamento.
    """
    return Colaborador.get_nome_mapeado(nome)


@register.filter(name="formatar_nome")
def formatar_nome_filter(nome: str) -> str:
    """Formata o nomes para exibição."""
    return formatar_nome(nome)


@register.filter
@stringfilter
def get_nivel_alerta_pelo_id(pk: int) -> str:
    if pk:
        NivelAlerta.objects.filter(id=pk).fisrt()

    return NivelAlerta.descricao if NivelAlerta else ""


# Retornar o Selo
@register.filter
@stringfilter
def get_selos(pedido_item_id):
    try:
        selo = SeloEletronico.objects.filter(pedido_item_id=pedido_item_id).first()

        return selo.codigo_sequencial_unico if selo else ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar a classe do imovel DESCRITA
@register.filter
@stringfilter
def formatar_classe_do_registro(tipo):
    tipo_descricao = {
        "L": "Lote",
        "U": "Urbano",
        "R": "Rural",
    }
    return tipo_descricao.get(tipo, "")


# Retornar o imovel
@register.filter
@stringfilter
def formatar_tipo_encerramento(value) -> str:
    return "Sim" if value == "T" else "Não"


# Retornar o SIM = TRUE e NAO = FALSE
@register.filter
@stringfilter
def formatar_true_sim(value) -> str:
    return "Sim" if value == "T" else "Não"


# Retornar a classe do imóvel
@register.filter
@stringfilter
def get_classe_do_imovel_pelo_pedido_item_id(pedido_item_id: int) -> str:
    """Obtém a classe do imóvel com base na chave de pedidos e itens fornecida."""
    try:
        pedido_item_id = int(pedido_item_id)
    except ValueError:
        return ""

    if not pedido_item_id:
        return ""

    cache_key = f"classe_imovel_{pedido_item_id}"
    classe_imovel = cache.get(cache_key)

    if classe_imovel is None:
        try:
            pedido_item = PedidoItem.objects.only("imovel__classe").get(
                pk=pedido_item_id,
            )

            if (
                hasattr(pedido_item, "imovel")
                and pedido_item.imovel
                and pedido_item.imovel.classe
            ):
                # Armazenar no cache por 300 segundos
                cache.set(cache_key, pedido_item.imovel.classe, 300)
                classe_imovel = pedido_item.imovel.classe
            else:
                classe_imovel = ""

        except PedidoItem.DoesNotExist:
            classe_imovel = ""
        except Exception:
            logger.exception("ERRO")
            classe_imovel = ""

    return classe_imovel


# Retornar o DOI praticado
@register.filter
@stringfilter
def get_codigo_doi(pedido_item_id: int) -> int:
    try:
        pedido_item_id = int(pedido_item_id)
    except ValueError:
        return 0

    if not pedido_item_id:
        return 0

    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
        ato_doi = pedido_item.ato.codigo_doi_id
        return ato_doi or 0
    except Exception:
        logger.exception("ERRO")
        return 0


# Retornar o Ato praticado
@register.filter
@stringfilter
def get_ato_praticado(pedido_item_id):
    """Obtém o ato praticado com base na chave de pedidos e itens fornecida."""
    try:
        cache_key = f"ato_praticado_{pedido_item_id.replace(' ', '_')}"
        ato_praticado = cache.get(cache_key)

        if ato_praticado:
            return ato_praticado

        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        ato_praticado = pedido_item.ato.tipo_ato

        if ato_praticado:
            cache.set(
                cache_key,
                ato_praticado,
                300,
            )  # Armazenar no cache por 300 segundos
            return ato_praticado
        else:
            return ""
    except Exception:
        logger.exception("ERRO")
        return pedido_item_id


# Retornar o Codigo da Tabela


@register.filter
@stringfilter
def get_codigo_tabela(pedido_item):
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item.pk).first()

        if pedido_item:
            codigo_tabela = pedido_item.codigo_tabela
            return codigo_tabela if codigo_tabela else ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar o numero do cartorio
@register.filter
@stringfilter
def get_numero_ri(pedido_item_id):
    """Obtém o número do cartório (RI) com base no pedido_item_id fornecido."""
    cache_key = f"numero_ri_{pedido_item_id}"
    numero_ri = cache.get(cache_key)

    if numero_ri:
        return numero_ri

    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        if pedido_item:
            numero_ri = pedido_item.numero_ri

        if numero_ri:
            # Armazenar no cache por 300 segundos
            cache.set(cache_key, numero_ri, 300)
            return numero_ri
        else:
            return ""
    except Exception:
        logger.exception("ERRO")
        return ""


@register.filter
def get_numero_registro_por_pedido(pedido_item_id):
    """
    Recupera o número do imóvel associado a um item de pedido.

    :param pedido_item_id: chave do item de pedido para filtrar.
    :return: número do imóvel ou string vazia em caso de erro ou não encontrado.
    """
    valor_decimal = decimal_ou_zero(pedido_item_id)

    try:
        # Obter o número do imóvel diretamente do PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=valor_decimal).first()

        return pedido_item.numero_registro if pedido_item else 0.00

    except Exception:
        logger.exception("ERRO")
        return 0.00


# Retornar o numero do ATO
@register.filter
@stringfilter
def get_numero_do_ato_pelo_pedido_item_id(pedido_item_id):
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        if pedido_item:
            return pedido_item.numero_ato if pedido_item.numero_ato else ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar o numero do PEDIDO
@register.filter
@stringfilter
def get_pedido_id(pedido_item_id):
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
        return pedido_item.pedido if pedido_item else 0
    except Exception:
        logger.exception("ERRO")
        return 0


# Retornar o numero do PROTOCOLO
@register.filter
def get_numero_protocolo_filter(pedido_item_id):
    try:
        pedido = get_pedido(pedido_item_id)
        if pedido:
            return get_numero_protocolo_pelo_pedido(pedido)
    except Exception:
        logger.exception("ERRO")
    return ""


def get_pedido(pedido_item_id):
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
    return pedido_item.pedido if pedido_item else None


def get_numero_protocolo_pelo_pedido(pedido):
    protocolo = (
        Livro01Protocolo.objects.filter(pedido=pedido)
        .values("numero_protocolo")
        .first()
    )
    return str(protocolo["numero_protocolo"]) if protocolo else ""


# Retornar a imagem do colaborador
@register.filter
@stringfilter
def get_user_image(user_id):
    return User.objects.filter(id=user_id).values_list("image", flat=True).first()


# Retornar o get_usuario_autenticado
@register.filter
@stringfilter
def get_usuario_autenticado(auth_user_id):
    user = ""

    try:
        for encaminhado in list(User.objects.all().values("id", "username")):
            if str(encaminhado["id"]) == str(auth_user_id):
                user = encaminhado["username"]

        if str(user) is not None:
            return user
        else:
            return ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Formatar para nao exibir NONE
@register.filter
@stringfilter
def opcao_selecionada_parte(opcao) -> str:
    return "A"


# Retornar o numero_registro
@register.filter
@stringfilter
def numero_proximo_ato_imovel(pedido_item_id):
    if not pedido_item_id:
        return 0

    # Iniciar as variaveis
    numero_vinculo, numero_vinculo_protocolo = -1, -1

    # Obter os atos do LIVRO 2
    vinculos = get_vinculos_livro02(pedido_item_id)

    # Exibir todos os vinculos do imovel
    for vinculo in vinculos:
        numero_vinculo = vinculo[2]

    # Retornar o ultimo numero do vinculo presente no indicador pessoal
    ultimo_numero_vinculo = int(str(numero_vinculo).split(".")[0])

    # PESQUISAR DENTRO DO PROTOCOLO
    for pedido_item in PedidoItem.objects.filter(pk=pedido_item_id):
        # Retonar o ultimo numero do vinculo presente no protocolo
        numero_vinculo_protocolo = exibir_numero_vinculos_protocolo(
            pedido_item.numero_registro,
            pedido_item.tipo_registro,
            pedido_item.numero_ri,
        )

    # Transformar em inteiro
    ultimo_numero_vinculo_protocolo = int(str(numero_vinculo_protocolo).split(".")[0])

    # Verificar se no protocolo existe um numero maior que no indicador pessoal
    if ultimo_numero_vinculo_protocolo > ultimo_numero_vinculo:
        ultimo_numero_vinculo = ultimo_numero_vinculo_protocolo

    # Retornar o ultimo numero do vinculo presente no indicador pessoal
    return ultimo_numero_vinculo + 1

    # Retornar o ultimo numero do vinculo


# Retornar o
@register.filter
@stringfilter
def get_tipo_ato_padrao(pedido_item_id):
    tipoato_dict = {
        "A": "Averbação",
        "R": "Registro",
        "M": "Matrícula",
    }

    try:
        # Filtrando o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        if pedido_item:
            tipoato = pedido_item.ato.tipo
            return tipoato_dict.get(tipoato, "Registro")
    except Exception:
        logger.exception("ERRO")

    return "Registro"


# Retornar o
@register.filter
@stringfilter
def get_tipo_ato_letra(pedido_item_id: int) -> str:
    try:
        # Filtrando o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        # Filtrando o ATO
        ato = pedido_item.ato

        return ato.tipo if ato.tipo in ["A", "R", "M"] else "R"
    except Exception:
        logger.exception("ERRO")

    return "R"


@register.filter
def capitalizar(value: str) -> str:
    return formatar_nome(value)


@register.filter
@stringfilter
# Buscar Dados do Loteamento
def get_loteamento_pelo_imovel(imovel_id) -> list:
    imovel = Livro02.objects.get(pk=imovel_id)
    return imovel.loteamento


# Buscar Dados do Condominio
@register.filter
@stringfilter
def get_condominio_pelo_imovel(
    registro_anterior_id=0,
    opcao=0,
    tipo_unidade="",
    imovel_id=0,
) -> list:
    # BUSCAR A FICHA PELO ID IMOVEL
    if opcao == 1:
        # FIltrando o imovel direto
        unidade_anterior = Unidade.objects.get(imovel_id=registro_anterior_id)
    else:
        # FIltrando as unidades
        unidade_anterior = Unidade.objects.get(id=registro_anterior_id)

    # FIltrando os LOTES
    lote = Lote.objects.get(unidade=registro_anterior_id)
    lote1 = unidade_anterior.imovel.lotes.fisrt()
    print(lote1)

    # FIltrando as unidades ATUAL
    unidade_atual = Unidade.objects.get(imovel_id=imovel_id)
    nomes_das_ruas_anteriores = get_nomes_das_ruas_pela_unidade(registro_anterior_id)

    # FIltrando o imovel
    imovel_anterior = Livro02.objects.get(pk=unidade_anterior.imovel_id)

    # FIltrando os dados do Condominio
    ficha_auxiliar_anterior = (
        FichaAuxiliar.objects.filter(id=unidade_anterior.imovel_id).first()
        if unidade_anterior
        else None
    )

    # Tipo de Unidade
    tipo_unidade = str(exibir_tipo_unidade_imovel(tipo_unidade))

    return [
        imovel_anterior.tipo if imovel_anterior else "",
        imovel_anterior.numero if imovel_anterior else "",
        imovel_anterior.cartorio if imovel_anterior else "",
        ficha_auxiliar_anterior.nome if ficha_auxiliar_anterior else "",
        ficha_auxiliar_anterior.nome_incorporadora if ficha_auxiliar_anterior else "",
        ficha_auxiliar_anterior.data_incorporacao if ficha_auxiliar_anterior else "",
        ficha_auxiliar_anterior.numero_edificacao if ficha_auxiliar_anterior else "",
        unidade_atual.numero_unidade if unidade_atual else "",
        unidade_anterior.nome_edificio if unidade_anterior else "",
        tipo_unidade if tipo_unidade else "",
        unidade_anterior.area if unidade_anterior else "",
        unidade_anterior.quadra if unidade_anterior else "",
        unidade_anterior.lote_auxiliar if unidade_anterior else "",
        lote.setor if lote else "",
        nomes_das_ruas_anteriores if nomes_das_ruas_anteriores else "",
    ]


# Retornar a tipo_unidade do imovel
@register.filter
@stringfilter
def exibir_tipo_unidade_imovel(pedido_item_id):
    try:
        # Obter o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        if not pedido_item:
            return ""

        # Obter o REGISTRO associado
        registro = Livro02.objects.get_pelo_pedido_item(pedido_item)

        return registro.tipo_unidade if registro and registro.tipo_unidade else ""

    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar a tipo_unidade do imovel
@register.filter
@stringfilter
def get_registro_anterior(pedido_item_id):
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
        registro = Livro02.objects.get_pelo_pedido_item(pedido_item)

        return registro.registro_anterior if registro.registro_anterior else ""
    except Exception:
        logger.exception("ERRO")
        return ""


@register.filter(name="concatenate")
def concatenate(value, arg) -> str:
    return f"{value}{arg}"


# Buscar Numero do Imovel
@register.filter(name="get_numero_registro_pelo_id")
def get_numero_registro_filter(imovel_id):
    from apps.home.models import get_numero_registro_pelo_id

    return get_numero_registro_pelo_id(imovel_id)


# Buscar Numero do Imovel
@register.filter(name="get_tipo_da_unidade_pelo_id")
def get_tipo_da_unidade_pelo_id_filter(unidade_id):
    from apps.home.models import get_tipo_da_unidade_pelo_id

    return get_tipo_da_unidade_pelo_id(unidade_id)


# Buscar Nome Rua
@register.filter(name="get_ruas")
def get_ruas_filter(unidade_id):
    from apps.home.models import get_ruas

    return get_ruas(unidade_id)


# Buscar Nome Rua
@register.filter
def retornar_ruas(unidade_id: int) -> str:
    """
    Retorna a rua baseada no id das unidades.

    :param unidade_id: Identificador das unidades.
    :return: Nome da rua e, se presente, o número da edificação.
    """
    ruas = [formatar_rua(item) for item in get_ruas(unidade_id)]
    return ", ".join(ruas)


def formatar_rua(rua) -> str:
    """
    Formata a informação da rua.

    :param rua: Objeto que representa a rua.
    :return: Nome da rua e, se presente, o número da edificação.
    """
    if rua.numero_edificacao:
        return f"{rua.nome} - {rua.numero_edificacao}"
    return rua.nome


# PEGANDO O Anterior DO IMOVEL
@register.filter
@stringfilter
def get_registros_anteriores(imovel_id):
    from apps.home.models import Anterior

    return Anterior.objects.filter(imovel_id=imovel_id)


# Buscar Nome Rua pelo ID IMOVEL


# Buscar Nome Rua
@register.filter
@stringfilter
def get_ruas_da_unidade(unidade_id):
    # PEGANDO O RUA DO IMOVEL URBANO
    return Rua.objects.filter(unidade_id=unidade_id)


# Buscar Nome Rua
@register.filter
@stringfilter
def get_nomes_das_ruas_pela_unidade(unidade_id) -> str:
    return Unidade.get_nomes_das_ruas_pela_unidade_id(unidade_id)


# Retornar o imovel
@register.simple_tag
def get_tipo_construcao_lote(value, residencial_id="", comercial_id="", as_var=None):
    # VERIFIR SE O IMOVEL E COMERCIAL
    comercial_residencial_id = ""

    if comercial_id == "T":
        comercial_residencial_id = "Comercial"
    if residencial_id == "T":
        comercial_residencial_id = "Residencial"
    if comercial_residencial_id == "":
        comercial_residencial_id = "Não informado"

    return str(comercial_residencial_id)


# Retornar os dados do imovel lote
@register.simple_tag
def get_rurais(value, imovel_id="", as_var=None):
    return Rural.objects.filter(imovel_id=imovel_id)


# Retornar os dados do imovel lote
@register.simple_tag
def get_rurais_nomes(value, imovel_id="", as_var=None):
    return RuralNome.objects.filter(imovel_id=imovel_id)


# Retornar os dados da pessoa
@register.simple_tag
def get_livro02_por_pessoa(value, pessoa_id, as_var=None):
    return (
        Vinculo.objects.select_related("pessoa", "tipo_vinculo")
        .filter(pessoa_id=pessoa_id)
        .order_by("-imovel__numero", "-numero_ato")
    )


# Buscar Endereco pelo LOTE
@register.filter
@stringfilter
def get_enderecos_do_imovel(imovel_id):
    # enderecos = []

    # imovel = Livro02.objects.filter(pk=imovel_id).first()

    # if imovel.classe == "R":
    #     nomes_rurais = RuralNome.objects.filter(imovel_id=imovel_id).first()
    #     imovel_rural = Rural.objects.filter(imovel_id=imovel_id).first()
    #     enderecos.append(
    #         [
    #             "Nome: " + nomes_rurais.nome,
    #             "Localização: " + imovel_rural.caracteristica,
    #             "Área: " + imovel_rural.area,
    #         ]
    #     )
    # else:
    #     unidade = Unidade.objects.filter(imovel_id=imovel_id).first()
    #     for lote in Lote.objects.filter(unidade=unidade.pk):
    #         enderecos.append(
    #             [
    #                 "Bairro: " + str(lote.setor),
    #                 "Quadra: "
    #                 + str(lote.quadra)
    #                 + "; Lote: "
    #                 + str(lote.numero_unidade)
    #                 + "; Área: "
    #                 + str(lote.area),
    #                 "Rua(s): " + str(get_nomes_das_ruas_pela_unidade(unidade.pk)),
    #             ]
    #         )

    # return enderecos

    imovel = Livro02.objects.filter(pk=imovel_id).first()

    return imovel.enderecos


def formatar_telefone(numero, pais="BR"):
    if numero is None or numero.strip() == "":
        return ""

    try:
        telefone = phonenumbers.parse(numero, pais)
        if phonenumbers.is_valid_number(telefone):
            return phonenumbers.format_number(
                telefone,
                phonenumbers.PhoneNumberFormat.NATIONAL,
            )
        else:
            return numero
    except phonenumbers.NumberParseException:
        return ""


@register.filter(name="formatar_telefone")
def formatar_telefone_filter(numero):
    return formatar_telefone(numero)


@register.filter(name="somente_numeros")
@stringfilter
def somente_numeros_filter(value) -> str:
    return somente_numeros(value)


def data_valida(data) -> bool:
    data = str(data).split(".", "/")

    try:
        datetime.strptime(data, settings.DATE_FORMAT_STR)
        return True
    except ValueError:
        return False


@register.filter
@stringfilter
def get_numero_registro(imovel_id: int) -> str:
    return Livro02.get_numero_do_registro_pelo_id(imovel_id) if imovel_id else ""


# Obter o numero maximo de datas previstas
@register.filter
@stringfilter
def get_prazo_do_pedido_em_dias(pedido_id, opcao="P", tipo_data="S"):
    pedido = Pedido.objects.get(pk=pedido_id)

    return pedido.get_prazo_em_dias(opcao)


# Obter o numero maximo de datas previstas
@register.filter
@stringfilter
def get_max_dias_titulo_total_dias(pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)

    return pedido.get_prazo_em_dias()[1]


@register.filter
@stringfilter
def proxima_data_prevista(pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)

    data_hora, max_dias = pedido.get_prazo_em_dias("P")
    return get_data_util_em_x_dias(data_hora, max_dias)


@register.filter
@stringfilter
def proxima_data_valida(pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)

    data_hora, max_dias = pedido.get_prazo_em_dias("V")

    return get_data_util_em_x_dias(data_hora, max_dias + 1)


@register.filter
@stringfilter
def primeira_data_exigencia(pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)

    data_hora, max_dias = pedido.get_prazo_em_dias("N")

    return get_data_util_em_x_dias(data_hora, max_dias)


@register.filter
@stringfilter
def total_dias_restantes(data):
    if data is None or data.strip() == "":
        return ""
    # Corrigindo o formato da data para corresponder à entrada '2024-02-16'
    data_format = "%Y-%m-%d"  # Ano com quatro dígitos, mês e dia

    # Convertendo a string de data para um objeto datetime
    data_date = datetime.strptime(data.split()[0], data_format)

    # DATA ATUAL
    data_atual = datetime.now()

    # Calculando a diferença
    diferenca = (
        data_date - data_atual
    )  # Usando diretamente data_date, já que é um objeto datetime
    return diferenca.days


# @register.filter
# def arrendamento_bancario(value, places):
#     """Arredonda um número para um número especificado de casas decimais usando o arredondamento half-even."""
#     try:
#         # Tenta converter o valor para float.
#         value = Decimal(value)
#     except (ValueError, TypeError):
#         # Se a conversão falhar, retorna 0.
#         return 0

#     # Se a conversão for bem-sucedida, realiza o arredondamento.
#     return round(decimal.Decimal(value), places)


@register.filter
def arrendamento_bancario(value, places):
    """Arredonda um número para um número especificado de casas decimais usando o arredondamento half-even."""
    try:
        # Tenta converter o valor para Decimal.
        value_decimal = decimal.Decimal(value)
    except (decimal.InvalidOperation, TypeError):
        # Se a conversão falhar, retorna 0.
        return 0

    # Define o contexto de arredondamento para HALF_EVEN (arredondamento bancário)
    context = decimal.getcontext().copy()
    context.rounding = decimal.ROUND_HALF_EVEN

    # Realiza o arredondamento.
    return context.quantize(value_decimal, decimal.Decimal("0." + "0" * places))


# Retornar da Livro 3 Vinculados
@register.simple_tag
def get_livro03_pelo_numero(value, numero_registro=0, as_var=None) -> list:
    return Livro03.get_dados_em_lista_pelo_numero_do_registro(numero_registro)


# Verificar se faz parte do EXIGENCIA
@register.filter(name="verificar_servicos_exigencia")
def verificar_servicos_exigencia_filter(servicos_id):
    return int(servicos_id) in TipoAndamento.objects.get_ids_de_tipo_exigencia()


# Verificar se faz parte do EXIGENCIA POSITIVA
@register.filter(name="verificar_servicos_exigencia_positiva")
def verificar_servicos_exigencia_positiva_filter(servicos_id) -> int:
    for item in TipoAndamento.objects.get_ids_de_tipo_exigencia_positiva():
        if int(item) == int(servicos_id):
            return 1
    return 0


# Verificar se faz parte do SUBJUDICE
@register.filter(name="verificar_servicos_subjudice")
def verificar_servicos_subjudice_filter(servico_id) -> int:
    for item in TipoAndamento.objects.get_ids_de_tipo_subjudice():
        if int(item) == int(servico_id):
            return 1
    return 0


# Verificar se faz parte do Registrados
@register.filter(name="verificar_servicos_distribuidos")
def verificar_servicos_distribuidos_filter(servico_id) -> int:
    for item in TipoAndamento.objects.get_ids_de_tipo_distribuicao():
        if int(item) == int(servico_id):
            return 1
    return 0


# Verificar se faz parte do Registrados
@register.filter(name="verificar_servicos_registrados")
def verificar_servicos_registrados_filter(servico_id) -> int:
    for item in TipoAndamento.objects.get_ids_tipo_registrado():
        if int(item) == int(servico_id):
            return 1
    return 0


# Verificar se faz parte do Registrados
@register.filter(name="verificar_servicos_cancelados")
def verificar_servicos_cancelados_filter(servico_id: int) -> bool:
    return servico_id in TipoAndamento.objects.get_ids_de_tipo_cancelado()


# Verificar se faz parte do finalizado
@register.filter(name="verificar_servicos_finalizado")
def verificar_servicos_finalizado_filter(servicos_id) -> int:
    for item in TipoAndamento.objects.get_ids_de_tipo_finalizado():
        if int(item) == int(servicos_id):
            return 1
    return 0


# Verificar se faz parte do EM REGISTRO
@register.filter(name="verificar_servicos_em_registro")
def verificar_servicos_em_registro_filter(servicos_id) -> int:
    for item in TipoAndamento.objects.filtrar_por_tipo_em_registro():
        if int(item) == int(servicos_id):
            return 1
    return 0


# Verificar se faz parte do finalizado
@register.filter(name="verificar_nome_servico_registrado")
def verificar_nome_servico_registrado():
    # for item in get_ids_de_tipo_finalizado():
    #    if int(item) == int(servicos_id):
    #        return 1
    return ["Registrado"]


@register.filter(name="verificar_nome_servico_cancelado")
def verificar_nome_servico_cancelado():
    # for item in get_ids_de_tipo_finalizado():
    #    if int(item) == int(servicos_id):
    #        return 1
    return ["Cancelado"]


@register.filter(name="verificar_nome_exigencia")
def verificar_nome_servico_exigencia():
    # for item in get_ids_de_tipo_finalizado():
    #    if int(item) == int(servicos_id):
    #        return 1
    return ["Exigência"]


# VERIFICAR SE O EVENTO JA EXISTE
@register.filter
def get_eventos_do_protocolo(protocolo, titulo_do_evento) -> list:
    try:
        return Event.objects.filter(
            numero=protocolo.numero_protocolo,
            title=titulo_do_evento,
        )
    except Exception:
        logger.exception("ERRO")
        return []


# Retornar os colaboradores que serao avisados sobre PROTOCOLO DIGITALIZAR
@register.filter
def get_usuarios_para_notificar_digitalizacao():
    # Utiliza values_list para obter diretamente uma lista dos IDs, com flat=True para obter uma lista simples, não uma lista de tuplas.
    usuario_model = apps.get_model("cartorios", "Usuario")
    return usuario_model.objects.filter(avisar_digitalizar="S")


# Retornar os colaboradores que serao avisados sobre PROTOCOLO VENCENDO
@register.filter
def get_usuarios_para_notificar_protocolo_vencendo():
    usuario_model = apps.get_model("cartorios", "Usuario")
    return list(
        usuario_model.get_usuarios_com_protocolos_prontos_registrar().values_list(
            "id",
            flat=True,
        ),
    )


# Retornar os colaboradores que serao avisados sobre PROTOCOLO NOTA DEVOLUCAO ANEXADA
@register.filter
def get_usuarios_para_notificar_nota_de_devolucao():
    usuario_model = apps.get_model("cartorios", "Usuario")

    return list(
        usuario_model.get_usuarios_com_protocolos_nota_devolucao_anexada().values_list(
            "id",
            flat=True,
        ),
    )


# # RETONAR O TEXTO PARA GRAVAR NO EVENTO - EXIGENCIA CUMPRIDA
def get_descricao_protocolo_distribuido() -> str:
    return "Distribuído o Protocolo: "


def get_descricao_cancelado() -> str:
    return "Cancelado"


def get_descricao_exigencia() -> str:
    return "Exigência"


# Retornar os colaboradores que serao avisados sobre PROTOCOLO VENCENDO
@register.filter
def get_usuarios_para_notificar_protocolo_assinar():
    usuario_model = apps.get_model("cartorios", "Usuario")

    try:
        return list(
            usuario_model.objects.filter(assinar_qualificar_titulo="S").values_list(
                "id",
                flat=True,
            ),
        )
    except Exception:
        logger.exception("ERRO")
        return []


# Dias posteriores que o relatorio vai verificar
@register.filter
def get_prazo_para_verificar_exigencia_cumprida() -> int:
    return 2


# Dias posteriores que o relatorio vai verificar
@register.filter
def get_prazo_para_registrar_exigencia_cumprida() -> int:
    return 5


# Dias posteriores que o relatorio vai verificar
@register.filter
def get_prazo_para_qualificar() -> int:
    return 7


# Dias posteriores que o relatorio vai verificar
@register.filter
def get_prazo_verificar_relatorios_posteriores() -> int:
    return 10


# Verificar Protocolo Pronto Registrar
@register.filter
def get_protocolo_pronto_para_registrar(protocolo) -> tuple:
    from apps.home.models import Livro01Andamento

    # OBTER OS ANDAMENTOS QUE SEJAM DO GRUPO_PRONTO_REGISTRAR NESTE PERIODO
    get_ids_de_tipo_pronto_registrar_id = (
        TipoAndamento.objects.get_ids_de_tipo_pronto_registrar()
    )

    # Verificar se existe para servicos prontos para registrar
    if len(get_ids_de_tipo_pronto_registrar_id) > 0:
        protocolos_andamentos = (
            Livro01Andamento.objects.filter(
                protocolo=protocolo.pk,
                tipo_andamento_id__in=get_ids_de_tipo_pronto_registrar_id,
            )
            .values_list("protocolo", "data")
            .order_by("data")
        )

        # Existe protocolos a gerar o EVENTO
        if len(protocolos_andamentos) > 0:
            # OBTER OS NUMEROS DOS PROTOCOLOS
            for andamento in protocolos_andamentos:
                protocolo_id, data = andamento
                protocolo_id = int(protocolo_id)

            return protocolo_id, data
        else:
            return None, None
    else:
        return None, None


# Verificar Protocolo Pronto Registrar
@register.filter
def get_apenas_nome_do_arquivo(filename):
    caminho_completo = Path(filename)

    return str(caminho_completo.name)


@register.filter(name="markdown")
def markdown_format(text):
    return md.markdown(text, extensions=["markdown.extensions.fenced_code"])


@register.filter
def ultimo_sincronismo(formato):
    """Retorna a data e hora do último sincronismo realizado."""
    cartorio_model = apps.get_model("cartorios", "Cartorio")

    logger.debug("Obtendo a maior data de sincronismo do cartório.")

    # Obtém a maior data
    maior_data = cartorio_model.objects.aggregate(
        maior_data=Max("data_hora_sincronismo"),
    )["maior_data"]

    # Formata a maior data, se ela existir
    if maior_data:
        if formato == "DATA":
            maior_data_formatada = maior_data.strftime("%d.%m.%Y %H:%M")
        else:
            maior_data_formatada = maior_data.strftime(settings.DATETIME_FORMAT_STR)

        logger.debug(f"Maior data de sincronismo: {maior_data_formatada}")
        return maior_data_formatada
    else:
        logger.debug("Nenhum sincronismo encontrado.")
        return None


@register.filter
def internacionalizar_telefone(value):
    # Remove caracteres não-numéricos
    numero = re.sub(r"\D", "", value)
    # Adiciona o código do país se não estiver presente (assumindo Brasil como +55)
    if not numero.startswith("55"):
        numero = "55" + numero
    return numero


# def formatar_moeda(valor, incluir_simbolo: bool = True) -> str:
#     """Formata um valor como moeda, com a opção de incluir ou não o símbolo da moeda."""
#     try:
#         valor_decimal = decimal.Decimal(valor)
#     except (decimal.InvalidOperation, TypeError):
#         # Define um valor padrão para casos de erro na conversão
#         valor_decimal = decimal.Decimal(0)

#     # Definição da moeda e localidade
#     moeda = "BRL"
#     localidade = "pt_BR"

#     # Condicional para incluir ou não o símbolo da moeda
#     if incluir_simbolo:
#         formatado = format_currency(valor_decimal, moeda, locale=localidade)
#     else:
#         formatado = format_currency(valor_decimal, moeda, locale=localidade, currency_digits=False, pattern="#,##0.00")

#     return formatado


# OBTER O ID DO PROTOCOLO PELO NUMERO DO PROTOCOLO
@register.filter
def get_id_protocolo_pelo_numero(numero_protocolo):
    protocolo = (
        Livro01Protocolo.objects.filter(numero_protocolo=numero_protocolo)
        .values("id")
        .first()
    )
    return protocolo["id"] if protocolo else 0


# Retornar o status da INDISPONIBILIDADE
@register.filter
@stringfilter
def status_indisponibilidade(value) -> str:
    return "Ativo" if value == "0" else "Cancelado"


# Retornar o estado_civil regime PESSOA
@register.filter
def get_descricao_tipo_regime_casamento(pk):
    descricao = ""
    if str(pk).isdigit():
        descricao = TipoRegimeCasamento.objects.get_descricao_por_id(pk)
    return descricao if descricao else ""


@register.filter
def get_apresentante_pedido_certidao(numero_pedido_certidao):
    pedido_certidao = PedidoCertidao.objects.filter(
        numero_pedido=numero_pedido_certidao,
    ).first()

    return pedido_certidao.apresentante if pedido_certidao else ""


@register.filter
def get_interessado_pedido_certidao(numero_pedido_certidao):
    pedido_certidao = PedidoCertidao.objects.filter(
        numero_pedido=numero_pedido_certidao,
    ).first()

    return pedido_certidao.nome_interessado if pedido_certidao else ""


@register.filter
def get_valor_total_caixa_pedido_certidao(numero_pedido_certidao):
    pedido_certidao = PedidoCertidao.objects.filter(
        numero_pedido=numero_pedido_certidao,
    ).first()

    return pedido_certidao.valor_total_caixa if pedido_certidao else 0.00


@register.filter
def configurar_cpf_cnp_retornar_descricao(value):
    value = apenas_numeros(value)

    if len(value) == 11:
        return "CPF"
    elif len(value) == 14:
        return "CNPJ"
    else:
        return "CPF"


# Retor
@register.filter
@stringfilter
def get_cpf(pessoa_id):
    if pessoa_id:
        try:
            return Livro05.objects.get(id=pessoa_id).cpf or ""
        except Livro05.DoesNotExist:
            return ""
    return None


@register.filter
def data_por_extenso(date):
    import datetime

    if isinstance(date, datetime.date):
        return f"{date.day} de {MONTHS[date.month - 1]} de {date.year}"
    return date


# Retornar da Livro 3 Vinculados
@register.simple_tag
def verificar_apresentante(value, pedido_id=0, as_var=None) -> str:
    """Retorar os dados do Apresentante do Pedido."""
    from apps.home.helpers import Agora
    from apps.pedidos.models import Pedido

    # PEGAR OS DADOS DO USUARIO
    usuario_model = apps.get_model("cartorios", "Usuario")

    # Obtendo o primeiro item da lista retornada
    usuario = usuario_model.objects.first()

    # PEGAR O PEDIDO DO REQUERIMENTO
    pedido = Pedido.objects.get(numero_pedido=pedido_id)

    # FORMATAR DOCUMENTO - CPF/CNPJ
    documento = (
        formatar_documento(pedido.apresentante.documento)
        if pedido.apresentante.documento
        else ""
    )

    # SUBSTITUIR AS VARIAVIES
    value = str(value).replace(
        "{{ apresentante_nome }}",
        (str(pedido.apresentante.nome)),
    )
    value = str(value).replace("{{ apresentante_cpf_cnpj }}", (str(documento)))
    value = str(value).replace(
        "{{ apresentante_telefone }}",
        (str(pedido.apresentante.telefone)),
    )
    value = str(value).replace(
        "{{ apresentante_telefone_2 }}",
        (str(pedido.apresentante.telefone_2)),
    )
    value = str(value).replace(
        "{{ apresentante_email }}",
        (str(pedido.apresentante.email)),
    )

    # CAMPOS NOVOS
    value = str(value).replace(
        "{{ apresentante_nacionalidade }}",
        (str(pedido.apresentante.nacionalidade)),
    )
    value = str(value).replace(
        "{{ apresentante_profissao }}",
        (str(pedido.apresentante.profissao)),
    )
    value = str(value).replace("{{ apresentante_rg }}", (str(pedido.apresentante.rg)))
    value = str(value).replace(
        "{{ apresentante_estado_civil }}",
        (str(pedido.apresentante.estado_civil)),
    )
    value = str(value).replace(
        "{{ apresentante_endereco }}",
        (str(pedido.apresentante.endereco)),
    )
    value = str(value).replace(
        "{{ apresentante_filiacao }}",
        (str(pedido.apresentante.filiacao)),
    )

    value = str(value).replace("{{ hoje }}", str(timezone.now()))
    value = str(value).replace("{{ cidade }}", str(usuario.cartorio.municipio))
    value = str(value).replace("{{ data_hoje_extenso }}", Agora.extenso())

    return str(value).replace("None", "")


@register.filter
def ultimas_mensagens(request):
    """EXIBIR NA TELA INICIAL TODAS AS MENSAGENS NAO LIDAS."""
    return Event.objects.filter(
        auth_user_id=request.user.id,
        end_time_checked__isnull=True,
    ).count()


@register.filter(name="message_color")
def message_color(tags):
    if tags == "success":
        return "success"
    elif tags == "error" or tags == "danger":
        return "danger"
    elif tags == "warning":
        return "warning"
    elif tags == "info":
        return "info"
    return "secondary"
