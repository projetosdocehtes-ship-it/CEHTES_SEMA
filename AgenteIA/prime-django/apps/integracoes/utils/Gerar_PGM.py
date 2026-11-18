import xml.etree.ElementTree as ET

from django.db.models import Max, Q
from django.utils import timezone

from apps.cartorios.models import Usuario
from apps.home.models import Livro02, Livro03
from apps.integracoes import views
from apps.integracoes.models import Pgnm, PgnmAuditor


def get_encerrado_do_registro(
    numero_registro: int,
    tipo_registro,
    cartorio_regitro: int,
) -> str:
    registro = Livro02.objects.filter(
        numero=numero_registro,
        tipo=tipo_registro,
        cartorio=cartorio_regitro,
    ).first()

    return registro.encerrado


# Retornar a situacao do IMOVEL
def get_situacao_do_registro(numero_registro, tipo_registro, cartorio_registro):
    registro = Livro02.objects.filter(
        numero=numero_registro,
        tipo=tipo_registro,
        cartorio=cartorio_registro,
    ).first()

    registro.encerrado = get_encerrado_do_registro(
        numero_registro,
        tipo_registro,
        cartorio_registro,
    )
    """
    0 - Ativa;    1 - Anulada;    2 - Encerrada;    3 - Cancelada;    4 - Inexistente;   """

    return "2" if registro.encerrado == "T" else "0"


# Gerar o LOTE CNN
def gerar_lote_cnm(
    request,
    tipo,
    livro,
    list_numero,
    list_numero_cnm,
    list_opcao_envio,
    imoveis_ids,
    numero_ri,
    cns,
):
    root = ET.Element("LOTE")

    nro_inicial, nro_final = "", ""
    item_inicial = 1
    for numero, numero_cnm, opcao_envio in zip(
        list_numero,
        list_numero_cnm,
        list_opcao_envio,
        strict=False,
    ):
        opcao = (
            "0" if tipo == "A" else get_situacao_do_registro(numero, tipo, numero_ri)
        )

        doc = ET.SubElement(root, "REGISTRO")
        ET.SubElement(doc, "SEQ").text = str(item_inicial)
        ET.SubElement(doc, "TIPO").text = str(opcao_envio)
        ET.SubElement(doc, "livro").text = str(livro)
        ET.SubElement(doc, "NUM").text = str(numero)
        ET.SubElement(doc, "CNM").text = str(numero_cnm)
        ET.SubElement(doc, "SITUACAO").text = str(opcao)

        if nro_inicial == "":
            nro_inicial = str(numero)
        nro_final = str(numero)
        item_inicial += 1

    tree = ET.ElementTree(root)

    arquivo = f"CNS_{cns}_{livro}_{str(nro_inicial).zfill(6)}_{str(nro_final).zfill(6)}_CNM.xml"

    tree.write(arquivo)

    # GRAVAR NO BA
    if imoveis_ids:
        if tipo == "A":
            # Atualiza todos os imóveis que correspondem aos IDs na Lista_id_imovel
            Livro03.objects.filter(id__in=imoveis_ids).update(
                data_envio_cnm=timezone.now(),
                enviar_cnm=False,
            )

        else:
            # Atualiza todos os imóveis que correspondem aos IDs na Lista_id_imovel
            Livro02.objects.filter(pk__in=imoveis_ids).update(
                data_envio_cnm=timezone.now(),
                enviar_cnm=False,
            )

        # GERAR UM ADITOR DE ENVIO DO PGNM
        for pk in imoveis_ids:
            _, created = Pgnm.objects.update_or_create(
                imovel_id=pk,
                livro=livro,
                created_at=timezone.now(),
                defaults={
                    "created_at": timezone.now(),
                },
            )

            print("PGNM do livro gerado .", livro)

    # return arquivo
    return views.download_file_xml(request, arquivo)


