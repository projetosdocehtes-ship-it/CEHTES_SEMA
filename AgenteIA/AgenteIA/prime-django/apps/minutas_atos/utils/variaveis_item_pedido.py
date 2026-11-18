import re

from django.db.models import Prefetch
from django.utils import timezone

# from apps.home.models import Pedidos_Itens as PedidoItem
from apps.home.models import (
    Anterior,
    EstadoCivil,
    Livro01Protocolo,
    Livro02,
    Livro03,
    Lote,
    PedidoItem,
    PedidoParte,
    PedidoParteAto,
    PerguntaMinuta,
    Rua,
    Rural,
    RuralNome,
    SeloEletronico,
    TipoRegimeCasamento,
    Unidade,
)
from apps.home.templatetags.home_formatos import (
    converter_data_para_formato_de_modelo,
)
from apps.home.utils import formatar_data
from apps.minutas_atos.models import VariavelMinutaModeloAto
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_documento


# Obter os dados do imóvel
def get_imovel_registro_auxiliar(numero_imovel, tipo_imovel, cartorio_imovel):
    # SELECIONAR IMOVEL OU REGISTRO AUXILIAR
    livro03 = Livro03.objects.filter(numero=numero_imovel, cartorio=cartorio_imovel)
    imovel = Livro02.objects.filter(
        numero=numero_imovel,
        tipo=tipo_imovel,
        cartorio=cartorio_imovel,
    )
    if tipo_imovel == "A":
        return None, livro03
    else:
        return imovel, None


# Obter o protocolo para retornar os dados
def get_protocolo(pedido_id):
    return Livro01Protocolo.objects.get(pedido_id=pedido_id)


# Obter o ato anterior da mesmo numero de imovel no protocolo
def get_numero_ato_anterior_atual(pedido_item):
    return (
        PedidoItem.objects.filter(
            pk__lt=pedido_item.pk,
            pedido_id=pedido_item.pedido_id,
            numero_registro=pedido_item.numero_registro,
        )
        .values_list("numero_ato", flat=True)
        .last()
    )


# Obter o iem do pedido para retornar os dados
def get_pedido_item_selo(pedido_item_id):
    return SeloEletronico.objects.get(pedido_item_id=pedido_item_id)


# Obter o iem do pedido para retornar os dados
def get_pedido_item(pedido_item_id, db):
    return PedidoItem.objects.get(pk=pedido_item_id)


# Obter a data de hoje
def get_data_hoje(formato, opcao=1):
    # 2 - FORMATO DE DATA POR EXTENSO
    if opcao == 2:
        data = str(formatar_data(timezone.now().strftime(formato), 2))
        return str(data)
    # FORMATO PADRAO
    else:
        data = timezone.now().strftime(formato)
        return str(data)


def get_data_hoje_extenso(formato, opcao=2):
    # 2 - FORMATO DE DATA POR EXTENSO
    if opcao == 2:
        data = str(formatar_data(timezone.now().strftime(formato), 2))
        return str(data)
    # FORMATO PADRAO
    else:
        data = timezone.now().strftime(formato)
        return str(data)


# OBTER OS DADOS DO CARTORIO
def get_lista_variaveis_temporarias():
    return PerguntaMinuta.objects.all().values_list("corrans", flat=True)


# OBTER O TEXTO CORRESPONDENTE AO ESTADO CIVIL DA PARTE
def get_texto_estado_id(estado_civil_id=1):
    estado_civil = EstadoCivil.objects.get(id=estado_civil_id)
    return estado_civil.observacao


# PROCESSAR AS VARIAVEIS TEMPORARIAS PELO VALOR DO TEXTO
def processar_variavel_pessoa_texto(dicionario, qualificado_pessoa):
    # SUBSTITUIR AS VARIAVEIS TEMPORARIAS PELO VALOR - PESSOA
    if dicionario and isinstance(dicionario, dict):
        for chave, valor in dicionario.items():
            # Verifica se o valor é None
            if valor is None:
                qualificado_pessoa = qualificado_pessoa.replace(
                    chave,
                    '<b><font color="red">NAO INFORMADO</font></b>',
                )
            else:
                qualificado_pessoa = qualificado_pessoa.replace(chave, str(valor))

    return qualificado_pessoa


