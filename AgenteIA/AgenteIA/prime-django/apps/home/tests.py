import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.home.helpers import get_arquivos_de_minutas
from apps.home.models import (
    Colaborador,
    Livro01Protocolo,
    Pedido,
    StatusProtocolo,
    TipoFaseProtocolo,
)
from apps.home.services.firebird import get_protocolo_fb
from core.utils.firebird_utils import firebirdsql, get_conexao_firebird


class TestListarMinutas(TestCase):
    @pytest.mark.django_db()
    @patch("views.get_lista_modelos_minuta")
    def test_minutas_tipo_a(self, mock_get_lista) -> None:
        # Configurar o mock para retornar um valor esperado
        mock_get_lista.return_value = ["minuta1", "minuta2"]

        # Chamar a função
        resultado = get_arquivos_de_minutas("A", "alguma_pasta")

        # Verificar o resultado
        assert resultado == ["minuta1", "minuta2"]

    @pytest.mark.django_db()
    @patch("views.get_lista_modelos_minuta")
    def test_minutas_tipo_m(self, mock_get_lista) -> None:
        # Configurar o mock para retornar um valor esperado
        mock_get_lista.return_value = ["minuta3", "minuta4"]

        # Chamar a função
        resultado = get_arquivos_de_minutas("M", "outra_pasta")

        # Verificar o resultado
        assert resultado == ["minuta3", "minuta4"]

    @pytest.mark.django_db()
    def test_minutas_tipo_invalido(self) -> None:
        # Chamar a função com um tipo que não é 'A' ou 'M'
        resultado = get_arquivos_de_minutas("Z", "qualquer_pasta")

        # Verificar o resultado
        assert resultado == []

    @pytest.mark.django_db()
    @patch("views.get_lista_modelos_minuta")
    def test_minutas_com_erro(self, mock_get_lista) -> None:
        # Configurar o mock para lançar uma exceção
        mock_get_lista.side_effect = Exception("ERRO simulado")

        # Chamar a função
        resultado = get_arquivos_de_minutas("A", "alguma_pasta")

        # Verificar o resultado
        assert resultado == []


class ProtocolosModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Configurar um ambiente de teste. Este código é executado uma vez antes dos métodos de teste.
        pedido = Pedido.objects.create(...)  # Substitua "..." pelos valores adequados.
        tipo_fase_protocolo = TipoFaseProtocolo.objects.create(
            ...,
        )  # Adicione os campos necessários.
        colaborador = Colaborador.objects.create(...)  # Adicione os campos necessários.
        status_protocolo = StatusProtocolo.objects.create(
            ...,
        )  # Adicione os campos necessários.

        cls.protocolo = Livro01Protocolo.objects.create(
            numero_protocolo=123456,
            titulo=1,
            pedido=pedido,
            data_protocolo=timezone.now().date(),
            observacao="Teste de Observação",
            numero_origem=123,
            origem_pedido=1,
            fases_protocolo=tipo_fase_protocolo,
            fases_protocolo_colaborador=colaborador,
            fases_protocolo_colaborador_atual=colaborador,
            status=status_protocolo,
        )

    def test_protocolo_creation(self) -> None:
        # Testar a criação de um protocolo.
        assert isinstance(self.protocolo, Livro01Protocolo)
        assert self.protocolo.__str__() == str(self.protocolo.numero_protocolo)

    def test_protocolo_fields(self) -> None:
        # Testar campos específicos
        assert self.protocolo.titulo == 1
        assert self.protocolo.numero_origem == 123
        # Adicione mais asserções conforme necessário para os seus campos.

    # Adicione mais métodos de teste conforme necessário.


class PedidoModelTest(TestCase):
    def setUp(self) -> None:
        # Este método é chamado antes de cada método de teste para configurar um ambiente de teste limpo.
        self.pedido = Pedido.objects.create(
            data_entrada=timezone.now().date(),
            data_prevista=timezone.now().date(),
            # data_validade=timezone.now().date(),
            endereco="Rua Exemplo, 123",
            municipio="Cidade Exemplo",
            uf=123,
            telefone="123456789",
            telefone1="987654321",
            observacao="Observação de teste",
            tipo_servico="X",
            email="teste@teste.com",
            tipo_documento_apresentante=123,
            documento_apresentante="123456789",
            numero_talao=12345,
            numero=67890,
        )

    def test_pedido_creation(self) -> None:
        # Testar a criação de um pedido.
        assert isinstance(self.pedido, Pedido)
        assert self.pedido.endereco == "Rua Exemplo, 123"

    def test_pedido_fields(self) -> None:
        # Testar campos específicos
        assert self.pedido.municipio == "Cidade Exemplo"
        assert self.pedido.uf == 123
        # Adicione mais asserções conforme necessário para os seus campos.


