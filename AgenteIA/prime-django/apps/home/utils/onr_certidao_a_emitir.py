import logging
import xml.etree.ElementTree as element_tree
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.comum.models import AuditorIntegracao, TipoOrigem
from apps.home import helpers as home_helpers
from apps.home.models import (
    Apresentante,
    Certidao,
    Finalidade,
    PedidoCertidao,
    PedidoCertidaoImovel,
    PedidoCertidaoPessoa,
    TipoCertidao,
    TipoTributacao,
)
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)


# Ler todo o arquivo XML

# def ler_arquivo_xml_certidoes_emitir(arquivo, user, municipio_id):
#     try:
#         tree = element_tree.parse(arquivo)
#         root = tree.getroot()  # Movendo para dentro do try para lidar com erros de parse

#         print("Percorrer ARQUIVO")
#     except Exception as e:
#         print("Erro ao abrir ou processar o arquivo: ", e)
#         return None

#     root = tree.getroot()

#     Lista = []

#     print("Percorrer ARQUIVO")

#     # Percorrer ARQUIVO
#     for protocolo_solicitacao in root.findall("PEDIDO_CERTIDAO"):
#         # <PROTOCOLO_SOLICITACAO>
#         itens_protocolo_solicitacao = next(
#             (
#                 itens_protocolo_solicitacao.text
#                 for itens_protocolo_solicitacao in protocolo_solicitacao.findall("PROTOCOLO_SOLICITACAO")
#             ),
#             "",
#         )
#         print(itens_protocolo_solicitacao)

#         # <DATA_PEDIDO>
#         data_protocolo_solicitacao = next(
#             (
#                 data_protocolo_solicitacao.text
#                 for data_protocolo_solicitacao in protocolo_solicitacao.findall("DATA_PEDIDO")
#             ),
#             "",
#         )
#         print(data_protocolo_solicitacao)

#         # <TIPO_COBRANCA>
#         tipo_cobranca_protocolo_solicitacao = next(
#             (
#                 tipo_cobranca_protocolo_solicitacao.text
#                 for tipo_cobranca_protocolo_solicitacao in protocolo_solicitacao.findall("TIPO_COBRANCA")
#             ),
#             "",
#         )
#         print(tipo_cobranca_protocolo_solicitacao)

#         # <VALOR>
#         valor_protocolo_solicitacao = next(
#             (
#                 valor_protocolo_solicitacao.text
#                 for valor_protocolo_solicitacao in protocolo_solicitacao.findall("VALOR")
#             ),
#             "",
#         )
#         print(valor_protocolo_solicitacao)

#         # <SOLICITANTE>
#         for solicitante_protocolo_solicitacao in protocolo_solicitacao.findall("SOLICITANTE"):
#             # <NOME>
#             nome_solicitante_protocolo_solicitacao = next(
#                 (
#                     nome_solicitante_protocolo_solicitacao.text
#                     for nome_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall("NOME")
#                 ),
#                 "",
#             )
#             print(nome_solicitante_protocolo_solicitacao)

#             # <TELEFONE>
#             telefone_solicitante_protocolo_solicitacao = next(
#                 (
#                     telefone_solicitante_protocolo_solicitacao.text
#                     for telefone_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
#                         "TELEFONE",
#                     )
#                 ),
#                 "",
#             )
#             print(telefone_solicitante_protocolo_solicitacao)

#             # <EMAIL>
#             email_solicitante_protocolo_solicitacao = next(
#                 (
#                     email_solicitante_protocolo_solicitacao.text
#                     for email_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall("EMAIL")
#                 ),
#                 "",
#             )
#             print(email_solicitante_protocolo_solicitacao)

#             # <CPFCNPJ>
#             cpfcnpj_solicitante_protocolo_solicitacao = next(
#                 (
#                     cpfcnpj_solicitante_protocolo_solicitacao.text
#                     for cpfcnpj_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
#                         "CPFCNPJ",
#                     )
#                 ),
#                 "",
#             )
#             print(cpfcnpj_solicitante_protocolo_solicitacao)

#             # <INSCRICAO_MUNICIPAL>
#             inscricao_solicitante_protocolo_solicitacao = next(
#                 (
#                     inscricao_solicitante_protocolo_solicitacao.text
#                     for inscricao_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
#                         "INSCRICAO_MUNICIPAL",
#                     )
#                 ),
#                 "",
#             )
#             print(inscricao_solicitante_protocolo_solicitacao)

#             # <ISENTO_CCM>
#             isento_ccm_solicitante_protocolo_solicitacao = next(
#                 (
#                     isento_ccm_solicitante_protocolo_solicitacao.text
#                     for isento_ccm_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
#                         "ISENTO_CCM",
#                     )
#                 ),
#                 "",
#             )
#             print(isento_ccm_solicitante_protocolo_solicitacao)

