import logging
import xml.etree.ElementTree as element_tree
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.cartorios.models import Usuario
from apps.comum import models as comum_models
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
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)


# Ler todo o arquivo XML
def ler_arquivo_xml_consulta_eletronica(arquivo, user, municipio_id, origem_id):
    import os

    print("ler_arquivo_xml_CONSULTA_ELETRONICA")

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
        logger.exception(
            f"Erro ao abrir ou processar o arquivo: {e}",
        )
        return None

    root = tree.getroot()

    lista = []

    print("Percorrer ARQUIVO")

    # Percorrer ARQUIVO
    for protocolo_solicitacao in root.findall("PESQUISA"):
        # <PEDIDOOFICIO>
        pedido_oficio = next(
            (
                pedido_oficio.text
                for pedido_oficio in protocolo_solicitacao.findall("PROTOCOLO")
            ),
            "",
        )

        # <NUMERODOOFICIO>
        numero_oficio = pedido_oficio

        # <DATAOFICIO>
        data_oficio = next(
            (
                data_oficio.text
                for data_oficio in protocolo_solicitacao.findall("DATAPESQUISA")
            ),
            "",
        )

        # <NOMEPESQUISA>
        nome_pesquisa = next(
            (
                nome_pesquisa.text
                for nome_pesquisa in protocolo_solicitacao.findall(
                    "NOMEDAPESSOAPESQUISADA",
                )
            ),
            "",
        )

        # <VLRRECPED>
        valor_certidao = next(
            (
                valor_certidao.text
                for valor_certidao in protocolo_solicitacao.findall("VLRRECPED")
            ),
            "",
        )

        # <CPFCNPJ>
        cpf_pesquisa = next(
            (
                cpf_pesquisa.text
                for cpf_pesquisa in protocolo_solicitacao.findall("CPFCNPJ")
            ),
            "",
        )

        # <FINALIDADE>
        finalidade = next(
            (
                finalidade.text
                for finalidade in protocolo_solicitacao.findall("FINALIDADE")
            ),
            "",
        )

        # <SOLICITANTE>
        for solicitante_protocolo_solicitacao in protocolo_solicitacao.findall(
            "SOLICITANTE",
        ):
            # <NOMESOLICPED>
            nome_instituicao = next(
                (
                    nome_instituicao.text
                    for nome_instituicao in solicitante_protocolo_solicitacao.findall(
                        "NOMESOLICPED",
                    )
                ),
                "",
            )

            # <FONESOLICPED>
            telefone_solicitante_protocolo_solicitacao = next(
                (
                    telefone_solicitante_protocolo_solicitacao.text
                    for telefone_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
                        "FONESOLICPED",
                    )
                ),
                "",
            )
            print(telefone_solicitante_protocolo_solicitacao)

            # <CPFCNPJSOLICPED>
            cpfcnpj_solicitante_protocolo_solicitacao = next(
                (
                    cpfcnpj_solicitante_protocolo_solicitacao.text
                    for cpfcnpj_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
                        "CPFCNPJSOLICPED",
                    )
                ),
                "",
            )
            print(cpfcnpj_solicitante_protocolo_solicitacao)

            # <MAILSOLICPED>
            email_solicitante_protocolo_solicitacao = next(
                (
                    email_solicitante_protocolo_solicitacao.text
                    for email_solicitante_protocolo_solicitacao in solicitante_protocolo_solicitacao.findall(
                        "MAILSOLICPED",
                    )
                ),
                "",
            )
            print(email_solicitante_protocolo_solicitacao)

            # <ISENTOCCM>
            next(
                (
                    isento_ccm.text
                    for isento_ccm in solicitante_protocolo_solicitacao.findall(
                        "ISENTOCCM",
                    )
                ),
                "",
            )

            # <ISENTOCCM>
            tipo_cobranca = next(
                (
                    tipo_cobranca.text
                    for tipo_cobranca in solicitante_protocolo_solicitacao.findall(
                        "TIPOCOBRANCA",
                    )
                ),
                "",
            )

            numero_matricula = ""

            # 12: ("Visualizar Matricula", "11"),
            codigo_certidao_onr = 12

            # <ENDSOLICPED>General Câmara</ENDSOLICPED>
            # <NUMENDSOLICPED>SN</NUMENDSOLICPED>
            # <COMPLENDSOLICPED />
            # <BAIRROSOLICPED>Centro</BAIRROSOLICPED>
            # <CIDADESOLICPED />
            # <ESTADOSOLICPED>RS</ESTADOSOLICPED>
            # <CEPSOLICPED>98005112</CEPSOLICPED>
            # <INCRICAOSOLICPED />
            # <CCM />
            # <NOMETOMADOR />
            # <CNPJTOMADOR />
            # <ENDERECOTOMADOR />
            # <CIDADEUFTOMADOR />
            # <TIPOCOBRANCA>1</TIPOCOBRANCA>

        # VERIFICAR SE O PROTOCOLO NAO ESTA CADATRADOprotocolo_solicitacao.findall("PROTOCOLO")
        if PedidoCertidao.objects.filter(
            protocolo_onr=protocolo_solicitacao.findall("PROTOCOLO"),
        ).exists():
            print(
                "Este protocolo já existe no sistema:",
                protocolo_solicitacao.findall("PROTOCOLO"),
            )
        else:
            with transaction.atomic(), FbConnection() as db:
                db.begin_transaction()
                try:
                    # GRAVAR PEDIDO DE CERTIDAO
                    pedido: PedidoCertidao = gerar_pedido_certidao(
                        protocolo_onr=pedido_oficio,
                        data_onr=str(data_oficio),
                        valor=valor_certidao,
                        nome_solicitante=nome_instituicao,
                        telefone=telefone_solicitante_protocolo_solicitacao,
                        email=email_solicitante_protocolo_solicitacao,
                        cpfcnpj=cpfcnpj_solicitante_protocolo_solicitacao,
                        numero_matricula=numero_matricula,
                        codigo_certidao_onr=codigo_certidao_onr,
                        isento_ccm=tipo_cobranca,
                        nome_pesquisa=nome_pesquisa,
                        cpf_pesquisa=cpf_pesquisa,
                        endereco=numero_oficio,
                        user=user,
                        origem_pedido=4,
                        finalidade=finalidade,
                        municipio_id=municipio_id,
                        origem_id=origem_id,
                    )

                    descricao = str("OFICIO ELETRONICO (ONR): " + str(pedido_oficio))

                    if pedido:
                        valor_certidao = str(valor_certidao).replace(".", "")
                        valor_certidao = str(valor_certidao).replace(",", ".")

                        # REGISTRAR CAIXA
                        pedido.enviar_pagamento_certidao_onr_caixa(
                            pk=pedido.id,
                            numero_pedido=pedido.numero_pedido,
                            valor_transacao=valor_certidao,
                            descricao=descricao,
                            db=db,
                        )

                        # Adicionando 4 horas
                        horario_atual = timezone.now()
                        horario_atual_final = horario_atual + timedelta(hours=4)

                        # COLABORADOR AVISADO CERTIDAO DA ONR
                        colaborador_avisar = (
                            Usuario.get_usuarios_avisar_certidao_onr() or [1]
                        )

                        # REGISTRAR EVENTO NA AGENDA - Gravar o evento na agenda do dia
                        for colaborador in colaborador_avisar:
                            Event.criar_evento_no_calendario(
                                user=colaborador,
                                auth_user=colaborador,
                                numero=str(pedido.numero_pedido),
                                title=str(pedido_oficio),
                                description=descricao,
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
                            descricao_observacao=descricao,
                            origem_id=1,
                            valor_transacao=valor_certidao,
                            db=db,
                        )

                        # REGISTRAR EVENTO NO CALENDARIO - ONR - CONSULTA ELETRONICA
                    db.commit()

                except Exception:
                    db.rollback()

                    logger.exception("Erro ao exportar pedido de certidão")
                    raise

        # lista.append(pedido.numero_pedido)

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
    municipio_id="",
    origem_id=4,
):
    print("Verificar se o pedido ONR ja foi gravado: ", str(protocolo_onr))

    # PROTOCOLO ONR - VERIFICAR SE O PEDIDO ONR JA FOI GRAVADO
    if PedidoCertidao.objects.filter(protocolo_onr=str(protocolo_onr)).exists():
        print("Já gravado: ", str(protocolo_onr))
        return None

    # Criar ou atualizar as finalidades
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
    data_pedido_onr = datetime.strptime(data_onr, "%d/%m/%Y %H:%M:%S")

    # FORMATAR ENDERECO COM VALOR DA ONR
    endereco = nome_solicitante + " " + str(valor)

    # GRAVAR PEDIDO - POSTGRESQL
    print("GRAVAR PEDIDO: ", str(protocolo_onr), " origem:", origem_pedido)

    # origem_id = 4

    try:
        origem_obj, created = comum_models.TipoOrigem.objects.get_or_create(
            id=4,
            defaults={
                "nome": "ONR - Consulta Eletrônica",
            },
        )
    except Exception as e:
        logger.exception(f"Erro ao criar origem: {e}")

    # ATUALIZAR A SEQUENCE ANTES DE GRAVAR
    with transaction.atomic(), FbConnection() as db:
        db.begin_transaction()
        # proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # while PedidoCertidao.objects.filter(numero_pedido=proximo_pedido).exists():
        #     proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo
        # db.commit()

        # print("PED_CERTIDOES_SEQ Firebird:", proximo_pedido)

        pedido = PedidoCertidao(
            # numero_pedido=proximo_pedido,
            origem=origem_obj,
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

        apresentante = Apresentante(
            nome=nome_solicitante,
            pedido=pedido,
            telefone=telefone,
            email=email,
            documento=cpfcnpj,
            tipo_documento_id=tipo_documento_id,
        )

        pedido.save()
        apresentante.save()

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

    return pedido
