import datetime
import logging
import os
import re
import zipfile
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import phonenumbers
import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import QuerySet
from django.utils import timezone
from num2words import num2words
from PIL import Image, ImageSequence

from apps.home.tipos import TipoRegistro

import math
import pandas as pd

DEFAULT_HSP = 5.0          # horas de sol pleno/dia
DEFAULT_SYSTEM_EFF = 0.78  # perdas globais do sistema
DEFAULT_PANEL_WATTS = 550  # Wp

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def upload(username, image):
    from storages.backends.ftp import FTPStorage

    file_obj = image

    # do your validation here e.g. file size/type check

    # organize a path for the file in bucket
    file_directory_within_bucket = f"{username}"

    # synthesize a full file path; note that we included the filename
    file_path_within_bucket = Path(file_directory_within_bucket) / file_obj.name

    media_storage = FTPStorage()

    # avoid overwriting existing file
    if not media_storage.exists(file_path_within_bucket):
        media_storage.save(file_path_within_bucket, file_obj)

    return media_storage.url(file_path_within_bucket)


def cfg_val(var_name):
    return getattr(settings, var_name, None)


def cfg_login_attempts():
    return cfg_val("LOGIN_ATTEMPTS")


def cfg_ftp_upload():
    return cfg_val("FTP_UPLOAD")


def get_emolumento_item():
    from apps.home.models import Emolumentos

    emolumento_id = Emolumentos.objects.filter(emolumento_default="S").values_list(
        "id",
        flat=True,
    )

    return next(iter(emolumento_id))
    # emolumento_item_id = 1377


# Grupo de Servicos do PROTOCOLO - Exigencia Positiva


# def get_ids_de_tipo_exigencia_positiva():
#     from apps.home.models import TipoAndamento

#     servicos_exigencia_positiva_id = TipoAndamento.objects.filter(
#         grupo_exigencia_positiva="S"
#     ).values_list("tipo_andamento", flat=True)

#     return list(servicos_exigencia_positiva_id)


# Provisorio
# GRAVAR UM NOVO ATO E ADICIONAR O NOVO NUMERO - firebird


def get_ato_item():
    from apps.home.models import AtoPratica

    tipo_ato_protocolo_id = AtoPratica.objects.filter(ato_default="S").values_list(
        "id",
        flat=True,
    )

    return next(iter(tipo_ato_protocolo_id))
    # tipo_ato_protocolo_id = 392


# PROVISORIO - lembrar de cria coluna na tabela servicos andamentos com o intuito de marcar os servicos que atualizam o colaborador atual que esta com o protocolo


def get_ids_servicos_para_atualizar_status():
    from apps.home.models import TipoAndamento

    """
    Obtém os identificadores de todos os serviços em andamento que necessitam de atualização de status.

    A função consulta o modelo `TipoAndamento` para encontrar todos os registros
    com a flag `atualizar_status_protocolo` configurada como "S" (Sim). Retorna uma lista
    com os campos `tipo_andamento` desses registros.

    Retorna:
        list: Lista de identificadores `tipo_andamento` para os serviços que precisam de atualização de status.
              Retorna uma lista vazia se nenhum serviço corresponder ao critério.

    Exemplo:
        >>> get_ids_servicos_para_atualizar_status()
        [1, 2, 3]  # Ou [] se nenhum serviço necessitar de atualização de status
    """

    servicos_para_atualizar = TipoAndamento.objects.filter(
        atualizar_status_protocolo="S",
    ).values_list("tipo_andamento", flat=True)

    return list(servicos_para_atualizar)


def get_url_pesquisa_protocolo(numero_protocolo):
    from apps.home.models import Livro01Protocolo

    protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo).first()
    return (
        protocolo.get_absolute_url() if protocolo else Livro01Protocolo.get_list_url()
    )


def decimal_ou_zero(valor=0):
    try:
        valor_decimal = Decimal(valor)
    except InvalidOperation:
        valor_decimal = Decimal("0.0")  # Definindo um valor padrão

    return valor_decimal


# FINALIZAR O EVENTO DA AGENDA
def finalizar_evento(numero, tipo, opcao, exibir_agenda_protocolo="S") -> None:
    from apps.home.models import Configuracao
    from apps.home.templatetags.home_formatos import (  # get_registrar_exigencia_cumprida,;; get_descricao_cancelado,; get_descricao_exigencia,;; get_texto_previsto,;; get_texto_protocolo,; get_texto_qualificar,; ,; get_texto_validade,; get_verificar_exigencia_cumprida,
        get_descricao_cancelado,
        get_descricao_exigencia,
        get_registrar_exigencia_cumprida,
        get_texto_previsto,
        get_texto_protocolo,
        get_texto_qualificar,
        get_texto_validade,
        get_verificar_exigencia_cumprida,
        protocolo_formatado,
    )

    # Inicializar titulo
    # FINALIZAR EVENTO DO PROTOCOLO
    if (tipo == "P") and (opcao == "P"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_texto_protocolo()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "D"):
        # numero = get_protocolo_pelo_id(numero)
        str(Configuracao.obter("DESCRICAO_SERVICO_REGISTRADO")) + str(
            protocolo_formatado(str(numero)),
        )

    elif (tipo == "P") and (opcao == "C"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_descricao_cancelado()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "N"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_descricao_exigencia()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "Q"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_texto_qualificar()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "R"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_texto_previsto()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "V"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_texto_validade()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "E"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_verificar_exigencia_cumprida()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "Z"):
        # numero = get_protocolo_pelo_id(numero)
        str(get_registrar_exigencia_cumprida()) + str(protocolo_formatado(str(numero)))

    elif (tipo == "P") and (opcao == "I"):
        # numero = get_protocolo_pelo_id(numero)
        texto = str(Configuracao.obter("descricao_servico_distribuido")).split(" ")[0]
        texto + str(protocolo_formatado(str(numero)))

    # FINALIZAR O EVENTO DA AGENDA
    # Event.objects.encerrar_evento_pelo_titulo(titulo=titulo, exibir_agenda_protocolo=exibir_agenda_protocolo)


# FINALIZAR TODOS OS EVENTO DA AGENDA
# def apagar_evento_pelo_numero(numero):
#     from apps.home.models import Event

#     # Filtrar eventos em uma única consulta
#     events_to_delete = Event.objects.filter(numero=str(numero))

#     # Apagar todos os registros filtrados
#     events_to_delete.delete()


# Grupo de Servicos do PROTOCOLO - Digitalizar


# # Diretorio onde ficaram as imagens
# def get_diretorio_ged_imagens():
#     retorno = Configuracao.obter("diretorio_ged_imagens")
#     return retorno


# Diretorio onde ficaram as imagens
# def get_diretorio_ged_protocolos():
#     diretorio_ged_protocolos = Configuracao.obter("diretorio_ged_protocolos")
#     return diretorio_ged_protocolos


# Diretorio onde ficaram as imagens
# def get_caminho_minutas():
#     return staticfiles_storage.path(DIRETORIO_NOTA_MINUTAS)


# def Get_Pesquisar_Protocolo(numero_protocolo):
#     return str(
#         "http://127.0.0.1:8000/protocolos/?numero_protocolo= " + numero_protocolo
#     )


# class ExportadorPedidoCertidao:
#     def __init__(self, pedido, db, request):
#         self.pedido = pedido
#         self.db = db
#         self.request = request

#     def exportar(self):
#         try:
#             self.db.begin_transaction()

#
#             # Substitua as chamadas para self.gravar_* por métodos dentro desta classe
#             # ...

#             self.db.commit()
#             mensagem_sucesso = f"SUCESSO! ID do pedido após a exportação: {pedido_fb['pedido_id']}"
#             messages.success(self.request, mensagem_sucesso)
#             print(mensagem_sucesso)
#         except Exception as e:
#             self.db.rollback()
#             mensagem_erro = f"ERRO ao tentar exportar o pedido: {e}"
#             messages.error(self.request, mensagem_erro)
#             print(mensagem_erro)

#         return HttpResponseRedirect(reverse("home:detalhes_pedido", args=[self.pedido.pk]))

#     # Métodos gravar_pessoa, gravar_imoveis, etc., podem ser movidos ou replicados aqui, adaptados conforme necessário.


