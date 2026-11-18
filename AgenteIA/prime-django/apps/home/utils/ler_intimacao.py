import logging
import re
import xml.etree.ElementTree as Et

from django.apps import apps

from apps.home.helpers import garantir_diretorio_existe, get_apenas_numeros
from apps.home.models import (
    Event,
    Livro01Andamento,
    Livro01Protocolo,
    Pedido,
    PedidoItem,
    PedidoParte,
    SeloEletronico,
)

# Configurar logging
from apps.home.utils.baixar_arquivo import baixar_url

logger = logging.getLogger(__name__)
# Iniciar os arquivos
arquivo, raiz = "", ""


def apenas_numeros(numero):
    return re.sub("[^0-9]", "", numero)


# Enviar o arquivo a ser gerado
def get_raiz_xml(caminho_arquivo):
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
        arquivo_xml = Et.parse(caminho_arquivo)
        return arquivo_xml.getroot()
    except Exception as e:
        logger.exception(f"ERRO ao ler o arquivo {caminho_arquivo}. Detalhes: {e}")
        return None


# Limpar lista
def limpar_lista() -> None:
    global \
        protocolosistema, \
        nrcontrato, \
        dv_contrato, \
        dtremessa, \
        idri, \
        agencia, \
        nome_agencia, \
        url_requerimento, \
        nome_solicitante, \
        cpf_cnpj_solicitante, \
        tel_solicitante, \
        email_solicitante, \
        qualificacao, \
        cpfcnpjapres, \
        participacao, \
        cpfcnpjpart, \
        matimovel, \
        endereco_imovel, \
        endereco

    (
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
    ) = ([], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [])


def get_do_imovel_pela_matricula(numero_matricula):
    tipo_imovel, nro_imovel, ato_imovel = "", "", ""

    # print("Separando os dados do imóvel: ", MATIMOVEL)
    if str(numero_matricula).split("Matrícula")[0]:
        ato_imovel = str(numero_matricula).split("Matrícula")[0]
        nro_imovel = str(numero_matricula).split("Matrícula")[1]

        ato_imovel = str(ato_imovel).split("nº")[1]
        ato_imovel = str(ato_imovel).split(",")[0]
        ato_imovel = get_apenas_numeros(str(ato_imovel).strip())

        nro_imovel = str(nro_imovel).split("nº")[1]
        nro_imovel = get_apenas_numeros(str(nro_imovel).strip())

    return tipo_imovel, nro_imovel, ato_imovel