#             # <NUMERO_CCM>
#             numero_ccm_solicitante_protocolo_solicitacao = next(
#                 (
#                     numero_ccm_solicitante_protocolo_solicitacao.text
#                     for numero_ccm_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
#                         "NUMERO_CCM",
#                     )
#                 ),
#                 "",
#             )
#             print(numero_ccm_solicitante_protocolo_solicitacao)

#             # <ENDERECO>
#             for endereco_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall("ENDERECO"):
#                 # <CEP>
#                 endereco_cep_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_cep_solicitante_protocolo_solicitacao.text
#                         for endereco_cep_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "CEP",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_cep_solicitante_protocolo_solicitacao)

#                 # <TIPO_LOGRADOURO>
#                 endereco_tipo_logradouro_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_tipo_logradouro_solicitante_protocolo_solicitacao.text
#                         for endereco_tipo_logradouro_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "TIPO_LOGRADOURO",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_tipo_logradouro_solicitante_protocolo_solicitacao)

#                 # <LOGRADOURO>
#                 endereco_logradouro_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_logradouro_solicitante_protocolo_solicitacao.text
#                         for endereco_logradouro_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "LOGRADOURO",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_logradouro_solicitante_protocolo_solicitacao)

#                 # <NUMERO>
#                 endereco_numero_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_numero_solicitante_protocolo_solicitacao.text
#                         for endereco_numero_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "NUMERO",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_numero_solicitante_protocolo_solicitacao)

#                 # <COMPLEMENTO>
#                 endereco_complemento_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_complemento_solicitante_protocolo_solicitacao.text
#                         for endereco_complemento_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "COMPLEMENTO",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_complemento_solicitante_protocolo_solicitacao)

#                 # <BAIRRO>
#                 endereco_bairro_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_bairro_solicitante_protocolo_solicitacao.text
#                         for endereco_bairro_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "BAIRRO",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_bairro_solicitante_protocolo_solicitacao)

#                 # <CIDADE>
#                 endereco_cidade_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_cidade_solicitante_protocolo_solicitacao.text
#                         for endereco_cidade_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "CIDADE",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_cidade_solicitante_protocolo_solicitacao)

#                 # <UF>
#                 endereco_uf_solicitante_protocolo_solicitacao = next(
#                     (
#                         endereco_uf_solicitante_protocolo_solicitacao.text
#                         for endereco_uf_solicitante_protocolo_solicitacao in endereco_solicitante_protocolo_solicitacao.findall(
#                             "UF",
#                         )
#                     ),
#                     "",
#                 )
#                 print(endereco_uf_solicitante_protocolo_solicitacao)

#         # <CERTIDAO>
#         for certidao_protocolo_solicitacao in protocolo_solicitacao.findall("CERTIDAO"):
#             # <TIPO>
#             tipo_certidao_protocolo_solicitacao = next(
#                 (
#                     tipo_certidao_protocolo_solicitacao.text
#                     for tipo_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall("TIPO")
#                 ),
#                 "",
#             )
#             print(tipo_certidao_protocolo_solicitacao)

#             # <PEDIDO_POR>
#             pedido_por_certidao_protocolo_solicitacao = next(
#                 (
#                     pedido_por_certidao_protocolo_solicitacao.text
#                     for pedido_por_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall(
#                         "PEDIDO_POR",
#                     )
#                 ),
#                 "",
#             )
#             print(pedido_por_certidao_protocolo_solicitacao)

#             # <MATRICULA>
#             for matricula_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall("MATRICULA"):
#                 # <NUMERO>
#                 certidao_matricula_solicitante_protocolo_solicitacao = next(
#                     (
#                         certidao_matricula_solicitante_protocolo_solicitacao.text
#                         for certidao_matricula_solicitante_protocolo_solicitacao in matricula_certidao_protocolo_solicitacao.findall(
#                             "NUMERO",
#                         )
#                     ),
#                     "",
#                 )
#                 print(certidao_matricula_solicitante_protocolo_solicitacao)

#                 # <LETRA>
#                 certidao_letra_solicitante_protocolo_solicitacao = next(
#                     (
#                         certidao_letra_solicitante_protocolo_solicitacao.text
#                         for certidao_letra_solicitante_protocolo_solicitacao in matricula_certidao_protocolo_solicitacao.findall(
#                             "LETRA",
#                         )
#                     ),
#                     "",
#                 )
#                 print(certidao_letra_solicitante_protocolo_solicitacao)

#                 # <MATRICULA_MAE>
#                 certidao_matricula_mae_solicitante_protocolo_solicitacao = next(
#                     (
#                         certidao_matricula_mae_solicitante_protocolo_solicitacao.text
#                         for certidao_matricula_mae_solicitante_protocolo_solicitacao in matricula_certidao_protocolo_solicitacao.findall(
#                             "MATRICULA_MAE",
#                         )
#                     ),
#                     "",
#                 )
#                 print(certidao_matricula_mae_solicitante_protocolo_solicitacao)

