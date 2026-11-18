import logging
from decimal import ROUND_HALF_UP, Decimal

import phonenumbers

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


def formatar_telefone(numero, pais="BR") -> str:
    """
    Formata um número de telefone de acordo com o padrão nacional do país especificado.

    Args:
    ----
        numero (str): O número de telefone a ser formatado.
        pais (str, optional): O código de duas letras do país para o qual o número de telefone deve ser formatado.
        Padrão é "BR" para Brasil.

    Returns:
    -------
        str: Número de telefone formatado no padrão nacional.

    Raises:
    ------
        ValueError: Se o número de telefone fornecido for inválido ou não puder ser analisado.

    Examples:
    --------
        >>> formatar_telefone("+5511999998888")
        '(11) 99999-8888'

        >>> formatar_telefone("1234", "US")
        ValueError: Número de telefone inválido: 1234

    """
    if not numero:
        return ""

    try:
        telefone = phonenumbers.parse(numero, pais)
        if phonenumbers.is_valid_number(telefone):
            return phonenumbers.format_number(
                telefone,
                phonenumbers.PhoneNumberFormat.NATIONAL,
            )
        else:
            return f"{numero}"
    except phonenumbers.NumberParseException:
        return "Não foi possível analisar o número de telefone."


def mascarar_documento(documento) -> str:
    ## COMENTANDO POR HORA PARA NÃO DAR ERRO NOS OUTROS RELATORIOS

    if not documento:
        return "Documento não informado"

    tamanho = len(documento)

    if tamanho == 11:  # Se for CPF
        # return f"{documento[:3]}.***.***-{documento[-2:]}"
        return f"{documento[0:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:11]}"
    elif tamanho == 14:
        # return f"{documento[:2]}.***.***.***/{documento[8:12]}-{documento[-2:]}"
        return f"{documento[0:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:14]}"
    else:  # Se for outro tipo de documento
        inicio = documento[:2] if tamanho > 4 else documento[:1]
        fim = documento[-2:] if tamanho > 4 else documento[-1:]
        return f"{inicio}***{fim}"


def arredondar_decimal_bancario(valor: Decimal) -> Decimal:
    """
    Arredonda um valor para duas casas decimais usando o método de arredondamento bancário.

    O arredondamento bancário, ou ROUND_HALF_UP, arredonda o valor para o número inteiro
    mais próximo que é maior, no caso de o número estar exatamente no meio do caminho
    entre dois números inteiros. Este método é comumente utilizado em operações financeiras
    e contábeis para garantir um arredondamento menos tendencioso ao longo do tempo.

    Parâmetros:
        valor (float ou str): O valor a ser arredondado. Pode ser um número em formato
        de ponto flutuante ou uma string representando um número decimal.

    Retorna:
        Decimal: O valor arredondado para duas casas decimais.

    Exemplos:
        >>> arredondar_valor_bancario(2.335)
        Decimal('2.34')

        >>> arredondar_valor_bancario("3.145")
        Decimal('3.15')
    """
    valor_decimal = Decimal(valor)
    return valor_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def importar_atos_do_e_vincular_id_antigo(self, atos) -> None:
    pass