class TestConversorHTMLParaRTF(unittest.TestCase):
    def test_converte_html_para_rtf(self) -> None:
        from apps.home.utils.libreoffice import converter_html_para_rtf

        # Uma string HTML simples para teste
        html_teste = "<html><body><p>Hello world mundo!</p></body></html>"

        # Chama a função de conversão
        rtf_resultado = converter_html_para_rtf(html_teste)

        # Verifica se o resultado é um byte não-nulo e contém uma string que esperamos encontrar em um arquivo RTF
        assert rtf_resultado is not None
        assert rtf_resultado.startswith("{\\rtf")
        assert "Hello" in rtf_resultado
        assert "world" in rtf_resultado
        assert "mundo" in rtf_resultado


class TestConverteRTFParaHTML(unittest.TestCase):
    def test_converter_rtf_para_html(self) -> None:
        from apps.home.utils.libreoffice import converter_rtf_para_html

        # Este é um exemplo simples de conteúdo RTF contendo texto "Hello, world!"
        rtf_teste = r"{\rtf1\ansi\ansicpg1252\cocoartf1671\cocoasubrtf600{\fonttbl\f0\fswiss\fcharset0 Helvetica;}{\colortbl;\red255\green255\blue255;}\margl1440\margr1440\vieww10800\viewh8400\viewkind0\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0\f0\fs24 \cf0 Hello, world!}"

        # Chama a função de conversão
        html_resultado = converter_rtf_para_html(rtf_teste)

        # Verifica se o resultado é uma string não-nula
        assert html_resultado is not None

        print(html_resultado)

        assert "Hello" in html_resultado
        assert "world" in html_resultado


# Assume-se que GLOBAL_CONN é uma variável global no módulo `seu_modulo`


@pytest.fixture()
def parametros_firebird():
    return {
        "IP": "localhost",
        "BANCO": "meu_banco",
        "PORTA": 3050,
        "USUARIO": "usuario",
        "SENHA": "senha",
        "CHARSET": "UTF8",
    }


def test_usa_conexao_existente_valida() -> None:
    with patch("core.utils.firebird_utils.GLOBAL_CONN") as mock_conn:
        mock_conn.cursor.return_value.__enter__.return_value.execute.return_value = None
        conexao = get_conexao_firebird()
        assert conexao is mock_conn


def test_reconecta_quando_conexao_existente_invalida(parametros_firebird) -> None:
    with (
        patch("core.utils.firebird_utils.GLOBAL_CONN", None),
        patch(
            "core.utils.firebird_utils.get_parametros_de_conexao_firebird",
            return_value=parametros_firebird,
        ),
        patch("firebirdsql.connect") as mock_connect,
    ):
        mock_connect.return_value = MagicMock()
        conexao = get_conexao_firebird()
        assert conexao is mock_connect.return_value


@pytest.mark.parametrize(
    "excecao",
    [firebirdsql.OperationalError, firebirdsql.ProgrammingError, Exception],
)
def test_tenta_reconectar_em_caso_de_falha(excecao, parametros_firebird) -> None:
    with (
        patch("core.utils.firebird_utils.GLOBAL_CONN", None),
        patch(
            "core.utils.firebird_utils.get_parametros_de_conexao_firebird",
            return_value=parametros_firebird,
        ),
        patch("firebirdsql.connect", side_effect=excecao),
        patch("time.sleep", return_value=None) as mock_sleep,
    ):
        conexao = get_conexao_firebird(max_tentativas=3, base_delay=1)
        assert conexao is None
        assert (
            mock_sleep.call_count == 2
        )  # Deve tentar 3 vezes, então dorme 2 vezes entre as tentativas


def test_respeita_tempo_espera_exponencial_entre_tentativas(
    parametros_firebird,
) -> None:
    with (
        patch("core.utils.firebird_utils.GLOBAL_CONN", None),
        patch(
            "core.utils.firebird_utils.get_parametros_de_conexao_firebird",
            return_value=parametros_firebird,
        ),
        patch("firebirdsql.connect", side_effect=firebirdsql.OperationalError),
        patch("time.sleep") as mock_sleep,
    ):
        get_conexao_firebird(max_tentativas=4, base_delay=1)
        # Verifica se os tempos de espera exponenciais são respeitados
        mock_sleep.assert_has_calls([patch.call(1), patch.call(2), patch.call(4)])