#                 # <IDENTIFICACAO_ADICIONAL_MATRICULA_MAE>
#                 certidao_identificacao_mae_solicitante_protocolo_solicitacao = next(
#                     (
#                         certidao_identificacao_mae_solicitante_protocolo_solicitacao.text
#                         for certidao_identificacao_mae_solicitante_protocolo_solicitacao in matricula_certidao_protocolo_solicitacao.findall(
#                             "IDENTIFICACAO_ADICIONAL_MATRICULA_MAE",
#                         )
#                     ),
#                     "",
#                 )
#                 print(certidao_identificacao_mae_solicitante_protocolo_solicitacao)

#                 # <NUMERO_ATO>
#                 certidao_numero_ato_solicitante_protocolo_solicitacao = next(
#                     (
#                         certidao_numero_ato_solicitante_protocolo_solicitacao.text
#                         for certidao_numero_ato_solicitante_protocolo_solicitacao in matricula_certidao_protocolo_solicitacao.findall(
#                             "NUMERO_ATO",
#                         )
#                     ),
#                     "",
#                 )
#                 print(certidao_numero_ato_solicitante_protocolo_solicitacao)

#             # <ENDERECO>
#             endereco_certidao_protocolo_solicitacao = ""
#             for endereco_certidao in certidao_protocolo_solicitacao.findall("ENDERECO"):
#                 # <CEP>
#                 endereco_certidao_cep = next(
#                     (endereco_certidao_cep.text for endereco_certidao_cep in endereco_certidao.findall("CEP")),
#                     "",
#                 )
#                 endereco_certidao_endereco = next(
#                     (
#                         endereco_certidao_endereco.text
#                         for endereco_certidao_endereco in endereco_certidao.findall("ENDERECO")
#                     ),
#                     "",
#                 )
#                 endereco_certidao_numero = next(
#                     (endereco_certidao_numero.text for endereco_certidao_numero in endereco_certidao.findall("NUMERO")),
#                     "",
#                 )
#                 endereco_certidao_complemento = next(
#                     (
#                         endereco_certidao_complemento.text
#                         for endereco_certidao_complemento in endereco_certidao.findall("COMPLEMENTO")
#                     ),
#                     "",
#                 )
#                 endereco_certidao_bloco = next(
#                     (
#                         endereco_certidao_bloco.text
#                         for endereco_certidao_bloco in endereco_certidao.findall("BLOCO_TORRE")
#                     ),
#                     "",
#                 )
#                 endereco_certidao_loteamento = next(
#                     (
#                         endereco_certidao_loteamento.text
#                         for endereco_certidao_loteamento in endereco_certidao.findall("LOTEAMENTO")
#                     ),
#                     "",
#                 )
#                 endereco_certidao_lote = next(
#                     (endereco_certidao_lote.text for endereco_certidao_lote in endereco_certidao.findall("LOTE")),
#                     "",
#                 )
#                 endereco_certidao_quadra = next(
#                     (endereco_certidao_quadra.text for endereco_certidao_quadra in endereco_certidao.findall("QUADRA")),
#                     "",
#                 )
#                 endereco_certidao_numero_contribuinte = next(
#                     (
#                         endereco_certidao_numero_contribuinte.text
#                         for endereco_certidao_numero_contribuinte in endereco_certidao.findall(
#                             "NUMERO_CONTRIBUINTE",
#                         )
#                     ),
#                     "",
#                 )

#                 # ENDERECO JUNTO
#                 if endereco_certidao_endereco:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_endereco
#                     )

#                 if endereco_certidao_numero:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_numero
#                     )

#                 if endereco_certidao_complemento:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_complemento
#                     )

#                 if endereco_certidao_bloco:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_bloco
#                     )

#                 if endereco_certidao_loteamento:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_loteamento
#                     )

#                 if endereco_certidao_lote:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_lote
#                     )

#                 if endereco_certidao_quadra:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_quadra
#                     )

#                 if endereco_certidao_cep:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_cep
#                     )

#                 if endereco_certidao_numero_contribuinte:
#                     endereco_certidao_protocolo_solicitacao = (
#                         endereco_certidao_protocolo_solicitacao + " " + endereco_certidao_numero_contribuinte
#                     )

#             # <TRANSCRICAO>
#             transcricao_certidao_protocolo_solicitacao = next(
#                 (
#                     transcricao_certidao_protocolo_solicitacao.text
#                     for transcricao_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall(
#                         "TRANSCRICAO",
#                     )
#                 ),
#                 "",
#             )
#             print(transcricao_certidao_protocolo_solicitacao)

#             # <PESSOA>
#             for pessoa_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall("PESSOA"):
#                 # <PESSOA NOME>
#                 pessoa_certidao_protocolo_solicitacao_NOME = next(
#                     (
#                         pessoa_certidao_protocolo_solicitacao_NOME.text
#                         for pessoa_certidao_protocolo_solicitacao_NOME in pessoa_certidao_protocolo_solicitacao.findall(
#                             "NOME",
#                         )
#                     ),
#                     "",
#                 )
#                 print(pessoa_certidao_protocolo_solicitacao_NOME)