# SUBSTITUIR AS VARIAVEIS TEMPORARIAS PELO VALOR DO TEXTO
def substituir_variavel_pessoa_texto(
    qualificado_pessoa,
    dicionario_pessoa,
    dicionario_pessoa_conjuge,
):
    # SUBSTITUIR AS VARIAVEIS TEMPORARIAS PELO VALOR - PESSOA
    qualificado_pessoa = processar_variavel_pessoa_texto(
        dicionario_pessoa,
        qualificado_pessoa,
    )
    return processar_variavel_pessoa_texto(
        dicionario_pessoa_conjuge,
        qualificado_pessoa,
    )


# REMOVER PARAGRAFO DO TEXTO SE EXISTIR
def remover_paragrafo_formatacoes(texto):
    # Remove todas as aberturas de tag <p> com ou sem atributos
    if texto:
        texto = re.sub(r"<p\s*([^>]*)>", "", texto)
        texto = re.sub(r"<span\s*([^>]*)>", "", texto)

        # Remove todas as tags de fechamento </span>
        texto = texto.replace("</p>", "")
        return texto.replace("</span>", "")
    else:
        return ""


# Verificar as adaptações de gênero
def verificar_adaptacoes(qualificado_pessoa, coluna):
    # Obter todas as variáveis da minuta
    variavel_minuta = VariavelMinutaModeloAto.objects.all()

    # Mapear colunas para os atributos do modelo
    coluna_para_atributo = {
        "descricao_masculino_simples": "descricao_masculino_simples",
        "descricao_masculino_composto": "descricao_masculino_composto",
        "descricao_feminino_simples": "descricao_feminino_simples",
        "descricao_feminino_composto": "descricao_feminino_composto",
    }

    # Verificar se a coluna é válida
    if coluna in coluna_para_atributo:
        for item in variavel_minuta:
            # Substituir a variável pela descrição apropriada
            qualificado_pessoa = qualificado_pessoa.replace(
                item.variavel,
                getattr(item, coluna_para_atributo[coluna]),
            )

    return qualificado_pessoa


# OBTER O CATEGORIA - Descricao da EstadoCivil
def get_estado_civil(pk=0, sexo="M"):
    # Mapear sexo para o campo correspondente na base de dados
    campos = {
        "M": "texto_masculino",
        "F": "texto_feminino",
        "default": "descricao_minuta",
    }

    # Selecionar o campo com base no sexo, padrão se sexo não for M ou F
    campo = campos.get(sexo, campos["default"])

    # Retornar o valor da estado_civil com base no campo selecionado
    return EstadoCivil.objects.filter(id=pk).values_list(campo, flat=True).first()


# SUBSTITUIR AS VARIAVEIS TEMPORARIAS PELO VALOR DO TEXTO
def substituir_variavel_dicionario_adaptacao(
    qualificado_pessoa,
    sexo_pessoa="M",
    sexo_conjuge="M",
):
    # Mapeamento das descrições baseado no sexo e na quantidade
    descricao_mapa = {
        (1, "F"): "descricao_feminino_simples",
        (1, "M"): "descricao_masculino_simples",
        (2, "F"): "descricao_feminino_composto",
        (2, "M"): "descricao_masculino_composto",
    }

    # Definir quantidade e descrição do sexo
    quantidade = 2 if sexo_conjuge else 1
    descricao_sexo = (
        "F" if sexo_pessoa == "F" and (quantidade == 1 or sexo_conjuge == "F") else "M"
    )

    # Obter o valor correspondente do dicionário
    coluna = descricao_mapa.get((quantidade, descricao_sexo))

    # Verificar se a coluna existe e substituir pelos DICIONARIOS cadastrados
    return verificar_adaptacoes(qualificado_pessoa, coluna)


