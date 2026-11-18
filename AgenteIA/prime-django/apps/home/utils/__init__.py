# https://www.quora.com/How-can-I-find-and-replace-text-in-a-Word-document-using-Python
# https://gist.github.com/adejones/a6d42984f66ea9990d78974531863bee
# https://stackoverflow.com/questions/25228106/how-to-extract-text-from-an-existing-docx-file-using-python-docx
# https://stackoverflow.com/questions/24805671/how-to-use-python-docx-to-replace-text-in-a-word-document-and-save
# https://pt.stackoverflow.com/questions/315783/substituir-lista-de-palavras-em-um-texto
# https://python-docx.readthedocs.io/en/latest/api/text.html?highlight=replace
# https://stackoverflow.com/questions/54928806/python-populate-a-docx-table-with-docxtemplate
# https://www.thepythoncode.com/article/convert-pdf-files-to-docx-in-python
# https://www.thepythoncode.com/article/convert-pdf-files-to-images-in-python
# https://www.thepythoncode.com/article/extract-pdf-metadata-in-python
# https://www.thepythoncode.com/article/replace-text-in-docx-files-using-python
import logging
import re
from calendar import HTMLCalendar
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
#from weasyprint import HTML

logger = logging.getLogger(__name__)


class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None) -> None:
        self.year = year
        self.month = month
        super().__init__()

    # formats a day as a td
    # filter events by day
    def formatday(self, day, events) -> str:
        events_per_day = events.filter(start_time__day=day)
        d = ""
        for event in events_per_day:
            d += f"<li> {event.get_html_url} </li>"

        if day != 0:
            return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"
        return "<td></td>"

    # formats a week as a tr
    def formatweek(self, theweek, events) -> str:
        week = ""
        for d, _weekday in theweek:
            week += self.formatday(d, events)
        return f"<tr> {week} </tr>"

    # formats a month as a table
    # filter events by year and month
    def formatmonth(self, withyear=True):
        from apps.home.models import Event

        events = Event.objects.filter(
            start_time__year=self.year,
            start_time__month=self.month,
        )

        cal = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f"{self.formatmonthname(self.year, self.month, withyear=withyear)}\n"
        cal += f"{self.formatweekheader()}\n"
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f"{self.formatweek(week, events)}\n"
        return cal


def somente_numeros_ou_zero(entrada):
    """
    Recebe uma entrada e retorna apenas os números presentes na entrada.

    :param entrada: String de entrada da qual os números serão extraídos.
    :return: apenas os dígitos presentes na entrada.
    """
    if entrada is None:
        return 0

    if isinstance(entrada, int | float):
        return entrada

    try:
        # Tenta executar a limpeza da entrada e retornar apenas números.
        return re.sub(r"\D", "", str(entrada))
    except Exception:
        # Em caso de exceção, retorna uma string vazia.
        logger.exception("ERRO ao processar a entrada: ")  # Opcional: Loga a exceção.
        return 0


def somente_numeros_ou_none(entrada):
    """
    Recebe uma entrada e retorna apenas os números presentes na entrada.

    :param entrada: String de entrada da qual os números serão extraídos.
    :return: apenas os dígitos presentes na entrada.
    """
    if entrada is None:
        return None

    if isinstance(entrada, int | float):
        return entrada

    try:
        return re.sub(r"\D", "", str(entrada))
    except Exception:
        logger.exception("ERRO ao processar a entrada: ")
        return None


def converter_para_int(valor, valor_padrao=0):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return valor_padrao


def converter_para_decimal(valor, valor_padrao=Decimal("0.0")):
    if not valor:
        return valor_padrao
    try:
        # Converte o valor para Decimal, o que é ideal para valores monetários
        return Decimal(valor)
    except (ValueError, TypeError, InvalidOperation):
        # Retorna um valor padrão Decimal('0.0') caso a conversão falhe
        return valor_padrao


def verificar_string_vazia(valor):
    """
    Verifica se o valor de entrada é None ou uma string vazia (incluindo strings com apenas espaços em branco).
    Retorna uma string vazia se for o caso, ou a string original sem espaços extras no início ou no fim.

    :param valor: O valor a ser verificado.
    :return: Uma string vazia ou a string original sem espaços extras.
    """
    if valor is None or str(valor).strip() == "":
        return ""
    else:
        return str(valor).strip()


def substituir_none_por_valor_padrao(valor, valor_padrao=0, tipo="int"):
    """
    Verifica se o valor é None ou a string "None" e substitui por um valor padrão numérico.
    Pode tratar o valor como int, float ou Decimal, conforme especificado.

    :param valor: O valor a ser verificado.
    :param valor_padrao: O valor padrão numérico a ser usado se `valor` for None ou "None".
    :param tipo: O tipo numérico desejado para o valor de retorno ('int', 'float', 'Decimal').
    :return: O valor numérico apropriado.
    """
    str_valor = str(valor).strip().lower()
    if str_valor in ["none", ""]:
        if tipo == "int":
            return int(valor_padrao)
        elif tipo in ("float", "Decimal"):
            return Decimal(valor_padrao)
        else:
            msg = f"Tipo '{tipo}' não é suportado."
            raise ValueError(msg)
    elif tipo == "int":
        return int(valor)
    elif tipo in ("float", "Decimal"):
        return Decimal(valor)
    else:
        msg = f"Tipo '{tipo}' não é suportado."
        raise ValueError(msg)


