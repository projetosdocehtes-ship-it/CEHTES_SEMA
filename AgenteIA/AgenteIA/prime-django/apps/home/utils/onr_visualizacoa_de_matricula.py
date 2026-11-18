import logging
import xml.etree.ElementTree as ET
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.comum import models as comum_models
from apps.home import helpers as home_helpers
from apps.home.models import (
    Apresentante,
    Certidao,
    PedidoCertidao,
    PedidoCertidaoImovel,
    TipoCertidao,
    TipoTributacao,
)
from core.utils.firebird_utils import FbConnection

# lista_arquivos_gerado = []

logger = logging.getLogger(__name__)


# Exibir os valores a serem cobrados 4.11.6.Tipo de Certidão
def get_tipo_valor_certidao(numero):
    # Dicionário mapeando números para tipos de certidões e códigos associados
    tipos_certidao = {
        1: (
            "Certidão Matrícula - De Inteiro Teor, de Ônus e Ações Reipersecutórias",
            "2",
        ),
        2: ("Certidão Matrícula - Inteiro Teor", "2"),
        3: ("Certidão de Propriedade", "4"),
        4: ("Certidão de Registro do Imóvel", "4"),
        5: ("Certidão de Registro Auxiliar", "3"),
        6: ("Certidões de Ônus e de Ações", "2"),
        7: ("Certidão de Transcrição – Inteiro Teor", "T"),
        8: ("Certidão de Documento Arquivado", "0"),
        9: ("Certidão de Registro Auxiliar – Inteiro Teor", "3"),
        10: ("Certidão de Registro Auxiliar – Por Quesito", "3"),
        12: ("Visualizar Matricula", "11"),
        13: ("Penhora Eletronica", "13"),
        14: ("Buscas", "14"),
    }

    # Acessar o dicionário usando o número fornecido
    tipo_certidao = tipos_certidao.get(numero)

    # Se um tipo de certidão for encontrado, retorna-o; caso contrário, retorna None
    if tipo_certidao:
        return tipo_certidao
    else:
        print("Número tipo da certidão desconhecido:", numero)
        return None


# Ler todo o arquivo XML
# def ler_arquivo_xml_matricula_visualizada(arquivo, user):
#     try:
#         tree = element_tree.parse(arquivo)
#         root = tree.getroot()  # Movendo para dentro do try para lidar com erros de parse

#         print("Percorrer ARQUIVO")
#     except Exception as e:
#         print("Erro ao abrir ou processar o arquivo: ", e)
#         return None

#     root = tree.getroot()

#     # Listas Gerar Gravacao
#     imoveis_titular = ""

#     # Percorrer ARQUIVO
#     for conteudo in root.findall("VISUALIZACAOMATRICULA"):
#         # <NUMERODOOFICIO>
#         next((numero.text for numero in conteudo.findall("MATRICULACNMSOLICITACAOPED")), "")

#         # <PEDIDOOFICIO>
#         pedido_oficio = next((pedido.text for pedido in conteudo.findall("NUMSOLICITACAOPED")), "")
#         print("Percorrer pedido_oficio", pedido_oficio)

#         # <DATAOFICIO>
#         data_oficio = next((data.text for data in conteudo.findall("DATAPED")), "")

#         # <NOMEINSTITUICAO>
#         nome_instituicao = next((nome.text for nome in conteudo.findall("NOMESOLICPED")), "")

#         # <VALOR VISUALIZACAO>
#         valor_visualizacao = next((valor.text for valor in conteudo.findall("VLRRECPED")), "")

#         # TIPO DE COBRANCA -  <TIPOCOBRANCA>3</TIPOCOBRANCA> ISENTO         <TIPOCOBRANCA>1</TIPOCOBRANCA> NORMAL
#         tipo_cobranca = next((cobranca.text for cobranca in conteudo.findall("TIPOCOBRANCA")), "")

#         # EMAIL SOLICITANTE
#         email_solicitante = next((email.text for email in conteudo.findall("MAILSOLICPED")), "")

#         # CPF SOLICITANTE
#         cpf_solicitante = next((cpf.text for cpf in conteudo.findall("CPFCNPJSOLICPED")), "")

#         # ENDERECO DA PESSOA
#         endereco_numero = next((endereco.text for endereco in conteudo.findall("NUMENDSOLICPED")), "")
#         endereco = next((endereco.text for endereco in conteudo.findall("ENDSOLICPED")), "")
#         endereco_complemento = next((x.text for x in conteudo.findall("COMPLENDSOLICPED")), "")
#         endereco_bairro = next((endereco_bairro.text for endereco_bairro in conteudo.findall("BAIRROSOLICPED")), "")
#         endereco_cidade = next((endereco_cidade.text for endereco_cidade in conteudo.findall("CIDADESOLICPED")), "")
#         endereco_estado = next((endereco_estado.text for endereco_estado in conteudo.findall("ESTADOSOLICPED")), "")
#         endereco_cep = next((endereco_cep.text for endereco_cep in conteudo.findall("CEPSOLICPED")), "")
#         fone_apresentante = next((fone_apresentante.text for fone_apresentante in conteudo.findall("FONESOLICPED")), "")