#                 # <PESSOA CPF>
#                 pessoa_certidao_protocolo_solicitacao_CPFCNPJ = next(
#                     (
#                         pessoa_certidao_protocolo_solicitacao_CPFCNPJ.text
#                         for pessoa_certidao_protocolo_solicitacao_CPFCNPJ in pessoa_certidao_protocolo_solicitacao.findall(
#                             "CPFCNPJ",
#                         )
#                     ),
#                     "",
#                 )
#                 print(pessoa_certidao_protocolo_solicitacao_CPFCNPJ)

#                 # <PESSOA RG>
#                 pessoa_certidao_protocolo_solicitacao_RG_IE = next(
#                     (
#                         pessoa_certidao_protocolo_solicitacao_RG_IE.text
#                         for pessoa_certidao_protocolo_solicitacao_RG_IE in pessoa_certidao_protocolo_solicitacao.findall(
#                             "RG_IE",
#                         )
#                     ),
#                     "",
#                 )
#                 print(pessoa_certidao_protocolo_solicitacao_RG_IE)

#             # <PROTOCOLO>
#             protocolo_certidao_protocolo_solicitacao = next(
#                 (
#                     protocolo_certidao_protocolo_solicitacao.text
#                     for protocolo_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall(
#                         "PROTOCOLO",
#                     )
#                 ),
#                 "",
#             )
#             print(protocolo_certidao_protocolo_solicitacao)

#             # <PACTO_ANTENUPCIAL>
#             pacto_antenupcial_certidao_protocolo_solicitacao = next(
#                 (
#                     pacto_antenupcial_certidao_protocolo_solicitacao.text
#                     for pacto_antenupcial_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall(
#                         "PACTO_ANTENUPCIAL",
#                     )
#                 ),
#                 "",
#             )
#             print(pacto_antenupcial_certidao_protocolo_solicitacao)

#             # <CONVENCAO>
#             convencao_certidao_protocolo_solicitacao = next(
#                 (
#                     convencao_certidao_protocolo_solicitacao.text
#                     for convencao_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall(
#                         "CONVENCAO",
#                     )
#                 ),
#                 "",
#             )
#             print(convencao_certidao_protocolo_solicitacao)

#             # <LIVRO3>
#             for _livro3_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall("LIVRO3"):
#                 # <NUMERO DO LIVRO 3>
#                 NUMERO_REGISTRO_LIVRO_3 = next(
#                     (
#                         NUMERO_REGISTRO_LIVRO_3.text
#                         for NUMERO_REGISTRO_LIVRO_3 in protocolo_solicitacao.findall("NUMERO_REGISTRO_LIVRO_3")
#                     ),
#                     "",
#                 )
#                 print(NUMERO_REGISTRO_LIVRO_3)

#                 # <NUMERO DO ATO DO LIVRO 3>
#                 NUMERO_ATO_LIVRO_3 = next(
#                     (NUMERO_ATO_LIVRO_3.text for NUMERO_ATO_LIVRO_3 in protocolo_solicitacao.findall("NUMERO_ATO")),
#                     "",
#                 )
#                 print(NUMERO_ATO_LIVRO_3)

#             # <OBSERVACAO>
#             observacao_certidao_protocolo_solicitacao = next(
#                 (
#                     observacao_certidao_protocolo_solicitacao.text
#                     for observacao_certidao_protocolo_solicitacao in certidao_protocolo_solicitacao.findall(
#                         "OBSERVACAO",
#                     )
#                 ),
#                 "",
#             )
#             print(observacao_certidao_protocolo_solicitacao)

#         finalidade, tipo_certidao_penhora = None, None

#         # COLOCAR O ENDERECO JUNTO A OBSERVACAO
#         if observacao_certidao_protocolo_solicitacao is None:
#             observacao_certidao_protocolo_solicitacao = " "

#         if endereco_certidao_protocolo_solicitacao is None:
#             endereco_certidao_protocolo_solicitacao = " "

#         observacao_certidao_protocolo_solicitacao = (
#             observacao_certidao_protocolo_solicitacao + " " + endereco_certidao_protocolo_solicitacao
#         )

#     return Lista


