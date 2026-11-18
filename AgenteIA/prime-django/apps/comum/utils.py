"""
utils.py.

Módulo de utilitários para funções de validação e outras operações comuns que são reutilizadas em diferentes partes do projeto.

"""

import decimal
import logging
import re
from datetime import datetime, timedelta

import phonenumbers
from babel.numbers import format_currency
from django.conf import settings
from workalendar.america.brazil import Brazil

from apps.comum.models import Feriado
from apps.home.padroes import BR, FORMATO_MONETARIO, LOCALIDADE, MOEDA

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def valida_cpf(cpf: str) -> bool:
    """Valida CPFs formatados (com ou sem pontos e traço) e retorna True se válido e False se inválido."""
    # Remove caracteres não numéricos
    # cpf = "".join(filter(str.isdigit, cpf))
    cpf = limpar_documento(cpf)

    # CPFs com tamanho diferente de 11 ou com todos os dígitos iguais são inválidos
    if len(cpf) != settings.CPF_LENGTH or cpf == cpf[0] * settings.CPF_LENGTH:
        return False

    # Calcula e verifica primeiro dígito verificador
    soma = sum(int(a) * b for a, b in zip(cpf, range(10, 1, -1), strict=False))
    digito_1 = (soma * 10) % 11
    digito_1 = 0 if digito_1 == 10 else digito_1

    # Calcula e verifica segundo dígito verificador
    soma = sum(int(a) * b for a, b in zip(cpf, range(11, 1, -1), strict=False))
    digito_2 = (soma * 10) % 11
    digito_2 = 0 if digito_2 == 10 else digito_2

    return cpf[-2:] == f"{digito_1}{digito_2}"


def mascarar_documento(documento) -> str:
    if not documento:
        return ""

    documento = limpar_documento(str(documento))

    tamanho = len(documento)

    if tamanho == settings.CPF_LENGTH:  # Se for CPF
        return f"{documento[:3]}.***.***-{documento[-2:]}"
    elif tamanho == settings.CNPJ_LENGTH:
        return f"{documento[:2]}.***.***.***/{documento[8:12]}-{documento[-2:]}"
    else:  # Se for outro tipo de documento
        inicio = documento[:2] if tamanho > 4 else documento[:1]
        fim = documento[-2:] if tamanho > 4 else documento[-1:]
        return f"{inicio}***{fim}"


def calcular_conclusao_horas_uteis(hora_inicio, horas_uteis):
    """Calcula a data e hora de conclusão de um prazo em horas úteis."""
    calendario = CalendarioBrasileiroPersonalizado()
    hora_atual = hora_inicio
    while horas_uteis > 0:
        # Verifica se o dia atual é um dia útil
        if calendario.is_working_day(hora_atual.date()):
            hora_fim_dia = hora_atual.replace(
                hour=17,
                minute=0,
                second=0,
                microsecond=0,
            )
            horas_restantes_dia = (hora_fim_dia - hora_atual).seconds / 3600

            if horas_uteis <= horas_restantes_dia:
                return hora_atual + timedelta(hours=horas_uteis)
            else:
                horas_uteis -= horas_restantes_dia

        # Avança para o próximo dia útil
        hora_atual = (hora_atual + timedelta(days=1)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )

    return hora_atual


def calcular_data_conclusao(data_inicio, dias_uteis):
    calendario = CalendarioBrasileiroPersonalizado()
    data_atual = data_inicio

    while dias_uteis > 0:
        data_atual += timedelta(days=1)
        if calendario.is_working_day(data_atual):
            dias_uteis -= 1

    return data_atual


class CalendarioBrasileiroPersonalizado(Brazil):
    """
    Classe de calendário personalizada para incluir feriados personalizados.
    Os feriados devem ser cadastrados no banco de dados através do modelo Feriado.
    """

    # Adicionando novos feriados personalizados
    def get_custom_holidays(self):
        feriados_personalizados = Feriado.objects.all()
        return [(feriado.data, feriado.nome) for feriado in feriados_personalizados]

    # Sobrescrevendo o método de feriados para incluir os personalizados
    def holidays(self, year=None):
        holidays = super().holidays(year)
        holidays.extend(self.get_custom_holidays())
        return holidays


def calcular_data_com_workalendar(data_inicio, prazo_em_dias):
    # Criar uma instância
    br_calendar = CalendarioBrasileiroPersonalizado()

    # Adiciona dias úteis à data de início
    return br_calendar.add_working_days(data_inicio, prazo_em_dias)

    # Exemplo de uso
    """
    data_inicio = datetime(2024, 1, 1)  # 1 de Janeiro de 2024
    prazo_em_dias = 10  # Exemplo: 10 dias úteis de prazo
    data_final_calculada = calcular_prazo_final_com_workalendar(data_inicio, prazo_em_dias)
    print(data_final_calculada)
    """
    return None


def formatar_telefone(numero, pais=BR) -> str:
    """Formata um número de telefone para o formato nacional do país."""
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


def limpar_documento(documento: str) -> str:
    """
    Remove todos os caracteres que não são dígitos de um documento.

    Args:
    ----
        documento (str): O documento a ser limpo.

    Returns:
    -------
        str: O documento contendo apenas dígitos.

    """
    return re.sub(r"\D", "", documento)


def formatar_moeda(valor: decimal.Decimal, incluir_simbolo: bool = True) -> str:
    """
    Formata um valor como moeda, com a opção de incluir ou não o símbolo da moeda.

    :param valor: Valor a ser formatado
    :param incluir_simbolo: Se deve incluir o símbolo da moeda no formato
    :return: Valor formatado como moeda
    """
    # Verifica se o valor é None, vazio ou inválido
    if valor is None or valor == "None" or valor == "":
        valor = decimal.Decimal(0)

    # Tenta converter o valor para decimal
    try:
        valor_decimal = decimal.Decimal(valor)
    except (decimal.InvalidOperation, TypeError) as e:
        logger.exception(f"ERRO ao converter {valor} para decimal: {e}")
        valor_decimal = decimal.Decimal(0)

    # Formata o valor com ou sem símbolo da moeda
    if incluir_simbolo:
        formatado = format_currency(valor_decimal, MOEDA, locale=LOCALIDADE)
    else:
        formatado = format_currency(
            valor_decimal,
            MOEDA,
            locale=LOCALIDADE,
            currency_digits=False,
            format=FORMATO_MONETARIO,
        )

    return formatado


def converter_data_para_formato_de_modelo(data: str) -> str:
    """Converte uma data no formato 'dd/mm/aaaa' para o formato 'aaaa-mm-dd'."""
    if not data or data.strip() == "" or data == "None":
        # Verificação de data vazia ou nula e retorno de string vazia
        return ""

    try:
        data_objeto = datetime.strptime(data.split(" ")[0], "%Y-%m-%d")
        data_formatada = data_objeto.strftime(settings.DATE_FORMAT_STR)

        # Verificação de data vazia
        if data_formatada == "01/01/1899":
            return ""

        return data_formatada
    except ValueError as e:
        logger.exception(
            f"ERRO ao converter data {data} para o formato de modelo aaaa-mm-dd. {e}",
        )
        return ""