def limpar_se_invalido(valor):
    """
    Verifica se o valor é None, 'None' (independente de maiúsculas ou minúsculas), ou uma string vazia.
    Retorna uma string vazia se qualquer uma das condições for verdadeira, caso contrário, retorna o valor original.

    :param valor: O valor a ser verificado.
    :return: Uma string vazia ou o valor original.
    """
    if (
        valor is None
        or str(valor).strip().upper() == "NONE"
        or str(valor).strip() == ""
    ):
        return ""
    else:
        return valor


def substituir_none_por_vazio(valor):
    """
    Verifica se o valor é a string "None" (independente de maiúsculas ou minúsculas)
    e substitui por uma string vazia. Se não, retorna o valor original.

    :param valor: O valor a ser verificado e possivelmente modificado.
    :return: Uma string vazia se o valor for "None", ou o valor original caso contrário.
    """
    if valor is None:
        return ""
    valor_str = str(valor)
    return valor_str.replace("None", "").replace("none", "")


def tentar_converter_para_int_ou_padrao(valor, funcao_valor_padrao):
    """
    Tenta converter o valor fornecido para um inteiro. Se a conversão falhar,
    chama a função fornecida para obter um valor padrão.

    :param valor: O valor a ser convertido para inteiro.
    :param funcao_valor_padrao: Função que será chamada para obter o valor padrão, caso a conversão falhe.
    :return: O valor convertido para inteiro ou o valor padrão obtido pela função.
    """
    try:
        return int(valor)
    except Exception:
        logger.exception("ERRO")
        return funcao_valor_padrao()


# https://docs.python.org/pt-br/3.7/library/datetime.html
def data_valida(data) -> bool | None:
    data_temp = str(data)
    data_temp = str(data_temp).replace(".", "")
    data_temp = str(data_temp).replace("/", "")
    data_temp = str(data_temp).replace(" ", "")

    # https://acervolima.com/python-converta-string-para-datetime-e-vice-versa/

    try:
        _ = datetime.date(int(data_temp[4:9]), int(data_temp[2:4]), int(data_temp[0:2]))
        return True
    except ValueError:
        return False


# Formatar para Gravar a data corretamente
def formatar_data_com_pontos(data):
    if str(data) != "None":
        return (
            str(data[8:10])
            + "."
            + str(data[5:7])
            + "."
            + str(data[0:4] + " " + str(data[10:18]))
        )
    else:
        return None


class FormatarData:
    def __init__(self, data) -> None:
        # Assume que data_qualquer é uma string em um formato reconhecível por strptime ou um objeto datetime.
        if isinstance(data, str):
            # Tenta converter a string de data para um objeto datetime.
            # Isso requer que você saiba o formato da string de data que está passando.
            # O exemplo abaixo assume o formato 'dia/mês/ano', mas isso pode ser ajustado.
            self.data = datetime.strptime(data, settings.DATE_FORMAT_STR)
        elif isinstance(data, datetime):
            self.data = data
        else:
            msg = "Data deve ser uma instância de str ou datetime"
            raise TypeError(msg)

    def por_extenso(self) -> str:
        return formatar_data(self.data, opcao=2)

    def ano_de_4_digitos(self) -> str:
        return formatar_data(self.data, opcao=1)

    def ano_de_2_digitos(self) -> str:
        return formatar_data(self.data, opcao=1)


def formatar_data(data, opcao=4) -> str:
    if not data or data == "None":
        return ""
    """
    Formata uma data fornecida em diferentes estilos.

    Parâmetros:
        data (str or datetime): A data a ser formatada, podendo ser uma string ou um objeto datetime.
        opcao (int): O estilo de formatação da data.
            1 ou 3: Retorna a data no formato DD/MM/AA.
            2: Retorna a data no formato "D de M de AAAA", onde M é o mês por extenso.
            4: Retorna a data no formato DD/MM/AAAA.
            Retorna uma string vazia para qualquer outro valor de opção.

    Retorna:
        str: A data formatada conforme a opção escolhida.
    """

    # Retorna uma string vazia se a data for falsy (None, '', etc.)
    if not data:
        return ""

    # Tenta converter a data para um objeto datetime se não for um já
    if not isinstance(data, datetime):
        try:
            data_obj = datetime.strptime(str(data), "%Y-%m-%d")
        except ValueError:
            # return f"Formato de data não reconhecido: {data}"
            return f"{data}"
    else:
        data_obj = data

    # Formatação baseada na opção
    if opcao in [1, 3]:
        return data_obj.strftime(settings.DATE_FORMAT_STR)
    elif opcao == 2:
        mes_extenso = data_obj.strftime(
            "%B",
        )  # Assume uma função 'get_nome_do_mes_pelo_numero'
        return f"{data_obj.day} de {mes_extenso} de {data_obj.year}"
    elif opcao == 4:
        return data_obj.strftime(settings.DATE_FORMAT_STR)

    return ""


def render_to_pdf(template_src, context_dict=None):
    if context_dict is None:
        context_dict = {}
    html_string = render_to_string(template_src, context_dict)
    html = HTML(string=html_string)
    result = BytesIO()
    html.write_pdf(target=result)
    return result.getvalue()