def ler_xml_certidoes_emitir_onr(arquivo) -> list[dict]:
    remover_linha_inicial = False
    verificar_ultima_data_importacao = False
    data_ultima_importacao_certidao = ""

    try:
        tree = element_tree.parse(arquivo)
        root = tree.getroot()
    except Exception:
        remover_linha_inicial = True

        # REMOVER LINHA
        arquivo = home_helpers.remover_linha_inicial_xml(arquivo)

    # APOS REMOVER LINHA
    if remover_linha_inicial:
        try:
            tree = element_tree.parse(arquivo)
            root = tree.getroot()

            # BUSCAR NO AUDITOR COMUM DE INTEGRACAO A ULTIMA IMPORTACAO REGISTRADA
            origem_id = 6
            auditores = AuditorIntegracao.objects.filter(tipo_integracao_id=origem_id)

            if auditores.exists():
                data_ultima_importacao_certidao = auditores.latest(
                    "created_at",
                ).created_at.date()
                data_ultima_importacao_certidao = (
                    data_ultima_importacao_certidao - timedelta(days=3)
                )
                verificar_ultima_data_importacao = True

            if data_ultima_importacao_certidao is False:
                data_ultima_importacao_certidao = timezone.now().date

        except Exception as e:
            logger.exception(
                f"Erro ao abrir ou processar o arquivo: {e}",
            )
            return []

    certidoes = []

    for protocolo_solicitacao in root.findall("PEDIDO_CERTIDAO"):
        certidao_data = {}

        certidao_data["PROTOCOLO_SOLICITACAO"] = next(
            (
                item.text
                for item in protocolo_solicitacao.findall("PROTOCOLO_SOLICITACAO")
            ),
            "",
        )
        certidao_data["DATA_PEDIDO"] = next(
            (item.text for item in protocolo_solicitacao.findall("DATA_PEDIDO")),
            "",
        )
        certidao_data["TIPO_COBRANCA"] = next(
            (item.text for item in protocolo_solicitacao.findall("TIPO_COBRANCA")),
            "",
        )
        certidao_data["VALOR"] = next(
            (item.text for item in protocolo_solicitacao.findall("VALOR")),
            "",
        )

        solicitante = protocolo_solicitacao.find("SOLICITANTE")
        if solicitante is not None:
            certidao_data["SOLICITANTE"] = {
                "NOME": next((item.text for item in solicitante.findall("NOME")), ""),
                "TELEFONE": next(
                    (item.text for item in solicitante.findall("TELEFONE")),
                    "",
                ),
                "EMAIL": next((item.text for item in solicitante.findall("EMAIL")), ""),
                "CPFCNPJ": next(
                    (item.text for item in solicitante.findall("CPFCNPJ")),
                    "",
                ),
                "INSCRICAO_MUNICIPAL": next(
                    (item.text for item in solicitante.findall("INSCRICAO_MUNICIPAL")),
                    "",
                ),
                "ISENTO_CCM": next(
                    (item.text for item in solicitante.findall("ISENTO_CCM")),
                    "",
                ),
                "NUMERO_CCM": next(
                    (item.text for item in solicitante.findall("NUMERO_CCM")),
                    "",
                ),
            }

            # Verifica se a chave 'SOLICITANTE' está presente e se não é um dicionário, inicializa como dicionário vazio
            if "SOLICITANTE" not in certidao_data or not isinstance(
                certidao_data["SOLICITANTE"],
                dict,
            ):
                certidao_data["SOLICITANTE"] = {}

            endereco = solicitante.find("ENDERECO")
            if endereco is not None:
                # Verifica se a chave 'ENDERECO' está presente e se não é um dicionário, inicializa como dicionário vazio

                if "ENDERECO" not in certidao_data["SOLICITANTE"] or not isinstance(
                    certidao_data["SOLICITANTE"]["ENDERECO"],
                    dict,
                ):
                    certidao_data["SOLICITANTE"]["ENDERECO"] = {}
                certidao_data["SOLICITANTE"]["ENDERECO"] = {
                    "CEP": next((item.text for item in endereco.findall("CEP")), ""),
                    "TIPO_LOGRADOURO": next(
                        (item.text for item in endereco.findall("TIPO_LOGRADOURO")),
                        "",
                    ),
                    "LOGRADOURO": next(
                        (item.text for item in endereco.findall("LOGRADOURO")),
                        "",
                    ),
                    "NUMERO": next(
                        (item.text for item in endereco.findall("NUMERO")),
                        "",
                    ),
                    "COMPLEMENTO": next(
                        (item.text for item in endereco.findall("COMPLEMENTO")),
                        "",
                    ),
                    "BAIRRO": next(
                        (item.text for item in endereco.findall("BAIRRO")),
                        "",
                    ),
                    "CIDADE": next(
                        (item.text for item in endereco.findall("CIDADE")),
                        "",
                    ),
                    "UF": next((item.text for item in endereco.findall("UF")), ""),
                }

        certidao = protocolo_solicitacao.find("CERTIDAO")
        if certidao is not None:
            certidao_data["CERTIDAO"] = {
                "TIPO": next((item.text for item in certidao.findall("TIPO")), ""),
                "PEDIDO_POR": next(
                    (item.text for item in certidao.findall("PEDIDO_POR")),
                    "",
                ),
            }

            matricula = certidao.find("MATRICULA")
            if matricula is not None:
                certidao_data["CERTIDAO"]["MATRICULA"] = {
                    "NUMERO": next(
                        (item.text for item in matricula.findall("NUMERO")),
                        "",
                    ),
                    "LETRA": next(
                        (item.text for item in matricula.findall("LETRA")),
                        "",
                    ),
                    "MATRICULA_MAE": next(
                        (item.text for item in matricula.findall("MATRICULA_MAE")),
                        "",
                    ),
                    "IDENTIFICACAO_ADICIONAL_MATRICULA_MAE": next(
                        (
                            item.text
                            for item in matricula.findall(
                                "IDENTIFICACAO_ADICIONAL_MATRICULA_MAE",
                            )
                        ),
                        "",
                    ),
                    "NUMERO_ATO": next(
                        (item.text for item in matricula.findall("NUMERO_ATO")),
                        "",
                    ),
                }

            certidao_data["CERTIDAO"]["ENDERECO"] = {
                "CEP": next(
                    (item.text for item in certidao.findall("ENDERECO/CEP")),
                    "",
                ),
                "ENDERECO": next(
                    (item.text for item in certidao.findall("ENDERECO/ENDERECO")),
                    "",
                ),
                "NUMERO": next(
                    (item.text for item in certidao.findall("ENDERECO/NUMERO")),
                    "",
                ),
                "COMPLEMENTO": next(
                    (item.text for item in certidao.findall("ENDERECO/COMPLEMENTO")),
                    "",
                ),
                "BLOCO_TORRE": next(
                    (item.text for item in certidao.findall("ENDERECO/BLOCO_TORRE")),
                    "",
                ),
                "LOTEAMENTO": next(
                    (item.text for item in certidao.findall("ENDERECO/LOTEAMENTO")),
                    "",
                ),
                "LOTE": next(
                    (item.text for item in certidao.findall("ENDERECO/LOTE")),
                    "",
                ),
                "QUADRA": next(
                    (item.text for item in certidao.findall("ENDERECO/QUADRA")),
                    "",
                ),
                "NUMERO_CONTRIBUINTE": next(
                    (
                        item.text
                        for item in certidao.findall("ENDERECO/NUMERO_CONTRIBUINTE")
                    ),
                    "",
                ),
            }

            # certidao_data["CERTIDAO"]["TRANSCRICAO"] = next(
            #     (item.text for item in certidao.findall("TRANSCRICAO")),
            #     "",
            # )

            transcricao = certidao.find("TRANSCRICAO")
            if transcricao is not None:
                certidao_data["CERTIDAO"]["TRANSCRICAO"] = {
                    "NUMERO": next(
                        (item.text for item in transcricao.findall("NUMERO")),
                        "",
                    ),
                    "LETRA": next(
                        (item.text for item in transcricao.findall("LETRA")),
                        "",
                    ),
                    "LIVRO": next(
                        (item.text for item in transcricao.findall("LIVRO")),
                        "",
                    ),
                    "DATA": next(
                        (item.text for item in transcricao.findall("DATA")),
                        "",
                    ),
                    "TRANSCRICAO_UNIDADE_LOTE": next(
                        (
                            item.text
                            for item in transcricao.findall("TRANSCRICAO_UNIDADE_LOTE")
                        ),
                        "",
                    ),
                    "INFORMACAO_ADICIONAL": next(
                        (
                            item.text
                            for item in transcricao.findall("INFORMACAO_ADICIONAL")
                        ),
                        "",
                    ),
                }

            pessoa = certidao.find("PESSOA")
            if pessoa is not None:
                certidao_data["CERTIDAO"]["PESSOA"] = {
                    "NOME": next((item.text for item in pessoa.findall("NOME")), ""),
                    "CPFCNPJ": next(
                        (item.text for item in pessoa.findall("CPFCNPJ")),
                        "",
                    ),
                    "RG_IE": next((item.text for item in pessoa.findall("RG_IE")), ""),
                }

            certidao_data["CERTIDAO"]["PROTOCOLO"] = next(
                (item.text for item in certidao.findall("PROTOCOLO")),
                "",
            )
            certidao_data["CERTIDAO"]["PACTO_ANTENUPCIAL"] = next(
                (item.text for item in certidao.findall("PACTO_ANTENUPCIAL")),
                "",
            )
            certidao_data["CERTIDAO"]["CONVENCAO"] = next(
                (item.text for item in certidao.findall("CONVENCAO")),
                "",
            )

            livro3 = certidao.find("LIVRO3")
            if livro3 is not None:
                certidao_data["CERTIDAO"]["LIVRO3"] = {
                    "NUMERO_REGISTRO_LIVRO_3": next(
                        (
                            item.text
                            for item in livro3.findall("NUMERO_REGISTRO_LIVRO_3")
                        ),
                        "",
                    ),
                    "NUMERO_ATO_LIVRO_3": next(
                        (item.text for item in livro3.findall("NUMERO_ATO")),
                        "",
                    ),
                }

            certidao_data["CERTIDAO"]["OBSERVACAO"] = next(
                (item.text for item in certidao.findall("OBSERVACAO")),
                "",
            )

        # VERIFICAR A ULTIMA IMPORTACAO
        anexar_xml_certidao = True

        if verificar_ultima_data_importacao:
            data_formatada = str(certidao_data["DATA_PEDIDO"])[:10]
            data_formatada = home_helpers.converter_string_para_data(
                data_formatada,
                settings.DATE_FORMAT_STR,
                0,
            )[0]
            data_formatada = data_formatada.date()

            if data_formatada < data_ultima_importacao_certidao:
                anexar_xml_certidao = False

        # VERIFICAR SE O PROTOCOLO NAO ESTA CADATRADO
        if PedidoCertidao.objects.filter(
            protocolo_onr=certidao_data["PROTOCOLO_SOLICITACAO"],
        ).exists():
            anexar_xml_certidao = False
            print(
                "Este protocolo já existe no sistema:",
                certidao_data["PROTOCOLO_SOLICITACAO"],
            )

        if anexar_xml_certidao:
            certidoes.append(certidao_data)

    return certidoes