# Gravando o XML na base de dados
def gravar_xml(
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
    titulo_id,
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
):
    var_cidade = cidade
    var_endereco_imovel = str(endereco_imovel[0])
    var_observacao = str(observacao) + ": " + str(protocolosistema[0])
    var_cpfcnpjapres = str(cpfcnpjpart[0])

    pedido = Pedido.objects.create(
        numero="1",
        tipo_servico="R",
        municipio=str(var_cidade),
        uf=str(numero_estado),
        numero_talao="1",
        observacao=str(var_observacao),
        endereco=str(var_endereco_imovel),
        tipo_documento_apresentante="1",
        documento_apresentante=str(var_cpfcnpjapres),
    )

    # gravar partes envolvidas
    # print("gravar envolvidos")
    for participacao_nome, participacao_cpf_cnpj in zip(
        participacao,
        cpfcnpjpart,
        strict=False,
    ):
        PedidoParte.criar(pedido.pk, participacao_nome, participacao_cpf_cnpj, "a")

    # gravar protocolo
    protocolo_novo = Livro01Protocolo.criar_protocolo(
        pedido_id=pedido.pk,
        titulo_id=titulo_id,
        observaco=var_observacao,
        protocolo_sistema=str(protocolosistema[0]),
    )
    print("fase de protocolo finalizado")

    # obter os dados do imóvel
    # print("iniciando os dados do imóvel")
    (
        var_tipo_registro,
        var_nro_imovel,
        var_ato_imovel,
    ) = get_do_imovel_pela_matricula(matimovel)
    var_ato_imovel = "r." + str(int(str(var_ato_imovel)))
    # print("gravou os dados do imóvel")

    # gravar item pedido
    # print("iniciando os dados do item pedido")
    Colaborador = apps.get_model("home", "Colaborador")
    colaborador = Colaborador.objects.get(pk=intimacao_funcionario_id)
    pedido_item_id, data = PedidoItem.criar_pedido_item(
        pedido_id=pedido.pk,
        valor_itbi=valor_itbi,
        valor_avaliacao=valor_avaliacao,
        tipo_registro=var_tipo_registro,
        numero_registro=var_nro_imovel,
        emolumento_id=intimacao_emolumento_id,
        quantidade=intimacao_quantidade_id,
        numero_ri=numero_ri,
        numero_titulo=intimacao_numero_titulo_id,
        numero_ato=var_ato_imovel,
        colaborador=colaborador,
        ato_id=intimacao_atos_id,
        titulo_id=intimacao_titulos_id,
    )
    print("gravou os os dados do item pedido")

    # gravar o selo
    SeloEletronico.alocar_selo_para_pedido_ou_certidao(
        pedido=pedido,
        pedido_item_id=pedido_item_id,
        pedido_certidao_id="",
        pedido_certidao_item="",
        opcao="p",
    )
    print("gravou os selos tem que verificar ainda - trabalhando")

    # gravar andamento
    Livro01Andamento.criar_andamento_protocolo(
        protocolo_id=protocolo_novo.pk,
        colaborador_id=intimacao_funcionario_id,
        tipo_andamento_id=intimacao_andamentos_id,
        colaborador_encaminhado_id=None,
    )
    print("gravou os andamentos")

    # descricao para o caixa
    descricao = (
        descricao_intimacao + ": " + str(protocolo_novo.numero_protocolo).split(".")[0]
    )
    from apps.home.models import Financeiro

    Financeiro.criar_financeiro(
        pedido_id=pedido.pk,
        valor="0",
        colaborador_id=intimacao_funcionario_id,
        descricao=descricao,
    )
    print("gravou o caixa")

    try:
        # print("baixando o arquivo do site.")
        # pasta_documentos_protocolo = Configuracao.get_lista('pasta_protocolo_id', '')[0]

        numero_protocolo = str(protocolo_novo.numero_protocolo).split(".")[0]
        numero_protocolo = str(numero_protocolo).zfill(6)
        diretorio = pasta_documentos_protocolo + "/" + numero_protocolo

        # print(pasta_documentos_protocolo)

        # criar o diretorio caso nao exista
        garantir_diretorio_existe(diretorio)
        arquivo = diretorio + "/" + numero_protocolo + ".pdf"

        # print(url_requerimento[0], arquivo)
        # import time

        baixar_url(url_requerimento[0], arquivo)

        print(" baixado ")
    except Exception:
        logger.exception("ERRO")
        # print("arquivo nao baixado: ", url_requerimento)

    print(" ")

    # retorna o numero de protocolo salvo no bd
    return numero_protocolo


