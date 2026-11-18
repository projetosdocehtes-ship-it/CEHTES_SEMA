import logging
import xml.etree.ElementTree as element_tree
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.cartorios.models import Usuario as User
from apps.home import helpers
from apps.home.models import (
    Apresentante,
    Certidao,
    Event,
    Finalidade,
    PedidoCertidao,
    PedidoCertidaoImovel,
    PedidoCertidaoPessoa,
    TipoCertidao,
    TipoTributacao,
)

# Usuario,
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)


# Ler todo o arquivo XML
def ler_arquivo_xml_penhora_online_sph(arquivo, user, municipio_id):
    import os

    print("ler_arquivo_xml_PENHORA ONLINE SPH")

    # arquivo = "/home/usuario/Documentos/prime-django/media/pesquisas.xml"
    # FORMATO NECESSARIO PARA O LINUX
    if os.name == "nt":
        # FORMATO NECESSARIO PARA O WIN
        print("Running on Windows")
    else:
        # FORMATO NECESSARIO PARA O LINUX
        arquivo = str(arquivo).replace("\\", "/")

    try:
        tree = element_tree.parse(arquivo)
        root = (
            tree.getroot()
        )  # Movendo para dentro do try para lidar com erros de parse

        print("Percorrer ARQUIVO")
    except Exception as e:
        logger.exception("Erro ao abrir ou processar o arquivo: ", e)
        return None

    root = tree.getroot()

    lista = []

    print("Percorrer ARQUIVO")

    # Percorrer ARQUIVO
    for protocolo_solicitacao in root.findall("CERTIDAO"):
        # <PEDIDOOFICIO>
        pedido_oficio = next(
            (
                pedido_oficio.text
                for pedido_oficio in protocolo_solicitacao.findall("PROTOCOLOCERTIDAO")
            ),
            "",
        )

        # <NUMERODOOFICIO>
        numero_oficio = next(
            (
                numero_oficio.text
                for numero_oficio in protocolo_solicitacao.findall("NUMERODOPROCESSO")
            ),
            "",
        )
        if numero_oficio is None:
            numero_oficio = ""

        # <DATAOFICIO>
        data_oficio = next(
            (
                data_oficio.text
                for data_oficio in protocolo_solicitacao.findall("DATAPED")
            ),
            "",
        )

        # <NOMEPESQUISA>
        nome_pesquisa = next(
            (
                nome_pesquisa.text
                for nome_pesquisa in protocolo_solicitacao.findall("NOMEPESQPED")
            ),
            "",
        )
        if nome_pesquisa is None:
            nome_pesquisa = ""

        # <CPFCNPJ>
        cpf_pesquisa = next(
            (
                cpf_pesquisa.text
                for cpf_pesquisa in protocolo_solicitacao.findall("CPFCNPJ")
            ),
            "",
        )
        if cpf_pesquisa:
            cpf_pesquisa = (
                cpf_pesquisa.replace(".", "").replace("/", "").replace("-", "")
            )

        valor_certidao = next(
            (
                valor_certidao.text
                for valor_certidao in protocolo_solicitacao.findall("VALORDADIVIDA")
            ),
            "",
        )

        next(
            (
                imoveis_direito.text
                for imoveis_direito in protocolo_solicitacao.findall("IMOVEISDEDIREITO")
            ),
            "",
        )

        nome_instituicao = next(
            (
                nome_instituicao.text
                for nome_instituicao in protocolo_solicitacao.findall("VARA")
            ),
            "",
        )

        # TIPO DE CERTIDAO = 1 (IMOVEL)     TIPO DE CERTIDAO = 2 (PESSOA)
        tipo_certidao_penhora = next(
            (
                tipo_certidao_penhora.text
                for tipo_certidao_penhora in protocolo_solicitacao.findall(
                    "TIPOCERTIDAO",
                )
            ),
            "",
        )

        # MATRICULA DO IMOVEL
        numero_matricula = next(
            (
                numero_matricula.text
                for numero_matricula in protocolo_solicitacao.findall("MATR1PESQPED")
            ),
            "",
        )

        if numero_matricula is None:
            numero_matricula = ""

        tipo_cobranca = 0
        finalidade = None

        # 14: ("Buscas", "14"),
        codigo_certidao_onr = 14

        with transaction.atomic():
            db = FbConnection()
            db.begin_transaction()
            try:
                # GRAVAR PEDIDO DE CERTIDAO
                pedido: PedidoCertidao = gerar_pedido_certidao(
                    protocolo_onr=pedido_oficio,
                    data_onr=str(data_oficio),
                    valor=valor_certidao,
                    nome_solicitante=nome_instituicao,
                    telefone="",
                    email="",
                    cpfcnpj="",
                    numero_matricula=numero_matricula,
                    codigo_certidao_onr=codigo_certidao_onr,
                    isento_ccm=tipo_cobranca,
                    nome_pesquisa=nome_pesquisa,
                    cpf_pesquisa=cpf_pesquisa,
                    endereco=numero_oficio,
                    user=user,
                    origem_pedido=5,
                    finalidade=finalidade,
                    tipo_certidao_imovel_pessoa=tipo_certidao_penhora,
                    municipio_id=municipio_id,
                )

                descricao_observacao = "OFICIO ELETRONICO (ONR): " + str(pedido_oficio)

                # REGISTRAR CAIXA
                if pedido:
                    pedido.enviar_pagamento_certidao_onr_caixa(
                        pk=pedido.id,
                        numero_pedido=pedido.numero_pedido,
                        valor_transacao=valor_certidao,
                        descricao=descricao_observacao,
                        db=db,
                    )

                # Adicionando 4 horas
                horario_atual = timezone.now()
                horario_atual_final = horario_atual + timedelta(hours=4)

                # COLABORADOR AVISADO CERTIDAO DA ONR
                colaborador_avisar = User.get_usuarios_avisar_certidao_onr() or [1]

                # REGISTRAR EVENTO NA AGENDA - Gravar o evento na agenda do dia
                if pedido:
                    for colaborador in colaborador_avisar:
                        Event.criar_evento_no_calendario(
                            user=colaborador,
                            auth_user=colaborador,
                            numero=str(pedido.numero_pedido),
                            title=str(pedido_oficio),
                            description=descricao_observacao,
                            origem="C",
                            horas_adicionais=0,
                            url="",
                            data_futura_inicio=horario_atual,
                            data_futura_fim=horario_atual_final,
                            gravar_apenas_data="N",
                            fase_agenda_id=1,
                            exibir_agenda="S",
                        )

                    pedido.exportar_pedido_certidao_para_fb(
                        descricao_observacao=descricao_observacao,
                        origem_id=5,
                        valor_transacao=valor_certidao,
                        db=db,
                    )

                db.commit()
                db.close()
            except Exception:
                db.rollback()
                db.close()
                logger.exception("Erro ao exportar pedido de certidão")
                raise

        if pedido:
            lista.append(pedido.numero_pedido)

    return lista


