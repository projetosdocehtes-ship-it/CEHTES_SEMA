import logging
import re
import xml.etree.ElementTree as et

from django.utils import timezone

from apps.home.helpers import get_apenas_numeros, get_data_util_em_x_dias
from apps.home.services import firebird
from core.utils.firebird_utils import FbConnection

# Configurar logging

logger = logging.getLogger(__name__)


# Iniciar os arquivos
def apenas_numeros(numero):
    return re.sub("[^0-9]", "", numero)


# Enviar o arquivo a ser gerado
def get_raiz_xml_intimacao(caminho_arquivo):
    """
    Lê um arquivo XML e retorna o elemento raiz.

    Args:
    ----
        caminho_arquivo (str): Caminho completo para o arquivo XML que deve ser lido.

    Returns:
    -------
        Element: O elemento raiz do arquivo XML.
        None: Se houver um erro ao ler o arquivo ou se o arquivo não for um XML válido.

    """
    try:
        arquivo_xml = et.parse(caminho_arquivo)
        return arquivo_xml.getroot()
    except Exception as e:
        logger.error(
            f"ERRO ao ler o arquivo {caminho_arquivo}. Detalhes: {e}",
            exc_info=True,
        )
        return None


def get_do_imovel_pela_matricula(matimovel):
    tipo_imovel, nro_imovel, ato_imovel = "", "", ""

    # print("Separando os dados do imóvel: ", matimovel)
    if str(matimovel).split("Matrícula")[0]:
        tipo_imovel = "M"

        ato_imovel = str(matimovel).split("Matrícula")[0]
        nro_imovel = str(matimovel).split("Matrícula")[1]

        ato_imovel = str(ato_imovel).split("nº")[1]
        ato_imovel = str(ato_imovel).split(",")[0]
        ato_imovel = get_apenas_numeros(str(ato_imovel).strip())

        nro_imovel = str(nro_imovel).split("nº")[1]
        nro_imovel = get_apenas_numeros(str(nro_imovel).strip())

    return tipo_imovel, nro_imovel, ato_imovel


