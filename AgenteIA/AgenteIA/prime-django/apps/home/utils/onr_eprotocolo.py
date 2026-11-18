import xml.etree.ElementTree as ET
from decimal import Decimal
from venv import logger

from django.utils import timezone

from apps.home.helpers import get_data_util_em_x_dias
from apps.home.services import firebird


def ler_xml_eprotocolo_onr(file) -> list:
    """Ler arquivo XML e-protocolo da ONR."""
    print("ler_arquivo_xml_e_protocolo")

    try:
        tree = ET.parse(file)
        root = tree.getroot()
        print("Percorrer ARQUIVO")
    except Exception as e:
        logger.exception("Erro ao abrir ou processar o arquivo: ", e)
        return None

    protocolos = []

    for protocolo_solicitacao in root.findall("CONTRATO"):
        protocolo_data = {
            "protocolo": protocolo_solicitacao.findtext("PROTOCOLO", ""),
            "livro": protocolo_solicitacao.findtext("LIVRO", ""),
            "folha": protocolo_solicitacao.findtext("FOLHA", ""),
            "datalavratura": protocolo_solicitacao.findtext("DATALAVRATURA", ""),
            "email": protocolo_solicitacao.findtext("EMAILINST", ""),
            "nomesolic": protocolo_solicitacao.findtext("NOMESOLIC", ""),
            "telefone": protocolo_solicitacao.findtext("TELSOLIC", ""),
            "cpfcnpjapres": protocolo_solicitacao.findtext("CPFCNPJAPRES", ""),
            "cidadeapres": protocolo_solicitacao.findtext("CIDADEAPRES", ""),
            "ufapres": protocolo_solicitacao.findtext("UFAPRES", ""),
            "matriculaimovel": protocolo_solicitacao.findtext("MATRICULAIMOVEL", ""),
            "endimovel": protocolo_solicitacao.findtext("ENDIMOVEL", ""),
            "nrimovel": protocolo_solicitacao.findtext("NRIMOVEL", ""),
            "compimovel": protocolo_solicitacao.findtext("COMPIMOVEL", ""),
            "bairroimovel": protocolo_solicitacao.findtext("BAIRROIMOVEL", ""),
            "ufimovel": protocolo_solicitacao.findtext("UFIMOVEL", ""),
            "cidadeimovel": protocolo_solicitacao.findtext("CIDADEIMOVEL", ""),
            "valorservico": protocolo_solicitacao.findtext("VALORSERVICO", ""),
        }

        # Adquirentes
        adquirentes = []
        for adquirente in protocolo_solicitacao.findall("ADQUIRENTE"):
            adquirentes.append(
                {
                    "nome": adquirente.findtext("NOME", ""),
                    "cpf_cnpj": adquirente.findtext("CPFCNPJ", ""),
                },
            )
        protocolo_data["adquirentes"] = adquirentes

        # Transmitentes
        transmitentes = []
        for transmitente in protocolo_solicitacao.findall("TRANSMITENTE"):
            transmitentes.append(
                {
                    "nome": transmitente.findtext("NOME", ""),
                    "cpf_cnpj": transmitente.findtext("CPFCNPJ", ""),
                },
            )
        protocolo_data["transmitentes"] = transmitentes

        protocolos.append(protocolo_data)

    return protocolos

    #     # Verificar se o e-Protocolo ja existe
    #     comando = " SELECT COUNT(NROORDEM) FROM PROTOCOLOS WHERE NUMEROPEDIDOCRI = '" + str(protocolo) + "'"
    #     numero_protocolo = firebird.get_comando_firebird(comando, db)[0]["COUNT"]

    #     # VERIFICAR SE O PROTOCOLO JA EXISTE
    #     if numero_protocolo == 0:
    #         print("Gravando Protocolo: ", protocolo)

    #         # Gravar Protocolo
    #         numero_protocolo = criar_protocolo_onr_no_fb(
    #             protocolo,
    #             nomesolic,
    #             cpfcnpjapres,
    #             valorservico,
    #             cidadeapres,
    #             cidadeimovel,
    #             endimovel,
    #             ufapres,
    #             user,
    #             matriculaimovel,
    #             livro,
    #             folha,
    #             email,
    #             datalavratura,
    #             telefone,
    #             origem_pedido_id,
    #             db,
    #         )

    #         # EXISTE PROTOCOLO
    #         Lista.append(numero_protocolo)

    # db.commit()
    # db.close()

    # # IMPORTAR OS DADOS PARA O POSTGRESQL
    # for numero_protocolo in Lista:
    #     print("Gerando: ", numero_protocolo)
    #     firebird.importar_protocolo_por_numero_fb(numero_protocolo, db=db)

    # return Lista