# INFORMAR: cns CARTORIO, livro DO CARTORIO, numero DO IMOVEL
def get_cnm_onr(cns, livro, numero):
    numero_gerado = str(cns).zfill(6) + str(livro).zfill(1) + str(numero).zfill(7)
    numero_gerado_formatado = (
        str(cns).zfill(6) + "." + str(livro).zfill(1) + "." + str(numero).zfill(7)
    )
    valor_gerado = int(numero_gerado) * 100
    valor_gerado_restante = valor_gerado % 97
    valor_gerado_restante = 98 - valor_gerado_restante
    return numero_gerado_formatado + "-" + str(valor_gerado_restante).zfill(2)


# Selecionar os numeros e enviar
def get_lista_numeros(pk, livro, tipo_imovel):
    # FILTRAR DE USUARIO
    usuario = Usuario.objects.get(pk=pk)

    # cns DO CARTORIO
    cns = usuario.cartorio.cns

    # NUMERO_CARTORIO  1 ou 2
    numero_cartorio = usuario.cartorio.numero_cartorio

    if tipo_imovel == "A":
        # FILTRAR TODOS OS IMOVEIS NAO ENVIADOS NO PGNM
        imovel = Livro03.objects.filter(
            Q(data_envio_cnm__isnull=True, cartorio=numero_cartorio)
            | Q(enviar_cnm=True, cartorio=numero_cartorio),
        )
    else:
        # FILTRAR TODOS OS IMOVEIS NAO ENVIADOS NO PGNM
        imovel = Livro02.objects.filter(
            Q(data_envio_cnm__isnull=True, tipo=tipo_imovel, cartorio=numero_cartorio)
            | Q(enviar_cnm=True, tipo=tipo_imovel, cartorio=numero_cartorio),
        )

    # GERAR A LISTA DE NUMEROS PARA O XML
    list_numero, list_numero_cnm, list_opcao_envio, lista_id_imovel = [], [], [], []
    for indice in imovel:
        # GERAR CNM
        numero_cnm = get_cnm_onr(cns, livro, indice.numero)

        # VERIFICAR SE O IMOVEL JA FOI ENVIADO
        opcao_envio = "I" if not indice.data_envio_cnm else "A"

        # Gerar a lista do XML
        list_numero.append(indice.numero)
        list_numero_cnm.append(numero_cnm)
        list_opcao_envio.append(opcao_envio)

        if tipo_imovel == "A":
            lista_id_imovel.append(indice.id)
        else:
            lista_id_imovel.append(indice.imovel)

    return (
        list_numero,
        list_numero_cnm,
        list_opcao_envio,
        lista_id_imovel,
        numero_cartorio,
        cns,
    )


# Selecionar a ultima data de envio do livro 3
def get_ultimo_envio_numero_onr_l3():
    # Sua consulta original modificada para incluir aggregate
    resultado = Livro03.objects.filter(
        Q(data_envio_cnm__isnull=False) & Q(numero__lte=115000),
    ).aggregate(maior_numero=Max("numero"))

    # maior_data_envio_cnm será None se não existirem registros
    return resultado["maior_numero"]


# Selecionar a ultima data de envio do livro 2
def ultimo_protocolo_enviado_onr():
    # Sua consulta original modificada para incluir aggregate
    resultado = Livro02.objects.filter(
        data_envio_cnm__isnull=False,
        numero__lte=115000,
    ).aggregate(maior_numero=Max("numero"))

    # maior_data_envio_cnm será None se não existirem registros
    return resultado["maior_numero"]


# Obter a ultima data de envio do livro 2 e 3 para o ONR
def get_ultima_data_envio_numero_onr(numero_livro):
    # Sua consulta original modificada para incluir aggregate
    resultado = PgnmAuditor.objects.filter(livro=numero_livro).aggregate(
        maior_data_envio=Max("created_at"),
    )

    # maior_data_envio_cnm será None se não existirem registros
    return resultado["maior_data_envio"]


# Selecionar a ultima data de envio do livro 2
def get_ultimo_envio_numero_onr_l4():
    # Sua consulta original modificada para incluir aggregate
    resultado = Livro02.objects.filter(
        Q(data_envio_livro_4__isnull=False) & Q(numero__lte=115000),
    ).aggregate(maior_numero=Max("numero"))

    # maior_data_envio_cnm será None se não existirem registros
    return resultado["maior_numero"]
