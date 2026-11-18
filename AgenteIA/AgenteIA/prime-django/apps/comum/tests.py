import decimal
import logging
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

from apps.comum.utils import (
    calcular_data_com_workalendar,
    converter_data_para_formato_de_modelo,
    formatar_moeda,
    limpar_documento,
)


class TestFormatarMoeda(unittest.TestCase):
    def test_formatar_moeda_com_simbolo(self):
        resultado = formatar_moeda(decimal.Decimal("1234.56")).replace("\xa0", " ")
        assert resultado == "R$ 1.234,56"

    def test_formatar_moeda_sem_simbolo(self):
        resultado = formatar_moeda(
            decimal.Decimal("1234.56"), incluir_simbolo=False,
        ).replace("\xa0", " ")
        assert resultado == "1.234,56"

    def test_formatar_moeda_valor_none(self):
        resultado = formatar_moeda(None).replace("\xa0", " ")
        assert resultado == "R$ 0,00"

    def test_formatar_moeda_valor_invalido(self):
        resultado = formatar_moeda("abc").replace("\xa0", " ")
        assert resultado == "R$ 0,00"

    def test_formatar_moeda_valor_vazio(self):
        resultado = formatar_moeda("").replace("\xa0", " ")
        assert resultado == "R$ 0,00"

    def test_formatar_moeda_zero(self):
        resultado = formatar_moeda(decimal.Decimal("0")).replace("\xa0", " ")
        assert resultado == "R$ 0,00"


class TestConverterDataParaFormatoDeModelo(unittest.TestCase):
    @patch("core.settings.DATE_FORMAT_STR", "%d/%m/%Y")
    def test_data_valida(self):
        assert converter_data_para_formato_de_modelo("2024-07-27") == "27/07/2024"

    def test_data_vazia(self):
        assert converter_data_para_formato_de_modelo("") == ""

    def test_data_nula(self):
        assert converter_data_para_formato_de_modelo(None) == ""

    def test_data_espacos_em_branco(self):
        assert converter_data_para_formato_de_modelo("   ") == ""

    @patch("core.settings.DATE_FORMAT_STR", "%d/%m/%Y")
    def test_data_padrao_vazia(self):
        assert converter_data_para_formato_de_modelo("2024-07-27") == "27/07/2024"
        assert converter_data_para_formato_de_modelo("1899-01-01") == ""

    @patch("apps.comum.utils.logger")
    def test_data_invalida(self, mock_logger):
        assert converter_data_para_formato_de_modelo("data_invalida") == ""
        mock_logger.exception.assert_called()


class TestLimparDocumento(unittest.TestCase):
    def test_documento_completo(self):
        assert limpar_documento("123.456.789-00") == "12345678900"

    def test_documento_com_espacos(self):
        assert limpar_documento("123 456 789 00") == "12345678900"

    def test_documento_com_letras(self):
        assert limpar_documento("abc123def456ghi789") == "123456789"

    def test_documento_vazio(self):
        assert limpar_documento("") == ""

    def test_documento_apenas_letras(self):
        assert limpar_documento("abcdef") == ""

    def test_documento_caracteres_especiais(self):
        assert limpar_documento("123!@#456$%^789&*()") == "123456789"

    def test_documento_misto(self):
        assert limpar_documento("a1!b2@c3#") == "123"


@pytest.mark.django_db()
class TestCalcularDataComWorkalendar:
    @patch("apps.comum.models.Feriado")
    def test_calcular_data_com_workalendar_sem_feriados_personalizados(
        self, MockFeriado,
    ):
        # Mockando o queryset do modelo Feriado para retornar nenhum feriado personalizado
        MockFeriado.objects.all.return_value = []

        data_inicio = datetime(2024, 1, 1)  # 1 de Janeiro de 2024 (segunda-feira)
        prazo_em_dias = 10  # 10 dias úteis

        # Calculando a data final
        data_final = calcular_data_com_workalendar(data_inicio, prazo_em_dias)

        # Verificação - considerando que não há feriados personalizados e dias úteis padrão
        # O prazo deve terminar em 15 de Janeiro de 2024 (segunda-feira)
        assert data_final == datetime(2024, 1, 15)

    @patch("apps.comum.models.Feriado")
    def test_calcular_data_com_workalendar_com_feriados_personalizados(
        self, MockFeriado,
    ):
        # Mockando o queryset do modelo Feriado para retornar feriados personalizados
        MockFeriado.objects.all.return_value = [
            MagicMock(data=datetime(2024, 1, 3), nome="Feriado Personalizado 1"),
            MagicMock(data=datetime(2024, 1, 10), nome="Feriado Personalizado 2"),
        ]

        data_inicio = datetime(2024, 1, 1)  # 1 de Janeiro de 2024 (segunda-feira)
        prazo_em_dias = 10  # 10 dias úteis

        # Calculando a data final
        data_final = calcular_data_com_workalendar(data_inicio, prazo_em_dias)

        # Verificação - considerando que há feriados personalizados em 3 e 10 de Janeiro
        # O prazo deve terminar em 17 de Janeiro de 2024 (quarta-feira)
        assert data_final == datetime(2024, 1, 17)