# Gravando o XML na base de dados
def criar_protocolo_intimacao_onr(
    protocolosistema,
    nrcontrato,
    dv_contrato,
    dtremessa,
    idri,
    agencia,
    nome_agencia,
    url_requerimento,
    nome_solicitante,
    cpf_cnpj_solicitante,
    tel_solicitante,
    email_solicitante,
    qualificacao,
    cpfcnpjapres,
    participacao,
    cpfcnpjpart,
    matimovel,
    endereco_imovel,
    endereco,
    observacao,
    cidade,
    numero_estado,
    titulo,
    valor_itbi,
    valor_avaliacao,
    intimacao_emolumento_id,
    intimacao_quantidade_id,
    numero_ri,
    intimacao_numero_titulo_id,
    intimacao_funcionario_id,
    intimacao_andamentos_id,
    pastaintimacao,
    descricao_intimacao,
    intimacao_atos_id,
    intimacao_titulos_id,
    qtde_dias_uteis,
    pasta_documentos_protocolo,
    user,
    origem_pedido_id,
    db: FbConnection,
):
    logger.info(f"Criando o protocolo de intimacao {protocolosistema}")
    # Atualizar a data prevista com base em dias uteis
    max_dias_uteis = 20

    var_participacao = participacao
    var_qualificacao = str(qualificacao).split("-")[0]
    var_cidade = cidade
    var_endereco_imovel = str(endereco_imovel)
    var_observacao = str(observacao) + ": " + str(protocolosistema)
    var_cpfcnpjapres = str(cpfcnpjpart)
    documento_apresentante = 1
    andamento_inicial_id = 12

    data_entrada = timezone.now().date()
    data_prevista = get_data_util_em_x_dias(data_entrada, int(max_dias_uteis))
    data_validade = get_data_util_em_x_dias(data_entrada, int(max_dias_uteis) + 1)
    telefone = "'" + str(tel_solicitante).replace("None", "") + "'"
    email = str(email_solicitante).replace("None", "")

    # PARAMETROS LIVRO DE NOTAS PARA O SISTEMA
    livro = "''"
    folha = "''"
    data_escritura = "null"

    print("iniciando os dados do imóvel")
    (
        var_tipo_registro,
        var_nro_imovel,
        var_ato_imovel,
    ) = get_do_imovel_pela_matricula(matimovel)

    var_ato_imovel = "R." + str(int(str(var_ato_imovel)))

    # RETIRAR CARACTERES ESPECIAIS
    var_qualificacao = str(var_qualificacao).replace("'", " ").replace("’", " ")
    nome_solicitante = str(nome_solicitante).replace("'", " ").replace("’", " ")
    var_participacao = str(var_participacao[0]).replace("'", " ").replace("’", " ")

    # Obter o proximo numero do pedido
    pedido_id = db.sequence("PEDIDOS_SEQ").proximo

    # GRAVANDO O PEDIDO - PROTOCOLO
    pedido_fb = firebird.gravar_pedido_protocolo_fb(
        pedido_id=pedido_id,
        numero_pedido=pedido_id,
        data_entrada=str(data_entrada.strftime("%d.%m.%Y")),
        data_prevista=str(data_prevista.strftime("%d.%m.%Y")),
        data_validade=str(data_validade.strftime("%d.%m.%Y")),
        tipo_servico="R",
        nomeadquirente=var_qualificacao,
        nomeapresentante=nome_solicitante,
        nometransmitente=var_participacao[0],
        municipio=var_cidade,
        uf=str(numero_estado),
        numero_talao=pedido_id,
        observacao=var_observacao,
        endereco=var_endereco_imovel,
        tipo_documento_apresentante=documento_apresentante,
        documento_apresentante=var_cpfcnpjapres[0],
        funcionario_id=user.id,
        fone=telefone,
        email=email,
        nrotalao=pedido_id,
        db=db,
    )

    # GRAVADO PEDIDO NO FIREBIRD
    if pedido_fb:
        # GRAVANDO O ITEM DO PEDIDO - PROTOCOLO
        pedido_item_fb = firebird.gravar_pedido_item_protocolo_fb(
            pedido_id=pedido_fb["CHAVE_PEDIDOS"],
            valor_itbi=0,
            valor_avaliacao=0,
            tipo_imovel=var_tipo_registro,
            numero_imovel=var_nro_imovel,
            emolumento_id=firebird.get_tipo_emolumento_prenotacao(),
            quantidade=1,
            numero_ri=numero_ri,
            numero_titulo=1,
            numero_ato=var_ato_imovel,
            colaborador_id=user.id,
            ato_id=firebird.get_ato_praticavel_prenotacao(),
            titulo_id=firebird.get_default_titulo_prenotacao(),
            tipo_tributacao_id=0,
            livro=livro,
            folha=folha,
            data_escritura=data_escritura,
            codigo_tabela="0",
            valor_emolumento="0",
            valor_fundo_estado="0",
            valor_tfj="0",
            valor_issqn="0",
            db=db,
        )
        # print(pedido_fb, pedido_item_fb, codigo_tabela)

    # GRAVAR PROTOCOLO
    print("Gerar Novo Protocolo")
    numero_protocolo, protocolo_id = firebird.gravar_protocolo_firebird(
        pedido_id=pedido_fb["CHAVE_PEDIDOS"],
        titulo_id=0,
        observacao=observacao,
        origem_pedido_id=origem_pedido_id,
        numero_pedido_cri=protocolosistema,
        db=db,
    )

    # GRAVAR ANDAMENTO NO FIREBIRD
    firebird.get_sequence_firebird("ANDAMENTOS_SEQ", db)["GEN_ID"]
    firebird.gravar_protocolo_andamento_firebird(
        protocolo_id=protocolo_id,
        funcionario_id=user.id,
        servico_id=andamento_inicial_id,
        andamento_id=0,
        db=db,
    )

    # GRAVANDO NO FIREBIRD - CAIXA
    firebird.gravar_caixa_do_protocolo_no_firebird(
        pedido_fb["CHAVE_PEDIDOS"],
        0,
        user.id,
        observacao,
        db,
    )

    # GRAVANDO NO FIREBIRD - SELO
    print("Selar:", pedido_fb["CHAVE_PEDIDOS"], pedido_item_fb)
    firebird.selar_protocolo_no_firebird(pedido_fb["CHAVE_PEDIDOS"], pedido_item_fb, db)

    # TRABALHANDO BAIXAR ARQUIVO
    # try:
    #     # print("baixando o arquivo do site.")
    #     pasta_documentos_protocolo = Configuracao.get_lista("pasta_protocolo_id", "")[0]
    #     numero_protocolo = str(nro_ordem).split(".")[0]
    #     numero_protocolo = str(numero_protocolo).zfill(6)
    #     diretorio = pasta_documentos_protocolo + numero_protocolo

    #     # criar o diretorio caso nao exista
    #     criarDirSeNaoExiste(diretorio)
    #     garantir_diretorio_existe(diretorio)
    #     arquivo = diretorio + "/" + numero_protocolo + ".pdf"
    #     baixar_url(url_requerimento, arquivo)

    #     print(" baixado ")
    # except Exception as e:
    #     logger.info(f"ERRO CRIAR DIRETORIO INTIMACAO. Erro: ")
    #     # print("arquivo nao baixado: ", url_requerimento)

    print(" ")

    # retorna o numero de protocolo salvo no bd
    return numero_protocolo, pedido_id