# # FINALIZAR O EVENTO DA AGENDA
# def finalizar_evento(numero, tipo, opcao):
#     from apps.home.models import Event
#     from apps.home.templatetags.home_formatos import (
#         get_texto_protocolo,
#         get_protocolo_pelo_id,
#         protocolo_formatado,
#     )

#     # Inicializar titulo
#     titulo = ""

#     # FINALIZAR EVENTO DO PROTOCOLO
#     if (tipo == "P") and (opcao == "P"):
#         numero = get_protocolo_pelo_id(numero)
#         titulo = str(get_texto_protocolo()) + str(protocolo_formatado(str(numero)))

#     # FILTRAR OS EVENTOS
#     event = Event.objects.filter(title=str(titulo), end_time_checked__isnull=True)

#     # FILTRAR OS EVENTOS
#     for eventos in event:
#         event_atualizar = Event.objects.get(pk=eventos.id)
#         event_atualizar.end_time_checked = Data.now().strftime("%Y-%m-%d %H:%M")

#         # Caso nao tenha sido definido o nicio do evento
#         if event_atualizar.start_time_checked == None:
#             event_atualizar.start_time_checked = Data.now().strftime("%Y-%m-%d %H:%M")

#         event_atualizar.save()


def get_user_id_2(auth_user):
    from apps.home.models import User

    # Se auth_user for uma instância de User, retorna diretamente os atributos
    if isinstance(auth_user, User):
        return auth_user.id, auth_user.is_staff

    try:
        # Se auth_user for um identificador único (ex: nome de usuário ou ID), tenta buscar o usuário
        if isinstance(auth_user, str):
            user = User.objects.get(username=auth_user)
        elif isinstance(auth_user, int):
            user = User.objects.get(id=auth_user)
        else:
            msg = "auth_user deve ser um nome de usuário (string) ou um ID (int)"
            raise TypeError(msg)

        return user.id, user.is_staff
    except User.DoesNotExist:
        # Se não encontrar o usuário, retorna None e False
        return None, False
    except ValueError as e:
        # Se auth_user não for de um tipo apropriado
        return str(e), False


# Grupo de Servicos de STATUS FINALIZADO (PROTOCOLO - CANCELADO ou REGISTRADO)
def get_servicos_finalizar_status():
    from apps.home.models import StatusProtocolo

    return StatusProtocolo.objects.filter(finalizar="S").values_list("id", flat=True)


def gerar_lista_numero_pesquisar(query, pedido_id):
    """Nesta rotina, todos os itens de protocolo que tiverem número são gerados para pesquisar se existem protocolos vinculados a eles."""
    # Remova duplicatas convertendo a lista de tuplas em um conjunto para reduzir as entradas.
    list_numero = {
        (item.numero_registro, item.tipo_registro, item.numero_ri) for item in query
    }

    total_protocolos_vinculados, total_protocolos_em_andamento = 0, 0

    # VERIFICAR SE O IMOVEL OU LIVRO 3 POSSUI PROTOCOLO EM ANDAMENTO
    for numero_registro, tipo_registro, numero_ri in list_numero:
        protocolo_vinculados, protocolo_em_andamento = get_protocolos_em_andamento(
            numero_registro,
            tipo_registro,
            numero_ri,
            pedido_id,
        )

        # Atualizar contagens com base na presença de protocolos
        total_protocolos_vinculados += protocolo_vinculados.exists()
        total_protocolos_em_andamento += protocolo_em_andamento.exists()

    return total_protocolos_em_andamento, total_protocolos_vinculados


def get_protocolos_em_andamento(
    numero_registro,
    tipo_registro,
    numero_ri,
    pedido_id=0,
):
    from apps.home.models import Livro01Protocolo, PedidoItem

    # Obtenha os IDs de Pedidos Itens relacionados à ID do pedido fornecida
    pedidos_ids = list(
        PedidoItem.objects.filter(
            numero_registro=numero_registro,
            tipo_registro=tipo_registro,
            numero_ri=numero_ri,
        ).values_list("pedido", flat=True),
    )  # Convertido diretamente para lista se não houver duplicatas.

    # SELECIONAR OS PROTOCOLOS VINCULADOS, EXCLUINDO O PROTOCOLO ATUAL E FILTRANDO PELOS STATUS DE FINALIZAÇÃO
    # Aqui combinamos a filtragem de protocolos vinculados e protocolos em andamento em uma única operação para eficiência.
    servicos_finalizar_status = get_servicos_finalizar_status()

    protocolo_vinculados = Livro01Protocolo.objects.filter(
        pedido_id__in=pedidos_ids,
    ).exclude(
        pedido_id=pedido_id,
    )

    protocolo_em_andamento = protocolo_vinculados.exclude(
        status_id__in=servicos_finalizar_status,
    )

    # RETORNAR OS PROTOCOLOS VINCULADOS E EM ANDAMENTO
    return protocolo_vinculados, protocolo_em_andamento


# Diretorio onde ficaram as imagens


def adicionar_fuso_horario_em_data(naive_value):
    """
    Converte um objeto datetime.date ou datetime.datetime 'naive' para 'aware' usando o fuso horário configurado no Django.
    Se o valor de entrada for um objeto date, ele será convertido para um objeto datetime com horário 00:00.

    Parâmetros:
    - naive_value: Um objeto datetime.date ou datetime.datetime que é 'naive' (sem fuso horário).

    Retorna:
    - Um objeto datetime.datetime 'aware' (com fuso horário), se o suporte a fuso horário estiver ativo.
    - O mesmo objeto datetime.datetime ou uma conversão para datetime.datetime, se o suporte a fuso horário não estiver ativo.
    """
    if isinstance(naive_value, datetime.date) and not isinstance(
        naive_value,
        datetime.datetime,
    ):
        # Converte objetos datetime.date para datetime.datetime com hora 00:00
        naive_datetime = datetime.datetime.combine(naive_value, datetime.time())
    else:
        naive_datetime = naive_value

    if settings.USE_TZ and naive_datetime is not None and naive_datetime.tzinfo is None:
        # Pega o fuso horário padrão do Django e converte o datetime 'naive' para 'aware'
        default_timezone = timezone.get_default_timezone()
        return timezone.make_aware(naive_datetime, default_timezone)
    return naive_datetime


def process_images(diretorio, padrao, file):
    images = []
    arquivos = os.listdir(diretorio)
    for arquivo in arquivos:
        if padrao in arquivo:
            caminho_completo = Path(diretorio) / arquivo
            with Image.open(caminho_completo) as image:
                for _i, page in enumerate(ImageSequence.Iterator(image)):
                    p = page.convert("RGB")
                    images.append(p)
    return images


def save_images_to_pdf(images, file) -> None:
    if len(images) == 0:
        return
    elif len(images) == 1:
        images[0].save(file, format="PDF")
    else:
        images[0].save(file, format="PDF", save_all=True, append_images=images[1:])
    for image in images:
        image.close()
    del images
    file.seek(0)


# Método modificado para incluir o tratamento de exceções
def get_urls_imagens_pela_webservice(pasta_de_imagens) -> list[str]:
    from apps.home.models import Configuracao

    try:
        logger.info(
            f"Iniciando get_urls_imagens_pela_webservice para a pasta: {pasta_de_imagens}",
        )
        path = f"{Configuracao.obter('url_ged')}{pasta_de_imagens}"
        logger.info(f"URL de requisição: {path}")
        response = requests.get(path, timeout=10)

        if response.status_code != 200:
            logger.info(
                f"Request to {path} failed with status code {response.status_code}",
            )
            return []

        arquivos = response.json()
        logger.info(f"Lista de arquivos recebida: {arquivos}")

        abs_path = "/".join(pasta_de_imagens.strip("/").split("/")[:-1])
        urls = [
            f"{Configuracao.obter('url_ged_download')}/{abs_path}/{arquivo}"
            for arquivo in arquivos
        ]
        logger.info(f"URLs construídas para os arquivos: {urls}")

        return urls
    except Exception:
        msg = f"ERRO: Falha ao obter as imagens da pasta: '{pasta_de_imagens}'"
        logger.exception(msg)
        return []