#         # FORMATAR O ENDERECO
#         endereco_parts = [
#             endereco,
#             endereco_numero,
#             endereco_complemento,
#             endereco_bairro,
#             endereco_cidade,
#             endereco_estado,
#             endereco_cep,
#         ]
#         endereco = " ".join(str(part).replace("None", "") for part in endereco_parts if part)
#         endereco = endereco.replace("  ", " ")

#         nome_pesquisa, cpf_pesquisa = "", ""

#         # <IMOVEISDEDIREITOTITULAR>
#         imoveis_titular = next((imovel.text for imovel in conteudo.findall("MATRICULACNMSOLICITACAOPED")), "")

#         # FALTA
#         # INCRICAOSOLICPED

#         # 12: ("Visualizar Matricula", "11"),
#         codigo_certidao_onr = 12


def ler_xml_matricula_visualizada(file) -> list[dict]:
    remover_linha_inicial = False

    try:
        tree = ET.parse(file)
        root = tree.getroot()
    except Exception:
        remover_linha_inicial = True

        # REMOVER LINHA
        # arquivo = home_helpers.remover_matricula_visualizada_xml(arquivo)
        # arquivo = home_helpers.remover_matricula_visualizada_xml(arquivo)
        file = home_helpers.remover_linha_inicial_xml(file)
        file = home_helpers.remover_linha_inicial_xml(file)
        file = home_helpers.remover_ultima_xml(file)

    except ET.ParseError as e:
        logger.info(f"Erro ao processar o arquivo XML: {e}")
        return []
    except FileNotFoundError as e:
        logger.info(f"Arquivo não encontrado: {e}")
        return []

    # APOS REMOVER LINHA
    if remover_linha_inicial:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
        except Exception as e:
            logger.exception(f"Erro ao abrir ou processar o arquivo: { e}")
            return []

    lista_dados = []

    campos = [
        ("numero_oficio", "MATRICULACNMSOLICITACAOPED"),
        ("pedido_oficio", "NUMSOLICITACAOPED"),
        ("data_oficio", "DATAPED"),
        ("nome_instituicao", "NOMESOLICPED"),
        ("valor_visualizacao", "VLRRECPED"),
        ("tipo_cobranca", "TIPOCOBRANCA"),
        ("email_solicitante", "MAILSOLICPED"),
        ("cpf_solicitante", "CPFCNPJSOLICPED"),
        ("endereco_numero", "NUMENDSOLICPED"),
        ("endereco", "ENDSOLICPED"),
        ("endereco_complemento", "COMPLENDSOLICPED"),
        ("endereco_bairro", "BAIRROSOLICPED"),
        ("endereco_cidade", "CIDADESOLICPED"),
        ("endereco_estado", "ESTADOSOLICPED"),
        ("endereco_cep", "CEPSOLICPED"),
        ("fone_apresentante", "FONESOLICPED"),
        ("imoveis_titular", "MATRICULACNMSOLICITACAOPED"),
    ]

    for conteudo in root.findall("VISUALIZACAOMATRICULA"):
        dados = {}
        for campo in campos:
            elemento = conteudo.find(campo[1])
            dados[campo[0]] = elemento.text if elemento is not None else ""
        dados["codigo_certidao_onr"] = 12

        endereco_parts = [
            dados["endereco"],
            dados["endereco_numero"],
            dados["endereco_complemento"],
            dados["endereco_bairro"],
            dados["endereco_cidade"],
            dados["endereco_estado"],
            dados["endereco_cep"],
        ]
        dados["endereco_formatado"] = " ".join(filter(None, endereco_parts)).replace(
            "  ",
            " ",
        )

        lista_dados.append(dados)

    return lista_dados