# Gerar a lista para salvar o Pedido de certidao
@transaction.atomic
def gerar_pedido_certidao_onr_certidoes_emitir(
    protocolo_onr,
    data_onr,
    valor,
    nome_solicitante,
    telefone,
    email,
    cpfcnpj,
    numero_matricula,
    codigo_certidao_onr,
    isento_ccm,
    nome_pesquisa,
    cpf_pesquisa,
    endereco,
    user,
    origem_pedido=6,
    finalidade="",
    tipo_certidao_imovel_pessoa=1,
    municipio_id="",
    observacao_certidao="",
    numero_registro_livro_3="",
    cartorio="1",
) -> "PedidoCertidao":
    print("Verificar se o pedido ONR ja foi gravado: ", str(protocolo_onr))

    # PROTOCOLO ONR - VERIFICAR SE O PEDIDO ONR JA FOI GRAVADO
    pedido_existente = PedidoCertidao.objects.filter(
        protocolo_onr=str(protocolo_onr),
    ).first()
    if pedido_existente:
        msg = f"Este pedido já existe no sistema sistema. {protocolo_onr!s}"
        print(msg)
        return pedido_existente

    # Criar ou atualizar as finalidades
    finalidade_object = None

    if finalidade:
        finalidade_object = Finalidade.objects.filter(nome=finalidade).first()
        if not finalidade:
            finalidade_object = Finalidade.objects.create(
                nome=finalidade,
                ativo=True,
            )

    # PEGAR DATA ATUAL
    data_atual = home_helpers.get_expediente(timezone.now()).date()

    # Conversão para datetime
    try:
        data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y %H:%M:%S")
        # data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y")
    except:
        # data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y %H:%M:%S")
        data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y")

    # FORMATAR ENDERECO COM VALOR DA ONR
    endereco_imovel = endereco
    endereco = endereco + " " + nome_solicitante + " " + str(valor)

    # GRAVAR PEDIDO - POSTGRESQL
    print("GRAVAR PEDIDO: ", str(protocolo_onr), " origem:", origem_pedido)

    if not TipoOrigem.objects.filter(id=6).exists():
        TipoOrigem.objects.create(id=6, nome="ONR - Pedido de Certidao")

    # ATUALIZAR A SEQUENCE ANTES DE GRAVAR
    with transaction.atomic(), FbConnection() as db:
        db.begin_transaction()
        # proximo_pedido = PedidoCertidao.get_proximo_numero_pedido()
        # proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # while PedidoCertidao.objects.filter(numero_pedido=proximo_pedido).exists():
        #     proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # db.commit()

        # print("PED_CERTIDOES_SEQ Firebird:", proximo_pedido)

        pedido = PedidoCertidao.objects.create(
            # numero_pedido=None,
            origem_id=6,
            data_entrada=data_atual,
            # data_validade=data_atual + timedelta(days=5),
            data_pedido_onr=data_pedido_onr,
            protocolo_onr=str(protocolo_onr),
            observacao=endereco,
            finalidade_id=finalidade_object.id if finalidade_object else None,
        )

        # GRAVAR APRESENTANTE - POSTGRESQL
        print("GRAVAR APRESENTANTE: ", str(nome_solicitante))

        # CPF OU CNPJ
        tipo_documento_id = 2 if len(cpfcnpj) >= 14 else 1

        Apresentante.objects.create(
            nome=nome_solicitante,
            pedido=pedido,
            telefone=telefone,
            email=email,
            documento=cpfcnpj,
            tipo_documento_id=tipo_documento_id,
        )

        # GRAVAR IMOVEL - POSTGRESQL
        print("GRAVAR REGISTRO: ", codigo_certidao_onr)

        # IMOVEL OU LIVRO 3
        tipo_registro_id = "1"  # Matrícula

        # TIPO DO IMOVEL
        tipo_imovel_id = "1"

        if int(codigo_certidao_onr) == 10:
            tipo_registro_id = "4"  # Registro Auxiliar

            # LIVRO 3
            tipo_imovel_id = None

            if numero_registro_livro_3:
                numero_matricula = numero_registro_livro_3

        elif int(codigo_certidao_onr) == 4:  # GRAVAR OBSERVACAO
            if not numero_matricula:
                numero_matricula = "0"

            tipo_registro_id = "2"  # Transcricao

        else:
            tipo_registro_id = "1"  # Matrícula

        # CASO NAO TENHA NUMERO DE MATRICULA
        if str(numero_matricula) == "" and str(nome_pesquisa) == "":
            numero_matricula = "0"

        imovel = None
        if str(numero_matricula) != "":
            imovel = PedidoCertidaoImovel.objects.create(
                pedido=pedido,
                cartorio=cartorio,
                municipio_id=municipio_id,
                tipo_imovel_id=tipo_imovel_id,
                numero_registro=numero_matricula,
                tipo_registro_id=tipo_registro_id,
                tipo_logradouro_id="1",
                anotacoes=observacao_certidao,
                complemento=endereco_imovel,
            )

        # GRAVAR PESSOA - POSTGRESQL
        tipo_documento_id = 1
        print("GRAVAR PESSOA: ")

        pessoa = None
        if str(nome_pesquisa) != "":
            pessoa = PedidoCertidaoPessoa.objects.create(
                pedido=pedido,
                nome=nome_pesquisa,
                documento=cpf_pesquisa,
                tipo_documento_id=tipo_documento_id,
                anotacoes=observacao_certidao,
            )

        # GRAVAR ANDAMENTOS - POSTGRESQL
        print("GRAVAR ANDAMENTOS: ")
        # Livro01Andamento.objects.create(pedido=pedido, data_hora=data_atual, tipo_andamento="CP", criado_por=user)

        # Verificar se o cobranca ISENTA OU NORMAL - POSTGRESQL
        percentual_desconto = 100 if Decimal(valor) == 0 else 0

        # LOCALIZAR TRIBUTACAO DE ACORDO COM O EMOLUMENTO
        tipo_tributacao = TipoTributacao.objects.filter(
            percentual_desconto=percentual_desconto,
        ).first()

        # CASO NAO ENCONTRE O TIPO DE TRIBUTACAO
        if tipo_tributacao is None:
            tipo_tributacao = TipoTributacao.objects.filter(id=0).first()

        # LOCALIZAR CERTIDAO ONR
        tipo_certidao = TipoCertidao.objects.filter(
            codigo_onr=codigo_certidao_onr,
        ).first()

        print("GERANDO ONR", " - ", codigo_certidao_onr, " - ", protocolo_onr)

        # CASO NAO ENCONTRE O TIPO DE CERTIDAO
        if tipo_certidao is None:
            tipo_certidao = TipoCertidao.objects.filter(codigo_onr=3).first()

        # GRAVAR O ITEM DA CERTIDAO1
        if int(codigo_certidao_onr) in (12, 15):
            # CERTIDOES DE ONUS, REPERSECUTORIAS E INTEIOR TEOR
            if int(codigo_certidao_onr) == 12:
                # GRAVAR CERTIDAO - POSTGRESQL - 2 VEZES COBRAR O CODIGO 8402-0 - CERTIDOES DE ONUS, REPERSECUTORIAS
                tipo_certidao = TipoCertidao.objects.filter(codigo_onr=1).first()
                Certidao.gerar_item_certidao(
                    tipo_certidao,
                    pessoa,
                    imovel,
                    data_atual,
                    tipo_tributacao,
                )

                Certidao.gerar_item_certidao(
                    tipo_certidao,
                    pessoa,
                    imovel,
                    data_atual,
                    tipo_tributacao,
                )

                # INTEIOR TEOR - 1 VEZ COBRAR O 8401-2
                tipo_certidao = TipoCertidao.objects.filter(codigo_onr=3).first()
                Certidao.gerar_item_certidao(
                    tipo_certidao,
                    pessoa,
                    imovel,
                    data_atual,
                    tipo_tributacao,
                )

            # CERTIDOES DE ONUS E REPERSECUTORIAS
            elif int(codigo_certidao_onr) == 15:
                # GRAVAR CERTIDAO - POSTGRESQL - 2 VEZES COBRAR O CODIGO 8402-0 - CERTIDOES DE ONUS
                tipo_certidao = TipoCertidao.objects.filter(codigo_onr=6).first()
                Certidao.gerar_item_certidao(
                    tipo_certidao,
                    pessoa,
                    imovel,
                    data_atual,
                    tipo_tributacao,
                )

                Certidao.gerar_item_certidao(
                    tipo_certidao,
                    pessoa,
                    imovel,
                    data_atual,
                    tipo_tributacao,
                )
        else:
            # GRAVAR CERTIDAO - POSTGRESQL
            print("GRAVAR CERTIDAO UNICA: ", str(tipo_certidao))
            Certidao.gerar_item_certidao(
                tipo_certidao,
                pessoa,
                imovel,
                data_atual,
                tipo_tributacao,
            )

        # # EXPORTAR PEDIDO DE CERTIDAO PARA FIREBIRD
        # print(" EXPORTAR PEDIDO DE CERTIDAO FIREBIRD: ")

        # print(" Salvo e exportado firebird")

    return pedido