def get_imagens_via_request(url_pasta) -> list[Image.Image]:
    from apps.home.models import Configuracao

    # Faz a requisição para obter a lista de arquivos
    response = requests.get(url_pasta, timeout=10)

    # Verifica se a requisição foi bem sucedida
    if response.status_code != 200:
        msg = f"Request to {url_pasta} failed with status code {response.status_code}"
        raise ValueError(msg)

    # Obtém a lista de arquivos da resposta
    arquivos = response.json()

    images = []
    for arquivo in arquivos:
        # Constrói o caminho completo para baixar o arquivo
        caminho_completo = Path(Configuracao.obter("url_ged_download")) / arquivo

        # Faz a requisição para baixar o arquivo
        response = requests.get(caminho_completo, stream=True, timeout=10)

        # Verifica se a requisição foi bem sucedida
        if response.status_code != 200:
            msg = f"Request to {caminho_completo} failed with status code {response.status_code}"
            raise ValueError(msg)

        # Abre a imagem a partir da resposta
        image = Image.open(response.raw)

        # Para cada página na imagem
        for _i, page in enumerate(ImageSequence.Iterator(image)):
            # Converte a página para RGB e adiciona à lista de imagens
            saida = page.convert("RGB")
            images.append(saida)
    return images


def get_lista_modelos_minuta(diretorio_minuta: str) -> list[str]:
    """Retorna os modelos de minutas."""
    caminho_padrao = (
        get_caminho_minutas_padrao()
    )  # Supõe-se que isso retorne um objeto Path
    dir_origem = (
        caminho_padrao / diretorio_minuta
    )  # Uso do operador / para unir caminhos

    # Garantindo que dir_origem seja um Path para usar o método .glob() ou equivalente
    if not isinstance(dir_origem, Path):
        dir_origem = Path(dir_origem)

    return [arquivo.stem for arquivo in dir_origem.glob("*.docx")]


def retornar_nomes(diretorio, extensao):
    """Retorna os nomes dos arquivos com a extensão especificada em um diretório."""
    return [
        arquivo for arquivo in os.listdir(diretorio) if arquivo.endswith("." + extensao)
    ]


def get_arquivos_de_minutas(tipo: "TipoRegistro", pasta: str = "") -> list[str]:
    from apps.home.tipos import TipoRegistro

    try:
        if tipo in [TipoRegistro.AVERBACAO, TipoRegistro.MATRICULA]:
            return get_lista_modelos_minuta(pasta)

        return []
    except Exception:
        logger.exception("ERRO")
        return []


def get_lotes_pelo_imovel(imovel_id=0) -> QuerySet:
    from apps.home.models import Lote, Unidade

    # FIltrando as unidades
    unidade = Unidade.objects.filter(imovel_id=imovel_id).first()
    return Lote.objects.filter(unidade_id=unidade.pk)


def get_quantidade_de_lotes_no_loteamento(imovel_id) -> int:
    from apps.home.models import Lote, Unidade

    unidades = Unidade.objects.filter(imovel_id=imovel_id)
    return Lote.objects.filter(unidade__in=unidades).count()


def get_unidades_do_condominio_pelo_imovel(imovel_id) -> QuerySet:
    from apps.home.models import FichaAuxiliar, Unidade

    if imovel_id:
        ficha_auxiliar = FichaAuxiliar.objects.get(id=imovel_id)
        registro_anterior = ficha_auxiliar.unidade_id
        return Unidade.objects.filter(registro_anterior=registro_anterior)
    else:
        return Unidade.objects.none()


def get_quantidade_de_unidades_no_condominio(imovel_id=0) -> int:
    from apps.home.models import FichaAuxiliar, Unidade

    if not imovel_id or imovel_id == 0:
        return 0

    try:
        ficha = FichaAuxiliar.objects.get(id=imovel_id)
        if ficha.unidade_id > 0:
            return Unidade.objects.filter(registro_anterior=ficha.unidade_id).count()
        return 0
    except FichaAuxiliar.DoesNotExist:
        return 0


# Retornar o camino da minuta
def get_caminho_minutas_padrao(tipo_registro=TipoRegistro.MATRICULA, subpasta=""):
    caminho_minutas = staticfiles_storage.path("ged/minutas/")

    if tipo_registro == TipoRegistro.AVERBACAO:
        caminho_minutas = (
            Path(caminho_minutas) / settings.NOME_PASTA_MINUTA_LIVRO03 / subpasta
        )
    elif tipo_registro == TipoRegistro.MATRICULA:
        caminho_minutas = (
            Path(caminho_minutas)
            / str(settings.NOME_PASTA_MINUTA_LIVRO02)
            / str(subpasta)
        )
    else:
        caminho_minutas = ""

    return caminho_minutas


def get_prazo_do_pedido_em_dias(pedido_id, opcao="P", tipo_data="S") -> None:
    from apps.home.models import Pedido

    pedido = Pedido.objects.get(pk=pedido_id)

    pedido.get_prazo_em_dias(opcao)


def get_documento_path(self, filename):
    # Extrai a extensão do arquivo original
    ext = filename.split(".")[-1] or ".pdf"

    # Gera um nome de arquivo com um timestamp
    filename = f"{self.usuario.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"

    # Define o caminho dentro do diretório MEDIA_ROOT onde o arquivo será salvo
    return Path("documentos_assinados") / filename


def formatar_codigo_seguranca(numero) -> str:
    from core.utils.formatacoes import somente_numeros

    numero = somente_numeros(numero)

    return numero[0:4] + "." + numero[4:8] + "." + numero[8:12] + "." + numero[12:16]


# def formatar_numero_registro(numero_registro):
#     if not numero_registro:
#         return ""

#     if len(numero_registro) <= 3:
#         return numero_registro

#     return numero_registro[:-3] + "." + numero_registro[-3:]


def formatar_protocolo(numero):
    # Verifica se o número já está no formato desejado usando uma expressão regular
    if re.match(r"^\d{3}\.\d{3}$", str(numero)):
        # Se já está no formato desejado, retorna o número como está
        return numero

    try:
        # Tenta converter o número para um inteiro, descartando qualquer coisa após o ponto
        numero_inteiro = int(str(numero).split(".")[0])
    except ValueError:
        # Em caso de falha na conversão (por exemplo, string não numérica), define o número como 0
        numero_inteiro = 0

    # Formata o número com 3 dígitos antes e depois do ponto, preenchendo com zeros à esquerda
    return f"{numero_inteiro // 1000:03d}.{numero_inteiro % 1000:03d}"


# Configurar logging


def retirar_caracteres_string(variavel):
    variavel = variavel.replace("None", "0")
    variavel = variavel.replace("(Decimal('", "")
    variavel = variavel.replace("'),)", "")
    return variavel.replace(".00", "")


def get_numeros_inteiro(variavel):
    resultado = re.search(r"\d+", variavel)
    if resultado:
        return int(resultado.group())

    msg = f"Nenhum número inteiro encontrado em: {variavel}"
    raise ValueError(msg)


def retornar_estado(numero):
    """Converte o número do estado em seu nome correspondente."""
    from apps.comum.models import UnidadeFederativa

    return UnidadeFederativa.retornar_estado(numero)


# Limpar espaco em branco
def retirar_espaco_em_branco(variavel):
    return variavel.strip()


# Retornar ARQUIVO COM EXTENSAO, ARQUIVO SEM EXTENSAO, EXTENSAO
def retonar_nome_e_extensao(arquivo) -> tuple:
    arquivo_com_extensao = os.path.split(os.path.abspath(arquivo))[1]
    arquivo_sem_extensao = os.path.splitext(arquivo_com_extensao)[0]
    extensao = os.path.splitext(arquivo_com_extensao)[1]

    return arquivo_com_extensao, arquivo_sem_extensao, extensao


def retornar_nome(diretorio, extensao):
    """
    Retorna uma lista de nomes de arquivos no diretório especificado, que possuem a extensão especificada.

    Args:
    ----
        diretorio (str): O diretório em que procurar arquivos.
        extensao (str): A extensão de arquivo para procurar.

    Returns:
    -------
        list: Uma lista de nomes de arquivos que correspondem à extensão especificada.

    """
    # Garantindo que a extensão não comece com um ponto
    extensao = extensao.lstrip(".")

    # Construindo o padrão de busca
    pattern = Path(diretorio) / f"*.{extensao}" if diretorio else f"*.{extensao}"

    return Path.glob(pattern)