# Gerando o XML
def ler_xml_intimacao_onr(arquivo) -> list:
    # ORIGEM DO PEDIDO - ONR INTIMACAO

    lista_resultados = []

    try:
        tree = et.parse(arquivo)
        root = tree.getroot()
    except Exception as e:
        logger.exception("Erro ao abrir ou processar o arquivo: ", e)
        return []

    # DADOS DA INTIMACAO
    for protocolo_solicitacao in root.findall("INTIMACAO"):
        dados_intimacao = {
            "protocolo": protocolo_solicitacao.findtext("PROTOCOLOSISTEMA", ""),
            "nrocontrato": protocolo_solicitacao.findtext("NRCONTRATO", ""),
            "dv_contrato": protocolo_solicitacao.findtext("DV_CONTRATO", ""),
            "dtremessa": protocolo_solicitacao.findtext("DTREMESSA", ""),
            "idri": protocolo_solicitacao.findtext("IDRI", ""),
            "solicitante": {
                "nomesolicitante": protocolo_solicitacao.find("SOLICITANTE").findtext(
                    "NOMESOLIC",
                    "",
                ),
                "cpfcnpjsolic": protocolo_solicitacao.find("SOLICITANTE").findtext(
                    "CPFCNPJSOLIC",
                    "",
                ),
                "telsolic": protocolo_solicitacao.find("SOLICITANTE").findtext(
                    "TELSOLIC",
                    "",
                ),
                "emailsolic": protocolo_solicitacao.find("SOLICITANTE").findtext(
                    "EMAILSOLIC",
                    "",
                ),
            },
            "credor": {
                "qualificacao": protocolo_solicitacao.find("CREDORAPRES").findtext(
                    "QUALIFICACAO",
                    "",
                ),
                "cpfcnpjapres": protocolo_solicitacao.find("CREDORAPRES").findtext(
                    "CPFCNPJAPRES",
                    "",
                ),
            },
            "participantes": [],
            "imoveis": [],
            "enderecos_participantes": [],
            "agencia": protocolo_solicitacao.findtext("AGENCIA", ""),
            "nome_agencia": protocolo_solicitacao.findtext("NOME_AGENCIA", ""),
            "url_requerimento": protocolo_solicitacao.findtext("URL_REQUERIMENTO", ""),
        }

        # TODOS OS PARTICIPANTES
        for lista_participantes in protocolo_solicitacao.findall("PARTICIPANTES"):
            for lista_participantes2 in lista_participantes.findall("PART"):
                dados_participante = {
                    "participacao": lista_participantes2.findtext("PARTICIPACAO", ""),
                    "cpfcnpjpart": lista_participantes2.findtext("CPFCNPJPART", ""),
                }
                dados_intimacao["participantes"].append(dados_participante)

        # DADOS DO IMOVEL
        for lista_imovel in protocolo_solicitacao.findall("IMOVEIS"):
            for lista_imovel2 in lista_imovel.findall("IMOVEL"):
                dados_imovel = {
                    "matimovel": lista_imovel2.findtext("matimovel", ""),
                    "endereco_imovel": lista_imovel2.findtext("ENDERECO_IMOVEL", ""),
                }
                dados_intimacao["imoveis"].append(dados_imovel)

        # DADOS DO ENDERECO DO PARTICIPANTE
        for lista_endereco_participantes in protocolo_solicitacao.findall(
            "ENDINTIMACAO",
        ):
            endereco = lista_endereco_participantes.findtext("ENDERECO", "")
            dados_intimacao["enderecos_participantes"].append(endereco)

        lista_resultados.append(dados_intimacao)

    return lista_resultados
