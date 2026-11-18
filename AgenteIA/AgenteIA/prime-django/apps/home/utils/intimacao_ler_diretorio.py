import logging
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

# from django.utils.timezone import datetime
from django.db import transaction
from django.utils import timezone

from apps.cartorios.models import Usuario
from apps.home import helpers as home_helpers
from apps.home.models import Event
from apps.home.models.models_certidoes import PedidoCertidao
from apps.home.padroes import MATRICULA_VISUALIZADA_ORIGEM_ID
from apps.home.services import firebird
from apps.home.utils.Importar_Consulta_ORN_Firebird import (
    ler_arquivo_xml_consulta_eletronica,
)
from apps.home.utils.Importar_Penhora_SPH_ORN_Firebird import (
    ler_arquivo_xml_penhora_online_sph,
)
from apps.home.utils.onr_eprotocolo import criar_protocolo_onr_no_fb
from apps.home.utils.onr_visualizacoa_de_matricula import (
    criar_pedido_de_certidao_onr_matricula_visualizada,
)
from core.utils.firebird_utils import FbConnection

if TYPE_CHECKING:
    from apps.home.models import Pedido

logger = logging.getLogger(__name__)


def processar_matriculas_visualizadas_onr(
    matriculas_visualizadas: list[dict[str, Any]],
    user,
) -> list[dict[str, str | None]]:
    """
    Processa o XML Matrícula Visualizadas da ONR para criar as pedidos de certidão no sistema.
    Retorna uma lista de dicionários, onde cada dicionário contém o pedido e a mensagem correspondente.
    """
    pedidos_processados = []

    for matricula in matriculas_visualizadas:
        try:
            pedido_oficio = matricula.get("pedido_oficio", "")
            data_oficio = matricula.get("data_oficio", "")
            valor_str = matricula.get("valor_visualizacao", "0")
            valor_formatado = valor_str.replace(".", "").replace(",", ".")
            valor_visualizacao = Decimal(valor_formatado)
            nome_instituicao = matricula.get("nome_instituicao", "")
            fone_apresentante = matricula.get("fone_apresentante", "")
            email_solicitante = matricula.get("email_solicitante", "")
            cpf_solicitante = matricula.get("cpf_solicitante", "")
            imoveis_titular = matricula.get("imoveis_titular", "")
            codigo_certidao_onr = matricula.get("codigo_certidao_onr", "")
            tipo_cobranca = matricula.get("tipo_cobranca", "")
            nome_pesquisa = matricula.get("nome_pesquisa", "")
            cpf_pesquisa = matricula.get("cpf_pesquisa", "")
            endereco = matricula.get("endereco", "")

            if PedidoCertidao.objects.filter(protocolo_onr=pedido_oficio).exists():
                mensagem = f"Protocolo {pedido_oficio} já importado anteriormente."
                logger.info(mensagem)
                pedidos_processados.append({"pedido": None, "mensagem": mensagem})
                continue

            with transaction.atomic(), FbConnection() as db:
                try:
                    db.begin_transaction()

                    pedido_de_certidao: PedidoCertidao = (
                        criar_pedido_de_certidao_onr_matricula_visualizada(
                            protocolo_onr=pedido_oficio,
                            data_onr=data_oficio,
                            valor=valor_visualizacao,
                            nome_solicitante=nome_instituicao,
                            telefone=fone_apresentante,
                            email=email_solicitante,
                            cpfcnpj=cpf_solicitante,
                            numero_matricula=imoveis_titular,
                            codigo_certidao_onr=codigo_certidao_onr,
                            isento_ccm=tipo_cobranca,
                            nome_pesquisa=nome_pesquisa,
                            cpf_pesquisa=cpf_pesquisa,
                            endereco=endereco,
                            user=user,
                            origem_pedido=MATRICULA_VISUALIZADA_ORIGEM_ID,
                            municipio_id=user.cartorio.municipio_id,
                            observacao=str(
                                "VISUALIZACAO MATRICULA (ONR): " + pedido_oficio,
                            ),
                        )
                    )

                    if pedido_de_certidao:
                        pedido_de_certidao.exportar_pedido_certidao_para_fb(
                            descricao_observacao=pedido_de_certidao.observacao,
                            origem_id=MATRICULA_VISUALIZADA_ORIGEM_ID,
                            valor_transacao=valor_visualizacao,
                            db=db,
                        )

                        mensagem_sucesso = f"Pedido de certidão ONR {pedido_oficio} criado com sucesso."
                        logger.info(mensagem_sucesso)
                        pedidos_processados.append(
                            {
                                "pedido": pedido_de_certidao,
                                "mensagem": mensagem_sucesso,
                            },
                        )
                    else:
                        mensagem_erro = "Erro ao criar pedido de certidão ONR - Matricula Visualizada."
                        logger.exception(mensagem_erro)
                        pedidos_processados.append(
                            {"pedido": None, "mensagem": mensagem_erro},
                        )
                        continue

                    db.commit()
                except Exception as e:
                    db.rollback()
                    mensagem_erro = f"Erro ao exportar pedido de certidão ONR - Matricula Visualizada: {e!s}"
                    logger.exception(mensagem_erro)
                    pedidos_processados.append(
                        {"pedido": None, "mensagem": mensagem_erro},
                    )
                    raise

        except Exception as e:
            mensagem_erro = f"Erro ao processar certidão ONR: {e!s}"
            logger.exception(mensagem_erro)
            pedidos_processados.append({"pedido": None, "mensagem": mensagem_erro})
            continue

    return pedidos_processados