# Retornar apenas os numeros de uma string
def get_apenas_numeros(numero) -> str:
    from core.utils.formatacoes import somente_numeros

    return somente_numeros(numero)


def formatar_codigo_seguranca_mg(numero, separador) -> str:
    """
    Formata o código de segurança para o padrão SELO DIGITAL MG.

    Por exemplo: '3803073247377028' com o separador '.' retorna '3803.0732.4737.7028'.

    Args:
    ----
        numero (str): Número de segurança original.
        separador (str): Separador a ser utilizado entre os blocos do código.

    Returns:
    -------
        str: Número de segurança formatado.

    """
    numero = formatar_inteiro_como_string(numero, 16)
    return f"{numero[:4]}{separador}{numero[4:8]}{separador}{numero[8:12]}{separador}{numero[12:]}"


def formatar_inteiro_como_string(numero, tamanho):
    """
    Formata um número inteiro como string, preenchendo com zeros à esquerda até alcançar o tamanho especificado.

    Args:
    ----
        numero (str/int): Número original.
        tamanho (int): Tamanho desejado da string resultante.

    Returns:
    -------
        str: Número formatado com zeros à esquerda.

    """
    return str(numero).zfill(tamanho)


# Formatar inteiro
def formatar_numero_registro(numero_registro, separador=","):
    if not numero_registro:
        return ""

    numero_registro = str(numero_registro)

    if len(numero_registro) <= 3:
        return numero_registro

    numero_registro = str(numero_registro)  # Convert s to string

    return (
        separador
        if len(separador) <= 3
        else formatar_numero_registro(separador[:-3], separador)
        + separador
        + separador[-3:]
    )


# Formatar masccara CPF
def formatar_cnpj(cnpj) -> str:
    return f"{cnpj[0:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


# Formatar masccara CPF
def formatar_cpf(cpf) -> str:
    return f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"


def formatar_cns(cns) -> str:
    if not cns:
        return ""
    # formato: 00.000-0
    # Total de 6 digitos com zeros a esquerda
    cns = cns.zfill(6)
    return f"{cns[0:2]}.{cns[2:5]}-{cns[5]}"


# Mes por extenso
def get_mes(mes):
    mes_ext = {
        1: "janeiro",
        2: "fevereiro",
        3: "março",
        4: "abril",
        5: "maio",
        6: "junho",
        7: "julho",
        8: "agosto",
        9: "setembro",
        10: "outubro",
        11: "novembro",
        12: "dezembro",
    }
    return mes_ext[int(mes)]


# print(convert_string_to_date_and_add_months("09/11/2020", settings.DATE_FORMAT_STR, 0))
def convert_string_to_date_and_add_months(
    date_string: str,
    date_formatter: str,
    months_to_add: int,
) -> tuple:
    """
    Converte uma string de data para um objeto datetime, adiciona uma quantidade especificada de meses
    e retorna várias representações dessa data futura.

    Parâmetros:
    - date_string (str): A string da data para converter.
    - date_formatter (str): O formato da string da data, conforme esperado pelo strptime.
    - months_to_add (int): A quantidade de meses para adicionar à data.

    Retorna:
    - Tuple: Um objeto datetime representando a data futura e várias strings formatadas
      representando diferentes aspectos dessa data (ano, mês, dia, etc.).
    """
    today_start = datetime.strptime(date_string, date_formatter).astimezone()
    add_months = relativedelta(months=months_to_add)
    future_start = today_start + add_months

    day_of_week_full = future_start.strftime("%A")  # Nome completo do dia da semana.
    day_of_week_short = future_start.strftime("%a")  # Nome abreviado do dia da semana.
    day_of_week_number = future_start.strftime("%w")  # Número do dia da semana.
    day_of_month_number = future_start.strftime("%d")  # Dia do mês.
    month_name_short = future_start.strftime("%b")  # Nome abreviado do mês.
    month_number = future_start.strftime("%m")  # Número do mês.
    month_name_full = future_start.strftime("%B")  # Nome completo do mês.
    year_2_digits = future_start.strftime("%y")  # Ano com dois dígitos.
    year_4_digits = future_start.strftime("%Y")  # Ano com quatro dígitos.

    return (
        future_start,
        year_4_digits,
        month_number,
        day_of_month_number,
        year_2_digits,
        day_of_week_short,
        day_of_week_full,
        day_of_week_number,
        month_name_short,
        month_name_full,
    )


# Formatar Valor Monetario
def real_br_money_mask(value):
    from core.utils.formatacoes import formatar_valor_real_br

    return formatar_valor_real_br(value)


# Escrever o valor por extenso


def valor_por_extenso(valor):
    """
    Converte um valor numérico para sua representação por extenso em reais e centavos.

    Args:
    ----
        valor (str): Valor numérico em formato string (por exemplo, "1.234,56").

    Returns:
    -------
        str: Valor por extenso em reais e centavos.

    """
    # Divide o valor em partes inteira e fracionária

    # converte valor para string
    valor = str(valor)

    if "," in valor:
        parte_inteira, parte_fracionaria = valor.split(",")
        parte_inteira = int(parte_inteira.replace(".", ""))
        parte_fracionaria = int(parte_fracionaria)
    else:
        parte_inteira = int(valor.replace(".", ""))
        parte_fracionaria = 0

    # Converte as partes para extenso
    extenso_inteira = num2words(parte_inteira, lang="pt_BR") + (
        " real" if parte_inteira == 1 else " reais"
    )
    extenso_fracionaria = num2words(parte_fracionaria, lang="pt_BR") + (
        " centavo" if parte_fracionaria == 1 else " centavos"
    )

    # Combina as partes convertidas, se necessário
    if parte_inteira > 0 and parte_fracionaria > 0:
        return f"{extenso_inteira} e {extenso_fracionaria}"

    if parte_inteira > 0:
        return extenso_inteira

    if parte_fracionaria > 0:
        return extenso_fracionaria

    return "zero reais"


def formatar_variavel(valor_variavel, mascara):
    from apps.home.templatetags.home_formatos import formatar_numero_registro

    """
    Formata a variável conforme o padrão informado.

    Args:
        valor_variavel: Valor original da variável.
        mascara (str): O formato desejado.

    Returns:
        str: Valor da variável formatado.
    """

    # Mapeamento das máscaras para as respectivas funções de formatação
    formatadores = {
        "VALORFINANCEIRO": formatar_valor_financeiro,
        "VALOR": formatar_valor,
        "VALOREXTENSO": formatar_valor_extenso,
        "NUMERO": retornar_estado_do_registro,
        "NUMEROMATRICULA": formatar_numero_registro,
        "NUMEROEXTENSO": formatar_por_extenso,
        "NUMERAL": formatar_numeral,
        "dd/mmmm/yyyy": formatar_data_extenso,
        "dd/mm/yyyy": formatar_data_str,
        "CODSEGURANCAMG": formatar_codigo_seguranca,
    }

    # Obtenha a função de formatação com base na máscara e aplique-a ao valor, se presente
    formatador = formatadores.get(mascara)
    if formatador:
        return formatador(valor_variavel)

    return valor_variavel  # Retorne o valor original se nenhuma condição corresponder


def formatar_valor_financeiro(valor):
    valor = valor.replace(",", "")
    try:
        return real_br_money_mask(valor)
    except Exception:
        logger.exception("ERRO")
        return valor


def formatar_valor(valor):
    try:
        return real_br_money_mask(valor)
    except Exception:
        logger.exception("ERRO")
        return valor


def retirar_espacos_extras(texto: str) -> str:
    texto = texto.replace("  ", " ")
    texto = texto.replace("( ", "(")
    # Supondo que retirar_espaco_em_branco seja uma função definida que retire espaços extras
    return retirar_espaco_em_branco(texto)


def formatar_valor_extenso(valor: str) -> str:
    # valor_formatado = numero_por_extenso.monetario(valor)
    valor_formatado = formatar_por_extenso(valor)
    return retirar_espacos_extras(valor_formatado)


def retornar_estado_do_registro(numero, formato="."):
    # print(Numero)
    numero = formatar_inteiro_como_string(numero, 6)
    return numero[0:3] + formato + numero[3:6]


def formatar_por_extenso(valor):
    return valor_por_extenso(get_apenas_numeros(valor))