# Gerar a lista para salvar o Pedido de certidao
def criar_protocolo_onr_no_fb(
    protocolo_solicitacao,
    nome_solicitante,
    cpf_cnpj_apresentante,
    valor_protocolo_solicitacao,
    cidadeapres,
    cidadeimovel,
    endimovel,
    ufapres,
    user,
    matriculaimovel,
    livro,
    folha,
    email,
    datalavratura,
    telefone,
    origem_pedido_id,
    db,
) -> int:
    from apps.cartorios.models import Cartorio

    # codigo_tabela = codigo_tabela or 0
    cartorio = Cartorio.objects.select_related("municipio").first()
    municipio = cartorio.municipio.nome if cartorio and cartorio.municipio else ""
    uf = cartorio.codigo_uf
    numero_cartorio = cartorio.numero_cartorio
    andamento_inicial_id = 12

    # Obter o proximo numero do pedido
    pedido_id = db.sequence("PEDIDOS_SEQ").proximo

    # Atualizar a data prevista com base em dias uteis
    max_dias_uteis = 20
    data_entrada = timezone.now()
    data_prevista = get_data_util_em_x_dias(data_entrada, int(max_dias_uteis))
    data_validade = get_data_util_em_x_dias(data_entrada, int(max_dias_uteis) + 1)
    documento_apresentante = 1
    observacao = "PROTOCOLO ELETRONICO (ONR) - " + str(protocolo_solicitacao)

    # FORMATAR VALOR
    valor_protocolo_solicitacao = (
        str(valor_protocolo_solicitacao).replace(".", "").replace(",", ".")
    )

    # FORMATAR MATRICULA
    matriculaimovel = "'" + str(matriculaimovel).replace("None", "") + "'"
    livro = "'" + str(livro).replace("None", "") + "'"
    folha = "'" + str(folha).replace("None", "") + "'"
    email = "'" + str(email).replace("None", "") + "'"
    telefone = "'" + str(telefone).replace("None", "") + "'"
    datalavratura = (
        "'" + str(datalavratura).replace("/", ".") + "'" if datalavratura else None
    )

    # TIPO DE TRIBUTACAO
    tipo_tributacao_id = 0 if Decimal(valor_protocolo_solicitacao) > 0 else 1

    try:
        # GRAVANDO O PEDIDO - PROTOCOLO
        pedido_fb = firebird.gravar_pedido_protocolo_fb(
            pedido_id=pedido_id,
            numero_pedido=pedido_id,
            data_entrada=str(data_entrada.strftime("%d.%m.%Y")),
            data_prevista=str(data_prevista.strftime("%d.%m.%Y")),
            data_validade=str(data_validade.strftime("%d.%m.%Y")),
            tipo_servico="R",
            nomeadquirente=nome_solicitante,
            nomeapresentante=nome_solicitante,
            nometransmitente=nome_solicitante,
            municipio=municipio,
            uf=uf,
            numero_talao=pedido_id,
            observacao=observacao,
            endereco=endimovel,
            tipo_documento_apresentante=documento_apresentante,
            documento_apresentante=cpf_cnpj_apresentante,
            funcionario_id=user.id,
            fone=telefone,
            email=email,
            nrotalao=pedido_id,
            db=db,
        )

        # GRAVADO PEDIDO NO FIREBIRD
        if pedido_fb:
            # GRAVANDO O ITEM DO PEDIDO - PROTOCOLO
            tipo_emolumento = firebird.get_tipo_emolumento_prenotacao_obj()
            codigo_tabela = tipo_emolumento.codigo_tabela
            pedido_item_fb = firebird.gravar_pedido_item_protocolo_fb(
                pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                valor_itbi=valor_protocolo_solicitacao,
                valor_avaliacao=valor_protocolo_solicitacao,
                tipo_imovel="M",
                numero_imovel=matriculaimovel,
                emolumento_id=firebird.get_tipo_emolumento_prenotacao(),
                quantidade=1,
                numero_ri=numero_cartorio,
                numero_titulo=1,
                numero_ato="",
                colaborador_id=user.id,
                ato_id=firebird.get_ato_praticavel_prenotacao(),
                titulo_id=firebird.get_default_titulo_prenotacao(),
                tipo_tributacao_id=tipo_tributacao_id,
                livro=livro,
                folha=folha,
                data_escritura=datalavratura,
                codigo_tabela=codigo_tabela,
                valor_emolumento="0",
                valor_fundo_estado="0",
                valor_tfj="0",
                valor_issqn="0",
                db=db,
            )
            # print(pedido_fb, pedido_item_fb, codigo_tabela)

            # GRAVAR PROTOCOLO
            print("Gerar Novo Protocolo")
            try:
                nro_ordem, protocolo_id = firebird.gravar_protocolo_firebird(
                    pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                    titulo_id=0,
                    observacao=observacao,
                    origem_pedido_id=origem_pedido_id,
                    numero_pedido_cri=protocolo_solicitacao,
                    db=db,
                )
            except Exception as e:
                logger.exception("Erro ao gravar protocolo no FB: ", e)

            # GRAVAR ANDAMENTO NO FIREBIRD
            try:
                firebird.gravar_protocolo_andamento_firebird(
                    protocolo_id=protocolo_id,
                    funcionario_id=user.id,
                    servico_id=andamento_inicial_id,
                    andamento_id=0,
                    db=db,
                )
            except Exception as e:
                logger.exception("Erro ao gravar andamento do protocolo no FB: ", e)

            try:
                # GRAVANDO NO FIREBIRD - CAIXA
                firebird.gravar_caixa_do_protocolo_no_firebird(
                    pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                    valor=valor_protocolo_solicitacao,
                    funcionarios_id=user.id,
                    descricao=observacao,
                    db=db,
                )
            except Exception as e:
                logger.exception("Erro ao gravar caixa do protocolo no FB: ", e)

            try:
                # GRAVANDO NO FIREBIRD - SELO
                firebird.selar_protocolo_no_firebird(
                    pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                    pedidos_id_itens=pedido_item_fb,
                    db=db,
                )
                # print(nro_ordem, protocolo_id)
            except Exception as e:
                logger.exception("Erro ao gravar selo do protocolo no FB: ", e)
        else:
            msg = "O pedido não foi gravado no Firebird"
            raise Exception(msg)

    except Exception:
        mensagem = "ERRO ao tentar exportar o pedido"
        logger.exception(mensagem)
        raise

    return nro_ordem


def get_protocolo_fb_pelo_numero_onr(numero_protocolo_onr):
    """Obter protocolo do Firebird pelo numero do protocolo da ONR."""
    try:
        protocolo = firebird.get_protocolo_fb_por_numero_onr(numero_protocolo_onr)
    except Exception as e:
        logger.exception("Erro ao obter protocolo do FB pelo numero ONR: ", e)
        return None

    return protocolo