# ARQUIVOS ONR DE OFICIO
def processar_xml_oficio_onr(file_location, uploaded_file, user) -> str:
    from apps.home.utils.Importar_Oficio_ORN_Firebird import (
        criar_pedido_certidao_oficio_onr,
        ler_arquivo_xml_oficio_onr,
    )

    try:
        arquivo_xml = file_location + "/" + str(uploaded_file)
    except:
        arquivo_xml = None

    if arquivo_xml:
        arquivo_xml = str(arquivo_xml).replace("\\", "/")
        arquivo_xml = str(arquivo_xml).replace("//", "/")

    print("Enviando arquivo............:", arquivo_xml)

    try:
        oficios_onr = ler_arquivo_xml_oficio_onr(arquivo_xml)
    except:
        oficios_onr = None
        return None

    if oficios_onr is None:
        logger.info(f"Nenhum ofício ONR processado no arquivo indicado {uploaded_file}")
        return None

    for oficio_onr in oficios_onr:
        try:
            pedido_oficio = oficio_onr.get("pedido_Oficio", "")
            data_oficio = oficio_onr.get("data_Oficio", "")
            nome_instituicao = oficio_onr.get("nome_Instituicao", "")
            oficio_onr.get("tipo_Pesquisa", "")
            numero_do_oficio = oficio_onr.get("numero_Oficio", "")
            nome_pesquisa = oficio_onr.get("nome_Pesquisa", "")
            cpf_pesquisa = oficio_onr.get("cpf_pesquisa", "")
            numero_matricula = oficio_onr.get("numero_matricula", "")
            numero_transcricao = oficio_onr.get("numero_transcricao", "")

            # Valores default não fornecidos pelo XML
            valor = 0
            isento_ccm = 0
            # codigo_certidao_onr = 2
            codigo_certidao_onr = 3  # Certidão de Ofício INTEIRO TEOR
            telefone = ""
            email = ""
            cpfcnpj = ""
            endereco = ""

            # FORMATAR O NUMERO DO OFICIO
            numero_do_oficio = str(numero_do_oficio).replace("None", "")
            if str(numero_do_oficio) != "":
                numero_do_oficio = "Nº Ofício: " + numero_do_oficio

            with transaction.atomic(), FbConnection() as db:
                try:
                    db.begin_transaction()
                    pedido: Pedido = criar_pedido_certidao_oficio_onr(
                        protocolo_onr=pedido_oficio,
                        data_onr=data_oficio,
                        valor=valor,
                        nome_solicitante=nome_instituicao,
                        telefone=telefone,
                        email=email,
                        cpfcnpj=cpfcnpj,
                        numero_matricula=numero_matricula,
                        numero_transcricao=numero_transcricao,
                        codigo_certidao_onr=codigo_certidao_onr,
                        isento_ccm=isento_ccm,
                        nome_pesquisa=nome_pesquisa,
                        cpf_pesquisa=cpf_pesquisa,
                        endereco=endereco,
                        user=user,
                        origem_pedido=3,
                        municipio_id=user.cartorio.municipio_id,
                        anotacoes=numero_do_oficio,
                    )

                    descricao_observacao = "OFICIO ELETRONICO (ONR): " + str(
                        pedido_oficio,
                    )

                    if pedido:
                        # REGISTRAR CAIXA
                        pedido.enviar_pagamento_certidao_onr_caixa(
                            pk=pedido.id,
                            numero_pedido=pedido.numero_pedido,
                            valor_transacao=valor,
                            descricao=descricao_observacao,
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
                            origem_id=6,
                            valor_transacao=valor,
                            db=db,
                        )

                    db.commit()
                except Exception:
                    db.rollback()
                    raise  # Sobe a exceção para não grava nada.
        except Exception:
            # Trata a exceção para não interromper o loop.
            logger.exception("Erro ao exportar pedido de certidão")
            continue


