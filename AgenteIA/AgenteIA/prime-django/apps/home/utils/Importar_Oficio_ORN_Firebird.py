import logging
import xml.etree.ElementTree as ET
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.home import helpers
from apps.home.models import (
    Apresentante,
    Certidao,
    PedidoCertidao,
    PedidoCertidaoImovel,
    PedidoCertidaoPessoa,
    TipoCertidao,
    TipoTributacao,
)
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)


def ler_arquivo_xml_oficio_onr(arquivo):
    """Ler arquivo XML de oficio ONR e retorna uma lista de dicionários com os dados dos ofícios."""
    print("ler_arquivo_xml_oficio_onr")

    try:
        tree = ET.parse(arquivo)
        root = tree.getroot()
        print("Arquivo processado com sucesso")
    except Exception as e:
        logger.exception("Erro ao abrir ou processar o arquivo: ", e)
        return None

    lista_oficios = []

    if not root.findall("OFICIO"):
        logger.error(
            f"Nao encontrado a TAG oficio para inicar no arquivo XML: {arquivo}",
        )

    for protocolo_solicitacao in root.findall("OFICIO"):
        oficio_dict = {
            "pedido_Oficio": protocolo_solicitacao.findtext("PEDIDOOFICIO", ""),
            "data_Oficio": protocolo_solicitacao.findtext("DATAOFICIO", ""),
            "nome_Instituicao": protocolo_solicitacao.findtext("NOMEINSTITUICAO", ""),
            "tipo_Pesquisa": protocolo_solicitacao.findtext("TIPOPESQUISA", ""),
            "numero_Oficio": protocolo_solicitacao.findtext("NUMERODOOFICIO", ""),
            "nome_Pesquisa": protocolo_solicitacao.findtext("NOMEPESQUISA", ""),
            "cpf_pesquisa": protocolo_solicitacao.findtext("CPFCNPJ", ""),
            "numero_matricula": protocolo_solicitacao.findtext("MATRICULA", ""),
            "numero_transcricao": protocolo_solicitacao.findtext("TRANSCRICAO", ""),
        }

        # VERIFICAR SE O PROTOCOLO NAO ESTA CADATRADO
        # if PedidoCertidao.objects.filter(protocolo_onr=protocolo_solicitacao["PEDIDOOFICIO"]).exists():
        #    print("Este protocolo já existe no sistema:", protocolo_solicitacao["PEDIDOOFICIO"])
        # else:
        lista_oficios.append(oficio_dict)

    return lista_oficios


def get_first_part_before_comma(s):
    """
    Retorna a primeira parte da string antes da vírgula, ou a string inteira se não houver vírgula.
    Remove espaços em branco ao redor da string resultante.
    """
    numero = s.split(",")[0].strip()
    return str(numero).replace(".", "")


