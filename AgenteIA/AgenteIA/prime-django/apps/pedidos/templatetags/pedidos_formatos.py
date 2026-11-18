"""Módulo de filtros pessoalizados para uso em templates do Django."""

import decimal
import logging
import re
from datetime import datetime
from pathlib import Path

import markdown as md
import phonenumbers
from django import template
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.template.defaultfilters import stringfilter
from django.utils import timezone

from apps.cartorios.models import Usuario
from apps.comum.utils import formatar_moeda
from apps.home.helpers import decimal_ou_zero, get_data_util_em_x_dias
from apps.home.models import AtoPratica as Ato
from apps.home.models import (
    Colaborador,
    Emolumentos,
    EstadoCivil,
    Event,
    FichaAuxiliar,
    Livro02,
    Livro02Texto,
    Livro03,
    Livro03Garantia,
    Livro03Ligacao,
    Livro05,
    NivelAlerta,
    Pedido,
    PedidoItem,
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

register = template.Library()


# Retornar a data por extenso e outros formatos
@register.filter
def formatar_data_hora(data):
    if not data:
        return ""
    else:
        return data.strftime(settings.DATETIME_FORMAT_STR)


# Retornar a data por extenso e outros formatos
@register.filter(name="formatar_data")
def formatar_data(data, opcao=1):
    from apps.home.utils import formatar_data

    return formatar_data(data, opcao)


# Retornar a opcao escolhida
@register.filter(name="retornar_sim_nao")
def retornar_sim_nao_filter(value):
    conversao = {"S": "Sim", "N": "Não"}

    return conversao.get(value, "")


# Retornar a opcao escolhida - BOOLEAN
@register.filter
@stringfilter
def retornar_sim_nao_boolean(value) -> str:
    # Converte o valor para booleano de acordo com regras específicas, se necessário
    # Nota: Isso assume que 'value' é uma string. Ajuste a lógica conforme necessário para outros tipos de dados.
    true_values = ["true", "1", "sim", "s", "yes", "y"]
    value = value.lower()  # Garante que a comparação seja case-insensitive
    if value in true_values:
        return "Sim"
    else:
        return "Não"


# Retornar a opcao escolhida
@register.filter
@stringfilter
def retornar_sim_nao(value) -> str | None:
    try:
        if value == "S":
            return "Sim"
        elif value == "N":
            return "Não"
        else:
            return ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar os dados da PESSOA - Nome
@register.filter
@stringfilter
def get_cpf(pessoa_id):
    if pessoa_id:
        try:
            return Livro05.objects.get(id=pessoa_id).cpf or ""
        except Livro05.DoesNotExist:
            return ""
    return None


# Retornar os dados dos itens do pedido
@register.filter
def get_total_valor_emolumento_do_item(pedido_item_id) -> str:
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

    if pedido_item is None:
        return ""

    return pedido_item.pedido.valor_emolumento_sum


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
                ],
            )

        return retornos
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar da hipoteca
@register.filter
def get_hipotecas_por_pedido_item(pedido_item_id) -> list:
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
    registro = Livro02.objects.get(pk=imovel_id)
    if registro is None:
        return []

    return registro.lembretes_v2


# Retornar da hipoteca
@register.simple_tag
def get_hipotecas_por_imovel(value, imovel_id: int, as_var=None) -> list:
    try:
        imovel = Livro02.objects.get(pk=imovel_id)
    except Livro02.DoesNotExist:
        return []

    return imovel.hipotecas_v2


# Retornar da Alienacao
@register.filter
def get_alienacoes_por_pedido_item(pedido_item_id: int) -> list:
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

    if pedido_item is None:
        return []

    return pedido_item.imovel.alienacoes_v2