# Gerar a lista para salvar o Pedido de certidao
@transaction.atomic
def gerar_pedido_certidao(
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
    origem_pedido=3,
    finalidade="",
    tipo_certidao_imovel_pessoa=1,
    municipio_id="",
):
    print("Verificar se o pedido ONR ja foi gravado: ", str(protocolo_onr))

    # PROTOCOLO ONR - VERIFICAR SE O PEDIDO ONR JA FOI GRAVADO
    if PedidoCertidao.objects.filter(protocolo_onr=str(protocolo_onr)).exists():
        print("Já gravado: ", str(protocolo_onr))
        return 0

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
    data_atual = timezone.now()

    # Conversão para datetime
    # try:
    #     data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y")
    # except:
    #     data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y %H:%M:%S")
    formatos = helpers.formatos_de_datas()

    for formato in formatos:
        try:
            data_pedido_onr = datetime.strptime(data_onr, formato)
            break  # Se conseguir converter, sai do loop
        except ValueError:
            continue  # Tenta o próximo formato se ocorrer um erro

    # FORMATAR ENDERECO COM VALOR DA ONR
    endereco = endereco + " " + nome_solicitante + " R$" + str(valor)

    # GRAVAR PEDIDO - POSTGRESQL
    print("GRAVAR PEDIDO: ", str(protocolo_onr), " origem:", origem_pedido)

    # ATUALIZAR A SEQUENCE ANTES DE GRAVAR
    with transaction.atomic(), FbConnection() as db:
        db.begin_transaction()
        # proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # while PedidoCertidao.objects.filter(numero_pedido=proximo_pedido).exists():
        #    proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # db.commit()

        # print("PED_CERTIDOES_SEQ Firebird:", proximo_pedido)

        pedido = PedidoCertidao.objects.create(
            # numero_pedido=proximo_pedido,
            origem_id=origem_pedido,
            data_entrada=data_atual,
            # data_validade=data_atual + timedelta(days=5),
            data_pedido_onr=data_pedido_onr or data_atual,
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
        print("GRAVAR REGISTRO: ")

        imovel = None
        if str(numero_matricula) != "":
            imovel = PedidoCertidaoImovel.objects.create(
                pedido=pedido,
                cartorio="1",
                municipio_id=municipio_id,
                tipo_imovel_id="1",
                numero_registro=numero_matricula,
                tipo_registro_id="1",
                tipo_logradouro_id="1",
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
            )

        # GRAVAR ANDAMENTOS - POSTGRESQL
        print("GRAVAR ANDAMENTOS: ")
        # Livro01Andamento.objects.create(pedido=pedido, data_hora=data_atual, tipo_andamento="CP", criado_por=user)

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
            tipo_certidao = TipoCertidao.objects.filter(codigo_onr=12).first()

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

        # EXPORTAR PEDIDO DE CERTIDAO PARA FIREBIRD
        print(" EXPORTAR PEDIDO DE CERTIDAO: ")

        valor = str(valor).replace(".", "")
        valor = str(valor).replace(",", ".")

        print(" Salvo e exportado firebird")

    # return pedido.numero_pedido
    return pedido