# OBTER O REGIME DE BENS - TipoRegimeCasamento - GERALMENTE PARA CASADO
def get_regime(pk=0, sexo="M"):
    return TipoRegimeCasamento.objects.filter(id=pk).values_list(
        "descricao_regime",
        flat=True,
    )[0]


def importar_pessoas_envolvidas(pedido_item_id, opcao):
    # PEGANDO PEDIDO
    db = FbConnection()
    pedido_item = get_pedido_item(pedido_item_id, db)

    # CADASTRAR AS PARTES ENVOLVIDAS
    pedidoparte = PedidoParte.objects.filter(pedido=pedido_item.pedido)

    # VINCULANDO ENVOLVIDOS DO PEDIDO AO ATO ESPECIFICIO
    for pedido in pedidoparte:
        PedidoParteAto.objects.update_or_create(
            pessoa_id=pedido.pessoa_id,
            # status=pedido.papel,
            tipo_parte=pedido.papel,
            pedido_item_id=pedido_item_id,
            defaults={
                "pessoa_id": pedido.pessoa_id,
                "tipo_parte": pedido.papel,
                "pedido_item_id": pedido_item_id,
            },
        )

    # FILTRAR AS PARTES ENVOLVIDAS
    return PedidoParteAto.objects.filter(
        pedido_item_id=pedido_item_id,
        # status=opcao,
        tipo_parte=opcao,
    ).order_by("id")