def formatar_numeral(valor):
    try:
        return num2words(get_apenas_numeros(valor), lang="pt-br", to="ordinal")
    except Exception:
        logger.exception("ERRO")
        return valor


def formatar_data_extenso(date_string):
    try:
        ano = convert_string_to_date_and_add_months(
            date_string,
            settings.DATE_FORMAT_STR,
            0,
        )[1]
        mes = convert_string_to_date_and_add_months(
            date_string,
            settings.DATE_FORMAT_STR,
            0,
        )[2]
        dia = convert_string_to_date_and_add_months(
            date_string,
            settings.DATE_FORMAT_STR,
            0,
        )[3]
        return dia + " de " + get_mes(mes) + " de " + ano
    except Exception:
        logger.exception("ERRO")
        return date_string


def exibir_data_extenso(data: datetime) -> str:
    try:
        return str(data.day) + " de " + get_mes(data.month) + " de " + str(data.year)
    except Exception:
        logger.exception("ERRO")
        return data


def formatar_data_str(data, opcao="0") -> str:
    if opcao == "1":
        ano, mes, dia = data.split(" ")[0].split("-")
    else:
        dia, mes, ano = data.split(" ")[0].split("-")

    return f"{dia}/{mes}/{ano}"


# Formatar a variavel conforme o padrao informado. Ex. datas dd/mm/yyy
# def formatar_variavel_old(valor_variavel, mascara):
#     mascara = str(mascara)

#     if mascara == "VALORFINANCEIRO":
#         valor_variavel = str(valor_variavel.replace(",", ""))

#         try:
#             valor_variavel = real_br_money_mask(valor_variavel)
#         except Exception:
#             logger.exception("ERRO")
#             valor_variavel = valor_variavel

#     if mascara == "VALOR":
#         try:
#             valor_variavel = real_br_money_mask(valor_variavel)
#         except Exception:
#             logger.exception("ERRO")
#             valor_variavel = valor_variavel

#     if mascara == "VALOREXTENSO":
#         # valor = numero_por_extenso.monetario(valor_variavel)
#         valor = formatar_por_extenso(valor_variavel)
#         valor = valor.replace("  ", " ")
#         valor = valor.replace("( ", "(")
#         valor = retirar_espaco_em_branco(valor)

#         # print("xxx", valor)
#         valor_variavel = valor

#     # Retornar numero igual um protocolo
#     if mascara == "NUMERO":
#         valor_variavel = retornar_estado_do_registro(valor_variavel, ".")

#     # Retornar numero igual um protocolo
#     if mascara == "NUMEROMATRICULA":
#         try:
#             valor_variavel = formatar_numero_registro(valor_variavel, ".")
#             valor_variavel = valor_variavel.replace("..", ".")
#         except Exception:
#             logger.exception("ERRO")
#             valor_variavel = valor_variavel

#     # Retornar o numero por extenso
#     if mascara == "NUMEROEXTENSO":
#         # print(valor_variavel, mascara)

#         valor_variavel = valor_por_extenso(get_apenas_numeros(valor_variavel))

#     # Escrevendo número ordinal por extenso
#     if mascara == "NUMERAL":
#         try:
#             num_ptbr_ord = num2words(
#                 get_apenas_numeros(valor_variavel),
#                 lang="pt-br",
#                 to="ordinal",
#             )

#             # Formato a retornar " primeiro"
#             valor_variavel = num_ptbr_ord
#         except Exception:
#             logger.exception("ERRO")

#     # Data por extenso
#     if mascara == "dd/mmmm/yyyy":
#         try:
#             ano = convert_string_to_date_and_add_months(
#                 valor_variavel,
#                 settings.DATE_FORMAT_STR,
#                 0,
#             )[1]
#             mes = convert_string_to_date_and_add_months(
#                 valor_variavel,
#                 settings.DATE_FORMAT_STR,
#                 0,
#             )[2]
#             dia = convert_string_to_date_and_add_months(
#                 valor_variavel,
#                 settings.DATE_FORMAT_STR,
#                 0,
#             )[3]

#             # Formato a retornar " 21 de março e 2021"
#             valor_variavel = dia + " de " + get_mes(mes) + " de " + ano
#         except Exception:
#             logger.exception("ERRO")

#     # Data padrao
#     if mascara == "dd/mm/yyyy":
#         data = str(valor_variavel).split(" ")[0]
#         valor_variavel = str(data).split("-")[2] + "/" + str(data).split("-")[1] + "/" + str(data).split("-")[0]

#     # Codigo Seguranca MG
#     if mascara == "CODSEGURANCAMG":
#         valor_variavel = formatar_codigo_seguranca_mg(str(valor_variavel), ".")

#     return valor_variavel


# Alterar formatacao em texto especifico - Verificar se o texto da qualificacao (MAIUSCULA, minuscula, Letra)
def formatar_texto(inicio, fim, txt, opcao):
    """
    Altera a formatação de um trecho específico do texto.

    Args:
    ----
        inicio (str): Delimitador inicial para identificar o texto a ser formatado.
        fim (str): Delimitador final para identificar o fim do texto a ser formatado.
        txt (str): Texto completo onde a formatação será aplicada.
        opcao (str):
            "1" para converter o texto em minúsculas,
            "2" para maiúsculas,
            "3" para capitalizar cada palavra.

    Returns:
    -------
        str: Texto com a formatação alterada.

    """

    # Função auxiliar para aplicar a formatação desejada
    def aplicar_formatacao(texto: str, opcao: str) -> str:
        if opcao == "1":
            return texto.lower()

        if opcao == "2":
            return texto.upper()

        if opcao == "3":
            return texto.title()

        return texto

    # Localizando todos os trechos do texto entre os delimitadores especificados
    padrao = re.compile(f"{re.escape(inicio)}(.*?){re.escape(fim)}")
    trechos = padrao.findall(txt)

    # Iterando sobre os trechos encontrados e aplicando a formatação
    for trecho in trechos:
        txt = txt.replace(f"{inicio}{trecho}{fim}", aplicar_formatacao(trecho, opcao))

    return txt


# Verificar se o ITEM nao esta VAZIO
def verificar_item_vazio(item, opcao):
    if str(item) == "":
        if opcao == "1":
            return "OBRIGATORIO"
        return "NAO INFORMADO"
    return item


# logger.info(formatar_variavel( str('1547250.00'),  str('VALOREXTENSO')))


def formatar_cnm(numero_cnm: str) -> str:
    if not numero_cnm:
        return ""

    parte1 = numero_cnm[:6]
    parte2 = numero_cnm[6:7]
    parte3 = numero_cnm[7:14]
    parte4 = numero_cnm[14:]

    # Junta as partes no novo formato
    return f"{parte1}.{parte2}.{parte3}-{parte4}"


MES_DO_ANO = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

NOME_PARA_NUMERO_MES = {nome.lower(): numero for numero, nome in MES_DO_ANO.items()}


# RETIRAR DADOS MONETARIOS
def retirar_dados_valor_monetario(value):
    return value.replace("R$", "").replace(".", "").replace(",", ".").replace(" ", "")


def convert_char_to_int(apps, schema_editor) -> None:
    auxiliar_garantia = apps.get_model("home", "auxiliar_garantias")
    print(auxiliar_garantia)

    for instance in auxiliar_garantia.objects.all():
        print(instance.campo_char)

        try:
            # Converta o valor do campo_char para um inteiro e armazene em campo_int_temp
            instance.campo_int_temp = int(instance.campo_char)
            instance.save()
        except ValueError:
            logger.exception("ERRO")
            # Caso não seja possível converter, você pode definir um valor padrão
            # ou simplesmente pular a instância (como estamos fazendo aqui)


def get_data_util_em_x_dias(data: date | None = None, dias=20) -> date:
    """
    Calcula a próxima data útil a partir de uma data dada, adicionando um número específico de dias úteis.

    Args:
    ----
        data (date): A data inicial a partir da qual o cálculo será feito.
        dias (int): O número de dias úteis a serem adicionados à data inicial. Valor padrão é 20.

    Returns:
    -------
        date: A data útil resultante após adicionar o número especificado de dias úteis.

    """
    from apps.comum.utils import CalendarioBrasileiroPersonalizado

    if not data:
        data = timezone.now().date()
    calendario = CalendarioBrasileiroPersonalizado()
    return calendario.add_working_days(data, dias)