def criar_pedido_de_certidao_onr_matricula_visualizada(
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
    origem_pedido=1,
    municipio_id="",
    observacao="",
) -> PedidoCertidao:
    logger.info("Criando pedido de certidao ONR - Matricula Visualizada")

    pedido = verificar_pedido_existente(protocolo_onr)
    if pedido:
        print("Pedido já existe:", protocolo_onr, pedido.numero_pedido)
        return pedido

    data_atual = timezone.now()
    data_pedido_onr = formatar_data_pedido(data_onr)
    endereco = formatar_endereco_com_valor(endereco, valor)

    with transaction.atomic(), FbConnection():
        pedido = criar_pedido_certidao(
            origem=comum_models.TipoOrigem.get_visualizacao_matricula(),
            data_atual=data_atual,
            data_pedido_onr=data_pedido_onr,
            protocolo_onr=protocolo_onr,
            observacao=observacao,
            endereco=endereco,
            user=user,
        )

        apresentante = criar_apresentante(
            nome_solicitante=nome_solicitante,
            telefone=telefone,
            email=email,
            cpfcnpj=cpfcnpj,
            pedido=pedido,
        )

        pedido.save()

        apresentante.save()

        registro = adicionar_registro_ao_pedido(pedido, municipio_id, numero_matricula)

        adicionar_certidao_ao_pedido(
            pedido, registro, data_atual, codigo_certidao_onr, isento_ccm
        )

        # GRAVAR FINANCEIRO
        pedido.enviar_para_pagamento_caixa(
            valor_transacao=valor,
            tipo_operacao_financeira_id=1,
            tipo_transacao_id=1,
            descricao="ONR: " + str(protocolo_onr),
            nome_pagador="ONR",
            data_original=timezone.now(),
            colaborador_financeiro_id=user.id,
        )

    return pedido


def verificar_pedido_existente(protocolo_onr):
    pedido = PedidoCertidao.objects.filter(protocolo_onr=str(protocolo_onr)).first()
    if pedido:
        logger.info(
            f"Este pedido ONR já foi importado anteriormente: {protocolo_onr!s}",
        )
    return pedido


def formatar_data_pedido(data_onr):
    return datetime.strptime(data_onr, "%d/%m/%Y %H:%M:%S")


def formatar_endereco_com_valor(endereco, valor):
    return f"{endereco} {valor}"


def obter_proximo_pedido(db):
    # proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
    # while PedidoCertidao.objects.filter(numero_pedido=proximo_pedido).exists():
    #     proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
    # logger.debug(f"PED_CERTIDOES_SEQ Firebird: {proximo_pedido}")
    # return proximo_pedido
    pass


def criar_pedido_certidao(
    origem,
    data_atual,
    data_pedido_onr,
    protocolo_onr,
    observacao,
    endereco,
    user,
):
    return PedidoCertidao(
        # numero_pedido=proximo_pedido,
        origem=origem,
        data_entrada=data_atual,
        data_pedido_onr=data_pedido_onr,
        protocolo_onr=str(protocolo_onr),
        observacao=observacao if observacao else endereco,
        criado_por=user,
    )


def criar_apresentante(
    nome_solicitante,
    telefone,
    email,
    cpfcnpj,
    pedido,
) -> Apresentante:
    logger.debug(f"GRAVAR APRESENTANTE: {nome_solicitante!s}")
    return Apresentante(
        nome=nome_solicitante,
        telefone=telefone,
        email=email,
        documento=cpfcnpj,
        pedido=pedido,
    )


def adicionar_registro_ao_pedido(pedido, municipio_id, numero_matricula):
    logger.debug(f"GRAVAR REGISTRO: {numero_matricula!s}")
    return PedidoCertidaoImovel.objects.create(
        pedido=pedido,
        cartorio="1",
        municipio_id=municipio_id,
        tipo_imovel_id="1",
        numero_registro=numero_matricula,
        tipo_registro_id="1",
        tipo_logradouro_id="1",
    )


def adicionar_certidao_ao_pedido(
    pedido, imovel, data_atual, codigo_certidao_onr, isento_ccm
):
    percentual_desconto = 100 if str(isento_ccm) != "1" else 0
    tipo_tributacao = obter_tipo_tributacao(percentual_desconto)
    tipo_certidao = obter_tipo_certidao(codigo_certidao_onr)

    if tipo_certidao:
        logger.debug(f"GRAVAR CERTIDAO: {tipo_certidao}")
        Certidao.objects.create(
            tipo_certidao=tipo_certidao,
            pessoa=None,
            imovel=imovel,
            data_emissao=data_atual,
            tipo_tributacao=tipo_tributacao,
        )


def obter_tipo_tributacao(percentual_desconto):
    tipo_tributacao = TipoTributacao.objects.filter(
        percentual_desconto=percentual_desconto,
    ).first()
    if tipo_tributacao is None:
        tipo_tributacao = TipoTributacao.objects.filter(id=1).first()
    return tipo_tributacao


def obter_tipo_certidao(codigo_certidao_onr):
    tipo_certidao = TipoCertidao.objects.filter(codigo_onr=codigo_certidao_onr).first()
    if tipo_certidao is None:
        tipo_certidao = TipoCertidao.objects.filter(codigo_onr=12).first()
    return tipo_certidao