# FILTRAR AS PARTES ENVOLIDAS E PROCESSAR ALTERACAO
def gerar_partes_envolvidas(pedido_item_id, opcao):
    from apps.pedidos.models import Participacao as ParticipacaoPrime

    # Inicia o texto e obter no estado civil
    qualificado_pessoa = ""

    # Lista para armazenar os dicionários de cada pessoa
    lista_dicionarios_pessoa, lista_dicionarios_pessoa_conjuge = [], []

    # FILTRAR AS PARTES ENVOLVIDAS
    # partes_envolvidas = PedidoParteAto.objects.filter(
    #     pedido_item_id=pedido_item_id,
    #     # status__in=opcao,
    #     tipo_parte__in=opcao,
    # ).order_by("id")
    partes_envolvidas = ParticipacaoPrime.objects.filter(
        ato__id=pedido_item_id, papel_id=opcao
    )

    # CASO NAO TENHA SIDO DEFINIDO NENHUMA PARTE ENVOLVIDA
    # if not partes_envolvidas.exists():
    #    partes_envolvidas = importar_pessoas_envolvidas(pedido_item_id, opcao, db)

    # PROCESSAR INFORMAÇÃO DOS NOMES E CRIAR DICIONÁRIOS
    for item in partes_envolvidas:
        try:
            qualificado_pessoa = remover_paragrafo_formatacoes(
                get_texto_estado_id(item.parte.estado_civil_id),
            )

            if item.parte.tipo_regime_casamento:
                tipo_regime_casamento_id = get_regime(
                    item.parte.tipo_regime_casamento_id,
                )
            else:
                tipo_regime_casamento_id = ""

            if item.parte.data_casamento:
                data_casamento = converter_data_para_formato_de_modelo(
                    item.parte.data_casamento,
                )
            else:
                data_casamento = ""

            cpf_cpnj = formatar_documento(item.parte.documento)

            # Supondo que você tenha modelos relacionados ou campos adicionais para preencher os dados abaixo
            dicionario_pessoa = {
                "{{ pessoa_nome }}": str(item.parte.nome).upper(),
                "{{ pessoa_nacionalidade }}": item.parte.nacionalidade,
                "{{ pessoa_estado_civil }}": get_estado_civil(
                    item.parte.estado_civil_id,
                    item.parte.sexo,
                ),
                "{{ pessoa_profissao }}": item.parte.profissao,
                "{{ pessoa_documento }}": item.parte.documento_auxiliar,
                "{{ pessoa_endereco }}": item.parte.endereco,
                "{{ pessoa_cpf }}": cpf_cpnj,
                "{{ pessoa_tipo_regime_casamento }}": tipo_regime_casamento_id,
                "{{ pessoa_data_casamento }}": data_casamento,
            }
            lista_dicionarios_pessoa.append(dicionario_pessoa)

            # Verificar se existe pessoa conjuge
            if item.parte.conjuge:
                # CRIAR UM DICIONARIO COM AS VARIAVEIS TEMPORARIAS - PESSOA CONJUGUE
                dicionario_pessoa_conjuge = {
                    "{{ pessoa_conjuge_nome }}": str(item.pessoa_conjuge.nome).upper(),
                    "{{ pessoa_conjuge_nacionalidade }}": item.pessoa_conjuge.nacionalidade,
                    "{{ pessoa_conjuge_estado_civil }}": get_estado_civil(
                        item.pessoa_conjuge.estado_civil_id,
                        item.pessoa_conjuge.sexo,
                    ),
                    "{{ pessoa_conjuge_profissao }}": item.pessoa_conjuge.profissao,
                    "{{ pessoa_conjuge_documento }}": item.pessoa_conjuge.documento,
                    "{{ pessoa_conjuge_endereco }}": item.pessoa_conjuge.endereco,
                    "{{ pessoa_conjuge_cpf }}": formatar_documento(
                        item.pessoa_conjuge.cpf,
                    ),
                    "{{ pessoa_conjuge_tipo_regime_casamento }}": get_regime(
                        item.pessoa_conjuge.tipo_regime_casamento_id,
                    ),
                    "{{ pessoa_conjuge_data_casamento }}": converter_data_para_formato_de_modelo(
                        item.pessoa_conjuge.data_casamento,
                    ),
                }
            else:
                dicionario_pessoa_conjuge = {}
            lista_dicionarios_pessoa_conjuge.append(dicionario_pessoa_conjuge)

            # VERIFICAR O SEXO DA PESSOA E DO CONJUGE
            sexo = getattr(item.parte.sexo, "sexo", "M")

            if item.parte.conjuge:
                sexo_conjuge = getattr(item.parte.conjuge.sexo, "sexo", "")
            else:
                sexo_conjuge = ""

            # RETORNAR O TEXTO COM AS VARIAVEIS TEMPORARIAS SUBSTITUIDAS - DICIONARIO DE ADPTACOES
            qualificado_pessoa = substituir_variavel_dicionario_adaptacao(
                qualificado_pessoa,
                sexo,
                sexo_conjuge,
            )
        except:
            pass

    # Iterando sobre a lista de dicionários de pessoas
    for dicionario_pessoa, dicionario_pessoa_conjuge in zip(
        lista_dicionarios_pessoa,
        lista_dicionarios_pessoa_conjuge,
        strict=False,
    ):
        # SUBSTITUIR AS VARIAVEIS TEMPORARIAS PELO VALOR
        qualificado_pessoa = substituir_variavel_pessoa_texto(
            qualificado_pessoa,
            dicionario_pessoa,
            dicionario_pessoa_conjuge,
        )

    # print(qualificado_pessoa)
    return qualificado_pessoa


# TRABALHAR AQUI PARA OBTER ADQUIRENTE (A=Adquirente, T=Transmitente, P=Proprietário)
def get_qualificado_parte(pedido_item_id, opcao="1"):
    return gerar_partes_envolvidas(pedido_item_id, opcao)


# PEGANDO OS DADOS DO INDICE CADASTRAL DO IMOVEL
def get_imovel_indice_cadastral(imovel):
    return {"{{ registro_indice_cadastral }}": "; ".join(imovel.indice_cadastral)}