def retornar_estado_do_registro_imagem(numero):
    """
    Formata um número para ter 6 dígitos, preenchendo com zeros à esquerda se necessário.

    Args:
    ----
        numero (int): O número a ser formatado.

    Returns:
    -------
        str: O número formatado com 6 dígitos.

    """
    return str(numero).zfill(6)


# Retornar a pasta da imagem
def formatar_subpasta(opcao):
    """
    Formata o valor fornecido para um padrão de nomenclatura de subpasta.

    Args:
    ----
        opcao: Um valor numérico que será formatado.

    Returns:
    -------
        str: Uma string representando os três primeiros dígitos do valor fornecido,
             completado com zeros à esquerda para alcançar pelo menos seis dígitos.

    """
    temp = str(opcao).zfill(6)
    return temp[:3]


# Retornar a pasta da imagem
def get_pasta_de_imagem_pelo_tipo(letra_tipo_registro="M") -> str:
    if letra_tipo_registro == "A":
        return "RAuxiliar"

    return "Matriculas"


# Retornar o caminho da pasta e do arquivo
def get_caminho_do_arquivo(letra_tipo_registro, pk):
    from apps.home.models import Configuracao

    caminho = Configuracao.obter("diretorio_ged_imagens")

    pasta = get_pasta_de_imagem_pelo_tipo(letra_tipo_registro)
    numero = Path(formatar_subpasta(pk)) / retornar_estado_do_registro_imagem(id)
    path_dir = Path(caminho) / pasta / numero

    print("Comandos: Caminho imagem: ", path_dir)

    return path_dir


def get_meses_do_ano() -> dict:
    # Apenas retorna o dicionário já definido.
    return MES_DO_ANO


def get_numero_do_mes(nome: str) -> int:
    """
    Retorna o número do mês com base no nome fornecido.

    Args:
    ----
        nome (str): Nome do mês.

    Returns:
    -------
        int: Número do mês.

    """
    # Busca diretamente no dicionário invertido.
    return NOME_PARA_NUMERO_MES.get(nome.lower(), 0)


def get_nome_do_mes_pelo_numero(numero: int) -> str:
    """
    Retorna o nome do mês com base no número fornecido.

    Args:
    ----
        numero (int): Número do mês.

    Returns:
    -------
        str: Nome do mês.

    """
    return MES_DO_ANO.get(numero, "")


def formatar_data(data, opcao) -> str:
    """
    Formata a data de acordo com a opção especificada.

    Args:
    ----
        data (str): A data no formato 'YYYY-MM-DD'.
        opcao (int): A opção desejada para o formato de data.
                     - Opção 1: Formato 'DD/MM/YYYY'.
                     - Opção 2: Formato 'DD de Mês de Y'.
                     - Opção 3: Formato 'D/M/YYYY'.

    Returns:
    -------
        str: A data formatada conforme a opção escolhida.

    """
    if data is None:
        return ""

    lista_meses = get_meses_do_ano()

    if opcao == 2:
        dia_temp = str(data[0:2])
        mes_temp = lista_meses[int(data[3:5])]
        ano_temp = str(data[6:10])
    else:
        dia_temp = str(data[8:10])
        mes_temp = lista_meses[int(data[5:7])]
        ano_temp = str(data[0:4])

    if opcao == 1:
        return f"{dia_temp}/{mes_temp}/{ano_temp}"

    if opcao == 2:
        return f"{dia_temp} de {mes_temp} de {ano_temp[0]}.{ano_temp[1:]}"

    if opcao == 3:
        return f"{dia_temp}/{mes_temp}/{ano_temp}"

    return ""


def get_data_e_hora_por_opcao(opcao) -> str:
    """
    Obtém a data e hora atual em um formato específico, dependendo da opção fornecida.

    Args:
    ----
        opcao (int): A opção desejada para o formato de data e hora.
                     - Opção 1: Formato "31 de dezembro de 2022".
                     - Opção 2: Formato "31/09/2022".

    Returns:
    -------
        str: A data e hora formatada conforme a opção escolhida.

    """
    lista_meses = get_meses_do_ano()

    hoje = timezone.now().date()

    if opcao == 1:
        return f"{hoje.day:02d} de {lista_meses[hoje.month]} de {hoje.year}"

    if opcao == 2:
        return f"{hoje.day:02d}/{hoje.month:02d}/{hoje.year}"

    if opcao == 3:  # formato "YYYY-MM-DD"
        return f"{hoje.year}-{hoje.month:02d}-{hoje.day:02d}"

    return ""


# Obtenção de data e hora por nome
def data_atual_opcoes():
    # agora = time.localtime()
    hj = timezone.now().date()

    return hj.day, hj.month, hj.year


# Formatar Codigo de Seguranca - 3101 3559 7678 4633
# def formatar_codigo_seguranca(numero):
#     numero = get_apenas_numeros(numero)

#     return numero[0:4] + "." + numero[4:8] + "." + numero[8:12] + "." + numero[12:16]


def gerar_remetentes(texto):
    """
    Gera uma lista de remetentes a partir de uma string de texto separada por vírgulas.

    Args:
    ----
        texto (str): A string de texto contendo os remetentes separados por vírgulas.

    Returns:
    -------
        list: Uma lista de remetentes.

    """
    return [item.strip() for item in texto.split(",")]


# Exemplo de uso:
# remetentes = gerar_remetentes('Remetente 1, Remetente 2, Remetente 3')


# Gerar um frame atraves de lista
def gerar_frame_list():
    vendas = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    index = gerar_datas_a_partir_de("12/01/2021", 10)
    data_frame = pd.DataFrame(vendas, index, columns=["Vendas Diarias"])

    print("As 5 primeiras linhas: ", data_frame.head())  # As 5 primeiras linhas
    # Descrer principais itens
    print("Descrever principais itens: ", data_frame.describe())
    print("Medias das vendas: ", data_frame.mean())  # Medias das vendas
    print("Desvio padrao das vendas: ", data_frame.std())  # Desvio padrao das vendas
    print("Variancia das vendas: ", data_frame.var())  # Variancia das vendas
    # Desvio absoluto das vendas
    print("Desvio absoluto das vendas: ", data_frame.mad())
    print("Venda maxima: ", data_frame.max())  # Venda maxima
    print("Dia da Venda maxima: ", data_frame.idxmax())  # Dia da Venda maxima
    print("Venda minima: ", data_frame.min())  # Venda minima
    print("Dia da Venda minima: ", data_frame.idxmin())  # Dia da Venda minima

    return data_frame


def gerar_datas_a_partir_de(data_inicial, periodo):
    """
    Gera uma lista de datas a partir de uma data inicial e um período.

    Args:
    ----
        data_inicial (str): A data inicial no formato 'dd/mm/yyyy'.
        periodo (int): O número de dias a serem gerados.

    Returns:
    -------
        pandas.core.indexes.datetimes.DatetimeIndex: Uma lista de datas.

    """
    return pd.date_range(start=data_inicial, periods=periodo)


# Exemplo de uso:
# datas_geradas = gerar_datas_a_partir_de('12/01/2021', 10)


def apenas_numeros(numero):
    return re.sub("[^0-9]", "", numero)


# Executando o zipar de um arquivo pelo nome dele - print(zip_file_by_name('C:/TESTE.WORD'))
def zip_file_by_name(file_name):
    # File name to zip
    zip_file_name = file_name + ".rar"

    # Zip the file
    with zipfile.ZipFile(zip_file_name, "w") as zip_file:
        zip_file.write(file_name, compress_type=zipfile.ZIP_DEFLATED)

    return zip_file_name


# # Retornar ARQUIVO COM EXTENSAO, ARQUIVO SEM EXTENSAO, EXTENSAO
# def retonar_nome_e_extensao(Arquivo):
#     ArquivoComExtensao = os.path.split(os.path.abspath(Arquivo))[1]
#     ArquivoSemExtensao = os.path.splitext(ArquivoComExtensao)[0]
#     Extensao = os.path.splitext(ArquivoComExtensao)[1]

#     return ArquivoComExtensao, ArquivoSemExtensao, Extensao
#     """ Passo (D:\Helder\Q2 - 302F - R03.xlsm) e recebo:
#     Q2 - 302F - R03.xlsm
#     Q2 - 302F - R03
#     .xlsm
#     """