@pytest.fixture()
def mock_executar_query_sucesso():
    """Fixture que simula o retorno de sucesso da função executar_e_get_resultado_em_dict."""
    return [
        {
            "CHAVE_PROTOCOLOS": 1,
            "NROORDEM": "12345",
            # Adicione os demais campos conforme esperado
        },
    ]


@pytest.fixture()
def mock_executar_query_vazio():
    """Fixture que simula um retorno vazio (nenhum resultado) da função executar_e_get_resultado_em_dict."""
    return []


def test_get_protocolo_com_resultado(mock_executar_query_sucesso) -> None:
    numero_protocolo = "12345"
    with patch(
        "apps.home.utils.firebird.executar_e_get_resultado_em_dict",
        return_value=mock_executar_query_sucesso,
    ) as mock_executar:
        resultado = get_protocolo_fb(numero_protocolo)
        mock_executar.assert_called_once()
        assert resultado == mock_executar_query_sucesso
        assert "12345" in str(
            resultado,
        )  # Verifica se o número do protocolo está nos resultados


def test_get_protocolo_sem_resultado(mock_executar_query_vazio) -> None:
    numero_protocolo = "54321"
    with patch(
        "apps.home.utils.firebird.executar_e_get_resultado_em_dict",
        return_value=mock_executar_query_vazio,
    ) as mock_executar:
        resultado = get_protocolo_fb(numero_protocolo)
        mock_executar.assert_called_once()
        assert resultado is None


def test_get_protocolo_com_excecao() -> None:
    numero_protocolo = "erro"
    with patch(
        "apps.home.utils.firebird.executar_e_get_resultado_em_dict",
        side_effect=Exception("Erro de conexão"),
    ):
        with pytest.raises(Exception) as exc_info:
            get_protocolo_fb(numero_protocolo)
        assert "Erro de conexão" in str(exc_info.value)


class TestFirebirdGetEmolumento(unittest.TestCase):
    @patch("FbConnection")
    def test_firebird_get_emolumento_valid_result(self, MockFbConnection):
        # Mocking the database connection and the execute_query method
        mock_db_instance = Mock()
        MockFbConnection.return_value = mock_db_instance
        expected_result = [
            {
                "EMOLUMENTO": "test_emolumento",
                "VALOR": 100,
                "ADIC_EMOLUMENTO": "test_adic_emolumento",
                "CODIGO_TABELA": "test_codigo_tabela",
                "CHAVE_EMOLUMENTOS_ITENS": "test_chave_emolumentos_itens",
                "TAXA1": "test_taxa1",
            },
        ]
        mock_db_instance.execute_query.return_value = expected_result

        # Parameters for the function
        valor = 50
        emolumento_id = 1
        vigencia_id = 1

        from apps.home.services.firebird import firebird_get_emolumento

        result = firebird_get_emolumento(valor, emolumento_id, vigencia_id, None)
        assert result == expected_result[0]

    @patch("FbConnection")
    def test_firebird_get_emolumento_no_result(self, MockFbConnection):
        # Mocking the database connection and the execute_query method
        mock_db_instance = Mock()
        MockFbConnection.return_value = mock_db_instance
        mock_db_instance.execute_query.return_value = []

        # Parameters for the function
        valor = 50
        emolumento_id = 1
        vigencia_id = 1

        from apps.home.services.firebird import firebird_get_emolumento

        result = firebird_get_emolumento(valor, emolumento_id, vigencia_id, None)
        assert result == []

    @patch("FbConnection")
    def test_firebird_get_emolumento_query(self, MockFbConnection):
        # Mocking the database connection and the execute_query method
        mock_db_instance = Mock()
        MockFbConnection.return_value = mock_db_instance
        mock_db_instance.execute_query.return_value = []

        # Parameters for the function
        valor = 50
        emolumento_id = 1
        vigencia_id = 1

        expected_query = f"""
            SELECT EI.EMOLUMENTO, EI.VALOR, EI.ADIC_EMOLUMENTO, EI.CODIGO_TABELA, EI.CHAVE_EMOLUMENTOS_ITENS, TAXA1
            FROM EMOLUMENTOS_ITENS EI
            JOIN EMOLUMENTOS E ON E.CHAVE_EMOLUMENTOS = EI.CHAVE_EMOLUMENTOS
            WHERE {valor!s} BETWEEN EI.VL_INICIO AND EI.VL_FIM
            AND EI.CHAVE_EMOLUMENTOS = {emolumento_id!s}
            AND EI.CHAVE_VIGOR = {vigencia_id!s}
            """

        from apps.home.services.firebird import firebird_get_emolumento

        firebird_get_emolumento(valor, emolumento_id, vigencia_id, None)
        mock_db_instance.execute_query.assert_called_with(expected_query)