# PEGANDO O RUAS DO IMOVEL
def get_imovel_ruas(unidades_id):
    # Buscar todos as ruas relacionados ao imóvel
    ruas = Rua.objects.filter(unidade_id=unidades_id)

    # Inicializar lista para armazenar strings formatadas
    registro = []

    for rua in ruas:
        # Verificar se numero_edificacao está presente e adicionar à string adequadamente
        endereco = rua.nome
        if rua.numero_edificacao:
            endereco += ", " + rua.numero_edificacao
        registro.append(endereco)

    return registro


# PEGANDO O Anterior DO IMOVEL
def get_registro_anterior(imovel_id):
    # Buscar todos os registros anteriores relacionados ao imóvel
    anteriores = Anterior.objects.filter(imovel_id=imovel_id)

    # Inicializar lista para armazenar strings formatadas
    registro = []

    # Pré-processar descrições e matrículas se necessário
    tipos_processados = {}
    matriculas_processadas = {}

    for anterior in anteriores:
        # Processar e armazenar resultados únicos para evitar recalculo
        tipo = tipos_processados.setdefault(
            anterior.tipo,
            anterior.tipo_descrito,
        )
        matricula = matriculas_processadas.setdefault(
            anterior.numero,
            anterior.numero_formatado,
        )

        registro.append(f"{tipo} {matricula}, {anterior.complemento or ''}")

    return {
        "{{ registro_anterior }}": "; ".join(filter(None, registro)),
    }


# TRATAR O DADOS DO IMOVEL RURAL
def get_imovel_rural(imovel_id):
    return Rural.objects.filter(imovel_id=imovel_id).first()


# TRATAR O DADOS DO IMOVEL RURAL
def get_imovel_rural_nome(imovel_id):
    return RuralNome.objects.filter(imovel_id=imovel_id).first()


# TRATAR O DADOS DO IMOVEL URBANO
def get_imovel_urbanos(imovel_id) -> str:
    return "DADOS DO IMOVEL URBANO"


# TRATAR O DADOS DO IMOVEL RURAL
def get_imovel_condominio(imovel_id) -> str:
    return "DADOS DO IMOVEL CONDOMINIO"


# TRATAR O DADOS DO IMOVEL LOTE
def get_imovel_lote(imovel_id):
    # Utilizar prefetch_related para reduzir o número de consultas ao DB
    unidades = Unidade.objects.filter(imovel_id=imovel_id).prefetch_related(
        Prefetch(
            "lote",
            queryset=Lote.objects.all(),
        ),  # Ajuste o 'lotes_set' conforme o nome real do related_name
    )

    # Inicializar conjuntos para armazenar valores únicos
    areas, quadras, setores, numeros_unidade = set(), set(), set(), set()

    # Iterar sobre as unidades
    for unidade in unidades:
        lote = unidade.lote
        # for lote in unidade.lote.all():  # Ajuste de acordo com o nome real do relacionamento
        if lote:  # Certifica que o lote está presente antes de acessar seus atributos
            areas.add(lote.area if lote.area else "")
            quadras.add(lote.quadra if lote.quadra else "")
            setores.add(lote.setor if lote.setor else "")
            numeros_unidade.add(lote.numero_unidade if lote.numero_unidade else "")

            # SEMPRE OBTER TODAS AS RUAS
            ruas = get_imovel_ruas(unidade.pk)

    # Converter conjuntos em strings, unindo elementos com " / "
    # CRIAR UM DICIONARIO COM AS VARIAVEIS TEMPORARIAS - UNIDADE LOTE
    # filter(None, ...) remove elementos vazios ou None,
    return {
        "{{ unidade_lote_bairro }}": "; ".join(filter(None, setores)),
        "{{ unidade_lote_quadra }}": "; ".join(filter(None, quadras)),
        "{{ unidade_lote_numero_unidade }}": "; ".join(filter(None, numeros_unidade)),
        "{{ unidade_lote_area }}": "; ".join(filter(None, areas)),
        "{{ imovel_ruas }}": "; ".join(filter(None, ruas)),
    }