def retornar_nome_arquivo_e_extensao(arquivo):
    """
    Retorna o nome do arquivo com extensão, o nome do arquivo sem extensão e a extensão do arquivo.

    Args:
    ----
        arquivo (str): O caminho do arquivo.

    Returns:
    -------
        tuple: Uma tupla contendo o nome do arquivo com extensão, o nome do arquivo sem extensão e a extensão do arquivo.

    """
    arquivo_com_extensao = os.path.basename(os.path.abspath(arquivo))
    arquivo_sem_extensao, extensao = os.path.splitext(arquivo_com_extensao)

    return arquivo_com_extensao, arquivo_sem_extensao, extensao


def converter_string_para_data(data_string, formato_data, meses_a_adicionar):
    """
    Converte uma string para um objeto de data, adiciona uma quantidade especificada de meses e retorna detalhes formatados da data.

    Args:
    ----
        data_string (str): A string contendo a data.
        formato_data (str): O formato da data na string.
        meses_a_adicionar (int): A quantidade de meses a ser adicionada à data.

    Returns:
    -------
        tuple: Uma tupla contendo:
            - A data futura como um objeto datetime.
            - Ano com 4 dígitos.
            - Mês como número com dois dígitos.
            - Dia do mês como número com dois dígitos.
            - Ano com 2 dígitos.
            - Dia da semana como nome abreviado.
            - Dia da semana como nome completo.
            - Dia da semana como número.
            - Mês como nome abreviado.
            - Mês como nome completo.

    """
    data_inicial = datetime.datetime.strptime(data_string, formato_data)
    data_futura = data_inicial + relativedelta(months=meses_a_adicionar)

    detalhes_data = {
        "Ano_4digito": data_futura.strftime("%Y"),
        "Mes_com_Nro": data_futura.strftime("%m"),
        "Dia_do_mes_Nro": data_futura.strftime("%d"),
        "Ano_2digito": data_futura.strftime("%y"),
        "Dia_da_semana": data_futura.strftime("%a"),
        "Dia_da_semanacompleto": data_futura.strftime("%A"),
        "Dia_da_semana_Nro": data_futura.strftime("%w"),
        "Dia_do_mes_Nome": data_futura.strftime("%b"),
        "Mes_com_Nome": data_futura.strftime("%B"),
    }

    return (data_futura, *detalhes_data.values())


# Exemplo de uso:
# data_futura, ano_4digito, mes_com_nro, dia_do_mes_nro, ano_2digito, dia_da_semana, dia_da_semanacompleto, dia_da_semana_nro, dia_do_mes_nome, mes_com_nome = converter_string_para_data("09/11/2020", settings.DATE_FORMAT_STR, 0)


# # Adicionar meses a data atual
# # print(AdicionarMesDataAtual("09/11/2020", 1)[1])
# def AdicionarMesDataAtual(DataInicio, mesadicionar):
#     today = DataModuloGeral.timezone.now().date()
#     addMonths = relativedelta(months=mesadicionar)
#     future = today + addMonths
#     return (
#         future,
#         future.year,
#         future.month,
#         future.day,
#         today,
#         today.year,
#         today.month,
#         today.day,
#     )


def adicionar_meses_a_data(data_inicio, meses_a_adicionar):
    """
    Adiciona uma quantidade especificada de meses à data fornecida.

    Args:
    ----
        data_inicio (date): A data inicial a partir da qual os meses serão adicionados.
        meses_a_adicionar (int): O número de meses a serem adicionados à data inicial.

    Returns:
    -------
        tuple: Uma tupla contendo:
            - A data futura após a adição dos meses.
            - O ano, mês e dia da data futura.
            - A data inicial.
            - O ano, mês e dia da data inicial.

    """
    adicionar_meses = relativedelta(months=meses_a_adicionar)
    data_futura = data_inicio + adicionar_meses

    return (
        data_futura,
        data_futura.year,
        data_futura.month,
        data_futura.day,
        data_inicio,
        data_inicio.year,
        data_inicio.month,
        data_inicio.day,
    )


# Horario e data do dia
def data_atual():
    return timezone.now().date()


def data_e_hora_atuais():
    return timezone.now()


# Passando o caminho do dir e tipo de extensao que quero - usando o GLOB


# Retonar nome da pasta anterior
def get_nome_diretorio_anterior(caminho):
    return os.path.abspath(os.path.dirname(caminho))
    # os.path.abspath(os.path.dirname("E:/ServidorFtp/Database"))
    # E:\ServidorFtp


def garantir_diretorio_existe(path) -> None:
    # Converter o caminho para um objeto Path se não for um
    path = Path(path) if not isinstance(path, Path) else path
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)


# Retornar a data por extenso
def data_atual_extenso():
    # LISTA DE OPCOES DE DATA
    list_opcoes = list(data_atual_opcoes())

    # Data com opcoes
    dia_temp = formatar_inteiro_como_string(str(list_opcoes[0]), 2)
    mes_temp = list_opcoes[1]
    ano_temp = formatar_inteiro_como_string(str(list_opcoes[2]), 2)

    # print(dia_temp, mes_temp, ano_temp)

    return (
        str(dia_temp)
        + " de "
        + str(mes_temp)
        + " de "
        + str(ano_temp)[0]
        + "."
        + str(ano_temp)[1:]
    )


# Valor do numero porExtenso
def limpar_valor_credito(valor_credito: str) -> str:
    """
    Limpa a string do valor de crédito, removendo caracteres indesejados e formatando o valor.

    :param valor_credito: Valor de crédito como string.
    :return: Valor de crédito limpo.
    """
    valor_limpo = valor_credito.replace("R$", "").strip()
    return valor_limpo.replace(".", "").replace(",", ".")


def gerar_valor_extenso(valor_credito: str) -> str:
    """
    Transforma um valor de crédito em sua representação extensa.

    :param valor_credito: Valor de crédito como string.
    :return: Valor de crédito formatado.
    """
    try:
        valor_credito = limpar_valor_credito(valor_credito)
        # valor_extenso = formatar_variavel(valor_credito, "VALOREXTENSO")
        valor_extenso = formatar_valor_extenso(valor_credito)
    except Exception:
        logger.exception("ERRO")
        valor_extenso = ""

    return valor_extenso


def excluir_arquivos(arquivos: list) -> None:
    for arquivo in arquivos:
        try:
            Path(str(arquivo)).unlink()
        except Exception:
            logger.exception("ERRO")


# Formatar masccara CPF
# def formatar_cnpj(cnpj: str) -> str:
#     if len(str(cnpj)) == 14:
#         return f"{cnpj[0:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"

#     return cnpj


# # Formatar masccara CPF
# def formatar_cpf(cpf: str) -> str:
#     if len(str(cpf)) == 11:
#         return f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"

#     return cpf


class Agora:
    @staticmethod
    def get_meses_do_ano() -> list:
        # Retorna uma lista com os nomes dos meses em português.
        return [
            "",
            "janeiro",
            "fevereiro",
            "março",
            "abril",
            "maio",
            "junho",
            "julho",
            "agosto",
            "setembro",
            "outubro",
            "novembro",
            "dezembro",
        ]

    @staticmethod
    def extenso() -> str:
        hoje = timezone.now().date()
        meses = Agora.get_meses_do_ano()
        return f"{hoje.day:02d} de {meses[hoje.month]} de {hoje.year}"

    @staticmethod
    def padrao() -> str:
        hoje = timezone.now().date()
        return f"{hoje.day:02d}/{hoje.month:02d}/{hoje.year}"

    @staticmethod
    def database() -> str:
        hoje = timezone.now().date()
        return f"{hoje.year}-{hoje.month:02d}-{hoje.day:02d}"


# # Exemplo de uso:
# print(Agora.extenso())  # Exemplo de saída: "25 de abril de 2024"
# print(Agora.padrao())  # Exemplo de saída: "25/04/2024"
# print(Agora.database())  # Exemplo de saída: "2024-04-25"


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