# ARQUIVOS ONR DE Pesquisa Qualificada - CONSULTA ELETRONICA
def processar_xml_consulta_eletronica_onr(
    file_location,
    uploaded_file,
    user,
    origem_id=4,
) -> str:
    arquivo_xml = file_location + "/" + str(uploaded_file)
    print("Enviando arquivo............:", arquivo_xml)

    ler_arquivo_xml_consulta_eletronica(
        arquivo=arquivo_xml,
        user=user,
        municipio_id=user.cartorio.municipio_id,
        origem_id=origem_id,
    )
    print("Arquivo enviando.......", arquivo_xml)


# ARQUIVOS ONR DE PENHORA ONLINE SPH
def processar_xml_penhora_online_sph_onr(file_location, uploaded_file, user) -> str:
    arquivo_xml = file_location + "/" + str(uploaded_file)
    print("Enviando arquivo............:", arquivo_xml)

    ler_arquivo_xml_penhora_online_sph(arquivo_xml, user, user.cartorio.municipio_id)
    print("Arquivo enviando.......", arquivo_xml)


# ARQUIVOS ONR CERTIDOES EMITIR
def processar_certidoes_emitir_onr(certidoes_emitir_onr, user) -> str:
    """
    Processa os dados extraidos do XML de Certidoes da Emitir da ONR para criar as pedidos de certidão no sistema.
    Retorna uma lista de dicionários, onde cada dicionário contém o pedido e a mensagem correspondente.
    """
    from apps.home.utils.onr_certidao_a_emitir import (
        gerar_pedido_certidao_onr_certidoes_emitir,
    )

    certidoes_emitir = []

    for certidao_onr in certidoes_emitir_onr:
        try:
            protocolo_onr = certidao_onr.get("PROTOCOLO_SOLICITACAO", "")

            if PedidoCertidao.objects.filter(protocolo_onr=protocolo_onr).exists():
                mensagem = f"Protocolo {protocolo_onr} já importado anteriormente."
                logger.info(mensagem)
                certidoes_emitir.append({"pedido": None, "mensagem": mensagem})
                continue

            data_onr = certidao_onr.get("DATA_PEDIDO", "")
            valor = certidao_onr.get("VALOR", "")
            tipo_cobranca = certidao_onr.get("TIPO_COBRANCA", "")

            solicitante = certidao_onr.get("SOLICITANTE", {})
            nome_solicitante = solicitante.get("NOME", "")
            telefone = solicitante.get("TELEFONE", "")
            email = solicitante.get("EMAIL", "")
            cpfcnpj = solicitante.get("CPFCNPJ", "")

            certidao = certidao_onr.get("CERTIDAO", {})
            numero_matricula = certidao.get("MATRICULA", {}).get("NUMERO", "")
            numero_registro_livro_3 = certidao.get("LIVRO3", {}).get(
                "NUMERO_REGISTRO_LIVRO_3",
                "",
            )
            tipo_certidao = certidao.get("TIPO", "")
            pessoa = certidao.get("PESSOA", {})
            nome_pesquisa = pessoa.get("NOME", "")
            cpf_pesquisa = pessoa.get("CPFCNPJ", "")
            observacao_certidao = certidao.get("OBSERVACAO", "")

            # LISTA DE ENDERECOS
            endereco_certidao = certidao.get("ENDERECO", {})

            # MONTAR ENDERECO DA CERTIDAO
            endereco = home_helpers.replace_string_none(
                endereco_certidao.get("ENDERECO", ""),
            )
            cep = home_helpers.replace_string_none(endereco_certidao.get("CEP", ""))
            numero = home_helpers.replace_string_none(
                endereco_certidao.get("NUMERO", ""),
            )
            complemento = home_helpers.replace_string_none(
                endereco_certidao.get("COMPLEMENTO", ""),
            )
            bloco = home_helpers.replace_string_none(
                endereco_certidao.get("BLOCO_TORRE", ""),
            )
            loteamento = home_helpers.replace_string_none(
                endereco_certidao.get("LOTEAMENTO", ""),
            )
            lote = home_helpers.replace_string_none(endereco_certidao.get("LOTE", ""))
            quadra = home_helpers.replace_string_none(
                endereco_certidao.get("QUADRA", ""),
            )
            numero_contribuinte = home_helpers.replace_string_none(
                endereco_certidao.get("NUMERO_CONTRIBUINTE", ""),
            )

            # LISTA DE ENDERECOS
            transcricao_certidao = certidao.get("TRANSCRICAO", {})

            # MONTAR ENDERECO DA CERTIDAO
            numero_transcricao = transcricao_certidao.get("NUMERO", "")
            letra_transcricao = transcricao_certidao.get("LETRA", "")
            livro_transcricao = transcricao_certidao.get("LIVRO", "")
            data_transcricao = transcricao_certidao.get("DATA", "")
            unidade_transcricao = transcricao_certidao.get(
                "TRANSCRICAO_UNIDADE_LOTE",
                "",
            )
            informacao_transcricao = transcricao_certidao.get(
                "INFORMACAO_ADICIONAL",
                "",
            )

            # EXISTE TRANSCRICAO
            if numero_transcricao:
                numero_matricula = home_helpers.replace_string_none(
                    str(numero_transcricao),
                )

                observacao_certidao = (
                    home_helpers.replace_string_none(str(letra_transcricao))
                    + " "
                    + home_helpers.replace_string_none(str(livro_transcricao))
                    + " "
                    + home_helpers.replace_string_none(str(data_transcricao))
                    + " "
                    + home_helpers.replace_string_none(str(unidade_transcricao))
                    + " "
                    + home_helpers.replace_string_none(str(informacao_transcricao))
                )

            try:
                endereco = f"{endereco} {lote} {quadra} {numero} {complemento} {bloco} {loteamento} {numero_contribuinte} {cep}".strip()
            except:
                endereco = " "
            endereco = str(endereco).replace("  ", " ")

            # verificar se o pedido nao pode ser feito
            if (
                str(numero_matricula) == ""
                and str(nome_pesquisa) == ""
                and str(endereco) == ""
                and Decimal(valor) == 0
            ):
                cancelar_pedido = True
            else:
                cancelar_pedido = False

            with transaction.atomic(), FbConnection() as db:
                db.begin_transaction()
                try:
                    pedido = gerar_pedido_certidao_onr_certidoes_emitir(
                        protocolo_onr=protocolo_onr,
                        data_onr=data_onr,
                        valor=valor,
                        nome_solicitante=nome_solicitante,
                        telefone=telefone,
                        email=email,
                        cpfcnpj=cpfcnpj,
                        numero_matricula=numero_matricula,
                        codigo_certidao_onr=tipo_certidao,
                        isento_ccm=tipo_cobranca,
                        nome_pesquisa=nome_pesquisa,
                        cpf_pesquisa=cpf_pesquisa,
                        endereco=endereco,
                        user=user,
                        origem_pedido=None,
                        finalidade="",
                        tipo_certidao_imovel_pessoa=1,
                        municipio_id=user.cartorio.municipio_id,
                        observacao_certidao=observacao_certidao,
                        numero_registro_livro_3=numero_registro_livro_3,
                        cartorio=user.cartorio.numero_cartorio,
                    )

                    descricao = (
                        f"CERTIDAO ELETRONICA (ONR) - ({valor}) - {protocolo_onr}"
                    )

                    if pedido:
                        # REGISTRAR CAIXA
                        pedido.enviar_pagamento_certidao_onr_caixa(
                            pk=pedido.id,
                            numero_pedido=pedido.numero_pedido,
                            valor_transacao=valor,
                            descricao=descricao,
                            db=db,
                        )

                        # Adicionando 4 horas
                        horario_atual = home_helpers.get_expediente(timezone.now())
                        horario_atual_final = horario_atual + timedelta(hours=4)

                        # COLABORADOR AVISADO CERTIDAO DA ONR
                        usuarios_avisar_certidao_onr = (
                            Usuario.get_usuarios_avisar_certidao_onr()
                        )

                        # REGISTRAR EVENTO NA AGENDA - Gravar o evento na agenda do dia
                        for usuario in usuarios_avisar_certidao_onr:
                            Event.criar_evento_no_calendario(
                                user=usuario,
                                auth_user=usuario,
                                numero=str(pedido.numero_pedido),
                                title=str(protocolo_onr),
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

                        # EXPORTAR PARA O FIREBIRD
                        pedido.exportar_pedido_certidao_para_fb(
                            descricao_observacao=descricao,
                            origem_id=6,
                            valor_transacao=valor,
                            db=db,
                        )

                        db.commit()

                        # PEDIDO NAO PODER SER FEITO
                        if cancelar_pedido:
                            print("Pedido não pode ser feito")

                            # GERAR O CANCELAMENTO e DEVOLUCAO
                            item = PedidoCertidao.objects.get(pk=pedido.id)
                            item.registrar_cancelar_devolucao(usuario)

                        mensagem_sucesso = f"Pedido de certidão ONR {protocolo_onr} criado com sucesso."
                        logger.info(mensagem_sucesso)
                        certidoes_emitir.append(
                            {"pedido": pedido, "mensagem": mensagem_sucesso},
                        )
                    else:
                        mensagem_erro = (
                            "Erro ao criar pedido de certidão ONR - Certidão Emitir."
                        )
                        logger.exception(mensagem_erro)
                        certidoes_emitir.append(
                            {"pedido": None, "mensagem": mensagem_erro},
                        )
                        continue

                except Exception as e:
                    db.rollback()
                    mensagem_erro = f"Erro ao exportar pedido de certidão ONR - Certidão Emitir: {e!s}"
                    logger.exception(mensagem_erro)
                    certidoes_emitir.append(
                        {"pedido": None, "mensagem": mensagem_erro},
                    )
                    raise

        except Exception as e:
            mensagem_erro = f"Erro ao processar certidão ONR: {e!s}"
            logger.exception(mensagem_erro)
            certidoes_emitir.append({"pedido": None, "mensagem": mensagem_erro})
            continue

    return certidoes_emitir


# ARQUIVOS ONR e-PROTOCOLO
def processar_eprotocolos_onr(
    protocolos_onr: list[dict[str, Any]],
    user: Any,
) -> list[dict[str, str | None]]:
    """
    Processa os protocolos ONR para criar registros no sistema FB e importar do Firebird.
    Retorna uma lista de dicionários, onde cada dicionário contém o número do protocolo e uma mensagem correspondente.
    """
    from apps.home import models

    protocolos_processados = []

    for protocolo_data in protocolos_onr:
        # Verificar se o protocolo já não existe no Prime
        if models.Livro01Protocolo.objects.filter(
            protocolo_onr=protocolo_data.get("protocolo"),
        ).exists():
            mensagem = f"Protocolo {protocolo_data.get('protocolo')} já importado anteriormente no Prime."
            logger.info(mensagem)
            protocolos_processados.append({"protocolo": None, "mensagem": mensagem})
            continue

        try:
            numero_protocolo_onr = protocolo_data.get("protocolo")
            if not numero_protocolo_onr:
                msg = "Número de Protocolo ONR é obrigatório."
                raise ValueError(msg)

            with transaction.atomic(), FbConnection() as db:
                # Verificar se o protocolo já foi importado anteriormente no Firebird
                protocolo_fb = firebird.get_protocolo_fb_por_numero_onr(
                    numero_protocolo_onr,
                    db,
                )
                if protocolo_fb:
                    mensagem = f"Protocolo ONR {numero_protocolo_onr} já importado anteriormente no Firebird."
                    logger.info(mensagem)
                    protocolos_processados.append(
                        {"protocolo": protocolo_fb["NROORDEM"], "mensagem": mensagem},
                    )
                    continue

                try:
                    numero_protocolo_fb = criar_protocolo_onr_no_fb(
                        protocolo_solicitacao=numero_protocolo_onr,
                        nome_solicitante=protocolo_data.get("nomesolic"),
                        cpf_cnpj_apresentante=protocolo_data.get("cpfcnpjapres"),
                        valor_protocolo_solicitacao=Decimal(
                            protocolo_data.get(
                                "valorservico",
                                "0",
                            ).replace(",", "."),
                        ),
                        cidadeapres=protocolo_data.get("cidadeapres"),
                        cidadeimovel=protocolo_data.get("cidadeimovel"),
                        endimovel=protocolo_data.get("endimovel"),
                        ufapres=protocolo_data.get("ufapres"),
                        user=user,
                        matriculaimovel=protocolo_data.get("matriculaimovel"),
                        livro=protocolo_data.get("livro"),
                        folha=protocolo_data.get("folha"),
                        email=protocolo_data.get("email"),
                        datalavratura=protocolo_data.get("datalavratura"),
                        telefone=protocolo_data.get("telefone"),
                        origem_pedido_id=None,
                        db=db,
                    )
                    logger.info(f"Protocolo criado no FB: {numero_protocolo_fb}")
                    db.commit()

                    mensagem_sucesso = (
                        f"Protocolo ONR {numero_protocolo_fb} criado com sucesso."
                    )
                    protocolos_processados.append(
                        {
                            "protocolo": numero_protocolo_fb,
                            "mensagem": mensagem_sucesso,
                        },
                    )

                except Exception as e:
                    db.rollback()
                    mensagem_erro = f"Erro ao criar protocolo ONR no Firebird: {e!s}"
                    logger.exception(mensagem_erro)
                    protocolos_processados.append(
                        {"protocolo": None, "mensagem": mensagem_erro},
                    )
                    continue

        except Exception as e:
            mensagem_erro = f"Erro ao processar protocolo ONR: {e!s}"
            logger.exception(mensagem_erro)
            protocolos_processados.append(
                {"protocolo": None, "mensagem": mensagem_erro},
            )
            continue

    # IMPORTAR OS DADOS PARA O POSTGRESQL
    for protocolo in protocolos_processados:
        numero_protocolo_onr = protocolo.get("protocolo")
        protocolo_importado = numero_protocolo_onr
        if numero_protocolo_onr:
            try:
                with transaction.atomic(), FbConnection() as db:
                    try:
                        protocolo_importado, _ = (
                            firebird.importar_protocolo_por_numero_fb(
                                numero_protocolo=numero_protocolo_onr,
                                tipo_importacao=None,
                                db=db,
                            )
                        )
                        protocolo_importado.origem_pedido = 6
                        protocolo_importado.save()
                        logger.info(
                            f"Protocolo {numero_protocolo_onr} importado com sucesso.",
                        )
                    except Exception as e:
                        mensagem_erro = f"Erro ao importar protocolo ONR {numero_protocolo_onr}: {e!s}"
                        logger.exception(mensagem_erro)
                        protocolos_processados.append(
                            {
                                "protocolo": protocolo_importado,
                                "mensagem": mensagem_erro,
                            },
                        )

            except Exception as e:
                mensagem_erro = (
                    f"Erro ao importar protocolo: {numero_protocolo_onr} - {e!s}"
                )
                logger.exception(mensagem_erro)
                protocolos_processados.append(
                    {"protocolo": protocolo_importado, "mensagem": mensagem_erro},
                )

    return protocolos_processados


# ARQUIVOS ONR INTIMACAO
def processar_xml_intimacao_onr(file_location, uploaded_file, user) -> None:
    from apps.home.models import Configuracao, PedidoParte
    from apps.home.utils.Importar_Intimacao_ORN_Firebird import (
        criar_protocolo_intimacao_onr,
        ler_xml_intimacao_onr,
    )

    arquivo_xml = file_location + "/" + str(uploaded_file)

    intimacoes_onr = ler_xml_intimacao_onr(arquivo_xml)

    # Pegando do configuracao - DADOS DO CARTORIO
    cidade = Configuracao.obter("cidade_atual_id", "")
    numero_estado = Configuracao.obter("estado_numero_atual_id", "")
    pastaintimacao = Configuracao.obter("pasta_intimacao_id", "")
    pasta_documentos_protocolo = Configuracao.obter("pasta_protocolo_id", "")
    intimacao_emolumento_id = Configuracao.obter("intimacao_emolumento_id", "")
    valor_itbi = Configuracao.obter("intimacao_valor_venal_id", "")
    valor_avaliacao = Configuracao.obter("intimacao_valor_avaliacao_id", "")
    chave_titulos = Configuracao.obter("intimacao_titulos_id", "")
    intimacao_numero_titulo_id = Configuracao.obter("intimacao_numero_titulo_id", "")
    numero_ri = Configuracao.obter("intimacao_numero_cartorio_id", "")
    intimacao_quantidade_id = Configuracao.obter("intimacao_quantidade_id", "")[0]
    intimacao_funcionario_id = Configuracao.obter("intimacao_funcionario_id", "")[0]
    intimacao_andamentos_id = Configuracao.obter(
        "intimacao_tipos_andamentos_id",
        "",
    )[0]
    observacao = Configuracao.obter("intimacao_observacao_protocolo_id", "")
    descricao_intimacao = Configuracao.obter("intimacao_descricao_id", "")
    intimacao_atos_id = Configuracao.obter("intimacao_atos_id", "")
    intimacao_titulos_id = Configuracao.obter("intimacao_titulos_id", "")
    intimacao_qtde_dias_uteis_id = Configuracao.obter(
        "intimacao_qtde_dias_uteis_id",
        "",
    )

    for intimacao_onr in intimacoes_onr:
        print("Intimacao ONR: ", intimacao_onr)
        try:
            with transaction.atomic(), FbConnection() as db:
                try:
                    protocolo = intimacao_onr["protocolo"]
                    nrocontrato = intimacao_onr["nrocontrato"]
                    dv_contrato = intimacao_onr["dv_contrato"]
                    dtremessa = intimacao_onr["dtremessa"]
                    idri = intimacao_onr["idri"]
                    agencia = intimacao_onr["agencia"]
                    nome_agencia = intimacao_onr["nome_agencia"]
                    url_requerimento = intimacao_onr["url_requerimento"]
                    solicitante = intimacao_onr["solicitante"]
                    credor = intimacao_onr["credor"]
                    participantes = intimacao_onr["participantes"]
                    imoveis = intimacao_onr["imoveis"]
                    enderecos_participantes = intimacao_onr["enderecos_participantes"]

                    nomesolicitante = solicitante["nomesolicitante"]
                    cpfcnpjsolic = solicitante["cpfcnpjsolic"]
                    telsolic = solicitante["telsolic"]
                    emailsolic = solicitante["emailsolic"]
                    qualificacao = credor["qualificacao"]
                    cpfcnpjapres = credor["cpfcnpjapres"]

                    lista_dos_participantes = [p["participacao"] for p in participantes]
                    lista_dos_cpfcnpj_participantes = [
                        p["cpfcnpjpart"] for p in participantes
                    ]

                    matimovel = imoveis[0]["matimovel"] if imoveis else ""
                    endereco_imovel = imoveis[0]["endereco_imovel"] if imoveis else ""
                    endereco = (
                        enderecos_participantes[0] if enderecos_participantes else ""
                    )

                    # Verifica se já não há protocolos para esta intimacao
                    comando = f"SELECT COUNT(NROORDEM) FROM PROTOCOLOS WHERE NUMEROPEDIDOCRI = {protocolo!r}"
                    quantidade = db.execute_query(comando)[0]["COUNT"]

                    # Nao tendo sido importado antes - processa
                    if quantidade > 0:
                        logger.info(
                            f"Protocolo {protocolo} já importado anteriormente.",
                        )
                        continue

                    # Gravando o XML na base de dados
                    numero_protocolo, pedido_id = criar_protocolo_intimacao_onr(
                        protocolosistema=protocolo,
                        nrcontrato=nrocontrato,
                        dv_contrato=dv_contrato,
                        dtremessa=dtremessa,
                        idri=idri,
                        agencia=agencia,
                        nome_agencia=nome_agencia,
                        url_requerimento=url_requerimento,
                        nome_solicitante=nomesolicitante,
                        cpf_cnpj_solicitante=cpfcnpjsolic,
                        tel_solicitante=telsolic,
                        email_solicitante=emailsolic,
                        qualificacao=qualificacao,
                        cpfcnpjapres=cpfcnpjapres,
                        participacao=lista_dos_participantes,
                        cpfcnpjpart=lista_dos_cpfcnpj_participantes,
                        matimovel=matimovel,
                        endereco_imovel=endereco_imovel,
                        endereco=endereco,
                        observacao=observacao,
                        cidade=cidade,
                        numero_estado=numero_estado,
                        titulo=chave_titulos,
                        valor_itbi=valor_itbi,
                        valor_avaliacao=valor_avaliacao,
                        intimacao_emolumento_id=intimacao_emolumento_id,
                        intimacao_quantidade_id=intimacao_quantidade_id,
                        numero_ri=numero_ri,
                        intimacao_numero_titulo_id=intimacao_numero_titulo_id,
                        intimacao_funcionario_id=intimacao_funcionario_id,
                        intimacao_andamentos_id=intimacao_andamentos_id,
                        pastaintimacao=pastaintimacao,
                        descricao_intimacao=descricao_intimacao,
                        intimacao_atos_id=intimacao_atos_id,
                        intimacao_titulos_id=intimacao_titulos_id,
                        qtde_dias_uteis=intimacao_qtde_dias_uteis_id,
                        pasta_documentos_protocolo=pasta_documentos_protocolo,
                        user=user,
                        origem_pedido_id=None,
                        db=db,
                    )

                    protocolo, _ = firebird.importar_protocolo_por_numero_fb(
                        numero_protocolo,
                        tipo_importacao=None,
                        db=db,
                    )

                    # # VINCULAR AS PARTES AO PROTOCOLO
                    # pedido_id_protocolo = Livro01Protocolo.objects.filter(numero_protocolo=numero_protocolo).values_list(
                    #     "pedido_id",
                    #     flat=True,
                    # )[0]

                    # print("gravar envolvidos")
                    for participacao_nome, participacao_cpf_cnpj in zip(
                        lista_dos_participantes,
                        lista_dos_cpfcnpj_participantes,
                        strict=False,
                    ):
                        PedidoParte.criar(
                            protocolo.pedido_id,
                            participacao_nome,
                            participacao_cpf_cnpj,
                            "a",
                        )

                    # EXISTE PROTOCOLO
                    # Lista.append(numero_protocolo)

                    db.commit()
                except Exception:
                    db.rollback()
                    raise
        except Exception:
            logger.exception(f"Erro ao processar intimação ONR: {intimacao_onr}")
            continue

    return len(intimacoes_onr)

    print("Arquivo enviando.......", arquivo_xml)
    return None