# Gerando o XML
def gerar_leitura_xml(user) -> None:
    from apps.home.models import Configuracao

    # Pegando do configuracao - DADOS DO CARTORIO
    cidade = Configuracao.obter("cidade_atual_id")
    numero_estado = Configuracao.obter("estado_numero_atual_id")
    pastaintimacao = Configuracao.obter("pasta_intimacao_id")
    pasta_documentos_protocolo = Configuracao.obter("pasta_protocolo_id")
    intimacao_emolumento_id = Configuracao.obter("intimacao_emolumento_id")
    # intimacao_valor_id = Configuracao.obter("intimacao_valor_id")
    valor_itbi = Configuracao.obter("intimacao_valor_venal_id")
    valor_avaliacao = Configuracao.obter("intimacao_valor_avaliacao_id")
    chave_titulos = Configuracao.obter("intimacao_titulos_id")
    intimacao_numero_titulo_id = Configuracao.obter("intimacao_numero_titulo_id")
    numero_ri = Configuracao.obter("intimacao_numero_cartorio_id")
    intimacao_quantidade_id = Configuracao.obter("intimacao_quantidade_id")[0]
    intimacao_funcionario_id = Configuracao.obter("intimacao_funcionario_id")[0]
    intimacao_andamentos_id = Configuracao.obter("intimacao_tipos_andamentos_id")[0]
    observacao = Configuracao.obter("intimacao_observacao_protocolo_id")
    descricao_intimacao = Configuracao.obter("intimacao_descricao_id")
    url_intimacao_onr = Configuracao.obter("url_intimacao_onr_id")
    user_inicial_intimacao_onr_id = Configuracao.obter("user_inicial_intimacao_onr_id")
    horas_adic_intimacao_onr_id = Configuracao.obter(
        "horas_adicionais_intimacao_onr_id",
    )
    intimacao_atos_id = Configuracao.obter("intimacao_atos_id")
    intimacao_titulos_id = Configuracao.obter("intimacao_titulos_id")
    intimacao_qtde_dias_uteis_id = Configuracao.obter("intimacao_qtde_dias_uteis_id")

    count = 1

    try:
        # DADOS DA INTIMACAO
        for filhas in raiz.findall("INTIMACAO"):
            # Iniciar nova lista
            limpar_lista()

            # Lendo os dados
            protocolosistema.append(filhas.find("PROTOCOLOSISTEMA").text)
            nrcontrato.append(filhas.find("NRCONTRATO").text)
            dv_contrato.append(filhas.find("DV_CONTRATO").text)
            dtremessa.append(filhas.find("DTREMESSA").text)
            idri.append(filhas.find("IDRI").text)

            # DADOS DO SOLICITANTE
            for solicitante in filhas.findall("SOLICITANTE"):
                nome_solicitante.append(solicitante.find("NOMESOLIC").text)
                cpf_cnpj_solicitante.append(solicitante.find("CPFCNPJSOLIC").text)
                tel_solicitante.append(solicitante.find("TELSOLIC").text)
                email_solicitante.append(solicitante.find("EMAILSOLIC").text)
                # print(NOME_SOLICITANTE)

            # DADOS DO CREDOR
            for credor in filhas.findall("CREDORAPRES"):
                qualificacao.append(credor.find("QUALIFICACAO").text)
                cpfcnpjapres.append(credor.find("CPFCNPJAPRES").text)
                # print(CPFCNPJAPRES)

            # DADOS DO PARTICIPANTES
            for participantes in filhas.findall("PARTICIPANTES"):
                for participantes2 in participantes.findall("PART"):
                    participacao.append(participantes2.find("PARTICIPACAO").text)
                    cpfcnpjpart.append(participantes2.find("CPFCNPJPART").text)
                    # print(PARTICIPACAO, CPFCNPJPART)

            # DADOS DO PARTICIPANTES
            for imoveis in filhas.findall("IMOVEIS"):
                for imoveis2 in imoveis.findall("IMOVEL"):
                    matimovel.append(imoveis2.find("MATIMOVEL").text)
                    endereco_imovel.append(imoveis2.find("ENDERECO_IMOVEL").text)
                    # print(MATIMOVEL)

            # DADOS DO ENDERECO DO PARTICIPANTE
            for endereco_participantes in filhas.findall("ENDINTIMACAO"):
                endereco.append(endereco_participantes.find("ENDERECO").text)
                # print(ENDERECO)

            agencia.append(filhas.find("AGENCIA").text)
            nome_agencia.append(filhas.find("NOME_AGENCIA").text)
            url_requerimento.append(filhas.find("URL_REQUERIMENTO").text)

            # Verificar se o item ja ao foi importando antes - INTIMACAO
            qtde_protocolo_origem = Livro01Protocolo.objects.filter(
                numero_origem=protocolosistema[0],
                origem_pedido=6,
            ).count()

            # Nao tendo sido importado antes - processa
            if qtde_protocolo_origem == 0:
                # Gravando o XML na base de dados
                numero_protocolo = gravar_xml(
                    protocolosistema=protocolosistema,
                    nrcontrato=nrcontrato,
                    dv_contrato=dv_contrato,
                    dtremessa=dtremessa,
                    idri=idri,
                    agencia=agencia,
                    nome_agencia=nome_agencia,
                    url_requerimento=url_requerimento,
                    nome_solicitante=nome_solicitante,
                    cpf_cnpj_solicitante=cpf_cnpj_solicitante,
                    tel_solicitante=tel_solicitante,
                    email_solicitante=email_solicitante,
                    qualificacao=qualificacao,
                    cpfcnpjapres=cpfcnpjapres,
                    participacao=participacao,
                    cpfcnpjpart=cpfcnpjpart,
                    matimovel=matimovel,
                    endereco_imovel=endereco_imovel,
                    endereco=endereco,
                    observacao=observacao,
                    cidade=cidade,
                    numero_estado=numero_estado,
                    titulo_id=chave_titulos,
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
                )

                # print("Iniciar Gravar Evento", user, USER_INICIAL_INTIMACAO_ONR_ID)

                # Gravar o evento na agenda do dia
                evento = Event.criar_evento_no_calendario(
                    user=user,
                    auth_user=user_inicial_intimacao_onr_id,
                    numero=str(numero_protocolo),
                    title=str("Prot. Intimação: " + str(numero_protocolo)),
                    description=str(descricao_intimacao),
                    url=str(url_intimacao_onr),
                    origem="P",
                    horas_adicionais=str(horas_adic_intimacao_onr_id),
                    data_futura_inicio=None,
                    data_futura_fim=None,
                )

                # Gravar o membro do evento na agenda do dia
                Event.criar_membro_no_evento_do_calendario(
                    event=evento,
                    colaborador_i=user_inicial_intimacao_onr_id,
                    salvar_membr="S",
                )

                # print(" Quantidade de protocolos: ", str(count), '  -   ', filhas.find('PROTOCOLOSISTEMA').text)
                count += 1
            else:
                print("Protocolo de intimação já importado: ", protocolosistema[0])

        # print("Encerrado")
    except Exception:
        logger.exception("ERRO")
        print("Arquivo não lido")