def data_formato_modelo_hora(data) -> str:
    """
    Converte uma data (que pode ser string ou objeto datetime) no formato "%Y-%m-%d %H:%M:%S"
    para "%d/%m/%y às %H:%M". Se a data for "01/01/1899" ou inválida, retorna uma string vazia.
    """
    if not data or data == "None":
        return ""

    # Se 'data' já for um objeto datetime, não precisa converter
    if not isinstance(data, datetime.datetime):
        try:
            data = datetime.datetime.strptime(data, settings.DATETIME_FIREBIRD_FORMAT)
        except ValueError:
            logger.exception(f"Data inválida: {data}")
            return ""

    formatar_data = data.strftime("%d/%m/%y às %H:%M")

    if formatar_data.startswith("01/01/1899"):
        return ""

    return formatar_data


def formatar_telefone(numero, pais="BR") -> str:
    """
    Formata um número de telefone de acordo com o padrão nacional do país especificado.

    Args:
    ----
        numero (str): O número de telefone a ser formatado.
        pais (str, optional): O código de duas letras do país para o qual o número de telefone deve ser formatado.
                               Padrão é "BR" para Brasil.

    Returns:
    -------
        str: Número de telefone formatado no padrão nacional.

    Raises:
    ------
        ValueError: Se o número de telefone fornecido for inválido ou não puder ser analisado.

    Examples:
    --------
        >>> formatar_telefone("+5511999998888")
        '(11) 99999-8888'

        >>> formatar_telefone("1234", "US")
        ValueError: Número de telefone inválido: 1234

    """
    telefone = phonenumbers.parse(numero, pais)
    if phonenumbers.is_valid_number(telefone):
        return phonenumbers.format_number(
            telefone,
            phonenumbers.PhoneNumberFormat.NATIONAL,
        )
    else:
        # adicione um traço para separar os ultimos 4 digitos
        return numero[: len(numero) - 4] + "-" + numero[-4:]


def mascarar_documento(documento) -> str:
    ## COMENTANDO POR HORA PARA NÃO DAR ERRO NOS OUTROS RELATORIOS
    # return documento

    if not documento:
        return "Documento não informado"

    tamanho = len(documento)

    if tamanho == 11:  # Se for CPF
        return f"{documento[:3]}.***.***-{documento[-2:]}"
        # return f"{documento[0:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:11]}"
    elif tamanho == 14:
        return f"{documento[:2]}.***.***.***/{documento[8:12]}-{documento[-2:]}"
        # return f"{documento[0:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:14]}"
    else:  # Se for outro tipo de documento
        inicio = documento[:2] if tamanho > 4 else documento[:1]
        fim = documento[-2:] if tamanho > 4 else documento[-1:]
        return f"{inicio}***{fim}"


def remover_linha_inicial_xml(xml_file):
    """Lê todo o conteúdo do arquivo XML e remove a primeira linha."""
    with open(xml_file, encoding="utf-8") as file:
        lines = file.readlines()

    # Remove a primeira linha
    lines = lines[1:]

    # Reescreve o arquivo sem a primeira linha
    with open(xml_file, "w", encoding="utf-8") as file:
        for line in lines:
            file.write(line)

    return xml_file  # Retorna o nome do arquivo atualizado


def remover_ultima_xml(xml_file):
    """Lê todo o conteúdo do arquivo XML e remove a primeira linha."""
    with open(xml_file, encoding="utf-8") as file:
        lines = file.readlines()

    # Remove a ultima linha
    lines = lines[:-1]

    # Reescreve o arquivo sem a primeira linha
    with open(xml_file, "w", encoding="utf-8") as file:
        for line in lines:
            file.write(line)

    return xml_file  # Retorna o nome do arquivo atualizado


def get_expediente(data):
    dia_da_semana = data.weekday()  # 0 para Segunda, 1 para Terça, etc.

    # Dicionário para mapear o dia da semana a um valor específico
    mapeamento_dias = {5: 2, 6: 1}  # Sábado mapeado para 5, Domingo para 6

    # Usar o método get para retornar o valor correspondente ao dia da semana, ou 0 se não for sábado ou domingo
    dias_uteis = mapeamento_dias.get(dia_da_semana, 0)

    data += timedelta(days=dias_uteis)

    return data


def formatos_de_datas():
    return ["%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]


# RETORNAR AS CUSTAS PARA O FIREBIRD
def get_custas_firebird(percentual_desconto, emolumento_id):
    from apps.home.models import Emolumentos, TipoTributacao
    from apps.pedidos.models import TipoEmolumento

    # PESQUISAR O CORRESPONDENTE PARA O SISTEMA ANTERIOR
    tipo_tributacao = TipoTributacao.objects.filter(
        percentual_desconto=percentual_desconto,
    ).first()

    if percentual_desconto and not tipo_tributacao:
        logger.warning(
            f"Tipo de tributação não encontrado: {percentual_desconto} - Procurando pelo percentual de desconto: {percentual_desconto}",
        )
        tipo_tributacao = TipoTributacao.objects.filter(
            percentual_desconto=percentual_desconto,
        ).first()

    if not tipo_tributacao:
        msg = f"Tipo de tributação não encontrado com o ID fornecido {percentual_desconto}."
        logger.error(
            f"Tipo de tributação não encontrado: {percentual_desconto} - Emolumento: {emolumento_id}",
        )
        raise ValueError(msg)

    tipoemolumento = TipoEmolumento.objects.filter(
        home_emolumento=emolumento_id,
    ).first()

    if tipoemolumento:
        emolumento_id = Emolumentos.objects.get_emolumentos_por_tributacao(
            tipoemolumento,
            tipo_tributacao,
        )

    custas_por_tipo = {100: 0, 50: 4, 75: 14, 1: 1}

    return custas_por_tipo, emolumento_id


# RETORNAR AS CUSTAS PARA O FIREBIRD
def replace_string_none(value):
    return str(value).replace("None", "")




def kwh_mes_por_placa(panel_watts: float, hsp: float, system_eff: float) -> float:
    return (panel_watts / 1000.0) * hsp * 30.0 * system_eff

def placas_necessarias(meta_kwh_mes: float, panel_watts: float, hsp: float, system_eff: float):
    prod_por_placa = kwh_mes_por_placa(panel_watts, hsp, system_eff)
    if prod_por_placa <= 0:
        return 0, 0.0, 0.0
    qnt = math.ceil(meta_kwh_mes / prod_por_placa)
    producao_prevista = qnt * prod_por_placa
    sobra = producao_prevista - meta_kwh_mes
    return qnt, producao_prevista, sobra

def ranquear_empresas(df: pd.DataFrame, pesos=None, filtros=None) -> pd.DataFrame:
    df_ = df.copy()
    filtros = filtros or {}
    pesos = pesos or {
        "preco_por_watt": 0.35,
        "garantia_anos": 0.20,
        "nota_servico": 0.25,
        "eficiencia_modulo": 0.20,
    }

    # filtros simples
    for col, (op, val) in filtros.items():
        if col not in df_.columns:
            continue
        if op == ">=":
            df_ = df_[df_[col] >= val]
        elif op == "<=":
            df_ = df_[df_[col] <= val]
        elif op == ">":
            df_ = df_[df_[col] > val]
        elif op == "<":
            df_ = df_[df_[col] < val]
        elif op == "==":
            df_ = df_[df_[col] == val]

    # normalização
    for c in ["preco_por_watt", "garantia_anos", "nota_servico", "eficiencia_modulo"]:
        if c in df_.columns and len(df_) > 0:
            cmin, cmax = df_[c].min(), df_[c].max()
            df_[f"{c}_norm"] = 0.5 if cmax == cmin else (df_[c] - cmin) / (cmax - cmin)
        else:
            df_[f"{c}_norm"] = 0.5

    preco_term = pesos.get("preco_por_watt", 0) * (1 - df_["preco_por_watt_norm"])  # menor é melhor
    garantia_term = pesos.get("garantia_anos", 0) * df_["garantia_anos_norm"]
    servico_term = pesos.get("nota_servico", 0) * df_["nota_servico_norm"]
    eficiencia_term = pesos.get("eficiencia_modulo", 0) * df_["eficiencia_modulo_norm"]

    df_["score"] = preco_term + garantia_term + servico_term + eficiencia_term
    cols_final = ["id", "nome", "preco_por_watt", "garantia_anos", "nota_servico", "eficiencia_modulo", "score"]
    # se não tiver 'id', ajusta
    cols_final = [c for c in cols_final if c in df_.columns or c == "score"]
    return df_.sort_values("score", ascending=False)[cols_final]
