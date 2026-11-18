import re
from decimal import Decimal
from functools import lru_cache

from django.apps import apps


def remover_caracteres_nao_numericos(valor):
    return re.sub(r"\D", "", str(valor))


def formatar_documento(value, tipo=None):
    """Adiciona mascara ao documento (CPF ou CNPJ) no formato padrão."""
    if not value:
        return ""

    value = remover_caracteres_nao_numericos(value)

    if tipo == "CPF" or len(value) == 11:
        return f"{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}"
    elif tipo == "CNPJ" or len(value) == 14:
        return f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}"
    else:
        return value


def configurar_cpf_cnpj(value) -> tuple:
    value = remover_caracteres_nao_numericos(value)

    if len(value) == 11:
        return "CPF", formatar_documento(value, "CPF")
    elif len(value) == 14:
        return "CNPJ", formatar_documento(value, "CNPJ")
    else:
        return "", value or ""


def formatar_documento_com_descricao(value, descricao):
    if value:
        return f"{descricao}: {formatar_documento(value)}"
    return ""


def formatar_documento_com_descricao(value):
    if value:
        Configuracao = apps.get_model("home", "Configuracao")

        tipo, valor = configurar_cpf_cnpj(value)
        if tipo == "CPF":
            return f"{valor}", Configuracao.obter("DESCRICAO_CPF_ID", "CPF")
        elif tipo == "CNPJ":
            return f"{valor}", Configuracao.obter("DESCRICAO_CPF_ID", "CNPJ")
    return ""


def mascarar_documento(documento) -> str:
    if not documento:
        return "Documento não informado"

    tamanho = len(documento)

    if tamanho == 11:  # Se for CPF
        return f"{documento[:3]}.***.***-{documento[-2:]}"
        # return f"{documento[0:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:11]}"
    elif tamanho == 14:
        return f"{documento[:2]}.***.***.***/{documento[8:12]}-{documento[-2:]}"
        # return f"{documento[0:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:14]}"
    else:  # Se for outro tipo de documento
        inicio = documento[:2] if tamanho > 4 else documento[:1]
        fim = documento[-2:] if tamanho > 4 else documento[-1:]
        return f"{inicio}***{fim}"


@lru_cache(maxsize=None)  # Cache ilimitado, ajuste o maxsize conforme necessário
def get_palavras_minimas() -> set:
    """
    Retorna uma lista de palavras que não devem ser capitalizadas.
    """
    from apps.home.models import Configuracao

    # Busca a configuração uma vez e cacheia o resultado
    return Configuracao.obter(
        "palavras_para_manter_minuscula",
        {
            "de",
            "da",
            "do",
            "dos",
            "das",
            "e",
        },
    )


def formatar_nome(nome: str) -> str:
    """
    Formata um nome, capitalizando a primeira letra de cada palavra, exceto palavras específicas.

    :param nome: Nome a ser formatado
    :return: Nome formatado
    """
    if not nome:
        return nome

    palavras_minimas = get_palavras_minimas()

    # Converte o nome para minúsculo
    palavras = nome.lower()

    # Remove espaços extras entre palavras
    palavras = re.sub(r"\s+", " ", palavras)

    # Remove espaços no início e no final da string
    palavras = palavras.strip()

    # Divide o nome em palavras
    palavras = palavras.split(" ")

    # Capitalizar a primeira letra de cada palavra, exceto as específicas
    return " ".join(palavra.capitalize() if palavra not in palavras_minimas else palavra for palavra in palavras)


def somente_numeros(value: str) -> str:
    return re.sub(r"\D", "", str(value))


def formatar_valor_real_br(value) -> str:
    # Verifica se o valor é None ou não pode ser convertido para Decimal
    try:
        decimal_value = Decimal(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return "0,00"

    # Formata o valor para o formato de moeda brasileiro
    return f"{decimal_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