def criar_pedido_certidao_oficio_onr(
    protocolo_onr,
    data_onr,
    valor,
    nome_solicitante,
    telefone,
    email,
    cpfcnpj,
    numero_matricula,
    numero_transcricao,
    codigo_certidao_onr,
    isento_ccm,
    nome_pesquisa,
    cpf_pesquisa,
    endereco,
    user,
    origem_pedido=3,
    municipio_id="",
    anotacoes="",
):
    print("Verificar se o pedido ONR ja foi gravado: ", str(protocolo_onr))

    # PROTOCOLO ONR - VERIFICAR SE O PEDIDO ONR JA FOI GRAVADO
    if PedidoCertidao.objects.filter(protocolo_onr=str(protocolo_onr)).exists():
        msg = f"Já gravado: {protocolo_onr!s}"
        logger.error(
            f"Este pedido já foi gravado anteriormente: {protocolo_onr!s}",
        )
        raise ValueError(msg)

    # PEGAR DATA ATUAL
    data_atual = timezone.now()

    # data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y")
    # Conversão para datetime
    # try:
    #     data_pedido_onr = datetime.strptime(data_onr, "%d-%m-%Y %H:%M:%S")
    # except:
    #     data_pedido_onr = datetime.strptime(data_onr, "%Y-%m-%d")
    formatos = helpers.formatos_de_datas()

    for formato in formatos:
        try:
            data_pedido_onr = datetime.strptime(data_onr, formato)
            break  # Se conseguir converter, sai do loop
        except ValueError:
            continue  # Tenta o próximo formato se ocorrer um erro

    # FORMATAR ENDERECO COM VALOR DA ONR
    endereco = nome_solicitante + " " + endereco + " " + str(valor)

    # GRAVAR PEDIDO - POSTGRESQL
    print("GRAVAR PEDIDO: ", str(protocolo_onr), " origem:", origem_pedido)

    # ATUALIZAR A SEQUENCE ANTES DE GRAVAR
    with transaction.atomic(), FbConnection() as db:
        db.begin_transaction()
        # proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # while PedidoCertidao.objects.filter(numero_pedido=proximo_pedido).exists():
        #     proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # # db.commit()

        # print("PED_CERTIDOES_SEQ Firebird:", proximo_pedido)

        pedido_certidao = PedidoCertidao.objects.create(
            # numero_pedido=proximo_pedido,
            # numero_pedido_firebird=proximo_pedido,
            origem_id=origem_pedido,
            data_entrada=data_atual,
            # data_validade=data_atual + timedelta(days=5),
            data_pedido_onr=data_pedido_onr,
            protocolo_onr=str(protocolo_onr),
            observacao=endereco,
        )

        # GRAVAR APRESENTANTE - POSTGRESQL
        print("GRAVAR APRESENTANTE: ", str(nome_solicitante))

        # CPF OU CNPJ
        tipo_documento_id = 2 if len(cpfcnpj) >= 14 else 1

        Apresentante.objects.create(
            nome=nome_solicitante,
            pedido=pedido_certidao,
            telefone=telefone,
            email=email,
            documento=cpfcnpj,
            tipo_documento_id=tipo_documento_id,
            observacao=protocolo_onr if protocolo_onr else "",
        )

        # GRAVAR IMOVEL - POSTGRESQL
        print("GRAVAR REGISTRO: ")

        imovel = None

        # Verifica se há uma vírgula na string
        # Usa a função auxiliar para tratar as strings
        numero_matricula = get_first_part_before_comma(numero_matricula)
        numero_transcricao = get_first_part_before_comma(numero_transcricao)

        # NUMERO DE MATRICULA
        try:
            if str(numero_matricula) != "":
                imovel = PedidoCertidaoImovel.objects.create(
                    pedido=pedido_certidao,
                    cartorio="1",
                    municipio_id=municipio_id,
                    tipo_imovel_id="1",
                    numero_registro=str(numero_matricula),
                    tipo_registro_id="1",
                    tipo_logradouro_id="1",
                )
        except:
            print("Erro ao gravar imovel no oficio: ", str(numero_matricula))

        # NUMERO DE TRANSCRICAO
        numero_transcricao = str(numero_transcricao).replace("None", "")
        if str(numero_transcricao) != "":
            imovel = PedidoCertidaoImovel.objects.create(
                pedido=pedido_certidao,
                cartorio="1",
                municipio_id=municipio_id,
                tipo_imovel_id="1",
                numero_registro=str(numero_transcricao),
                tipo_registro_id="2",
                tipo_logradouro_id="1",
            )

        # GRAVAR PESSOA - POSTGRESQL
        tipo_documento_id = 1
        print("GRAVAR PESSOA: ")

        pessoa = None
        if str(nome_pesquisa) != "":
            pessoa = PedidoCertidaoPessoa.objects.create(
                pedido=pedido_certidao,
                nome=nome_pesquisa,
                documento=cpf_pesquisa,
                tipo_documento_id=tipo_documento_id,
                anotacoes=anotacoes,
            )

        # GRAVAR ANDAMENTOS - POSTGRESQL
        print("GRAVAR ANDAMENTOS: ")
        # Livro01Andamento.objects.create(pedido=pedido, data_hora=data_atual, tipo_andamento="CP", criado_por=user)

        """
            tipo_certidao_protocolo_solicitacao == "3"    # MATRICULA - INTEIRO TEOR
            tipo_certidao_protocolo_solicitacao == "12":  # VISUALIZAR MATRICULA
        """

        # Verificar se o cobranca ISENTA OU NORMAL - POSTGRESQL
        percentual_desconto = 100 if str(isento_ccm) != "1" else 0

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

        # CASO NAO ENCONTRE O TIPO DE CERTIDAO
        if tipo_certidao is None:
            tipo_certidao = TipoCertidao.objects.filter(codigo_onr=3).first()

        # GRAVAR CERTIDAO - POSTGRESQL
        if tipo_certidao:
            print("GRAVAR CERTIDAO: ", str(tipo_certidao))
            Certidao.objects.create(
                tipo_certidao=tipo_certidao,
                pessoa=pessoa,
                imovel=imovel,
                data_emissao=data_atual,
                tipo_tributacao=tipo_tributacao,
            )

    # return pedido_certidao.numero_pedido
    return pedido_certidao