# Retornar da Alienacao
@register.simple_tag
def filtrar_alienacoes_do_imovel(value, imovel_id: int, as_var=None) -> list:
    imovel = Livro02.objects.get(pk=imovel_id)
    return imovel.alienacoes_v2


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
            1 for ligacao in ligacoes if ligacao.figuras.tipo_figura == TipoParte.CREDOR
        )
        qtde_devedor = sum(
            1
            for ligacao in ligacoes
            if ligacao.figuras.tipo_figura == TipoParte.DEVEDOR
        )
        qtde_avalistas = sum(
            1
            for ligacao in ligacoes
            if ligacao.figuras.tipo_figura == TipoParte.AVALISTA
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
        logger.exception(f"ERRO ao obter proprietário atual {e!s}")
        return ""


# Retornar a descricao do origem_evento
@register.filter
@stringfilter
def origem_evento(value):
    return TipoEvento.get_descricao(value)
    # try:
    #     if value == "P":
    #         return "Protocolo"
    #     elif value == "E":
    #         return "Exame Cálculo"
    #     elif value == "C":
    #         return "Pedido Certidão"
    #     elif value == "G":
    #         return "Geral"
    #     else:
    #         return ""
    # except Exception as e:
    #     logger.exception("ERRO")
    #     return ""


# Retornar a descricao do imovel
@register.filter
@stringfilter
def get_descricao_tipo_registro(value):
    return Livro02.get_descricao_tipo_registro(value)


# Retornar a descricao do imovel
@register.filter
@stringfilter
def descricao_tipo_livro(value) -> str | None:
    try:
        if value == "M":
            return "Livro 02"
        elif value == "T":
            return "Transcrição"
        elif value == "I":
            return "Inscrição"
        elif value == "A":
            return "Livro 03"
        else:
            return ""
    except Exception:
        logger.exception("ERRO")
        return ""


@register.filter
@stringfilter
def formatar_numero_registro(matricula):
    if not matricula:
        return ""

    if len(matricula) <= 3:
        return matricula

    return matricula[:-3] + "." + matricula[-3:]


# Retornar o sexo da pessoa
@register.filter
@stringfilter
def lista_sexo(value):
    # Exibir uma tupla com valores igual lista
    return (
        ("M", "Masculino"),
        ("F", "Feminino"),
        ("N", "Não informado"),
    )


# Retornar o sexo da pessoa
@register.filter
@stringfilter
def formato_sexo(value) -> str | None:
    try:
        if value == "M":
            return "Masculino"
        elif value == "F":
            return "Feminino"
        elif value == "N":
            return "Não informado"
        else:
            return ""
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
def tipo_transacao(transacao):
    transacao = str(transacao).split(".")[0]

    try:
        transacao = int(transacao)
    except Exception:
        logger.exception("ERRO")
        transacao = 0

    # Dicionario de estados do BRASIL
    tipo_transacao = {"-1": "", "0": "", "1": "Crédito", "2": "Débito"}

    return tipo_transacao[str(transacao)]


@register.filter
def tipo_cobranca(cobranca):
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


# Retornar Apenas o tipo de documento
@register.filter
@stringfilter
def retornar_documento(numero):
    numero = str(numero).split(".")[0]

    try:
        documento = int(numero)
    except Exception:
        logger.exception("ERRO")
        documento = 0

    # Dicionario de estados do BRASIL
    documentos = {
        "-1": "",
        "0": "CNPJ",
        "1": "CPF",
        "2": "Insc. Produtor Rural",
        "3": "Inscrição Estadual",
        "4": "Outros",
    }

    return documentos[str(documento)]


# Retornar Apenas Numero
@register.filter
@stringfilter
def apenas_numeros(numero):
    return re.sub("[^0-9]", "", numero)


# Formatar CPF para exibir corretamente
@register.filter(name="formatar_documento")
def formatar_documento_filter(value):
    return formatar_documento(value)


# Formatar numero de protocolo corretamente
@register.filter(name="protocolo_formatado")
def protocolo_formatado(numero):
    # Verifica se o número já está no formato desejado usando uma expressão regular
    if re.match(r"^\d{3}\.\d{3}$", str(numero)):
        # Se já está no formato desejado, retorna o número como está
        return numero

    try:
        # Tenta converter o número para um inteiro, descartando qualquer coisa após o ponto
        numero_inteiro = int(str(numero).split(".")[0])
    except ValueError:
        # Em caso de falha na conversão (por exemplo, string não numérica), define o número como 0
        numero_inteiro = 0

    # Formata o número com 3 dígitos antes e depois do ponto, preenchendo com zeros à esquerda
    return f"{numero_inteiro // 1000:03d}.{numero_inteiro % 1000:03d}"


# Formatar numero de protocolo corretamente
@register.filter
@stringfilter
def protocolo_formatado_apenas_numeros(numero):
    return apenas_numeros(numero)


@register.filter
@stringfilter
def get_valor_atual(value):
    # print(value)
    # import time

    return value


@register.filter(name="formatar_moeda")
def formatar_moeda_filter(valor, incluir_simbolo=None) -> str:
    incluir_simbolo = incluir_simbolo is None
    return formatar_moeda(valor, incluir_simbolo)


def get_data_atual() -> str:
    data_atual = timezone.now().date()
    return data_atual.strftime(settings.DATE_FORMAT_STR)


def get_data_atual_separada_por_pontos() -> str:
    data_atual = timezone.now().date()
    return data_atual.strftime(settings.DATE_FORMAT_STR).replace("/", ".")


def get_data_atual_separada_por_tracos() -> str:
    data_atual = timezone.now().date()
    return data_atual.strftime(settings.DATE_FORMAT_STR).replace("/", "-")


# Verificar data
@register.filter
@stringfilter
def verificar_data_fase(data: str) -> int:
    # Tentativa de analisar a data no formato 'YYYY-MM-DD'
    try:
        data_1 = datetime.strptime(data, "%Y-%m-%d").date()
    except ValueError:
        # Se falhar, tenta o formato 'DD/MM/YY'
        try:
            data_1 = datetime.strptime(data, settings.DATE_FORMAT_STR).date()
        except ValueError:
            # Se ambas as tentativas falharem, retorne um valor indicando o erro
            return "-1"  # ou lance uma exceção pessoalizada

    # Obtenção da data atual no formato correto (ajuste conforme necessário)
    data_2 = datetime.strptime(
        str(get_data_atual_separada_por_tracos()),
        "%d-%m-%y",
    ).date()

    # Comparação das datas
    if data_1 > data_2:
        # Data da fase maior que data atual
        return 0
    elif data_1 == data_2:
        # Datas são iguais
        return 1
    else:
        # Data atual maior
        return 2


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
        formatar_data = data_objeto.strftime(settings.DATE_FORMAT_STR)

        # Verificação de data vazia
        if formatar_data == "01/01/1899":
            return ""

        return formatar_data
    except ValueError:
        logger.exception("ERRO ao converter data: ")
        return ""


@register.filter
def remover_numero_texto(valor):
    numero = protocolo_formatado(apenas_numeros(valor))
    """Remover pontos de uma string."""
    return str(valor).replace(numero, "")


@register.filter
def remover_pontuacao(valor):
    """Remover ponto e vírgula de uma string, bem como sufixos ".00" e ",00"."""
    valor_str = str(valor)
    return (
        valor_str.replace(".00", "")
        .replace(",00", "")
        .replace(".", "")
        .replace(",", "")
    )


# Formatar para retornar o numero inteiro
@register.filter
@stringfilter
def numero_inteiro(valor):
    # print("valor", valor)
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
    estado_civil_regime_model = apps.get_model("home", "TipoRegimeCasamento")
    return estado_civil_regime_model.objects.lista_tipo_regime_casamento()


# Retornar se existe texto
@register.filter
@stringfilter
def get_texto_imovel(value) -> int:
    return Livro02Texto.objects.filter(pedido_item_id=value).count()


@register.filter
@stringfilter
def pedido_item_possui_nota_devolucao(pedido_item_id: int) -> bool:
    nota_devolucao_model = apps.get_model("home", "NotaDevolucaoTexto")
    return nota_devolucao_model.objects.filter(pedido_item_id=pedido_item_id).exists()


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
    # Converter queryset para uma list
    return list(
        EstadoCivil.objects.filter(Q(exibir="S"))
        .values_list("id", "descricao_estado_civil")
        .order_by("descricao_estado_civil"),
    )


# Retornar o estado_civil regime PESSOA
@register.filter
def get_descricao_tipo_regime_casamento(pk):
    descricao = ""
    if str(pk).isdigit():
        descricao = TipoRegimeCasamento.objects.get_descricao_por_id(pk)
    return descricao if descricao else ""


@register.filter
def get_id_regime_bens_filter(descricao_regime):
    from models import get_regime_bens

    return get_regime_bens(descricao_regime)


# Retornar o estado_civil PESSOA
@register.filter
def get_descricao_estado_civil(estado_civil_id) -> str:
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
    except ValueError as e:
        logger.exception(f"ID de estado_civil_id {estado_civil_id} inválido: {e}")
        estado_civil_id = 1  # Valor padrão em caso de erro

    estado_civil = EstadoCivil.objects.filter(id=estado_civil_id).first()

    if estado_civil:
        return estado_civil.descricao_estado_civil

    return ""


# Retornar o estado_civil PESSOA
@register.filter
@stringfilter
def get_estado_civil_pela_descricao(descricao_estado_civil):
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
    """Obtém o nome do funcionário com base na chave fornecida."""
    try:
        if pk in ["", "None", "home"]:
            return ""

        cache_key = f"funcionario_nome_{pk}"
        nome = cache.get(cache_key)

        if nome is None:
            funcionario = Colaborador.objects.get(pk=pk)
            nome = funcionario.nome
            # Armazenar no cache por 300 segundos
            cache.set(cache_key, nome, 300)

        return Colaborador.get_nome_mapeado(nome)
    except Colaborador.DoesNotExist:
        logger.exception(f"Funcionário não encontrado: {pk}")
        return ""
    except Exception:
        logger.exception("ERRO ao buscar nome do funcionário: ")
        return ""


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
def get_selos_pelo_pedido_item_id(pedido_item_id: int) -> str:
    try:
        selo = SeloEletronico.objects.filter(pedido_item=pedido_item_id).first()

        return selo.codigo_sequencial_unico if selo else ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar a classe do imovel DESCRITA
# @register.filter
# @stringfilter
# def get_descricao_classe_registro_pela_letra(tipo: str) -> str:
#     if str(tipo) is not None:
#         if str(tipo) == "L":
#             return "Lote"
#         elif str(tipo) == "U":
#             return "Urbano"
#         elif str(tipo) == "R":
#             return "Rural"
#         else:
#             return ""
#     else:
#         return ""


# # Retornar o imovel
# @register.filter
# @stringfilter
# def verificar_se_registro_encerrado(value: str) -> str:
#     return "Sim" if value == "T" else "Não"


# def preload_data(pedido_item_id) -> None:
#     data = {}
#     # Aqui, você preenche o dicionário "data" com todos os campos necessários
#     # usando suas consultas otimizadas.
#     # 300 segundos = 5 minutos de cache
#     cache.set(pedido_item_id, data, 300)


# Retornar a classe do imóvel
@register.filter
@stringfilter
def get_classe_do_imovel_pelo_pedido_item_id(pedido_item_id):
    """Obtém a classe do imóvel com base na chave de pedidos e itens fornecida."""
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
                classe_imovel = 0

        except PedidoItem.DoesNotExist:
            classe_imovel = 0
        except Exception:
            logger.exception("ERRO")
            classe_imovel = 0

    return classe_imovel


# # Retornar o DOI praticado
# @register.filter
# @stringfilter
# def get_numero_doi_pelo_pedido_item_id(pedido_item_id: int) -> int:
#     try:
#         pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
#         ato_doi = pedido_item.ato.codigo_doi_id
#         return ato_doi if ato_doi else 0
#     except Exception:
#         logger.exception("ERRO")
#         return 0


# # Retornar o Ato praticado
# @register.filter
# @stringfilter
# def get_ato_praticado_pelo_pedido_item_id(pedido_item_id: int) -> str:
#     """Obtém o ato praticado com base na chave de pedidos e itens fornecida."""
#     try:
#         cache_key = f"ato_praticado_{pedido_item_id.replace(' ', '_')}"
#         ato_praticado = cache.get(cache_key)

#         if ato_praticado:
#             return ato_praticado

#         pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

#         ato_praticado = pedido_item.ato.tipo_ato

#         if ato_praticado:
#             cache.set(
#                 cache_key,
#                 ato_praticado,
#                 300,
#             )  # Armazenar no cache por 300 segundos
#             return ato_praticado
#         else:
#             return ""
#     except Exception:
#         logger.exception("ERRO")
#         return pedido_item_id


# Retornar o Codigo da Tabela


# @register.filter
# @stringfilter
# def get_codigo_da_tabela_pelo_pedido_item(pedido_item) -> str:
#     try:
#         pedido_item = PedidoItem.objects.filter(pk=pedido_item.pk).first()

#         if pedido_item:
#             codigo_tabela = pedido_item.codigo_tabela
#             return codigo_tabela if codigo_tabela else ""
#     except Exception:
#         logger.exception("ERRO")
#         return ""


# # Retornar o numero do cartorio
# @register.filter
# @stringfilter
# def get_numero_do_cartorio_pelo_pedido_item_id(pedido_item_id: int) -> str:
#     """Obtém o número do cartório (RI) com base no pedido_item_id fornecido."""
#     cache_key = f"numero_ri_{pedido_item_id}"
#     numero_ri = cache.get(cache_key)

#     if numero_ri:
#         return numero_ri

#     try:
#         pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

#         if pedido_item:
#             numero_ri = pedido_item.numero_ri

#         if numero_ri:
#             # Armazenar no cache por 300 segundos
#             cache.set(cache_key, numero_ri, 300)
#             return numero_ri
#         else:
#             return ""
#     except Exception:
#         logger.exception("ERRO")
#         return ""


@register.filter
def get_numero_registro_por_pedido(pedido_item_id: int) -> str:
    """
    Recupera o número do registro associado a um item de pedido.

    :param pedido_item_id: chave do item de pedido para filtrar.
    :return: número do registro ou string vazia em caso de erro ou não encontrado.
    """
    valor_decimal = decimal_ou_zero(pedido_item_id)

    try:
        # Obter o número do registro diretamente do PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=valor_decimal).first()

        return pedido_item.numero_registro if pedido_item else 0.00

    except Exception:
        logger.exception("ERRO ao obter número do registro")
        return 0.00


# Retornar o tipo_registro
@register.filter
def get_tipo_de_registro_pelo_pedido_item_id(pedido_item_id: int) -> str:
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        return pedido_item.tipo_registro if pedido_item.tipo_registro else ""
    except Exception:
        logger.exception("ERRO ao obter tipo de registro")


# Retornar o numero do ATO
@register.filter
def get_numero_do_ato_pelo_pedido_item_id(pedido_item_id: int) -> str:
    try:
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        if pedido_item:
            return pedido_item.numero_ato if pedido_item.numero_ato else ""
    except Exception:
        return ""


# # Retornar o numero do PEDIDO
# @register.filter
# def get_id_pedido(pedido_item_id: int) -> int:
#     try:
#         pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
#         return pedido_item.pedido if pedido_item else 0
#     except Exception:
#         return 0


# @register.filter
# def get_pedido(pedido_item_id):
#     pedidos = PedidoItem.objects.filter(pk=pedido_item_id).values("pedido").first()
#     return pedidos["pedido"] if pedidos else None


# Retornar o Ato Praticado
@register.filter
@stringfilter
def get_descricao_do_ato(ato) -> str:
    tipoato = ""

    try:
        ato = Ato.objects.filter(pk=ato).first()

        tipoato = ato.tipo_ato

        if str(tipoato) is not None:
            return tipoato
        else:
            return ""
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar o get_usuario_autenticado
@register.filter
@stringfilter
def get_usuario_autenticado(auth_user_id: int) -> str:
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


# Retornar o
@register.filter
@stringfilter
def tipo_ato_padrao(pedido_item_id: int) -> str | None:
    tipoato = "Registro"

    try:
        # Filtrando o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        if pedido_item:
            tipoato = pedido_item.ato.tipo

        if tipoato == "A":
            return "Averbação"
        elif tipoato == "R":
            return "Registro"
        elif tipoato == "M":
            return "Matrícula"
        else:
            return "Registro"
    except Exception:
        return "Registro"


# Retornar o
@register.filter
@stringfilter
def tipo_ato_padrao_id(pedido_item_id: int) -> str:
    try:
        # Filtrando o PEDIDO ITEM
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        # Filtrando o ATO
        ato = pedido_item.ato

        if ato.tipo == "A":
            return "A"
        elif ato.tipo == "R":
            return "R"
        elif ato.tipo == "M":
            return "M"
        else:
            return "R"
    except Exception:
        logger.exception("ERRO")
        return "R"


@register.filter(name="capitalizar")
def capitalizar(value: str) -> str:
    return formatar_nome(value)


@register.filter(name="get_loteamento_pelo_imovel")
@stringfilter
def get_loteamento_pelo_imovel_filter(value):
    return get_loteamento_pelo_imovel(value)


# Buscar Dados do Loteamento
def get_loteamento_pelo_imovel(imovel_id) -> list:
    lista = []

    # registro_anterior_id = str(registro_anterior_id).split('.')[0]

    # Filtrando o IMOVEL
    imovel = Livro02.objects.filter(pk=imovel_id).first()

    # FIltrando os dados do loteamento
    ficha = FichaAuxiliar.objects.filter(pk=imovel_id).first()

    # Criando uma lista temporária
    temp_list = []

    if imovel:
        temp_list.extend(
            [
                imovel.tipo or "",
                imovel.numero or "",
                imovel.cartorio or "",
            ],
        )

    if ficha:
        temp_list.extend(
            [
                ficha.nome or "",
                ficha.nome_incorporadora or "",
                ficha.data_incorporacao or "",
            ],
        )

    lista.append(temp_list)

    return lista


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


# Retornar os dados da pessoa
@register.simple_tag
def get_livro02_por_pessoa(value, pessoa_id, as_var=None):
    return Vinculo.objects.filter(pessoa=pessoa_id).order_by("numero_ato")


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
        return numero


@register.filter(name="formatar_telefone")
def formatar_telefone_filter(numero):
    return formatar_telefone(numero)


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

    data_hora, max_dias = pedido.get_prazo_em_dias()

    return get_data_util_em_x_dias(data_hora, max_dias)


@register.filter
@stringfilter
def proxima_data_valida(pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)

    data_hora, max_dias = pedido.get_prazo_em_dias(opcao="V")

    return get_data_util_em_x_dias(data_hora, max_dias + 1)


@register.filter
@stringfilter
def primeira_data_exigencia(pedido_id):
    pedido = Pedido.objects.get(pk=pedido_id)

    data_hora, max_dias = pedido.get_prazo_em_dias(opcao="N")

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
    data_atual = timezone.now().date()

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


# Verificar se faz parte do EXIGENCIA
@register.filter(name="verificar_servicos_exigencia")
def verificar_servicos_exigencia_filter(servicos_id) -> int:
    for item in TipoAndamento.objects.get_ids_de_tipo_exigencia():
        if int(item) == int(servicos_id):
            return 1
    return 0


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
def get_eventos_do_protocolo(protocolo, titulo_do_evento):
    lista_eventos = []

    try:
        return Event.objects.filter(
            numero=protocolo.numero_protocolo,
            title=titulo_do_evento,
        )

    except Exception:
        return lista_eventos


# Retornar os colaboradores que serao avisados sobre PROTOCOLO DIGITALIZAR
@register.filter
def get_usuarios_para_notificar_digitalizacao():
    # Utiliza values_list para obter diretamente uma lista dos IDs, com flat=True para obter uma lista simples, não uma lista de tuplas.
    return Usuario.objects.filter(avisar_digitalizar="S")


# Retornar os colaboradores que serao avisados sobre PROTOCOLO VENCENDO
@register.filter
def get_usuarios_para_notificar_protocolo_vencendo() -> list:
    return Usuario.get_usuarios_ids_para_notificar_protocolo_vencendo()


# Retornar os colaboradores que serao avisados sobre PROTOCOLO NOTA DEVOLUCAO ANEXADA
@register.filter
def get_usuarios_para_notificar_nota_de_devolucao() -> list:
    return Usuario.get_usuarios_ids_para_notificar_nota_de_devolucao()


# Retornar os colaboradores que serao avisados sobre PROTOCOLO VENCENDO
@register.filter
def get_usuarios_para_notificar_protocolo_assinar():
    return Usuario.get_usuarios_para_notificar_protocolo_assinar()


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
def get_apenas_nome_do_arquivo(filename):
    return str(Path(filename).name)


@register.filter(name="markdown")
def markdown_format(text):
    return md.markdown(text, extensions=["markdown.extensions.fenced_code"])


# Retornar o provisorio
@register.filter
@stringfilter
def retirar_provisorio(value):
    if str(value).upper() in ["PROVISÓRIO", "PROVISORIO"]:
        return ""
    else:
        return value


@register.filter
def internacionalizar_telefone(value):
    # Remove caracteres não-numéricos
    numero = re.sub(r"\D", "", value)
    # Adiciona o código do país se não estiver presente (assumindo Brasil como +55)
    if not numero.startswith("55"):
        numero = "55" + numero
    return numero


# OBTER O DATA DO PROTOCOLO PELO NUMERO DO PROTOCOLO
@register.filter
def get_data_protocolo(numero_protocolo):
    from apps.home.models import Livro01Protocolo

    return Livro01Protocolo.objects.get(
        numero_protocolo=numero_protocolo,
    ).data_protocolo


@register.filter
def get_data_prevista_protocolo(numero_protocolo):
    from apps.home.models import Livro01Protocolo

    return Livro01Protocolo.objects.get(
        numero_protocolo=numero_protocolo,
    ).data_protocolo


@register.filter
def get_data_prevista(numero_protocolo):
    from apps.home.models import Livro01Protocolo

    protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)
    return proxima_data_prevista(protocolo.pedido_id)


@register.filter
def get_data_agendamento(numero_protocolo):
    from apps.home.models import Livro01Protocolo

    try:
        data_agendamento = (
            Livro01Protocolo.objects.filter(numero_protocolo=numero_protocolo)
            .values_list("data_agendamento", flat=True)
            .first()
        )
        return data_agendamento if data_agendamento is not None else None
    except Livro01Protocolo.DoesNotExist:
        return None
