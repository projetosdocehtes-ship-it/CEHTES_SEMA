import base64
import calendar
import configparser
import contextlib
import csv
import io
import json
import logging
import math
import mimetypes
import os
import platform
import random
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import uuid
import zipfile
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import django_tables2 as tables
import img2pdf
import matplotlib.pyplot as plt
import openai
import openpyxl
import pandas as pd
import pdfkit
import plotly.express as px
import requests
import xlwt
from bs4 import BeautifulSoup
from chartjs.views import HighChartsView
from django import template
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    SuspiciousOperation,
)
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import (
    DatabaseError,
    Error,
    IntegrityError,
    InterfaceError,
    InternalError,
    OperationalError,
    ProgrammingError,
    connection,
    models,
    transaction,
)
from django.db.models import (
    Count,
    F,
    IntegerField,
    Max,
    OuterRef,
    Q,
    Subquery,
    Sum,
)
from django.db.models.functions import Cast, Upper
from django.forms import ValidationError
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
    HttpResponseRedirect,
    HttpResponseServerError,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template import Context, Template, loader
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.views import FilterView
from django_tables2 import RequestConfig, SingleTableMixin
from django_tables2.export.export import TableExport
from openpyxl import Workbook
from PIL import Image
from rest_framework import filters as rest_filters
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from slugify import slugify

# from weasyprint import HTML
from apps.cartorios.models import Usuario as User
from apps.comum.helpers import ajustar_sequence
from apps.comum.models import AuditorIntegracao, TipoIntegracao
from apps.home import filters, forms, helpers, utils
from apps.home.filters import (
    EventColaboradorFilter,
    Livro01ProtocoloFilter,
    PedidoCertidaoFilter,
)
from apps.home.forms import (
    CriarBateriaForm,
    CriarHidrogenioForm,
    CriarInversorForm,
    CriarPainelForm,
    CriarPedidoCertidaoForm,
    CriarProjetoForm,
    PedidoCertidaoAnexoForm,
    ProjetoForm,
)
from apps.home.llm import ask_llm
from apps.home.models import (
    Anexo,
    Apresentante,
    AtoPratica,
    Bateria,
    Caixa,
    Certidao,
    CertificadoDigital,
    ChatRoom,
    ChecklistBalcao,
    ChecklistBalcaoAto,
    ChecklistBalcaoAtoTexto,
    CheckListRealizado,
    ChecklistRealizadoHistorico,
    Cidade,
    Colaborador,
    Configuracao,
    Emolumentos,
    EstadoCivil,
    Event,
    EventMember,
    FichaAuxiliar,
    Financeiro,
    FinanceiroPeriodicidade,
    Funcionario,
    Hidrogenio,
    ImovelMedida,
    Inversor,
    Lembrete,
    Livro01Andamento,
    Livro01Protocolo,
    Livro02,
    Livro02Texto,
    Livro03,
    Livro03Garantia,
    Livro03Ligacao,
    Livro04,
    Livro05,
    Lote,
    MinutaAuxiliar,
    ModeloTexto,
    MotivoAssinaturaDigital,
    NivelAlerta,
    NotaDevolucaoTexto,
    OrdemDigitalizarBalcaoAto,
    PainelSolar,
    PedidoCertidao,
    PedidoCertidaoAndamento,
    PedidoCertidaoAnexo,
    PedidoCertidaoImovel,
    PedidoCertidaoPessoa,
    PedidoItem,
    PedidoItemImovel,
    PedidoParte,
    PedidoParteAto,
    Pergunta,
    PerguntaGrupo,
    PerguntaMinuta,
    Projeto,
    RegistroVinculado,
    Rua,
    Rural,
    RuralNome,
    SeloEletronico,
    ServicoLivro01Historico,
    TipoAndamento,
    TipoAndamentoCertidao,
    TipoCategoriaFinanceira,
    TipoCertidao,
    TipoFaseProtocolo,
    TipoOperacaoFinanceira,
    TipoRegistroProtocolo,
    TipoTransacaoFinanceira,
    TipoTributacao,
    Titulo,
    Transacao,
    Unidade,
    Vinculo,
    get_regime_bens,
    get_user_id,
)
from apps.home.models.models_certidoes import ProjetoInversor, ProjetoPainelSolar
from apps.home.models.models_home import PerguntasIA, SeloEletronico
from apps.home.padroes import (
    MATRICULA_VISUALIZADA_ORIGEM_ID,
    ONR_CERTIDOES_A_EMITIR_ID,
    ONR_EPROTOCOLO_ID,
    SIM,
    VALOR_MAXIMO,
)
from apps.home.serializers import PedidoCertidaoImovelSerializer, ProtocoloSerializer
from apps.home.services import firebird, services
from apps.home.services.openai import analisar_texto_da_ficha
from apps.home.tables import (
    AndamentosExigenciasTable,
    AndamentosPrenotadosTable,
    AndamentosRegistradosTable,
    AndamentosTableExport,
    AndamentosValoresTableExport,
    AndamentoTable,
    CertidaoAgrupadaTable,
    CertidaoTable,
    DoiTable,
    EventColaboradorTable,
    FinanceiroColaboradorTable,
    FinanceiroTable,
    FinanceiroTableExport,
    ImovelTable,
    Livro01AndamentoTable,
    Livro01ProtocoloOnrTable,
    Livro01ProtocoloTable,
    Livro02Table,
    Livro03Table,
    Livro04Table,
    Livro05Table,
    PedidoCertidaoAndamentoTable,
    PedidoCertidaoAnexoTable,
    PedidoCertidaoPessoasTable,
    PedidoCertidaoTable,
    PedidoPartesTable,
    ProtocoloAndamentosTable,
    ProtocoloAndamentosTableExport,
    SeloTable,
)
from apps.home.templatetags.home_formatos import (
    configurar_cpf_cnp_retornar_descricao,
    converter_data_para_formato_de_modelo,
    formatar_data,
    formatar_numero_registro,
    get_estado_civil_pela_descricao,
    get_nome_colaborador_pelo_id,
    get_usuarios_para_notificar_digitalizacao,
)
from apps.home.tipos import (
    TipoAtivoCancelado,
    TipoClasseRegistro,
    TipoImportacao,
    TipoParte,
    TipoRegistro,
)
from apps.home.utils import comandos_sql, planilhas, resumo
from apps.home.utils.arquivos import GerenciadorDeArquivos
from apps.home.utils.Atualizar_Nome_Arquivo_Protocolo import processar_importar_titulo
from apps.home.utils.importar_livro2 import (
    converter_livro02_do_fb,
    converter_livro02_pelo_id_do_fb,
    get_registro_do_fb,
    gravar_registro_importado_do_fb,
)
from apps.home.utils.importar_livro3 import importar_livro03_do_fb
from apps.home.utils.intimacao_ler_diretorio import (
    processar_certidoes_emitir_onr,
    processar_eprotocolos_onr,
    processar_matriculas_visualizadas_onr,
    processar_xml_consulta_eletronica_onr,
    processar_xml_intimacao_onr,
    processar_xml_oficio_onr,
    processar_xml_penhora_online_sph_onr,
)

# # Adicionar valores das variaveis do LIVRO 2 - LV2
from apps.home.utils.mala_direta_minutas import (
    get_livro02,
    get_livro03,
    get_livro03_garantia,
    get_minuta_origem,
    ler_minuta_origem,
    salvar_documento_alterado,
    variaveis_minuta_impressao,
)
from apps.home.utils.onr_certidao_a_emitir import (
    ler_xml_certidoes_emitir_onr,
)
from apps.home.utils.onr_eprotocolo import ler_xml_eprotocolo_onr
from apps.home.utils.onr_visualizacoa_de_matricula import (
    ler_xml_matricula_visualizada,
)
from apps.home.utils.texto_livro02_service import (
    importar_ficha_do_fb_e_gravar_no_livro02,
)
from apps.integracoes.utils.Gerar_PGM import (
    get_ultima_data_envio_numero_onr,
    get_ultimo_envio_numero_onr_l3,
    get_ultimo_envio_numero_onr_l4,
)
from apps.minuta_exigencia.models import MinutaExigencia, MinutaExigenciaAto
from apps.minutas_atos.models import MinutaLigacaoAto, MinutaModeloAto
from core.mixins import ExportMixin
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_documento, formatar_documento_com_descricao

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")

if TYPE_CHECKING:
    from apps.home.managers import Livro01ProtocoloQuerySet

DEFAULT_GASTO_KWH = 500
AREA_POR_PAINEL = 2
PRECO_KW = 1800

pedido_item_atual = 0
pedido_atual = 0
protocolo_atual = 0
titulo_atual_id = 0
minuta_atual_id = ""
lista_perguntas_atuais = []
ato_praticado_atual = ""
ato_praticado_atual_id = ""
codigo_tabela_atual = ""
numero_ato_praticado_atual = ""
numero_matricula_atual = ""
tipo_registro_atual = ""

lista_indice_temporaria = []
lista_variaveis_temporaria = []
current_user_atual = ""


# Iniciando as configuracoes - LIVRO 3
(
    configuracao_id_devedor,
    configuracao_id_credor,
    configuracao_id_avalista,
    configuracao_id_fiel_depositario,
    configuracao_id_adquirente,
    configuracao_id_transmitente,
) = ([], [], [], [], [], [])

# Obtendo a formatacoa do texto
configuracao_id_descricao_cnpj, configuracao_id_descricao_cpf = "", ""

# Iniciando as configuracoes do cartorio
(
    configuracao_id_cidade_atual,
    configuracao_id_estado_atual,
    configuracao_id_nome_oficial,
) = ([], [], [])


openai.api_key = settings.OPENAI_API_KEY


# GRAVAR HTML NO BANCO DE DADOS
def gravar_html_bd_livro02(
    pedido_item_id,
    arquivo_gerado_final_html,
    numero_ato,
) -> None:
    # Gerar apenas numero inteiro

    pedido_item_id = str(pedido_item_id).split(".")[0]
    numero_ato = int(helpers.apenas_numeros(numero_ato))

    # Leitura do arquivo HTML
    with Path(arquivo_gerado_final_html, encoding="utf_8").open() as file:
        html_content = file.read()

    Livro02Texto.create(
        id=pedido_item_id,
        imovel=None,
        pedido_item_id=pedido_item_id,
        numero_ato=numero_ato,
        texto=html_content,
    )


# Colaborador Solicita Servico
def solicitar_servico_colaborador(request, colaborador_id):
    colaborador = Colaborador.objects.get(pk=colaborador_id)

    (
        quantidade_colaboradores,
        nome_colaboradores,
    ) = utils.Solicitar_Servico.colaborador_solicitar_servico(colaborador.pk)

    # VERIFICAR SE ENCONTROU PESSOAS PARA SOLICITAR
    if int(quantidade_colaboradores) > 0:
        messages.success(
            request,
            "Serviços Solicitados .      " + str("(" + nome_colaboradores + ")"),
        )
    else:
        messages.error(request, "Nenhum colaborador encontrado para solicitar serviços")

    return redirect(reverse("home:distribuicao_protocolo_colaboradores"))


# Verificar Colaborador Solicita Servico
def verificar_solicitar_servico_colaborador(request, colaborador_id):
    colaborador = Colaborador.objects.get(pk=colaborador_id)

    # Chama a função apropriada com base na quantidade de títulos
    return (
        solicitar_servico_colaborador(request, colaborador_id)
        if colaborador.protocolos_em_aberto.count == 0
        else protocolos_distribuidos_por_colaborador_list_view(request, colaborador_id)
    )


def pedido_item_delete_view(request, pedido_item_id=0, pedidos_itens_origem_id=0):
    pessoadelete = get_object_or_404(PedidoItem, pk=pedido_item_id)
    pessoadelete.delete()

    # REMOVER ITEM
    firebird.firebird_remover_pedido_item(pedido_item_id)

    messages.success(request, "Dados excluídos!")

    if int(pedidos_itens_origem_id) == 0:
        # Atualizar_Protocolo_Atual(pedido_item_atual)
        # success_url = reverse_lazy("atualizar_protocolo")
        return redirect(reverse("home:protocolo_search"))
    else:
        # VOLTAR PARA O EMOLUMENTO COMPLEMENTAR
        return solicitar_item_protocolo_complementar(
            request,
            pedido_item_id=pedidos_itens_origem_id,
        )


# Obter o ultimo protocolo do sistema
# def Protocolo_Final(request, opcao=0, numero=0):
#     global protocolo_atual, current_user_atual
#     # Pegando o usuario atual
#     current_user_atual = str(request.user).upper()

#     # DADOS DO PROTOCOLO

#     # Primeiro Numero
#     if opcao == "1":
#         protocolo = Livro01Protocolo.objects.filter(numero_protocolo__gte=1).aggregate(
#             Min("numero_protocolo")
#         )
#         protocolo_atual = str(protocolo["numero_protocolo__min"]).split(".")[0]
#     # Anterior Numero
#     elif opcao == "2":
#         protocolo_atual = str(
#             int(Livro01Protocolo.objects.get(numero_protocolo=numero).numero_protocolo) - 1
#         )
#     # Proximo Numero
#     elif opcao == "3":
#         protocolo_atual = str(
#             int(Livro01Protocolo.objects.get(numero_protocolo=numero).numero_protocolo) + 1
#         )
#     # Ultimo Numero
#     elif opcao == "4":
#         protocolo = Livro01Protocolo.objects.filter(numero_protocolo__gte=1).aggregate(
#             Max("numero_protocolo")
#         )
#         protocolo_atual = str(protocolo["numero_protocolo__max"]).split(".")[0]
#     # Numero Informado
#     elif opcao == "5":
#         protocolo_atual = str(
#             int(Livro01Protocolo.objects.get(numero_protocolo=numero).numero_protocolo)
#         )

#     success_url = reverse_lazy("atualizar_protocolo")
#     return redirect(reverse("home:protocolo_search"))


# def Protocolo_Informado(request, numero_protocolo):
#     global current_user_atual
#     # Pegando o usuario atual
#     current_user_atual = str(request.user).upper()

#     webbrowser.open(get_url_pesquisa_protocolo(numero_protocolo), new=1)

#     success_url = reverse_lazy("atualizar_protocolo")
#     return redirect(reverse("home:protocolo_search"))


@login_required
def abrir_protocolo(request, numero_protocolo):
    # Pegando o usuário atual
    # current_user_atual = str(request.user).upper()

    # Se for necessário executar alguma lógica antes de redirecionar,
    # faça isso aqui...

    # Redirecionar para a página desejada
    return redirect("home:protocolo_search")


# CONVERTER WORD TO PDF
# def converter_word_pdf_salvar(origem_xls, diretorio, destino_pdf):
#     docx2pdf.convert(origem_xls)
#     return diretorio + destino_pdf + ".pdf"


# CONVERTER EXCELL TO PDF
def gerar_excell_pdf(origem_xls, diretorio, destino_pdf):
    # origem_xls      = "D:/TESTE_12/django-datta-able-master/apps/static/assets/images/ged/uploads/Caixa_Diario_10_03_2022_20_19_54.xlsx"
    # destino_html    = "D:/TESTE_12/django-datta-able-master/apps/static/assets/images/ged/uploads/file.html"
    # arquivo_salvar  = "D:/TESTE_12/django-datta-able-master/apps/static/assets/images/ged/uploads/file.pdf"

    # https://pypi.org/project/aspose-cells-python/
    # Load Excel file
    workbook = Workbook(origem_xls)

    # Convert Excel to PDF
    arquivo_salvar = diretorio + destino_pdf + ".pdf"
    workbook.save(arquivo_salvar)

    """ CONVERTER EXCELL PARA PDF
    df = pd.read_excel(origem_xls)
    df.to_html(destino_html)

    # Caminho para instalar
    # https://github.com/JazzCore/python-pdfkit/wiki/Installing-wkhtmltopdf
    config = pdfkit.configuration(wkhtmltopdf= "C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe") #replace with your path
    pdfkit.from_file(destino_html, arquivo_salvar, configuration=config)
    """

    return arquivo_salvar


# Converter arquivo TIFF to PDF
def converter_tiff_to_pdf(origem, diretorio, destino):
    # opening image
    image = Image.open(origem)

    # converting into chunks using img2pdf
    pdf_bytes = img2pdf.convert(image.filename)

    # opening or creating pdf file
    arquivo_salvo = diretorio + destino + ".pdf"
    file = open(arquivo_salvo, "wb")

    # writing pdf files with chunks
    file.write(pdf_bytes)

    # closing image file
    image.close()

    # closing pdf file
    file.close()

    return arquivo_salvo


# Converter arquivo PNG to PDF
def converter_png_to_pdf(origem, diretorio, destino):
    image_1 = Image.open(origem)
    im_1 = image_1.convert("RGB")
    arquivo_salvo = diretorio + destino + ".pdf"
    im_1.save(arquivo_salvo)
    return arquivo_salvo


def get_descricao_documento():
    # Chave para o cache
    cache_key_cpf = "configuracao_id_descricao_cpf"
    cache_key_cnpj = "configuracao_id_descricao_cnpj"

    # Tentar obter o valor do cache primeiro
    configuracao_id_descricao_cpf = cache.get(cache_key_cpf)
    configuracao_id_descricao_cnpj = cache.get(cache_key_cnpj)

    # Se não estiver no cache, buscar no banco de dados
    if configuracao_id_descricao_cpf is None:
        try:
            configuracao_id_descricao_cpf = Configuracao.obter(
                "CONFIGURACAO_ID_DESCRICAO_CPF",
            )
            # Armazenar o valor no cache
            cache.set(
                cache_key_cpf,
                configuracao_id_descricao_cpf,
                3600,
            )  # 1 hora de cache
        except Configuracao.DoesNotExist:
            configuracao_id_descricao_cpf = ""

    if configuracao_id_descricao_cnpj is None:
        try:
            configuracao_id_descricao_cnpj = Configuracao.obter(
                "CONFIGURACAO_ID_DESCRICAO_CNPJ",
            )
            # Armazenar o valor no cache
            cache.set(
                cache_key_cnpj,
                configuracao_id_descricao_cnpj,
                3600,
            )  # 1 hora de cache
        except Configuracao.DoesNotExist:
            configuracao_id_descricao_cnpj = ""

    return configuracao_id_descricao_cpf, configuracao_id_descricao_cnpj


# Filtras os dados do LIVRO 03


# Template Inicial
class Home(TemplateView):
    template_name = "home.html"


class UUIDPrimaryKeyField(models.UUIDField):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["primary_key"] = True
        kwargs["default"] = uuid.uuid4
        kwargs["editable"] = False
        kwargs["verbose_name"] = "ID"
        super().__init__(*args, **kwargs)

    @staticmethod
    def generate_uuid() -> uuid.UUID:
        return uuid.uuid4()


# CRIAR PROPRIETARIOS
def get_proprietarios_lv2(request, pedido_item_id):
    pedido_item: PedidoItem = PedidoItem.objects.filter(pk=pedido_item_id).first()

    dados_do_imovel = pedido_item.get_dados_do_registro()

    # OBTER A ID IMOVEL
    imovel_id = dados_do_imovel["imovel_id"]

    # OBTER A ID PEDIDOS
    pedido_id = str(pedido_item.pedido_id)

    # Proprietarios Atuais
    partes = Vinculo.objects.select_related("pessoa", "tipo_vinculo").filter(
        imovel_id=imovel_id,
        situacao="F",
        tipo_vinculo_id__in=Configuracao.obter("proprietario_id"),
    )

    # Filtrar todas as partes
    for adquirente in partes:
        gravar_pedidos_partes_ato(
            pedido_id=pedido_id,
            pedido_item_id=pedido_item_id,
            pessoa=adquirente.pessoa,
            status="T",
            estado_civil=adquirente.pessoa.estado_civil,
            total=partes.count(),
            ato_baixa_id=adquirente.id,
            percentual_ato=adquirente.area_pecentual,
        )

    # RETONAR PARA O Checklist
    return minuta_list_lv2(request, pedido_item_id, opcao="1")


# # Documentos Diversos - LIVRO 1
def anexar_documento_view(request, protocolo_id) -> None:
    #     from apps.home.utils.comandos import retornar_nome_arquivo_e_extensao

    #     if request.method == "POST":
    #         files = request.FILES.getlist("files")
    #         extensao = ".pdf"
    #         arquivo_apagar = []

    #         # Filtrar as imagens do protocolo
    #         numero_extensao_inicial = (
    #             int(len(get_arquivos_de_imagens_protocolo(Configuracao.obter("diretorio_ged_imagens"), "protocolos", protocolo_id)))
    #             + 1
    #         )

    #         # Iterando sobre os arquivos enviados
    #         for nro_item, file in enumerate(files):
    #             fs = FileSystemStorage()
    #             fs.save(file.name, file)

    #             # Verificar a extensao
    #             (
    #                 temp_1,
    #                 apenas_nome_arquivo,
    #                 extensao_arquivo,
    #             ) = retornar_nome_arquivo_e_extensao(file.name)

    #             # Renomear o arquivo
    #             numero_item_atual = int(numero_extensao_inicial) + int(nro_item)
    #             origem = str(fs.location) + "/" + str(file)

    #             # Verificar se dir nao existe - CRIAR
    #             diretorio = str(Configuracao.obter("diretorio_ged_protocolos") + "/" + str(id)
    #             if not os.path.isdir(diretorio):
    #                 os.mkdir(diretorio)

    #             # Nome do Arquivo a Salvar
    #             arquivo_salvar = (
    #                 diretorio + "/" + str(id) + "." + str(numero_item_atual).zfill(4) + str(extensao)
    #             )

    #             # Verificar a extensao do arquivo
    #             if str(extensao_arquivo).upper() != ".PDF":
    #                 arquivo_apagar.append(origem)
    #                 diretorio_temp = str(fs.location) + "/"

    #                 # print(extensao_arquivo)
    #                 #

    #                 # CONVERTER IMAGEM PARA PDF
    #                 if str(extensao_arquivo).upper() in [
    #                     ".PNG",
    #                     ".jpg",
    #                     ".JPEG",
    #                     ".BMP",
    #                     ".JFIF",
    #                 ]:
    #                     origem = converter_png_to_pdf(origem, diretorio_temp, apenas_nome_arquivo)

    #                 elif str(extensao_arquivo).upper() in [".TIF", ".TIFF"]:
    #                     origem = converter_tiff_to_pdf(origem, diretorio_temp, apenas_nome_arquivo)

    #                 # CONVERTER EXCELL PARA PDF
    #                 elif str(extensao_arquivo).upper() in [".XLS", ".XLSX"]:
    #                     origem = gerar_excell_pdf(origem, diretorio_temp, apenas_nome_arquivo)

    #                 # CONVERTER WORD PARA PDF
    #                 elif str(extensao_arquivo).upper() in [".DOC", ".DOCX"]:
    #                     origem = converter_word_pdf_salvar(origem, diretorio_temp, apenas_nome_arquivo)

    #                 else:
    #                     print("Tipo nao definido. Usar padrao TIFF ")
    #                     origem = converter_tiff_to_pdf(origem, diretorio_temp, apenas_nome_arquivo)
    #                     # arquivo_apagar.clear()

    #             # Salvar na pasta correta do PROTOCOLO
    #             os.rename(origem, arquivo_salvar)

    #         # Apagar arquivo temporarios
    #         for apagar in arquivo_apagar:
    #             try:
    #                 os.remove(apagar)
    #             except Exception as e:
    #                 logger.exception("ERRO")

    #         # success_url = reverse_lazy("atualizar_protocolo")
    #         messages.success(request, "Documentos anexados!")
    #         return redirect(reverse("home:protocolo_search"))

    ...


def read_token():
    path_dir = os.path.split(os.path.abspath(__file__))[0]

    config = configparser.ConfigParser()
    config.read(path_dir + "/utils" + "/Token.ini", encoding="utf-8")
    arquivo_pem = str(config["TOKEN"]["CAMINHO_TOKEN_PEM"])
    arquivo_pfx = str(config["TOKEN"]["CAMINHO_TOKEN_PFX"])
    senha = str(config["TOKEN"]["SENHA"])

    return str(arquivo_pem).strip(), str(arquivo_pfx).strip(), str(senha).strip()


# Assinado arquivo digitalmente
def assinar_digitalmente_pdf(arquivo):
    token_pem, token_pfx, senha = read_token()

    if token_pem != "":
        utils.criar_assinatura_no_arquivo_pdf.add_token(arquivo, arquivo + ".temp")
        shutil.copyfile(arquivo + ".temp", arquivo)

        # ASSINAR O ARQUIVO PARA SER VAILIDADO AS ASSINATURAS
        utils.Assinar_PDF_A1.main(token_pfx, senha, arquivo)

        # REMOVER ARQUIVO TEMPORARIO
        with contextlib.suppress(Exception):
            Path(arquivo + ".temp").unlink()

    return arquivo


# Nota de Devolucao - LIVRO 1
def anexar_nota_devolucao_view(request, pedido_item_id):
    pedido_item = PedidoItem.objects.get(pk=pedido_item_id)
    from apps.home.helpers import retornar_nome_arquivo_e_extensao

    arquivo_apagar = []

    if request.method == "POST":
        files = request.FILES.getlist("files")
        extensao = ".pdf"

        # Filtrar as imagens do protocolo
        numero_extensao_inicial = (
            int(len(pedido_item.protocolo.imagens_protocolo())) + 1
        )

        # Iterando sobre os arquivos enviados
        for nro_item, file in enumerate(files):
            fs = FileSystemStorage()
            fs.save(file.name, file)

            # OBTER O NUMERO DO PROTOCOO
            # numero_protocolo = str(remover_pontuacao(get_numero_protocolo_filter(id)))

            # Verificar a extensao
            (
                _,
                apenas_nome_arquivo,
                extensao_arquivo,
            ) = retornar_nome_arquivo_e_extensao(file.name)

            # Renomear o arquivo
            numero_item_atual = int(numero_extensao_inicial) + int(nro_item)
            origem = str(fs.location) + "/" + str(file)

            # Verificar se dir nao existe - CRIAR
            # diretorio = str(Configuracao.obter("diretorio_ged_nota_devolucao")) + "/" + str(id)
            diretorio = (
                str(Configuracao.obter("diretorio_ged_nota_devolucao"))
                + "/"
                + str(pedido_item.protocolo.numero_protocolo)
            )
            if not os.path.isdir(diretorio):
                os.mkdir(diretorio)

            # Nome do Arquivo a Salvar
            arquivo_salvar = (
                diretorio
                + "/"
                + str(id)
                + "."
                + str(numero_item_atual).zfill(4)
                + str(extensao)
            )

            # Verificar a extensao do arquivo
            if str(extensao_arquivo).upper() != ".PDF":
                arquivo_apagar.append(origem)
                diretorio_temp = str(fs.location) + "/"

                # CONVERTER IMAGEM PARA PDF
                if str(extensao_arquivo).upper() in [
                    ".PNG",
                    ".jpg",
                    ".JPEG",
                    ".BMP",
                    ".JFIF",
                ]:
                    origem = converter_png_to_pdf(
                        origem,
                        diretorio_temp,
                        apenas_nome_arquivo,
                    )

                elif str(extensao_arquivo).upper() in [".TIF", ".TIFF"]:
                    origem = converter_tiff_to_pdf(
                        origem,
                        diretorio_temp,
                        apenas_nome_arquivo,
                    )

                # CONVERTER EXCELL PARA PDF
                elif str(extensao_arquivo).upper() in [".XLS", ".XLSX"]:
                    origem = gerar_excell_pdf(
                        origem,
                        diretorio_temp,
                        apenas_nome_arquivo,
                    )

                # CONVERTER WORD PARA PDF
                elif str(extensao_arquivo).upper() in [".DOC", ".DOCX"]:
                    print("Anexar nota devolução: ", origem)
                    print(
                        "Destino da nota devolução: ",
                        diretorio_temp,
                        apenas_nome_arquivo,
                    )
                    # origem = converter_word_pdf_salvar(origem, diretorio_temp, apenas_nome_arquivo)
                    # origem = converter_word_pdf_salvar(origem, diretorio_temp, apenas_nome_arquivo)

                else:
                    print("Tipo nao definido. Usar padrao TIFF ")
                    origem = converter_tiff_to_pdf(
                        origem,
                        diretorio_temp,
                        apenas_nome_arquivo,
                    )
                    # arquivo_apagar.clear()

            # Salvar na pasta correta do PROTOCOLO
            # os.rename(origem, arquivo_salvar)
            shutil.copy(origem, arquivo_salvar)

            # ASSINAR DIGITALMENTE
            arquivo_assinado = assinar_digitalmente_pdf(arquivo_salvar)

            # GERAR EVENTO PARA NOFITICAR NOTA DE DEVOLUCAO ANEXADA NO PROTOCOLO
            tarefa_protocolo_nota_devolucao_anexada(
                request,
                str(pedido_item.protocolo.numero_protocolo),
                "Anexado nota:",
                "Anexada nota de exigência ao protocolo:",
            )

        # # Apagar arquivo temporarios
        # for apagar in arquivo_apagar:
        #     try:
        #         os.remove(apagar)
        #     except Exception as e:
        #         logger.exception("ERRO")

        # success_url = reverse_lazy("atualizar_protocolo")
        # messages.success(request, "Documentos anexados!")
        # return redirect(reverse("home:protocolo_search"))
        return view_pdf(request, arquivo_assinado)
    return None


# Serviços de intimacao - LIVRO 1
def handle_uploaded_file(uploaded_file):
    """Salva o arquivo enviado pelo usuário."""
    fs = FileSystemStorage()
    filename = fs.save(uploaded_file.name, uploaded_file)
    return fs.location, filename


def get_configuration(key, default=""):
    """Obtém uma configuração específica."""
    return Configuracao.obter(key, default)


@login_required(login_url="/login/")
def integracoes_view(request):
    if request.method == "POST":
        uploaded_file = request.FILES["document"]

        # VERIFICAR SE O ARQUIVO E ZIP
        if uploaded_file.name.endswith(".zip"):
            print("Arquivo zip encontrado...")

        dir_intimacao_onr, filename = handle_uploaded_file(uploaded_file)
        # url_intimacao_onr = get_configuration("URL_INTIMACAO_ONR_ID")
        # processar_xml_intimacao_onr(dir_intimacao_onr, url_intimacao_onr, request.user)
        processar_xml_intimacao_onr(
            file_location=dir_intimacao_onr,
            uploaded_file=uploaded_file,
            user=request.user,
        )

    return render_integracoes_page(request)


class IntegracoesImportarONRProtocoloView(LoginRequiredMixin, View):
    def post(self, request, origem_id):
        origem_id = int(origem_id)
        try:
            uploaded_file = request.FILES["document"]

            # VERIFICAR SE O ARQUIVO E ZIP
            if uploaded_file.name.endswith(".zip"):
                print("Arquivo zip encontrado ..")
                fs = FileSystemStorage()
                extracted_files = extract_zip_file(request, fs, uploaded_file)
                print(extracted_files)

            # ENVIAR ARQUIVO PARA O DIRETORIO
            dir_protocolo_onr, filename = handle_uploaded_file(uploaded_file)

            # ATUALIZAR ARQUIVO SALVO
            uploaded_file = filename

            logger.info(
                f"Iniciando envio do arquivo xml... {dir_protocolo_onr} - {uploaded_file} - {request.user} ",
            )

            # LEITURA DO ARQUIVO
            # if int(origem_id) == 7:
            #     # ONR - e-PROTOCOLO
            #     try:
            #         numeros = processar_eprotocolos_onr(
            #             file_location=dir_protocolo_onr,
            #             uploaded_file=uploaded_file,
            #             user=request.user,
            #         )
            #         messages.success(
            #             request,
            #             f"{len(numeros)} protocolos processados da ONR",
            #         )
            #     except Exception as e:
            #         messages.error(request, f"Erro ao processar Protocolos ONR {e!s}")

            if origem_id == 8:
                # ONR - INTIMACAOO
                try:
                    quantidade = processar_xml_intimacao_onr(
                        dir_protocolo_onr,
                        uploaded_file,
                        request.user,
                    )
                    messages.success(
                        request,
                        f"{quantidade} intimações ONR processadas",
                    )
                except Exception as e:
                    messages.error(request, f"Erro ao processar Intimação ONR:  {e!s}")

            # GRAVAR NO AUDITOR ULTIMA LEITURA DE ARQUIVO
            AuditorIntegracao.objects.create(tipo_integracao_id=origem_id)

            return render_integracoes_onr_protocolo(request, origem_id)
        except Exception as e:
            logger.exception("ERRO ao importar arquivo...")
            messages.error(request, f"Erro ao importar arquivo...{e!s}")
            return render_integracoes_onr_protocolo(request, origem_id)

    def get(self, request, origem_id):
        return render_integracoes_onr_protocolo(request, origem_id)


# class IntegracoesImportarONRView(LoginRequiredMixin, View):
#     def dispatch(self, *args, **kwargs):
#         return super().dispatch(*args, **kwargs)

#     def get(self, request, origem_id):
#         # Redirect to the IntegracoesONRView with GET request
#         return IntegracoesONRView.as_view()(request, origem_id=origem_id)

#     def post(self, request, origem_id):
#         # Handle file upload and processing
#         file = request.FILES.get("document")
#         if not file:
#             messages.error(request, "Nenhum arquivo foi enviado.")
#             return IntegracoesONRView.as_view()(request, origem_id=origem_id)

#         mensagem_retorno = handle_file_import(file, origem_id, request)
#         if mensagem_retorno:
#             messages.info(request, f"Retorno da importação: {mensagem_retorno}")
#             AuditorIntegracao.objects.create(tipo_integracao_id=origem_id)

#         return IntegracoesONRView.as_view()(request, origem_id=origem_id)


def handle_file_import(file, origem_id, request):
    try:
        mensagem_retorno = ""

        if file.name.endswith(".zip"):
            mensagem_retorno = handle_zip_file(file, request)
        else:
            file_location, filename = handle_uploaded_file(file)
            mensagem_retorno = process_file_by_tipo_integracao(
                origem_id,
                file_location,
                filename,
                request,
            )

        return mensagem_retorno

    except Exception as e:
        msg = f"Erro ao importar arquivo... {e!s}"
        messages.error(request, msg)
        logger.exception(msg)
        return None


def handle_zip_file(file, request):
    print("Arquivo zip encontrado...")
    fs = FileSystemStorage()
    extracted_files = extract_zip_file(request, fs, file)
    print(extracted_files)
    return "Arquivo zip processado com sucesso."


def process_file_by_tipo_integracao(origem_id, file_location, filename, request):
    """Processa um arquivo baseado no tipo de integração especificado pelo 'origem_id'."""
    try:
        # Dicionário que mapeia os tipos de integração às suas funções de processamento correspondentes.
        tipo_integracao_processors = {
            TipoIntegracao.get_onr_oficio().id: processar_xml_oficio_onr,
            TipoIntegracao.get_tipo_integracao_onr_consulta_eletronica().id: processar_xml_consulta_eletronica_onr,
            TipoIntegracao.get_onr_penhora_online_sph().id: processar_xml_penhora_online_sph_onr,
        }

        # Logando o início do processamento do arquivo
        logger.info(
            f"Iniciando o processamento do arquivo '{filename}' com origem_id '{origem_id}'.",
        )

        # Obtendo a função de processamento com base no 'origem_id'
        processar_func = tipo_integracao_processors[origem_id]
        if processar_func:
            # Logando a função de processamento que será utilizada
            logger.info(
                f"Função de processamento '{processar_func.__name__}' selecionada para o tipo de integração '{origem_id}'.",
            )

            # Chamando a função de processamento
            mensagem_retorno = processar_func(file_location, filename, request.user)

            # Logando o sucesso do processamento
            logger.info(f"Processamento do arquivo '{filename}' concluído com sucesso.")

            # Retornando a mensagem de retorno sem "None"
            return str(mensagem_retorno).replace("None", "")
        else:
            # Logando o erro de tipo de integração desconhecido
            msg = f"Tipo de integração desconhecido para origem_id '{origem_id}'."
            logger.error(msg)
            raise ValueError(msg)

    except Exception as e:
        # Capturando e logando a exceção ocorrida durante o processamento
        error_message = f"Erro ao processar arquivo '{filename}': {e!s}"
        messages.error(request, error_message)
        logger.exception(error_message)
        return None


def integracoes_view_importar(request):
    """Visão para manipular integrações importar."""
    if request.method == "POST":
        uploaded_file = request.FILES["document"]

        # VERIFICAR SE O ARQUIVO E ZIP
        if uploaded_file.name.endswith(".zip"):
            print("Arquivo zip encontrado ..")

        dir_intimacao_onr, filename = handle_uploaded_file(uploaded_file)
        url_intimacao_onr = get_configuration("url_intimacao_onr_id")
        print(dir_intimacao_onr, url_intimacao_onr, request.user)
        # arquivos_onr(dir_intimacao_onr, url_intimacao_onr, request.user)

    return render_integracoes_page_importar(request)


def render_integracoes_page(request):
    """Renderiza a página de integrações."""
    context = build_integracoes_context()
    return render(request, "integracoes.html", context)


def build_integracoes_context():
    """Constrói o contexto para a página de integrações."""
    servico__id01_intimacao = get_configuration("servico__id01_intimacao")
    last_intimacao_date = get_last_intimacao_date(servico__id01_intimacao)

    # ULTIMOS NUMEROS DO ARQUIVO
    ultimo_numero_enviado_onr_l2 = Livro02.ultimo_registro_enviado_onr()
    ultimo_numero_enviado_onr_l3 = formatar_numero_registro(
        get_ultimo_envio_numero_onr_l3(),
    )
    ultimo_numero_enviado_onr_l4 = formatar_numero_registro(
        get_ultimo_envio_numero_onr_l4(),
    )

    # DATA DA ULTIMA VERIFICACAO DO ARQUIVO
    ultima_datarelatorio_enviado_onr_l2 = get_ultima_data_envio_numero_onr("2")
    ultima_datarelatorio_enviado_onr_l3 = get_ultima_data_envio_numero_onr("3")
    ultima_datarelatorio_enviado_onr_l4 = get_ultima_data_envio_numero_onr("4")

    return {
        "Servicos_01_Intimacao": last_intimacao_date,
        "Ultimo_Numero_Enviado_ONR_L2": ultimo_numero_enviado_onr_l2,
        "Ultimo_Numero_Enviado_ONR_L3": ultimo_numero_enviado_onr_l3,
        "Ultimo_Numero_Enviado_ONR_L4": ultimo_numero_enviado_onr_l4,
        "Ultima_DataRelatorio_Enviado_ONR_L2": ultima_datarelatorio_enviado_onr_l2,
        "Ultima_DataRelatorio_Enviado_ONR_L3": ultima_datarelatorio_enviado_onr_l3,
        "Ultima_DataRelatorio_Enviado_ONR_L4": ultima_datarelatorio_enviado_onr_l4,
    }


# IMPORTAR MATIRICULA VISUALIZADA, OFICIO, PENHORA ONR
def render_integracoes_onr_protocolo(request, origem_id):
    # Onr PROTOCOLO
    origem_id = int(origem_id)

    # Use request.GET.get para obter os parâmetros da URL
    start_date = request.GET.get("data_entrada_inicial")
    end_date = request.GET.get("data_entrada_final")

    # VERIFICAR SE EXISTE DATA DE INICIO
    if start_date is None:
        # Filtragem para Protocolo
        start_date = timezone.now().date()
        end_date = timezone.now().date() + timedelta(1)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(1)

    protocolo_filter = filters.Livro01ProtocoloFilter(
        request.GET,
        queryset=Livro01Protocolo.objects.filter(
            origem_pedido=origem_id,
            data_protocolo__range=[start_date, end_date],
        ),
    )

    protocolos_ids = list(protocolo_filter.qs.values_list("id", flat=True))

    # Construindo a URL de impressão
    base_url = reverse("home:impressao_registrados")
    query_string = urlencode({"protocolo_id": protocolos_ids}, doseq=True)
    impressao_url = f"{base_url}?{query_string}"

    quantidade = protocolo_filter.queryset.count()

    protocolos = (
        Livro01Protocolo.objects.filter(
            origem_pedido=origem_id,
            data_protocolo__range=[start_date, end_date],
        ).all(),
    )

    pedidos_table = Livro01ProtocoloOnrTable(protocolos)

    # BUSCAR NO AUDITOR COMUM DE INTEGRACAO A ULTIMA IMPORTACAO REGISTRADA
    auditores = AuditorIntegracao.objects.filter(tipo_integracao_id=origem_id)

    if auditores.exists():
        data_servicos_matricula_visualiza = auditores.latest("created_at").created_at
        # Seleciona o auditor mais recente
    else:
        data_servicos_matricula_visualiza = timezone.now()

    data_servicos_matricula_visualiza = data_servicos_matricula_visualiza.strftime(
        "%d/%m/%Y %H:%M:%S",
    )

    context = {
        "data_servicos_matricula_visualiza": data_servicos_matricula_visualiza,
        "data_inicial": start_date,
        "data_final": end_date,
        "table": pedidos_table,
        "filter": protocolo_filter,
        "quantidade_certidoes": quantidade,
        "impressao_url": impressao_url,
    }

    # Renderizar a página de acordo com a origem
    if origem_id == 7:
        return render(request, "integracoes_importar_e-protocolo.html", context)
    elif origem_id == 8:
        return render(request, "integracoes_importar_intimacao.html", context)

    return None


def get_date_range(start_date, end_date):
    if start_date is None:
        start_date = timezone.now().date() - timedelta(days=0)
        end_date = timezone.now().date()
    else:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            start_date = timezone.now().date() - timedelta(days=1000)
            end_date = timezone.now().date()

    start_date = datetime.combine(start_date, datetime.min.time())
    end_date = datetime.combine(end_date, datetime.max.time())
    return start_date, end_date


def get_filtered_pedidos(origem_id, start_date, end_date, request):
    pedidos = PedidoCertidao.objects.filter(
        origem_id=origem_id,
        data_entrada__range=[start_date, end_date],
    )
    pedido_filter = filters.PedidoCertidaoFilter(request.GET, queryset=pedidos)
    return pedido_filter.qs, pedido_filter


def build_urls_pedido_certidao(pedidos_filtrados):
    numero_pedidos = list(pedidos_filtrados.values_list("numero_pedido", flat=True))
    base_url = reverse("home:pedido_certidao_impressao_recibos")
    query_string = urlencode({"numero_pedido": numero_pedidos}, doseq=True)
    impressao_url = f"{base_url}?{query_string}"

    pedidos_ids = list(pedidos_filtrados.values_list("id", flat=True))
    base_url = reverse("home:pedido_certidao_gerar_selo_pedido_certidao_onr")
    query_string = urlencode({"pedido_id": pedidos_ids}, doseq=True)
    selar_url = f"{base_url}?{query_string}"

    pedidos_ids = list(pedidos_filtrados.values_list("id", flat=True))
    base_url = reverse("home:certidoes_onr_relatorio_excel_por_ids")
    query_string = urlencode({"pedido_ids": ",".join(map(str, pedidos_ids))})
    excel_url = f"{base_url}?{query_string}"

    return impressao_url, selar_url, excel_url


def build_urls_protocolos(protocolos_filtrados):
    # Contruir URL para impressão de recibos
    numero_protocolos = list(
        protocolos_filtrados.values_list("numero_protocolo", flat=True),
    )
    base_url = reverse("home:pedido_certidao_impressao_recibos")
    query_string = urlencode({"numero_protocolo": numero_protocolos}, doseq=True)
    impressao_url = f"{base_url}?{query_string}"

    # Contruir URL para selar protocolos
    ids = list(protocolos_filtrados.values_list("id", flat=True))
    base_url = reverse("home:gerar_selo_protocolos_onr")
    query_string = urlencode({"id": ids}, doseq=True)
    selar_url = f"{base_url}?{query_string}"

    # Contruir URL para exportar protocolos para Excel
    ids = list(protocolos_filtrados.values_list("id", flat=True))
    base_url = reverse("home:protocolos_onr_relatorio_excel_por_ids")
    query_string = urlencode({"ids": ",".join(map(str, ids))})
    excel_url = f"{base_url}?{query_string}"

    return impressao_url, selar_url, excel_url


def get_last_auditor_timestamp(origem_id):
    auditores = AuditorIntegracao.objects.filter(tipo_integracao_id=origem_id)
    if auditores.exists():
        data_servicos_matricula_visualiza = auditores.latest("created_at").created_at
    else:
        data_servicos_matricula_visualiza = timezone.now()
    return data_servicos_matricula_visualiza.strftime("%d/%m/%Y %H:%M:%S")


@login_required
def integracoes_onr_view(request, origem_id):
    template_name = get_template_name(origem_id)
    context = {}

    if request.method == "POST":
        return handle_post(request, origem_id)

    pedidos_filtrados, pedido_filter = get_queryset(request, origem_id)

    # Correção: Certificar que o objeto 'table' está sendo criado e passado para o template
    tabela = PedidoCertidaoTable(pedidos_filtrados)
    RequestConfig(request, paginate={"per_page": 100}).configure(tabela)

    impressao_url, selar_url, excel_url = build_urls_pedido_certidao(pedidos_filtrados)
    quantidade = pedidos_filtrados.count()

    context.update(
        {
            "table": tabela,
            "filter": pedido_filter,
            "data_servicos_matricula_visualiza": get_last_auditor_timestamp(origem_id),
            "data_inicial": request.GET.get("data_entrada_inicial"),
            "data_final": request.GET.get("data_entrada_final"),
            "quantidade_certidoes": quantidade,
            "impressao_url": impressao_url,
            "selar_url": selar_url,
            "excel_url": excel_url,
        },
    )

    return render(request, template_name, context)


@login_required
def onr_matricula_visualizada_view(request):
    """
    Visão para importar as Matrículas Visualizadas da ONR.
    Matricula Visualizada é um serviço oferecido pela ONR e pago ao cartório.
    A ONR envia ao Cartório a informação de quais e quem fez a visualização para gerar uma certidão.
    Nenhuma informação precisa ser devolvida à ONR.
    """
    pedidos_processados_ids = []

    if request.method == "POST":
        file = request.FILES.get("document")
        if not file:
            messages.error(request, "Nenhum arquivo foi enviado.")
            return redirect("home:onr_matricula_visualizada")

        certidoes_onr = ler_xml_matricula_visualizada(file)

        if not certidoes_onr:
            messages.error(request, "Nenhuma certidão foi encontrada no arquivo.")
            return redirect("home:onr_matricula_visualizada")

        # Processar as certidões e capturar o retorno
        pedidos_processados = processar_matriculas_visualizadas_onr(
            certidoes_onr,
            request.user,
        )

        # Armazenar os IDs dos pedidos processados para o filtro
        pedidos_processados_ids = [
            p["pedido"].id for p in pedidos_processados if p["pedido"]
        ]

        # Informar ao usuário sobre os pedidos processados
        total_pedidos = len(pedidos_processados)
        mensagens_processadas = [
            p["mensagem"] for p in pedidos_processados if p["mensagem"]
        ]

        messages.info(request, f"Total de pedidos processados: {total_pedidos}")
        for mensagem in mensagens_processadas:
            messages.info(request, mensagem)

    # Filtrar o queryset para exibir apenas os pedidos processados, caso existam
    if pedidos_processados_ids:
        queryset = PedidoCertidao.objects.filter(id__in=pedidos_processados_ids)
    else:
        queryset = PedidoCertidao.objects.filter(
            origem_id=MATRICULA_VISUALIZADA_ORIGEM_ID,
        )

    filtro = PedidoCertidaoFilter(request.GET, queryset)
    tabela = PedidoCertidaoTable(filtro.qs)
    RequestConfig(request, paginate={"per_page": 5}).configure(tabela)

    # Construir URLs para impressão, selagem e exportação para Excel
    impressao_url, selar_url, excel_url = build_urls_pedido_certidao(filtro.qs)

    # Obter a data da última importação
    data_ultima_importacao = (
        AuditorIntegracao.get_data_ultima_importacao_matricula_visualizada()
    )

    context = {
        "table": tabela,
        "filter": filtro,
        "data_ultima_importacao": data_ultima_importacao,
        "data_inicial": request.GET.get("data_entrada_inicial"),
        "data_final": request.GET.get("data_entrada_final"),
        "impressao_url": impressao_url,
        "selar_url": selar_url,
        "excel_url": excel_url,
    }

    return render(request, "integracoes_importar_matricula_visualizada.html", context)


@login_required
def onr_certidoes_a_emitir_view(request):
    """
    Visão para importar as Certidões a Emitir da ONR .
    Codigo ONR_CERTIDOES_A_EMITIR_ID: 6.
    """
    tipo_integracao_id = ONR_CERTIDOES_A_EMITIR_ID
    pedidos_processados_ids = []
    url = redirect("home:onr_certidoes_a_emitir")

    if request.method == "POST":
        file = request.FILES.get("document")
        if not file:
            messages.error(request, "Nenhum arquivo foi enviado.")
            return url

        certidoes_onr = ler_xml_certidoes_emitir_onr(file)

        if not certidoes_onr:
            messages.error(request, "Nenhuma certidão foi encontrada no arquivo.")
            return url

        # Processar as certidões e capturar o retorno que são os pedidos criados.
        pedidos_processados = processar_certidoes_emitir_onr(
            certidoes_onr,
            request.user,
        )

        # Armazenar os IDs dos pedidos processados para o filtro
        pedidos_processados_ids = [
            p["pedido"].id for p in pedidos_processados if p["pedido"]
        ]

        # Informar ao usuário sobre os pedidos processados
        total_pedidos = len(pedidos_processados)
        mensagens_processadas = [
            p["mensagem"] for p in pedidos_processados if p["mensagem"]
        ]

        messages.info(request, f"Total de pedidos processados: {total_pedidos}")
        for mensagem in mensagens_processadas:
            messages.info(request, mensagem)

    # Filtrar o queryset para exibir apenas os pedidos processados, caso existam
    if pedidos_processados_ids:
        queryset = PedidoCertidao.objects.filter(id__in=pedidos_processados_ids)
    else:
        queryset = PedidoCertidao.objects.filter(
            origem_id=tipo_integracao_id,
        )

    filtro = PedidoCertidaoFilter(request.GET, queryset)
    tabela = PedidoCertidaoTable(filtro.qs)
    RequestConfig(request, paginate={"per_page": 5}).configure(tabela)

    # Construir URLs para impressão, selagem e exportação para Excel
    impressao_url, selar_url, excel_url = build_urls_pedido_certidao(filtro.qs)

    # Obter a data da última importação
    data_ultima_importacao = AuditorIntegracao.get_data_ultima_importacao(
        tipo_integracao_id,
    )

    context = {
        "table": tabela,
        "filter": filtro,
        "data_ultima_importacao": data_ultima_importacao,
        "data_inicial": request.GET.get("data_entrada_inicial"),
        "data_final": request.GET.get("data_entrada_final"),
        "impressao_url": impressao_url,
        "selar_url": selar_url,
        "excel_url": excel_url,
    }

    return render(request, "onr_certidoes_a_emitir.html", context)


@login_required
def onr_eprotocolo_view(request):
    """
    Visão para importar os e-protocolos da ONR.
    Codigo ONR_EPROTOCOLO_ID: 7.
    """
    tipo_integracao_id = ONR_EPROTOCOLO_ID
    protocolos_processados_ids = []
    url = redirect("home:onr_eprotocolo")
    template_name = "onr/onr_eprotocolo.html"

    if request.method == "POST":
        file = request.FILES.get("document")
        if not file:
            messages.error(request, "Nenhum arquivo foi enviado.")
            return url

        protocolos_onr = ler_xml_eprotocolo_onr(file)

        if not protocolos_onr:
            messages.error(request, "Nenhum protocolo foi encontrado no arquivo.")
            return url

        # Processar as certidões e capturar o retorno que são os pedidos criados.
        protocolos_processados = processar_eprotocolos_onr(
            protocolos_onr,
            request.user,
        )

        # Armazenar os IDs dos pedidos processados para o filtro
        protocolos_processados_ids = [
            p["protocolo"].id for p in protocolos_processados if p["protocolo"]
        ]

        # Informar ao usuário sobre os pedidos processados
        total_protocolos = len(protocolos_processados)
        mensagens_processadas = [
            p["mensagem"] for p in protocolos_processados if p["mensagem"]
        ]

        messages.info(request, f"Total de protocolos processados: {total_protocolos}")
        for mensagem in mensagens_processadas:
            messages.info(request, mensagem)

    # Filtrar o queryset para exibir apenas os pedidos processados, caso existam
    if protocolos_processados_ids:
        queryset = Livro01Protocolo.objects.filter(id__in=protocolos_processados_ids)
    else:
        queryset = Livro01Protocolo.objects.filter(origem_pedido=tipo_integracao_id)

    filtro = Livro01ProtocoloFilter(request.GET, queryset)
    tabela = Livro01ProtocoloTable(filtro.qs)
    RequestConfig(request, paginate={"per_page": 5}).configure(tabela)

    # Construir URLs para impressão, selagem e exportação para Excel
    impressao_url, selar_url, excel_url = build_urls_protocolos(filtro.qs)

    # Obter a data da última importação
    data_ultima_importacao = AuditorIntegracao.get_data_ultima_importacao(
        tipo_integracao_id,
    )

    context = {
        "table": tabela,
        "filter": filtro,
        "data_ultima_importacao": data_ultima_importacao,
        "data_inicial": request.GET.get("data_entrada_inicial"),
        "data_final": request.GET.get("data_entrada_final"),
        "impressao_url": impressao_url,
        "selar_url": selar_url,
        "excel_url": excel_url,
    }

    return render(request, template_name, context)


def handle_post(request, origem_id):
    file = request.FILES.get("document")
    if not file:
        messages.error(request, "Nenhum arquivo foi enviado.")
        return redirect("home:integracoes_onr", origem_id=origem_id)

    mensagem_retorno = handle_file_import(file, origem_id, request)
    if mensagem_retorno:
        messages.info(request, f"Retorno da importação: {mensagem_retorno}")
        AuditorIntegracao.objects.create(tipo_integracao_id=origem_id)

    return redirect("home:integracoes_onr", origem_id=origem_id)


def get_queryset(request, origem_id):
    start_date = request.GET.get("data_entrada_inicial")
    end_date = request.GET.get("data_entrada_final")

    start_date, end_date = get_date_range(start_date, end_date)
    pedidos_filtrados, pedido_filter = get_filtered_pedidos(
        origem_id,
        start_date,
        end_date,
        request,
    )

    return pedidos_filtrados, pedido_filter


def get_template_name(origem_id):
    template_mapping = {
        2: "integracoes_importar_matricula_visualizada.html",
        3: "integracoes_importar_oficio.html",
        4: "integracoes_importar_consulta_eletronica.html",
        5: "integracoes_importar_penhora_online_sph.html",
        6: "integracoes_importar_certidao_imprimir.html",
    }

    return template_mapping.get(origem_id)


def render_integracoes_page_importar(request):
    """Renderiza a página de integrações."""
    servico__id01_intimacao = get_configuration("servico__id01_intimacao")
    last_intimacao_date = get_last_intimacao_date(servico__id01_intimacao)
    context = {"Servicos_01_Intimacao": last_intimacao_date}
    return render(request, "integracoes_importar.html", context)


def get_last_intimacao_date(servico__id01_intimacao):
    """Obtém a data da última intimacao."""
    servico_livro01_historico = ServicoLivro01Historico.objects.filter(
        servico_livro01_id=servico__id01_intimacao,
    ).aggregate(Max("data"))
    return servico_livro01_historico["data__max"]


# Obter a sub pasta do ATO DO LIVRO 02
def get_sub_pasta_ato_livro02(atos_id):
    try:
        ato = AtoPratica.objects.get(id=atos_id)
        pasta_minutas = str(ato.pasta_minutas) if ato.pasta_minutas else ""
    except AtoPratica.DoesNotExist:
        logger.info(f"Erro: Ato com ID {atos_id} não encontrado.")
        pasta_minutas = ""
    except Exception:
        logger.exception(f"ERRO ao buscar ato com ID {atos_id}: ")
        pasta_minutas = ""

    return pasta_minutas


# Gerar as perguntas olhando o modelo escolhido
def get_perguntas_vinculadas_minuta(minuta_atual, pedido_item_id, atual_id):
    # global lista_perguntas_atuais, minuta_atual_id

    print("INICIO 1: ", minuta_atual_id, atual_id)
    tipo_registro, minuta = "", ""

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

    tipo_registro = str(pedido_item.tipo_registro)
    atos_id = str(pedido_item.ato.id)

    # Verificar sub_pasta
    # Obter a sub pasta do ATO DO LIVRO 02
    sub_pasta = get_sub_pasta_ato_livro02(atos_id)

    # Caminho da minuta Padrao
    if sub_pasta != "":
        minuta = (
            helpers.get_caminho_minutas_padrao(tipo_registro, ("/" + sub_pasta))
            + "/"
            + str(minuta_atual)
            + ".docx"
        )
    else:
        minuta = (
            helpers.get_caminho_minutas_padrao(tipo_registro, "")
            + "/"
            + str(minuta_atual)
            + ".docx"
        )

    # print("MINUTA", minuta)

    # Minuta existe
    if Path(minuta).exists():
        # Gerando as variaveis presentes na minutas
        document = ler_minuta_origem(minuta)
        lista_variaveis_presentes_minuta = variaveis_minuta_impressao(document)
    else:
        lista_variaveis_presentes_minuta = []

    # Selecionar as perguntas as variaveis presentes banco dados
    lista_variaveis_presentes_banco = list(
        PerguntaMinuta.objects.values_list("corrans", flat=True),
    )

    # Intersecao das variaveis existentes
    return list(
        set(lista_variaveis_presentes_minuta).intersection(
            set(lista_variaveis_presentes_banco),
        ),
    )


# Listar todas as minutas auxiliares para esta minuta
def get_minutas_auxiliares(minuta_atual_id, tipo_registro_atual, diretorio_atual):
    # Verificando se a minuta pertence ao livro 2 ou 3
    tipo_livro = "3" if tipo_registro_atual == "A" else "2"

    # Filtrar as minutas
    minutas_auxiliar = MinutaAuxiliar.objects.filter(
        Q(nome_minuta_principal=minuta_atual_id) & Q(tipo_livro=tipo_livro),
    )

    # print(minutas_auxiliar)

    lista_minutas_auxiliares = []

    for item in minutas_auxiliar:
        if (
            item.nome_minuta_auxiliar_01 is not None
            and item.nome_minuta_auxiliar_01 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_01),
            )

        if (
            item.nome_minuta_auxiliar_02 is not None
            and item.nome_minuta_auxiliar_02 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_02),
            )

        if (
            item.nome_minuta_auxiliar_03 is not None
            and item.nome_minuta_auxiliar_03 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_03),
            )

        if (
            item.nome_minuta_auxiliar_04 is not None
            and item.nome_minuta_auxiliar_04 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_04),
            )

        if (
            item.nome_minuta_auxiliar_05 is not None
            and item.nome_minuta_auxiliar_05 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_05),
            )

        if (
            item.nome_minuta_auxiliar_06 is not None
            and item.nome_minuta_auxiliar_06 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_06),
            )

        if (
            item.nome_minuta_auxiliar_07 is not None
            and item.nome_minuta_auxiliar_07 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_07),
            )

        if (
            item.nome_minuta_auxiliar_08 is not None
            and item.nome_minuta_auxiliar_08 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_08),
            )

        if (
            item.nome_minuta_auxiliar_09 is not None
            and item.nome_minuta_auxiliar_09 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_09),
            )

        if (
            item.nome_minuta_auxiliar_10 is not None
            and item.nome_minuta_auxiliar_10 != ""
        ):
            lista_minutas_auxiliares.append(
                str(diretorio_atual) + "/Modelo/" + str(item.nome_minuta_auxiliar_10),
            )

    return lista_minutas_auxiliares


# Passar os parametros para substituir - TRABALHANDO
def processar_sustituir_arquivo(
    minuta,
    lista_pessoa,
    lista_conjuge,
    tipo_registro_atual,
    descricao_minuta,
):
    # global lista_arquivos_excluir

    # Arquivo a retornar
    caminho_nota_minutas_final = ""

    # Novo arquivo a ser gerado
    arquivo = minuta
    extensao = minuta
    temporario = (
        str(arquivo).split(".")[0]
        + "_TEMP_"
        + str(random.random()).replace(".", "")
        + "."
        + str(extensao).split(".")[1]
    )
    final = (
        str(arquivo).split(".")[0]
        + "_FINAL_"
        + str(random.random()).replace(".", "")
        + "."
        + str(extensao).split(".")[1]
    )

    # Diretorio e pasta do MODELO DE TEXTO LIVRO 2 OU 3
    filename_master = (
        helpers.get_caminho_minutas_padrao(tipo_registro_atual, "")
        + "/Modelo/"
        + minuta
    )
    caminho_nota_minutas_criar = (
        helpers.get_caminho_minutas_padrao(tipo_registro_atual, "")
        + "/Modelo/"
        + temporario
    )
    caminho_nota_minutas_final = (
        helpers.get_caminho_minutas_padrao(tipo_registro_atual, "") + "/Modelo/" + final
    )

    # Copiando o modelo
    if os.path.exists(filename_master):
        shutil.copyfile(filename_master, caminho_nota_minutas_criar)

    # formatar a data de nascimento
    try:
        data_nascimento = formatar_data(str(lista_pessoa[7]), 3)
    except Exception:
        logger.exception("ERRO")
        data_nascimento = ""

    # Dados da pessoa
    nome_pessoa = str(lista_pessoa[0])
    cpf_cnpj_pessoa = str(lista_pessoa[1])
    documento_pessoa = str(lista_pessoa[2])
    descricao_cpf_cnpj = str(lista_pessoa[3])
    nacionalidade = str(lista_pessoa[4])
    estado_civil = str(lista_pessoa[5])
    profissao = str(lista_pessoa[6])
    data_nascimento = str(data_nascimento)
    naturalidade = str(lista_pessoa[8])
    endereco = str(lista_pessoa[9])
    str(lista_pessoa[10])

    # Dados do conjuge
    if len(lista_conjuge) > 0:
        # formatar a data de nascimento - conjuge
        try:
            data_nascimento_conjuge = formatar_data(str(lista_conjuge[7]), 3)
        except Exception:
            logger.exception("ERRO")
            data_nascimento_conjuge = ""

        nome_pessoa_conjuge = str(lista_conjuge[0])
        cpf_cnpj_pessoa_conjuge = str(lista_conjuge[1])
        documento_pessoa_conjuge = str(lista_conjuge[2])
        descricao_cpf_cnpj_conjuge = str(lista_conjuge[3])
        nacionalidade_conjuge = str(lista_conjuge[4])
        estado_civil_conjuge = str(lista_conjuge[5])
        profissao_conjuge = str(lista_conjuge[6])
        data_nascimento_conjuge = str(data_nascimento_conjuge)
        naturalidade_conjuge = str(lista_conjuge[8])
        endereco_conjuge = str(lista_conjuge[9])
        str(lista_conjuge[10])
    else:
        nome_pessoa_conjuge = ""
        cpf_cnpj_pessoa_conjuge = ""
        documento_pessoa_conjuge = ""
        descricao_cpf_cnpj_conjuge = ""
        nacionalidade_conjuge = ""
        estado_civil_conjuge = ""
        profissao_conjuge = ""
        data_nascimento_conjuge = ""
        naturalidade_conjuge = ""
        endereco_conjuge = ""

    # Gerando a substituicao Minutas temporarias como CREDOR
    minuta_origem = get_minuta_origem(caminho_nota_minutas_criar)

    document = minuta_origem

    if tipo_registro_atual == "A":
        # print('A    =   nome_pessoa_conjuge', nome_pessoa_conjuge)
        get_livro03(
            nome_pessoa=nome_pessoa,
            cpf_cnpj_pessoa=cpf_cnpj_pessoa,
            documento_pessoa=documento_pessoa,
            descricao_cpf_cnpj=descricao_cpf_cnpj,
            nacionalidade=nacionalidade,
            estado_civil=estado_civil,
            profissao=profissao,
            data_nascimento=data_nascimento,
            naturalidade=naturalidade,
            endereco=endereco,
            nome_pessoa_conjuge=nome_pessoa_conjuge,
            cpf_cnpj_pessoa_conjuge=cpf_cnpj_pessoa_conjuge,
            documento_pessoa_conjuge=documento_pessoa_conjuge,
            descricao_cpf_cnpj_conjuge=descricao_cpf_cnpj_conjuge,
            nacionalidade_conjuge=nacionalidade_conjuge,
            profissao_conjuge=profissao_conjuge,
            estado_civil_conjuge=estado_civil_conjuge,
            data_nascimento_conjuge=data_nascimento_conjuge,
            naturalidade_conjuge=naturalidade_conjuge,
            endereco_conjuge=endereco_conjuge,
            document=document,
        )
    else:
        # print('B    =   nome_pessoa', nome_pessoa, ' ', data_nascimento)
        get_livro02(
            nome_pessoa=nome_pessoa,
            cpf_cnpj_pessoa=cpf_cnpj_pessoa,
            documento_pessoa=documento_pessoa,
            descricao_cpf_cnpj=descricao_cpf_cnpj,
            nacionalidade=nacionalidade,
            estado_civil=estado_civil,
            profissao=profissao,
            data_nascimento=data_nascimento,
            naturalidade=naturalidade,
            endereco=endereco,
            # DADOS DO CONJUGUE
            nome_pessoa_conjuge=nome_pessoa_conjuge,
            cpf_cnpj_pessoa_conjuge=cpf_cnpj_pessoa_conjuge,
            documento_pessoa_conjuge=documento_pessoa_conjuge,
            descricao_cpf_cnpj_conjuge=descricao_cpf_cnpj_conjuge,
            nacionalidade_conjuge=nacionalidade_conjuge,
            profissao_conjuge=profissao_conjuge,
            data_nascimento_conjuge=data_nascimento_conjuge,
            naturalidade_conjuge=naturalidade_conjuge,
            document=document,
        )

    salvar_documento_alterado(document, caminho_nota_minutas_final)

    gerenciador = GerenciadorDeArquivos()
    # lista de arquivos a EXCLUIR
    gerenciador.adicionar_arquivo(caminho_nota_minutas_final)
    gerenciador.adicionar_arquivo(caminho_nota_minutas_criar)

    # Apenas o Nome do Arquivo
    # caminho_nota_minutas_final = retornar_nome_arquivo_e_extensao(caminho_nota_minutas_final)[0]

    return caminho_nota_minutas_final


# Passar os parametros para substituir - TRABALHANDO
def processar_sustituir_arquivo_garantia(minuta, lista_garantia, descricao_minuta):
    # global lista_arquivos_excluir

    # Arquivo a retornar
    caminho_nota_minutas_final = ""

    # Novo arquivo a ser gerado
    arquivo = minuta
    extensao = minuta
    temporario = (
        str(arquivo).split(".")[0]
        + "_TEMP_"
        + str(random.random()).replace(".", "")
        + "."
        + str(extensao).split(".")[1]
    )
    final = (
        str(arquivo).split(".")[0]
        + "_FINAL_"
        + str(random.random()).replace(".", "")
        + "."
        + str(extensao).split(".")[1]
    )

    # Diretorio e pasta do MODELO DE TEXTO LIVRO 2 OU 3
    filename_master = (
        helpers.get_caminho_minutas_padrao(tipo_registro_atual, "")
        + "/Modelo/"
        + minuta
    )
    caminho_nota_minutas_criar = (
        helpers.get_caminho_minutas_padrao(tipo_registro_atual, "")
        + "/Modelo/"
        + temporario
    )
    caminho_nota_minutas_final = (
        helpers.get_caminho_minutas_padrao(tipo_registro_atual, "") + "/Modelo/" + final
    )

    # Copiando o modelo
    if os.path.exists(filename_master):
        shutil.copyfile(filename_master, caminho_nota_minutas_criar)

    # Gerando a substituicao Minutas temporarias como CREDOR
    # ler_minuta_origem(document, caminho_nota_minutas_criar)
    document = ler_minuta_origem(caminho_nota_minutas_criar)

    # Separando os valores
    garantia_especie = lista_garantia[0]
    garantia_numero = lista_garantia[1]
    garantia_valor = lista_garantia[2]
    garantia_quantidade = lista_garantia[3]
    garantia_grau_penhor = lista_garantia[4]
    garantia_fazenda = lista_garantia[5]
    garantia_area = lista_garantia[6]
    garantia_tipo_registro = lista_garantia[7]
    garantia_numero_registro = lista_garantia[8]
    garantia_tipo_ato = lista_garantia[9]
    garantia_imovel_vinculado_descricao = lista_garantia[10]
    garantia_descricao = lista_garantia[11]

    # Substiuir variaveis
    get_livro03_garantia(
        penhorespecie=garantia_especie,
        penhornumero=garantia_numero,
        penhorvalor=garantia_valor,
        penhorquantidade=garantia_quantidade,
        penhorgrau=garantia_grau_penhor,
        penhorfazenda=garantia_fazenda,
        penhorarea=garantia_area,
        penhortipoimovel=garantia_tipo_registro,
        penhornumeroimovel=garantia_numero_registro,
        penhornumeroato=garantia_tipo_ato,
        penhodescricaovinculoimovel=garantia_imovel_vinculado_descricao,
        penhodescricaosafra=garantia_descricao,
        document=document,
    )

    salvar_documento_alterado(document, caminho_nota_minutas_final)

    # lista de arquivos a EXCLUIR
    lista_arquivos_excluir.append(caminho_nota_minutas_final)
    lista_arquivos_excluir.append(caminho_nota_minutas_criar)

    return caminho_nota_minutas_final


# Checar o texto da estado_civil, olhar se tem algum texto para minuta especifico
def checar_texto_estado_civil(descricao_estado_civil, sexo):
    descricao_estado_civil_atual = descricao_estado_civil
    descricao_estado_civil_atual_conjugue = descricao_estado_civil

    for estado_civil in EstadoCivil.objects.filter(
        descricao_estado_civil=descricao_estado_civil_atual,
    ):
        if sexo == "F":
            if estado_civil.texto_feminino is not None:
                descricao_estado_civil_atual = str(estado_civil.texto_feminino)
                descricao_estado_civil_atual_conjugue = str(
                    estado_civil.texto_masculino,
                )
        elif estado_civil.texto_masculino is not None:
            descricao_estado_civil_atual = str(estado_civil.texto_masculino)
            descricao_estado_civil_atual_conjugue = str(estado_civil.texto_feminino)

    return str(descricao_estado_civil_atual), str(descricao_estado_civil_atual_conjugue)


def get_pessoa_garantia(pedido_item_id, configuracao_id, minuta, inicial, final):
    global lista_arquivos_excluir

    pedido_item: PedidoItem = PedidoItem.objects.filter(pk=pedido_item_id).first()

    # Filtrar Registro Auxiliar
    registro_auxiliar_dict = pedido_item.get_dados_do_registro_auxiliar()

    # PEGANDO OS DADOS DAS GARANTIAS
    garantias = Livro03Garantia.objects.filter(
        registro_auxiliar_id=registro_auxiliar_dict["registro_auxiliar_id"],
    )

    # Listar os itens
    lista_arquivos, lista_garantia = [], []

    # Incluir o arquivo inicial
    lista_arquivos.append(inicial)

    descricao_minuta = minuta

    # Filtrando as VINCULOS
    for garantia in garantias:
        # Descricao da minuta

        imovel_vinculado = RegistroVinculado.objects.filter(
            id=garantia.imovel_vinculado_id,
        ).last()

        imovel_vinculado_descricao = imovel_vinculado.descricao

        # Listando a garantia
        lista_garantia.append(garantia.especie)
        lista_garantia.append(garantia.numero)
        lista_garantia.append(garantia.valor)
        lista_garantia.append(garantia.quantidade)
        lista_garantia.append(garantia.grau_penhor)
        lista_garantia.append(garantia.fazenda)
        lista_garantia.append(garantia.area)
        lista_garantia.append(garantia.tipo_registro)
        lista_garantia.append(garantia.numero_registro)
        lista_garantia.append(garantia.tipo_ato)
        lista_garantia.append(imovel_vinculado_descricao)
        lista_garantia.append(garantia.descricao)

        # Passar os parametros para substituir
        arquivo_retornar = processar_sustituir_arquivo_garantia(
            minuta,
            lista_garantia,
            descricao_minuta,
        )

        # Arquivo gerado
        lista_arquivos.append(arquivo_retornar)

        # Arquivo Apagar
        arquivo_excluir_atual = (
            helpers.get_caminho_minutas_padrao(tipo_registro_atual, "")
            + "/Modelo/"
            + arquivo_retornar
        )

        # lista de arquivos a EXCLUIR
        lista_arquivos_excluir.append(arquivo_excluir_atual)

        lista_garantia.clear()

    return lista_arquivos


# # Pegando os dados da PESSOA do LIVRO 2 - trabalhando
# def get_pessoa_lv2(
#     pedido_item,
#     configuracao_id,
#     minuta,
#     inicial,
#     final,
#     opcao_configuracao="",
# ):
#     global lista_arquivos_excluir

#     # Sempre a mesma minuta
#     # print("minuta: ", minuta)
#     #

#     minuta_temp = minuta

#     # # Pegando as configuracoes das DESCRICOES CNPJ ou CPF
#     # for item in Configuracao.objects.filter(id=11):
#     #     configuracao_id_descricao_cnpj = str(item.valor)

#     # for item in Configuracao.objects.filter(id=12):
#     #     configuracao_id_descricao_cpf = str(item.valor)

#     # Filtrar o IMOVEL
#     imoveis = models.filtrar_imovel_pedidos_itens(pedido_item.pk)

#     # OBTER A ID IMOVEL
#     imovel_id = imoveis["imovel_id"]
#     opcao_livro = imoveis["tipo_registro"]

#     # OBTER TODOS OS ADQUIRENTES DO ATO

#     # Todas as pessoas do ATO DO PROTOCOLO
#     if minuta == "Adquirente.docx":
#         vinculos = PedidoParteAto.objects.filter(
#             pedido_item_id=pedido_item.pk,
#             status="A",
#         ).order_by("id")
#     elif minuta == "Transmitente.docx":
#         vinculos = PedidoParteAto.objects.filter(
#             pedido_item_id=pedido_item.pk,
#             status="T",
#         ).order_by("id")
#     elif opcao_configuracao != "":
#         Vinculo.objects.select_related("pessoa", "tipo_vinculo").filter(
#             imovel_id=imovel_id,
#             tipos_vinculos__in=configuracao_id,
#             situacao=opcao_configuracao,
#         )
#     else:
#         Vinculo.objects.select_related("pessoa", "tipo_vinculo").filter(
#             imovel_id=imovel_id,
#             tipos_vinculos__in=configuracao_id,
#         )

#     # Listar os itens
#     lista_arquivos = []

#     # Incluir o arquivo inicial
#     lista_arquivos.append(inicial)

#     # print("Quantidade de pessoas: ", len(vinculos))
#     # Filtrando as VINCULOS
#     lista_pessoas_analisadas = []
#     for vinculo in vinculos:
#         pessoa = Livro05.objects.filter(id=vinculos.pessoa_id).first()

#         # Filtrar os dados da pessoa

#         # print("nome: ", nome.nome)
#         lista_pessoa, lista_conjuge = [], []

#         # Pegando o conjuge da pessoa ja vista
#         lista_pessoas_analisadas.append(vinculo.pessoa_conjuge_id)

#         # Descricao da minuta
#         descricao_minuta = vinculo.estado_civil.descricao_minuta

#         # Verificar a QUALIFICACAO DA PESSOA - CASADA, SOLTEIRA OU JURIDICA ou PADRAO - # Obter o estado_civil correta
#         if descricao_minuta is not None:
#             minuta = str(minuta).split(".")[0] + "_" + descricao_minuta

#         numero_cpf_cnpj, descricao_numero_cpf_cnpj = pessoa.documento_configurado

#         # data_nascimento = ''
#         data_nascimento = str(pessoa.data_nascimento)

#         # Fitrar e pesquisar o texto da estado_civil
#         descricao_estado_civil, tipoestado_civil_conjuge = checar_texto_estado_civil(
#             vinculo.estado_civil.descricao_estado_civil,
#             pessoa.sexo,
#         )
#         # print("nome", nome.sexo, descricao_estado_civil, tipoestado_civil_conjuge)

#         # INICIO - PESSOA JA ANALISADA
#         if vinculo.pessoa.id not in list(lista_pessoas_analisadas):
#             try:
#                 lista_pessoa.append(pessoa.nome)
#                 lista_pessoa.append(numero_cpf_cnpj)
#                 lista_pessoa.append(pessoa.documento)
#                 lista_pessoa.append(descricao_numero_cpf_cnpj)
#                 lista_pessoa.append(pessoa.nacionalidade)
#                 lista_pessoa.append(descricao_estado_civil)

#                 if pessoa.profissao is None:
#                     lista_pessoa.append("")
#                 else:
#                     lista_pessoa.append(pessoa.profissao)

#                 lista_pessoa.append(data_nascimento)
#                 lista_pessoa.append(pessoa.naturalidade)

#                 if pessoa.endereco is None:
#                     lista_pessoa.append("")
#                 else:
#                     lista_pessoa.append(pessoa.endereco)

#                 lista_pessoa.append(descricao_minuta)
#                 lista_pessoa.append(pessoa.sexo)

#                 # Procurar modelo
#                 if str(minuta_temp) == "Adquirente.docx" or str(minuta_temp) == "Transmitente.docx":
#                     pessoa_conjuge_id = int(vinculo.pessoa_conjuge_id)
#                 elif pessoa.pessoa_conjuge_id is None:
#                     pessoa_conjuge_id = 0
#                 else:
#                     pessoa_conjuge_id = int(pessoa.pessoa_conjuge_id)

#             except Exception:
#                 logger.exception("ERRO")
#                 pessoa_conjuge_id = 0

#             # Existe Conjugue
#             if pessoa_conjuge_id > 0:
#                 # conjuge = Livro05.objects.filter(id=pessoa_conjuge_id).first()
#                 conjuge = pessoa.get_conjuge()

#                 # Filtrar os dados da pessoa - conjuge
#                 (numero_cpf_cnpj, descricao_numero_cpf_cnpj) = conjuge.documento_configurado

#                 data_nascimento = str(conjuge.data_nascimento)

#                 lista_conjuge.append(conjuge.nome)
#                 lista_conjuge.append(numero_cpf_cnpj)
#                 lista_conjuge.append(conjuge.documento)
#                 lista_conjuge.append(descricao_numero_cpf_cnpj)
#                 lista_conjuge.append(conjuge.nacionalidade)
#                 lista_conjuge.append(tipoestado_civil_conjuge)

#                 if conjuge.profissao is None:
#                     lista_conjuge.append("")
#                 else:
#                     lista_conjuge.append(conjuge.profissao)

#                 lista_conjuge.append(conjuge.profissao if conjuge.profissao is not None else "")

#                 lista_conjuge.append(data_nascimento)
#                 lista_conjuge.append(conjuge.naturalidade)

#                 if conjuge.endereco is None:
#                     lista_conjuge.append("")
#                 else:
#                     lista_conjuge.append(conjuge.endereco)

#                 lista_conjuge.append(descricao_minuta)
#                 lista_conjuge.append(conjuge.sexo)

#             # Passar os parametros para substituir
#             arquivo_retornar = processar_sustituir_arquivo(
#                 minuta,
#                 lista_pessoa,
#                 lista_conjuge,
#                 opcao_livro,
#                 descricao_minuta,
#             )

#             # Arquivo gerado
#             lista_arquivos.append(arquivo_retornar)
#             # print("arquivo_retornar: ", arquivo_retornar)

#             # Arquivo Apagar
#             arquivo_excluir_atual = (
#                 helpers.get_caminho_minutas_padrao(tipo_registro_atual, "") + "/Modelo/" + arquivo_retornar
#             )

#             # lista de arquivos a EXCLUIR
#             with contextlib.suppress(Exception):
#                 lista_arquivos_excluir.append(arquivo_excluir_atual)
#             # print("arquivo_excluir_atual: ", arquivo_excluir_atual)

#             # Atualizar a mesma Sempre a mesma minuta
#             minuta = minuta_temp

#         # FIM - PESSOA JA ANALISADA

#     return lista_arquivos


# Pegando os dados da PESSOA do LIVRO 3
def get_pessoa_lv3(pedido_item: PedidoItem, configuracao_id, minuta, inicial, final):
    global lista_arquivos_excluir

    # Tipo do livro
    opcao_livro = "A"

    # Sempre a mesma minuta
    minuta_temp = minuta

    # Filtrar Registro Auxiliar
    registro_auxiliar_dict = pedido_item.get_dados_do_registro_auxiliar()

    # Lista de nomes a pular caso ja tenha sido qualificadaa
    lista_pular_pessoa, lista_pular_pessoa_conjuge = [], []

    # TODOs os vinculos
    ligacoes = Livro03Ligacao.objects.filter(
        registro_auxiliar_id=registro_auxiliar_dict["registro_auxiliar_id"],
        figuras_id__in=configuracao_id,
    )
    # print(ligacoes)
    #

    # Listar os itens
    lista_arquivos = []

    # Incluir o arquivo inicial
    lista_arquivos.append(inicial)

    # Filtrando as ligacoes
    for ligacao in ligacoes:
        pessoas = Livro05.objects.filter(id=ligacao.pessoa_id)

        # Criar Black list quando ja tiver lancados os dados da pessoa e do conjuge -
        # TRABALHANDO - CASO ENCONTRE LIMPA E VAI PARA O PROXIMO
        if len(lista_pular_pessoa) > 0 and len(lista_pular_pessoa_conjuge) > 0:
            for pesquisar in pessoas:
                nome_pesquisar = str(pesquisar.nome)
                figura_pesquisar = str(ligacao.figuras_id)

            # Encontrou nome limpa
            if str(nome_pesquisar) == str(lista_pular_pessoa[0]) and str(
                figura_pesquisar,
            ) == str(
                lista_pular_pessoa[1],
            ):
                lista_pular_pessoa, lista_pular_pessoa_conjuge = [], []
                continue

        # Filtrar os dados da pessoa
        for pessoa in pessoas:
            # Listar os itens
            lista_pessoa, lista_conjuge = [], []

            # Descricao da minuta
            descricao_minuta = ligacao.estado_civil.descricao_minuta

            # Verificar a QUALIFICACAO DA PESSOA - CASADA, SOLTEIRA OU JURIDICA ou PADRAO - # Obter o estado_civil correta
            if descricao_minuta is not None:
                minuta = str(minuta).split(".")[0] + "_" + descricao_minuta

            numero_cpf_cnpj, descricao_numero_cpf_cnpj = (
                formatar_documento_com_descricao(pessoa.cpf)
            )

            data_nascimento = str(pessoa.data_nascimento)

            # Fitrar e pesquisar o texto da estado_civil
            descricao_estado_civil, tipoestado_civil_conjuge = (
                checar_texto_estado_civil(
                    ligacao.estado_civil.descricao_estado_civil,
                    pessoa.sexo,
                )
            )
            # print(descricao_estado_civil, tipoestado_civil_conjuge)

            # Descricao da pessoa
            lista_pessoa.append(pessoa.nome)
            lista_pessoa.append(numero_cpf_cnpj)
            lista_pessoa.append(pessoa.documento)
            lista_pessoa.append(descricao_numero_cpf_cnpj)
            lista_pessoa.append(pessoa.nacionalidade)
            lista_pessoa.append(descricao_estado_civil)
            lista_pessoa.append(pessoa.profissao)
            lista_pessoa.append(data_nascimento)
            lista_pessoa.append(pessoa.naturalidade)
            lista_pessoa.append(pessoa.endereco)
            lista_pessoa.append(descricao_minuta)
            lista_pessoa.append(pessoa.sexo)

            # Existe Conjugue - Descricao da pessoa
            try:
                pessoa_conjuge_id = int(pessoa.pessoa_conjuge_id)
                # print("get_pessoa_lv3", "GGGGGGGGGG")
            except Exception:
                logger.exception("ERRO")
                pessoa_conjuge_id = 0

            if pessoa_conjuge_id > 0:
                nome_conjuge = Livro05.objects.filter(id=pessoa_conjuge_id)

                # Filtrar os dados da pessoa - conjuge
                for conjuge in nome_conjuge:
                    numero_cpf_cnpj, descricao_numero_cpf_cnpj = (
                        formatar_documento_com_descricao(conjuge.cpf)
                    )

                    data_nascimento = str(conjuge.data_nascimento)

                    # Conjugue - Descricao da pessoa
                    lista_conjuge.append(conjuge.nome)
                    lista_conjuge.append(numero_cpf_cnpj)
                    lista_conjuge.append(conjuge.documento)
                    lista_conjuge.append(descricao_numero_cpf_cnpj)
                    lista_conjuge.append(conjuge.nacionalidade)
                    lista_conjuge.append(tipoestado_civil_conjuge)
                    lista_conjuge.append(conjuge.profissao)
                    lista_conjuge.append(data_nascimento)
                    lista_conjuge.append(conjuge.naturalidade)
                    lista_conjuge.append(conjuge.endereco)
                    lista_conjuge.append(descricao_minuta)
                    lista_conjuge.append(conjuge.sexo)

                    # Criar Black list quando ja tiver lancados os dados da pessoa e do conjuge - TRABALHANDO
                    lista_pular_pessoa.append(conjuge.nome)
                    lista_pular_pessoa.append(ligacao.figuras_id)

                    lista_pular_pessoa_conjuge.append(pessoa.nome)
                    lista_pular_pessoa.append(ligacao.figuras_id)

            # TRABALHANDO NESTES NOMES
            """
            try:
                print(nome.nome, conjuge.nome, ligacao.figuras.id)
            except Exception as e:
                logger.exception("ERRO")
                print(nome.nome, nome.conjuge_id, ligacao.figuras.id)


            """

            # Passar os parametros para substituir
            arquivo_retornar = processar_sustituir_arquivo(
                minuta,
                lista_pessoa,
                lista_conjuge,
                opcao_livro,
                descricao_minuta,
            )

            # Incluir o arquivo final
            # lista_arquivos.append(final)

            # Arquivo gerado
            lista_arquivos.append(arquivo_retornar)

            # Arquivo Apagar
            arquivo_excluir_atual = (
                helpers.get_caminho_minutas_padrao(tipo_registro_atual, "")
                + "/Modelo/"
                + arquivo_retornar
            )

            # lista de arquivos a EXCLUIR
            lista_arquivos_excluir.append(arquivo_excluir_atual)

            # Atualizar a mesma Sempre a mesma minuta
            minuta = minuta_temp

    return lista_arquivos


# Atualizando as minutas temporarias
def atualizar_minutas_temporarias(lista_minutas_auxiliares, pedido_item, tipo_registro):
    # global configuracao_id_devedor, configuracao_id_credor, configuracao_id_avalista, configuracao_id_fiel_depositario, configuracao_id_adquirente, configuracao_id_transmitente

    # # Criar a lista de
    # lista_arquivos_temporario = []

    # # Gerando as minutas temporarias
    # for minuta in lista_minutas_auxiliares:
    #     # APENAS O NOME DO ARQUIVO
    #     minuta = os.path.basename(minuta)

    #     if tipo_registro == "A":
    #         if minuta == "Emitente.docx":
    #             DEVEDOR = get_pessoa_lv3(
    #                 pedido_item,
    #                 Configuracao.get_lista("devedor_id", "INTEIRO"),
    #                 minuta,
    #                 "Inicio_Emitente.docx",
    #                 "Fim_Emitente.docx",
    #             )
    #             lista_arquivos_temporario.append(DEVEDOR)
    #         elif minuta == "Credor.docx":
    #             CREDOR = get_pessoa_lv3(
    #                 pedido_item,
    #                 list(Configuracao.get_lista("credor_id", "INTEIRO")),
    #                 minuta,
    #                 "Inicio_Credor.docx",
    #                 "Fim_Credor.docx",
    #             )
    #             lista_arquivos_temporario.append(CREDOR)
    #         elif minuta == "Avalista.docx":
    #             AVALISTA = get_pessoa_lv3(
    #                 pedido_item,
    #                 Configuracao.get_lista("avalista_id", "INTEIRO"),
    #                 minuta,
    #                 "Inicio_Avalista.docx",
    #                 "Fim_Avalista.docx",
    #             )
    #             lista_arquivos_temporario.append(AVALISTA)
    #         elif minuta == "Garantidor.docx":
    #             GARANTIDOR = get_pessoa_lv3(
    #                 pedido_item,
    #                 Configuracao.get_lista("fiel_depositario_id", "INTEIRO"),
    #                 minuta,
    #                 "Inicio_Garantidor.docx",
    #                 "Fim_Garantidor.docx",
    #             )
    #             lista_arquivos_temporario.append(GARANTIDOR)
    #         elif minuta == "Garantia.docx":
    #             GARANTIAS = get_pessoa_garantia(
    #                 pedido_item,
    #                 "",
    #                 minuta,
    #                 "Inicio_Garantia.docx",
    #                 "Fim_Garantia.docx",
    #             )
    #             lista_arquivos_temporario.append(GARANTIAS)
    #     elif minuta == "Adquirente.docx":
    #         # ADQUIRENTE = get_pessoa_lv2(
    #         #     pedido_item,
    #         #     Configuracao.get_lista("adquirente_id", "INTEIRO"),
    #         #     minuta,
    #         #     "Inicio_Adquirente.docx",
    #         #     "Fim_Adquirente.docx",
    #         #     "F",
    #         # )
    #         # lista_arquivos_temporario.append(ADQUIRENTE)

    #     elif minuta == "Transmitente.docx":
    #         # TRANSMITENTE = get_pessoa_lv2(
    #         #     pedido_item,
    #         #     Configuracao.get_lista("transmitente_id", "INTEIRO"),
    #         #     minuta,
    #         #     "Inicio_Transmitente.docx",
    #         #     "Fim_Transmitente.docx",
    #         #     "T",
    #         # )
    #         # lista_arquivos_temporario.append(TRANSMITENTE)

    # return lista_arquivos_temporario
    pass


def limpar_registrar_perguntas_divergentes_protocolo(pedido_item_id) -> None:
    with contextlib.suppress(Exception):
        ChecklistRealizadoHistorico.objects.filter(
            pedido_item_id=pedido_item_id,
            funcionarios_id__isnull=True,
        ).delete()


# Registrar as DIVERGENCIAS DO PROTOCOLO
def registrar_perguntas_divergentes_protocolo(
    resposta,
    resposta_correta,
    estado_civil,
    perguntas,
    pessoa,
    conferido_usuario,
    pedido_item,
    pedidos,
    ordem,
) -> None:
    b = ChecklistRealizadoHistorico(
        resposta=resposta,
        resposta_correta=resposta_correta,
        estado_civil=estado_civil,
        perguntas=perguntas,
        pessoa=pessoa,
        conferido_usuario=conferido_usuario,
        pedido_item_id=pedido_item,
        pedido_id=pedidos,
        ordem=ordem,
    )

    b.save()


# def gerar_nota_minuta(pedido_item, minuta_atual):
#     global \
#         pedido_atual, \
#         protocolo_atual, \
#         ato_praticado_atual, \
#         numero_matricula_atual, \
#         tipo_registro_atual, \
#         minuta_atual_id, \
#         lista_arquivos_excluir, \
#         codigo_tabela_atual, \
#         numero_ato_praticado_atual, \
#         ato_praticado_atual_id

#     if not tipo_registro_atual:
#         tipo_registro_atual = TipoRegistro.MATRICULA

#     # print("INICIO 2: ", minuta_atual_id, minuta_atual)
#     # Diretorio e pasta do MODELO DE TEXTO LIVRO 2 OU 3
#     diretorio_atual = get_caminho_minutas_padrao(tipo_registro_atual, "")

#     minuta_atual_id = minuta_atual

#     # Atualizar Protocolo Atual
#     # Atualizar_Protocolo_Atual(pedido_item_atual)

#     # Listar todas as minutas auxiliares
#     lista_minutas_auxiliares = get_minutas_auxiliares(
#         minuta_atual_id,
#         tipo_registro_atual,
#         diretorio_atual,
#     )

#     # Atualizar as minutas temporarias
#     lista_minutas_temporarias = atualizar_minutas_temporarias(
#         lista_minutas_auxiliares,
#         pedido_item,
#         tipo_registro_atual,
#     )

#     print("ato_praticado_atual_id", ato_praticado_atual_id)
#     # Verificar sub_pasta
#     # Obter a sub pasta do ATO DO LIVRO 02
#     sub_pasta = get_sub_pasta_ato_livro02(ato_praticado_atual_id)
#     print("sub_pasta", sub_pasta)

#     # Encontrou Minuta Auxiliar
#     print("Encontrou Minuta Auxiliar", len(lista_minutas_auxiliares))

#     # Diretorio e pasta do MODELO DE TEXTO LIVRO 2 OU 3
#     # diretorio_atual = get_caminho_minutas_padrao(tipo_registro_atual, "")
#     # print("diretorio_atual", diretorio_atual)
#     # print('lista_minutas_auxiliares: ', lista_minutas_auxiliares)

#     # Encontrou Minuta Auxiliar
#     if len(lista_minutas_auxiliares) > 0:
#         # Arquivos a buscar da base AUXILIAR - 1 Arquivo como principal
#         # filename_master = diretorio_atual + "/Modelo/" + lista_minutas_auxiliares[0]
#         filename_master = lista_minutas_auxiliares[0]

#         # Tirando o 1 arquivo da lista
#         lista_minutas_auxiliares.pop(0)

#         # Diretorio com as listas auxiliares
#         files_list = lista_minutas_auxiliares

#         # Verificar se tem que quebrar em varias listas auxiliares
#         if len(lista_minutas_temporarias) > 0:
#             # Arquivo de finalizacao
#             finalizacao_arquivo = files_list[-1]

#             # Reiniciar lista
#             files_list = []

#             # Montar os arquivos
#             for nivel_1 in lista_minutas_temporarias:
#                 for nivel_2 in nivel_1:
#                     files_list.append(nivel_2)

#             # Obter o arquivo de finalizacao
#             files_list.append(finalizacao_arquivo)

#         # Caminho Temporarios dos arquivos
#         extensao_temporaria = str(random.random()).replace(".", "") + "_" + str(protocolo_atual).split(".")[0] + ".docx"

#         caminho_nota_minutas = diretorio_atual + "/_Temp_" + extensao_temporaria
#         caminho_nota_minutas_final = diretorio_atual + "/_Final_" + extensao_temporaria
#         caminho_nota_minutas_modelo = caminho_nota_minutas_final

#         print("caminho_nota_minutas_final", caminho_nota_minutas_final)
#         #

#         # Combinando os arquivos
#         caminho_nota_minutas_criar = combine_all_docx(
#             filename_master,
#             files_list,
#             diretorio_atual,
#             caminho_nota_minutas,
#         )

#         # lista de arquivos a EXCLUIR
#         with contextlib.suppress(Exception):
#             lista_arquivos_excluir.append(caminho_nota_minutas_final)

#     # Minuta unica
#     else:
#         # Caminho Salvar Arquivo
#         extensao_temporaria = str(random.random()).replace(".", "") + "_" + str(protocolo_atual).split(".")[0] + ".docx"
#         # print('extensao_temporaria', extensao_temporaria)

#         caminho_nota_minutas_criar = diretorio_atual + "/_Temp_" + extensao_temporaria
#         # print('caminho_nota_minutas_criar', caminho_nota_minutas_criar)

#         caminho_nota_minutas_final = diretorio_atual + "/_Final_" + extensao_temporaria
#         # print('caminho_nota_minutas_final', caminho_nota_minutas_final)

#         # Obter a sub pasta do ATO DO LIVRO 02
#         sub_pasta = get_sub_pasta_ato_livro02(ato_praticado_atual_id)

#         # Caminho da minuta Padrao
#         if sub_pasta != "":
#             caminho_nota_minutas_modelo = (
#                 get_caminho_minutas_padrao(tipo_registro_atual, ("/" + sub_pasta))
#                 + "/"
#                 + str(minuta_atual_id)
#                 + ".docx"
#             )
#         else:
#             caminho_nota_minutas_modelo = (
#                 get_caminho_minutas_padrao(tipo_registro_atual, "") + "/" + str(minuta_atual_id) + ".docx"
#             )

#         # print('caminho_nota_minutas_modelo', caminho_nota_minutas_modelo)

#         # lista de arquivos a EXCLUIR
#         with contextlib.suppress(Exception):
#             lista_arquivos_excluir.append(caminho_nota_minutas_final)

#     # Copiando o modelo
#     if os.path.exists(caminho_nota_minutas_modelo):
#         shutil.copyfile(caminho_nota_minutas_modelo, caminho_nota_minutas_criar)

#     # RETORNAR O NOME DO ARQUIVO CRIADO
#     return caminho_nota_minutas_criar, caminho_nota_minutas_final


# def gerar_nota_de_devolucao(pedido_item_id, opcao_nota=0):
#     from apps.comum.utils import formatar_moeda

#     global pedido_atual, protocolo_atual, numero_ato_praticado_atual, ato_praticado_atual_id

#     # print("Passo 1 - Nota de devolucao para: pedido_item_id", pedido_item_id)
#     pedido_item_atual = pedido_item_id

#     # Atualizar os valores do pedido atual
#     # print("Passo 2 - Nota de devolucao para: pedido_item_id", pedido_item_id)
#     # Atualizar o protocolo atual
#     # (
#     #     pedido_item_atual,
#     #     pedido_atual,
#     #     protocolo_atual,
#     #     ato_praticado_atual_id,
#     #     titulo_atual_id,
#     # ) = Atualizar_Protocolo_Atual(pedido_item_id)

#     # Atualizar_Protocolo_Atual(pedido_item_id)

#     # Filtrando as respostas que deram diferenca
#     # print("Passo 3 - Nota de devolucao para: pedido_item_id", pedido_item_id)
#     # perguntas = CheckListRealizado.objects.filter(Q(pedido_item_id=pedido_item_id)).exclude(resposta='.')
#     perguntas = CheckListRealizado.objects.filter(pedido_item_id=pedido_item_id)

#     # Limpar todas as perguntas registradas do item do protocolo
#     limpar_registrar_perguntas_divergentes_protocolo(pedido_item_id)

#     list_perguntas = []
#     for item in perguntas:
#         # list_perguntas.append(item.perguntas_id)

#         if item.resposta != item.resposta_correta:
#             list_perguntas.append(item.perguntas_id)

#             # Registrar nas pendencias do protocolo as perguntas DIVERGENTES
#             registrar_perguntas_divergentes_protocolo(
#                 resposta=item.resposta,
#                 resposta_correta=item.resposta_correta,
#                 estado_civil=item.estado_civil,
#                 perguntas=item.perguntas,
#                 pessoa=item.pessoa,
#                 conferido_usuario=item.funcionarios,
#                 pedido_item=str(item.pedido_item),
#                 pedidos=str(pedido_atual),
#                 ordem=item.ordem,
#             )

#     # Filtrando o nome dos arquivos com previsao LEGAL
#     previsao_legal = Pergunta.objects.filter(id__in=list_perguntas)
#     list_previsao_legal = []
#     for item in previsao_legal:
#         if item.previsao_legal is not None:
#             list_previsao_legal.append(item.previsao_legal)

#     diretorior_ged_nota_devolucao = Configuracao.obter("diretorio_ged_nota_devolucao")
#     # Gerando o modelo da nota devolucao
#     caminho_nota_devolucao_inicio_modelo = diretorior_ged_nota_devolucao + "/Modelo/Exigencia_INICIO.docx"
#     diretorior_ged_nota_devolucao + "/Modelo/Exigencia_FIM.docx"

#     # Gerando modelo temporario
#     caminho_nota_devolucao_modelo = (
#         diretorior_ged_nota_devolucao + "/" + str(random.random()).replace(".", "") + ".docx"
#     )
#     try:
#         shutil.copyfile(caminho_nota_devolucao_inicio_modelo, caminho_nota_devolucao_modelo)
#     except FileNotFoundError:
#         logger.error(f"The file {caminho_nota_devolucao_inicio_modelo} does not exist.")
#         return None
#         # Handle the error appropriately - perhaps stop execution or provide an alternative action

#     # print("Passo 5 - Nota de devolucao para: pedido_item_id", pedido_item_id)

#     # UNIFICANDO OS ARQUIVO
#     filename_master = "Modelo_Previsao_Legal.docx"

#     # Gerando a lista inicial
#     files_list = ["Exigencia_INICIO.docx"]

#     # NOTA DE PAGAMENTO
#     if not previsao_legal.exists() or int(opcao_nota) == 1:
#         list_previsao_legal = []
#         list_previsao_legal.append("Pagamento.docx")

#     # Gerando todas as previsoes legais
#     for previsao_legal in list_previsao_legal:
#         if previsao_legal != ".":
#             files_list.append(previsao_legal)

#     # Gerando a lista Final
#     files_list.append("Exigencia_FIM.docx")

#     # Combinando os arquivos
#     caminho_nota_devolucao_criar = combine_all_docx(
#         filename_master=filename_master,
#         files_list=files_list,
#         diretorio_modelo=diretorior_ged_nota_devolucao,
#         nome_salvar_arquivo=caminho_nota_devolucao_modelo,
#     )

#     caminho_nota_devolucao_criar = (
#         diretorior_ged_nota_devolucao + "/Temp_" + str(protocolo_atual).split(".")[0] + ".docx"
#     )

#     # print("Passo 8 - Nota de devolucao para: pedido_item_id", pedido_item_id)
#     # print("Passo 9 - Nota de devolucao para: pedido_item_id", pedido_item_id)

#     # Copiando o modelo
#     shutil.copyfile(caminho_nota_devolucao_modelo, caminho_nota_devolucao_criar)

#     # print("Passo 10 - Nota de devolucao para: pedido_item_id", pedido_item_id)

#     # DADOS DO PROTOCOLO
#     protocolo = Livro01Protocolo.objects.filter(numero_protocolo=protocolo_atual).first()

#     # DADOS DO PEDIDO
#     pedido = Pedido.objects.filter(pk=pedido_atual).first()

#     # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
#     pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
#     # pedido_id       = int(protocolo.pedido._itens.pedido_id)
#     # ato_id           = int(protocolo.pedido._itens.ato_id)
#     # codigo_tabela    = str(protocolo.pedido._itens.codigo_tabela)
#     # numero_ri        = str(protocolo.pedido._itens.numero_ri)
#     # numero_ato        = str(protocolo.pedido._itens.numero_ato)
#     numero_ato_praticado_atual = str(pedido_item.numero_ato)
#     ato_praticado_atual_id = int(pedido_item.ato_id)

#     # OBTER O VALOR DA DIFERENCA
#     pedido_item = PedidoItem.objects.filter(pedido=pedido_atual).first()

#     valor_total_protocolo = pedido_item.pedido.valor_total_protocolo
#     valor_total_caixa = Financeiro.objects.total_caixa(pedido_atual) or 0
#     valor_pagar = formatar_moeda(str(valor_total_protocolo - valor_total_caixa))

#     # print("Passo 11 - Nota de devolucao para: pedido_item_id", pedido_item_id)

#     # RETORNAR O NOME DO ARQUIVO CRIADO
#     # Atualizar os dados da nota de devolucao
#     return atualizando_nota_devolucao(
#         numero_protocolo=protocolo_atual,
#         pedido_item_atual=pedido_item_atual,
#         data_protocolo=protocolo.data_protocolo,
#         data_prevista=str(pedido.data_prevista),
#         nome_solicitante=pedido.nome_solicitante_formatado,
#         nome_titulo=str(pedido_item.ato.tipo_ato),
#         tipo_registro=str(pedido_item.tipo_registro),
#         numero_matricula=str(pedido_item.numero_registro),
#         caminho_nota_devolucao_criar=caminho_nota_devolucao_criar,
#         valor_pagar=valor_pagar,
#         pedido_atual=pedido_atual,
#         numero_ato=str(pedido_item.numero_ato),
#     )


# # Gerar o livro 02 para o texto da ficha
# def gerar_texto_livro02(request, pedido_item_id, numero_protocolo, pedidos_atual_id, login_atual):
#     global \
#         pedido_atual, \
#         protocolo_atual, \
#         pedido_item_atual, \
#         minuta_atual_id, \
#         ato_praticado_atual, \
#         numero_matricula_atual, \
#         tipo_registro_atual, \
#         lista_variaveis_temporaria, \
#         lista_indice_temporaria, \
#         configuracao_id_cidade_atual, \
#         configuracao_id_estado_atual, \
#         configuracao_id_nome_oficial, \
#         codigo_tabela_atual, \
#         numero_ato_praticado_atual, \
#         ato_praticado_atual_id

#     # SELECIONAR AS CHAVES PELO PEDIDOS
#     data_protocolo, _nome_solicitante_formatado, _data_prevista = "", "", ""

#     lista_arquivos_excluir = []

#     # DADOS DO PROTOCOLO
#     protocolo = Livro01Protocolo.objects.filter(numero_protocolo=numero_protocolo).first()
#     data_protocolo = str(protocolo.data_protocolo)
#     data_protocolo_extenso = str(protocolo.data_protocolo)

#     # DADOS DO PEDIDO
#     pedido = Pedido.objects.filter(pk=pedidos_atual_id)
#     str(pedido.nome_solicitante_formatado)
#     str(pedido.data_prevista)

#     # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
#     pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

#     int(pedido_item.pedido_id)
#     int(pedido_item.ato_id)
#     str(pedido_item.ato.tipo_ato)
#     str(pedido_item.numero_registro)
#     numero_matricula_atual = str(pedido_item.numero_registro)
#     tipo_registro = str(pedido_item.tipo_registro)
#     codigo_tabela = str(pedido_item.codigo_tabela)
#     numero_ato = str(pedido_item.numero_ato)
#     str(pedido_item.numero_ri)
#     valor_emolumento = str(pedido_item.valor_emolumento)
#     valor_recompe = str(pedido_item.valor_fundo_estado)
#     valor_tfj = str(pedido_item.valor_tfj)
#     valor_issqn = str(pedido_item.issqn)
#     valor_total = str(pedido_item.valor_total)
#     ato_praticado_atual = str(pedido_item.numero_ato)
#     codigo_tabela_atual = str(pedido_item.codigo_tabela)
#     quantidade = str(pedido_item.cdhu).split(".")[0]
#     numero_ato_praticado_atual = str(pedido_item.numero_ato)
#     ato_praticado_atual_id = pedido_item.ato_id

#     # Valores do documento
#     valor_documento = str(pedido_item.valor_avaliacao)
#     valor_documento_extenso = str(pedido_item.valor_avaliacao)
#     valor_itbi = str(pedido_item.valor_itbi)
#     valor_itbi_extenso = str(pedido_item.valor_itbi)

#     # Formatar valores
#     try:
#         valor_credito = str(pedido_item.valor_avaliacao).split(".")[0]
#     except Exception:
#         logger.exception("ERRO")
#         valor_credito = str(0)

#     valor_credito_extenso = valor_credito

#     # Formatar valores Nulos
#     if str(valor_documento) == "None" or str(valor_documento) == "":
#         valor_documento = str(0)
#     if str(valor_itbi) == "None" or str(valor_itbi) == "":
#         valor_itbi = str(0)

#     # Valores formatados para gerar
#     valor_credito_extenso = str(valor_credito_extenso).replace(".", ",")
#     valor_documento_extenso = str(valor_documento_extenso).replace(".", ",")
#     valor_itbi_extenso = str(valor_itbi_extenso).replace(".", ",")

#     # Valores por extenso
#     valor_credito_extenso = gerar_valor_extenso(valor_credito_extenso)
#     valor_documento_extenso = gerar_valor_extenso(valor_documento_extenso)
#     valor_itbi_extenso = gerar_valor_extenso(valor_itbi_extenso)

#     # FILTRANDO O SELO
#     selo_eletronico, codigo_de_seguranca, utilizado_em, data_selo_extenso = "", "", "", ""
#     selo = SeloEletronico.objects.filter(pedido_item=pedido_item).first()
#     selo_eletronico = str(selo.codigo_sequencial_unico)
#     codigo_de_seguranca = str(selo.codigo_de_seguranca)
#     utilizado_em = str(selo.utilizado_em)
#     data_selo_extenso = str(selo.utilizado_em)

#     # FORMATAR VALORES
#     try:
#         valor_credito = real_br__mask(valor_credito)
#     except Exception:
#         logger.exception("ERRO")
#         valor_credito = "0,00"

#     dt_momento_atual = get_data_e_hora_por_opcao(1)

#     # FORMATAR PROTOCOLO
#     numero_protocolo_atual = numero_protocolo
#     numero_protocolo_atual = formatar_variavel(str(numero_protocolo_atual), "NUMEROMATRICULA")
#     codigo_de_seguranca = formatar_variavel(codigo_de_seguranca, "CODSEGURANCAMG")
#     valor_emolumento = real_br_money_mask(formatar_variavel(valor_emolumento, "VALORFINANCEIRO"))
#     valor_tfj = real_br_money_mask(formatar_variavel(valor_tfj, "VALORFINANCEIRO"))
#     valor_recompe = real_br_money_mask(formatar_variavel(valor_recompe, "VALORFINANCEIRO"))
#     valor_issqn = real_br_money_mask(formatar_variavel(valor_issqn, "VALORFINANCEIRO"))
#     valor_total = real_br_money_mask(formatar_variavel(valor_total, "VALORFINANCEIRO"))
#     data_protocolo = formatar_data(data_protocolo, 1)
#     data_protocolo_extenso = formatar_data(data_protocolo_extenso, 2)

#     numero_matricula_atual = formatar_variavel(numero_matricula_atual, "NUMEROMATRICULA")

#     # Valores do documento
#     valor_documento = real_br_money_mask(formatar_variavel(valor_documento, "VALORFINANCEIRO"))
#     valor_itbi = real_br_money_mask(formatar_variavel(valor_itbi, "VALORFINANCEIRO"))

#     try:
#         utilizado_em = formatar_data(utilizado_em, 1)
#         data_selo_extenso = formatar_data(data_selo_extenso, 2)

#     except Exception:
#         logger.exception("ERRO")
#         utilizado_em = ""
#         data_selo_extenso = ""

#     if request.POST.get("cbxMinuta") is not None:
#         minuta_atual_id = request.POST.get("cbxMinuta")

#     print("Gerando", pedido_item.pk, minuta_atual_id)

#     # Gerar o nome da nota de minuta do protocolo
#     arquivo_gerado, arquivo_gerado_final = gerar_nota_minuta(pedido_item, minuta_atual_id)

#     print("Gerado", arquivo_gerado, arquivo_gerado_final)

#     # Lista com arquivos temporarios a serem apagados
#     try:
#         lista_arquivos_excluir.append(arquivo_gerado)
#         lista_arquivos_excluir.append(arquivo_gerado_final)
#     except Exception:
#         logger.exception("ERRO")
#         raise

#     # Ler a minuta - Gerada
#     if os.path.exists(arquivo_gerado):
#         # ler_minuta_origem(document, arquivo_gerado)
#         document = ler_minuta_origem(arquivo_gerado)
#     else:
#         html_template = loader.get_template("page-500.html")
#         return HttpResponse(html_template.render({}, request))

#     # print(" ********* LISTA DE VARIAVEIS ENCONTRADAS ********* ") - LIGADO A TABELA DE "PerguntaMinuta" obrigatorio cadastrar
#     nome_engenheiro = get_parametros_variaveis_temporaria("1", lista_variaveis_temporaria, lista_indice_temporaria)
#     crea_engenheiro = get_parametros_variaveis_temporaria("2", lista_variaveis_temporaria, lista_indice_temporaria)
#     art_engenheiro = get_parametros_variaveis_temporaria("3", lista_variaveis_temporaria, lista_indice_temporaria)
#     data_memorial = get_parametros_variaveis_temporaria("4", lista_variaveis_temporaria, lista_indice_temporaria)
#     livro_notas = get_parametros_variaveis_temporaria("5", lista_variaveis_temporaria, lista_indice_temporaria)
#     folha_notas = get_parametros_variaveis_temporaria("6", lista_variaveis_temporaria, lista_indice_temporaria)
#     data_notas = get_parametros_variaveis_temporaria("7", lista_variaveis_temporaria, lista_indice_temporaria)
#     atos_anteriores = get_parametros_variaveis_temporaria("8", lista_variaveis_temporaria, lista_indice_temporaria)
#     data_alienacao = get_parametros_variaveis_temporaria("9", lista_variaveis_temporaria, lista_indice_temporaria)
#     finalidade = get_parametros_variaveis_temporaria("10", lista_variaveis_temporaria, lista_indice_temporaria)
#     forma_utilizacao = get_parametros_variaveis_temporaria("11", lista_variaveis_temporaria, lista_indice_temporaria)
#     encargos_juros = get_parametros_variaveis_temporaria("12", lista_variaveis_temporaria, lista_indice_temporaria)
#     forma_pagamento = get_parametros_variaveis_temporaria("13", lista_variaveis_temporaria, lista_indice_temporaria)
#     praca_pagamento = get_parametros_variaveis_temporaria("14", lista_variaveis_temporaria, lista_indice_temporaria)
#     cartorio_notas = get_parametros_variaveis_temporaria("15", lista_variaveis_temporaria, lista_indice_temporaria)
#     cartorio_notas_cidade = get_parametros_variaveis_temporaria(
#         "16",
#         lista_variaveis_temporaria,
#         lista_indice_temporaria,
#     )
#     data_pagamento_itbi = get_parametros_variaveis_temporaria(
#         "17",
#         lista_variaveis_temporaria,
#         lista_indice_temporaria,
#     )
#     valor_pago_itbi = get_parametros_variaveis_temporaria("18", lista_variaveis_temporaria, lista_indice_temporaria)
#     livro03_numero = get_parametros_variaveis_temporaria("19", lista_variaveis_temporaria, lista_indice_temporaria)
#     livro03_data_emissao = get_parametros_variaveis_temporaria(
#         "20",
#         lista_variaveis_temporaria,
#         lista_indice_temporaria,
#     )
#     ato_cancelamento_alienacao = get_parametros_variaveis_temporaria(
#         "21",
#         lista_variaveis_temporaria,
#         lista_indice_temporaria,
#     )

#     # limpar lista
#     lista_variaveis_temporaria, lista_indice_temporaria = [], []

#     # Filtrar os dados do livro 3 no livro 2
#     (
#         livro03_numero_cedula,
#         livro03_data_abertura,
#         livro03_nome_devedor,
#         livro03_garantias,
#         livro03_numero_registro,
#         livro03_tipo_ato,
#         livro03_nome_credor,
#         livro03_nome_credor_cpf,
#     ) = ("", "", "", "", "", "", "", "")

#     if str(livro03_numero) != "None" and str(livro03_numero) != "":
#         try:
#             (
#                 livro03_numero_cedula,
#                 livro03_data_abertura,
#                 livro03_nome_devedor,
#                 livro03_garantias,
#                 livro03_numero_registro,
#                 livro03_tipo_ato,
#                 livro03_nome_credor,
#                 livro03_nome_credor_cpf,
#             ) = Livro03.objects.get_dados_do_livro03_em_dict(livro03_numero)

#             # Formatar o numero da matricula
#             livro03_numero = formatar_variavel(str(livro03_numero), "NUMEROMATRICULA")
#         except Exception:
#             logger.exception("ERRO")

#     # Processar as substituicoes - LV2
#     if tipo_registro == "A":
#         # Filtrar Registro Auxiliar
#         pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
#         # registro_auxiliar = models.filtrar_imovel_pedidos_itens_LV3((pedido_item_id))
#         dados_do_imovel_no_livro03 = pedido_item.get_dados_do_registro_auxiliar()

#         # OBTER A ID AUXILIAR
#         registro_auxiliar_id = dados_do_imovel_no_livro03["registro_auxiliar_id"]
#         data_emissao_cedula = str(dados_do_imovel_no_livro03["data_abertura_id"])
#         str(dados_do_imovel_no_livro03["data_vencimento_id"])
#         cancelado_em = str(dados_do_imovel_no_livro03["cancelado_em_id"])
#         numero_cedula_l3 = str(dados_do_imovel_no_livro03["numero_cedula_l_id3"])

#         # Obter data emissao
#         data_emissao_cedula_ext = formatar_data(data_emissao_cedula, 2)
#         data_emissao_cedula = formatar_data(data_emissao_cedula, 1)
#         cancelado_em = formatar_data(cancelado_em, 1)

#         # PEGANDO OS DADOS DAS GARANTIAS
#         Livro03Garantia.objects.filter(registro_auxiliar_id=registro_auxiliar_id)

#         # TODOs os vinculos
#         credor, emitente, garantidor, avalista = "", "", "", ""

#         credor_atual = Livro03Ligacao.objects.filter(
#             registro_auxiliar_id=registro_auxiliar_id,
#             figuras_id__in=configuracao_id_credor,
#         )
#         for nome in credor_atual:
#             credor = credor + ", " + str(nome.pessoa.nome)

#         configuracao_id_devedor = list(Configuracao.get_lista("devedor_id", "INTEIRO"))

#         devedor_atual = Livro03Ligacao.objects.filter(
#             Q(registro_auxiliar_id=registro_auxiliar_id) & Q(figuras_id__in=configuracao_id_devedor),
#         )
#         for nome in devedor_atual:
#             emitente = emitente + ", " + str(nome.pessoa.nome)

#         avalista_atual = Livro03Ligacao.objects.filter(
#             Q(registro_auxiliar_id=registro_auxiliar_id) & Q(figuras_id__in=configuracao_id_avalista),
#         )
#         for nome in avalista_atual:
#             avalista = avalista + ", " + str(nome.pessoa.nome)

#         garantidor_atual = Livro03Ligacao.objects.filter(
#             Q(registro_auxiliar_id=registro_auxiliar_id) & Q(figuras_id__in=configuracao_id_fiel_depositario),
#         )
#         for nome in garantidor_atual:
#             garantidor = garantidor + ", " + str(nome.pessoa.nome)

#         # PEGANDO DADOS DO CREDOR
#         credor = str(credor[1:100]).strip()
#         emitente = str(emitente[1:100]).strip()
#         avalista = str(avalista[1:100]).strip()
#         garantidor = str(garantidor[1:100]).strip()

#         # GERAR AS MINUTAS AQUI
#         Get_Livro_3(
#             numero_livro_3=numero_matricula_atual,
#             data_atual_extenso=dt_momento_atual,
#             data_atual=get_data_e_hora_por_opcao(2),
#             numero_protocolo=numero_protocolo_atual,
#             data_protocolo=data_protocolo,
#             valor_emolumento=valor_emolumento,
#             valor_tfj=valor_tfj,
#             valor_recompe=valor_recompe,
#             valor_issqn=valor_issqn,
#             valor_total=valor_total,
#             codigo_tabela=codigo_tabela,
#             selo_eletronico=selo_eletronico,
#             codigo_seguranca=codigo_de_seguranca,
#             data_utilizacao=utilizado_em,
#             data_utilizacao_extenso=data_selo_extenso,
#             data_emissao_cedula_extenso=data_emissao_cedula_ext,
#             numero_cedula_l3=numero_cedula_l3,
#             data_emissao_cedula=data_emissao_cedula,
#             emitente=emitente,
#             garantidor=garantidor,
#             credor=credor,
#             avalista=avalista,
#             data_vencimento=cancelado_em,
#             valor_credito=valor_credito,
#             valor_credito_extenso=valor_credito_extenso,
#             folha_protocolo=folha_notas,
#             livro_protocolo=livro_notas,
#             data_vencimento_verificar=cancelado_em,
#             nome_engenheiro=nome_engenheiro,
#             numero_crea_engenheiro=crea_engenheiro,
#             numero_art=art_engenheiro,
#             data_memorial=data_memorial,
#             data_notas=data_notas,
#             numero_ato_praticado=numero_ato,
#             quantidade=quantidade,
#             atos_anteriores=atos_anteriores,
#             data_alienacao=data_alienacao,
#             cidade_atual=configuracao_id_cidade_atual,
#             estado_atual=configuracao_id_estado_atual,
#             nome_oficial=configuracao_id_nome_oficial,
#             finalidade=finalidade,
#             forma_utilizacao=forma_utilizacao,
#             encargos_juros=encargos_juros,
#             forma_pagamento=forma_pagamento,
#             praca_pagamento=praca_pagamento,
#             login_atual=login_atual,
#             apenasnro_numero_ato_praticado=tipo_registro_atual,
#             data_protocolo_extenso=data_protocolo_extenso,
#             cartorio_notas=cartorio_notas,
#             cartorio_notas_cidade=cartorio_notas_cidade,
#             data_pagamento_itbi=data_pagamento_itbi,
#             valor_pago_itbi=valor_pago_itbi,
#             valor_documento=valor_documento,
#             valor_documento_extenso=valor_documento_extenso,
#             valor_itbi=valor_itbi,
#             valor_itbi_extenso=valor_itbi_extenso,
#             livro03_numero=livro03_numero,
#             livro03_numero_cedula=livro03_numero_cedula,
#             livro03_data_abertura=livro03_data_abertura,
#             livro03_data_emissao=livro03_data_emissao,
#             livro03_nome_devedor=livro03_nome_devedor,
#             livro03_garantias=livro03_garantias,
#             livro03_numero_registro=livro03_numero_registro,
#             livro03_tipo_ato=livro03_tipo_ato,
#             livro03_nome_credor=livro03_nome_credor,
#             livro03_nome_credor_cpf=livro03_nome_credor_cpf,
#             ato_cancelamento_alienacao=ato_cancelamento_alienacao,
#             document=document,
#         )

#     else:
#         # OBTER AS PESSOAS PARA O LIVRO - TRABALHANDO
#         Get_Livro_2(
#             numero_registro=numero_matricula_atual,
#             tipo_registro=tipo_registro_atual,
#             data_atual_extenso=dt_momento_atual,
#             data_atual=get_data_e_hora_por_opcao(2),
#             numero_protocolo=numero_protocolo_atual,
#             data_protocolo=data_protocolo,
#             nome_engenheiro=nome_engenheiro,
#             selo_eletronico=selo_eletronico,
#             codigo_seguranca=codigo_de_seguranca,
#             data_utilizacao=utilizado_em,
#             data_utilizacao_extenso=data_selo_extenso,
#             codigo_tabela=codigo_tabela,
#             valor_emolumento=valor_emolumento,
#             valor_tfj=valor_tfj,
#             valor_recompe=valor_recompe,
#             valor_issqn=valor_issqn,
#             valor_total=valor_total,
#             numero_crea_engenheiro=crea_engenheiro,
#             numero_art=art_engenheiro,
#             data_memorial=data_memorial,
#             folha_notas=folha_notas,
#             livro_notas=livro_notas,
#             data_notas=data_notas,
#             numero_ato_praticado=numero_ato,
#             ato_praticado_atual=ato_praticado_atual,
#             apenasnro_numero_ato_praticado=tipo_registro_atual,
#             valor_credito=valor_credito,
#             valor_credito_extenso=valor_credito_extenso,
#             quantidade=quantidade,
#             atos_anteriores=atos_anteriores,
#             data_alienacao=data_alienacao,
#             cidade_atual=configuracao_id_cidade_atual,
#             estado_atual=configuracao_id_estado_atual,
#             nome_oficial=configuracao_id_nome_oficial,
#             finalidade=finalidade,
#             forma_utilizacao=forma_utilizacao,
#             encargos_juros=encargos_juros,
#             forma_pagamento=forma_pagamento,
#             praca_pagamento=praca_pagamento,
#             login_atual=login_atual,
#             data_protocolo_extenso=data_protocolo_extenso,
#             cartorio_notas=cartorio_notas,
#             cartorio_notas_cidade=cartorio_notas_cidade,
#             data_pagamento_itbi=data_pagamento_itbi,
#             valor_pago_itbi=valor_pago_itbi,
#             valor_documento=valor_documento,
#             valor_documento_extenso=valor_documento_extenso,
#             valor_itbi=valor_itbi,
#             valor_itbi_extenso=valor_itbi_extenso,
#             livro03_numero=livro03_numero,
#             livro03_numero_cedula=livro03_numero_cedula,
#             livro03_data_abertura=livro03_data_abertura,
#             livro03_data_emissao=livro03_data_emissao,
#             livro03_nome_devedor=livro03_nome_devedor,
#             livro03_garantias=livro03_garantias,
#             livro03_numero_registro=livro03_numero_registro,
#             livro03_tipo_ato=livro03_tipo_ato,
#             livro03_nome_credor=livro03_nome_credor,
#             livro03_nome_credor_cpf=livro03_nome_credor_cpf,
#             ato_cancelamento_alienacao=ato_cancelamento_alienacao,
#             document=document,
#         )

#     print("Baixar arquivo 01", datetime.now())

#     # print("Salvar documento:", arquivo_gerado_final)
#     # Salvar documento temporario
#     Salvar_Documento_Alterado(document, arquivo_gerado_final)

#     print("Baixar arquivo 02", datetime.now())

#     # Pegando apenas o numero do protocolo
#     numero_nota_minuta = str(numero_matricula_atual)

#     # Processar os ajustes de paragrafos e caracteres - Nome_Arquivo_Minuta
#     arquivo_gerado_final, arquivo_gerado_final_html = converter_docx_para_html_e_voltar(
#         arquivo_gerado_final,
#     )

#     # GRAVAR HTML NO BANCO DE DADOS
#     try:
#         gravar_html_bd_livro02(pedido_item_id, arquivo_gerado_final_html, numero_ato)
#     except Exception:
#         logger.exception("ERRO")

#     return arquivo_gerado_final, numero_nota_minuta, tipo_registro, lista_arquivos_excluir


# # Baixar Word
# def test_export_docx_general(self) -> None:
#     """Ensure general content like
#     status response, content type, file name exported correctly.
#     """
#     response = self.client.get(reverse("export_docx"))
#     assert response.status_code == status.HTTP_200_OK
#     assert response.get("Content-Type") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#     filename = response.get("Content-Disposition").split("= ")
#     assert filename == "Test.docx"


# class DocumentHTMLParser(HTMLParser):
#     """Document Within HTML Parser."""

#     def __init__(self, document) -> None:
#         """Override __init__ method."""
#         HTMLParser.__init__(self)
#         self.document = document
#         self.paragraph = None
#         self.run = None

#     def add_paragraph_and_feed(self, html) -> None:
#         """Custom method where add paragraph and feed."""
#         self.paragraph = self.document.add_paragraph()
#         self.feed(html)

#     def handle_starttag(self, tag, attrs) -> None:
#         """Override handle_starttag method."""
#         self.run = self.paragraph.add_run()

#         if tag in ["ul"]:
#             self.run.add_break()
#         if tag in ["li"]:
#             self.run.add_text("        \u2022    ")

#     def handle_endtag(self, tag) -> None:
#         """Override handle_endtag method."""
#         if tag in ["li"]:
#             self.run.add_break()

#     def handle_data(self, data) -> None:
#         """Override handle_data method."""
#         self.run.add_text(data)


# # Exibir_minuta_lv2
# class ExportDocx_lv2(APIView):
#     global pedido_atual, protocolo_atual, pedido_item_atual, minuta_atual_id, lista_arquivos_excluir, ato_praticado_atual, numero_matricula_atual, tipo_registro_atual, lista_variaveis_temporaria, lista_indice_temporaria, configuracao_id_cidade_atual, configuracao_id_estado_atual, configuracao_id_nome_oficial, codigo_tabela_atual, numero_ato_praticado_atual, ato_praticado_atual_id

#     # print("INICIO 4: ", minuta_atual_id)
#     # print("Selecionado Minuta: ", minuta_atual_id)

#     # def get_context_data(self, *args, **kwargs):

#     def get(self, request, *args, **kwargs):
#         global \
#             minuta_atual_id, \
#             lista_variaveis_temporaria, \
#             lista_indice_temporaria, \
#             configuracao_id_cidade_atual, \
#             configuracao_id_estado_atual, \
#             configuracao_id_nome_oficial, \
#             lista_arquivos_excluir

#         # Pegando a chave pedidos ites que veio da view name= "download_doc_file" e do html href= "{% url 'home:download_doc_file' pedido_item_id %}
#         pedido_item_id = kwargs["pedido_item_id"]

#         # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
#         pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

#         pedido_id = int(pedido_item.pedido_id)
#         # ato_id = int(protocolo.ato_id)
#         # ato_praticado = str(protocolo.tipo_ato)
#         # numero_registro_auxiliar = str(protocolo.numero_registro)
#         tipo_registro = str(pedido_item.tipo_registro)
#         # codigo_tabela = str(protocolo.codigo_tabela)
#         # numero_ri = str(protocolo.numero_ri)
#         # numero_ato = str(protocolo.numero_ato)

#         protocolo = Livro01Protocolo.objects.get(pedido_id=pedido_id)
#         numero_protocolo = str(protocolo.numero_protocolo)

#         # Usuario Atual
#         login_atual = str(request.user).upper()

#         # Gerar o livro 02 para o texto da ficha
#         (
#             arquivo_gerado_final,
#             numero_nota_minuta,
#             tipo_registro,
#             lista_arquivos_excluir,
#         ) = gerar_texto_livro02(
#             request,
#             pedido_item_id,
#             numero_protocolo,
#             pedido_id,
#             login_atual,
#         )

#         print("Baixar arquivo 03", datetime.now())

#         # if os.path.exists(arquivo_gerado_final):
#         document = Document(arquivo_gerado_final)

#         buffer = io.BytesIO()
#         document.save(buffer)  # save your memory stream
#         buffer.seek(0)  # rewind the stream

#         print("Baixar arquivo 05", datetime.now())

#         # put them to streaming content response
#         response = StreamingHttpResponse(
#             streaming_content=buffer,  # use the stream's content
#             content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#         )

#         print("Baixar arquivo 06", datetime.now())

#         # Enviar o tipo de imovel
#         texto_inicio_arquivo = "Minuta_lv3_" if tipo_registro == "A" else "Minuta_lv2_"

#         print("Baixar arquivo 07", datetime.now())

#         # Nome_Arquivo de nota devolucao
#         nome_arquivo_minuta = (
#             texto_inicio_arquivo + str(random.random()).replace(".", "") + str(numero_nota_minuta) + ".docx"
#         )

#         # DOWNLOAD ARQUIVO
#         # print("Baixar arquivo: ", pedido_item_atual, arquivo_gerado_final)
#         try:
#             print("Baixar arquivo 07A", datetime.now())
#             # set_atualizar_bd_externo(pedido_item_atual, arquivo_gerado_final)
#             print("Baixar arquivo 07B", datetime.now())
#         except Exception:
#             logger.exception("ERRO")

#         print("Baixar arquivo 08", datetime.now())

#         # Excluir arquivos temporarios
#         excluir_arquivos(lista_arquivos_excluir)

#         response["Content-Disposition"] = "attachment;filename= " + str(nome_arquivo_minuta)
#         response["Content-Encoding"] = "UTF-8"
#         # else:
#         #    response['Content-Disposition'] = 'attachment;filename=' + str(arquivo_gerado)
#         #    response["Content-Encoding"] = 'UTF-8'

#         print("Baixar arquivo 09", datetime.now())

#         return response
#         # return redirect("https://pt.stackoverflow.com/")

#     # return response


# # Exibir_nota_devolucao
# class ExportDocx(View):
#     def get(self, request, *args, **kwargs):
#         pedido_item_id = kwargs.get("pedido_item_id")
#         opcao_nota = kwargs.get("opcao_nota")

#         arquivo_gerado = gerar_nota_de_devolucao(pedido_item_id, opcao_nota)

#         if not arquivo_gerado:
#             msg = "Nota de devolução não encontrada. O metodo gerar_nota_de_devolucao retornou vazio."
#             raise Http404(
#                 msg,
#             )

#         numero_nota_devolucao = self.get_numero_nota(arquivo_gerado)
#         if arquivo_gerado and numero_nota_devolucao:
#             buffer = self.get_buffer_documento(arquivo_gerado)
#             nome_arquivo_devolucao = f"Nota_Devolucao_{numero_nota_devolucao}.docx"
#             return FileResponse(
#                 buffer,
#                 as_attachment=True,
#                 filename=nome_arquivo_devolucao,
#                 content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#             )
#         else:
#             msg = "Nota de devolução não encontrada"
#             raise Http404(msg)

#     def get_numero_nota(self, arquivo_gerado):
#         # Verifica se o arquivo_gerado é uma string válida
#         if not isinstance(arquivo_gerado, str) or not arquivo_gerado:
#             msg = "O nome do arquivo gerado deve ser uma string não vazia."
#             raise ValueError(msg)

#         nome_arquivo = os.path.basename(arquivo_gerado)

#         # Verifica se nome_arquivo tem a extensão .docx
#         if not nome_arquivo.lower().endswith(".docx"):
#             msg = "O arquivo fornecido não possui a extensão .docx"
#             raise ValueError(msg)

#         # Remove a extensão e qualquer ponto adicional do nome do arquivo
#         numero_nota = nome_arquivo[:-5]  # Remove a extensão '.docx'

#         return numero_nota.replace(".", "")  # Remove pontos adicionais

#     def get_buffer_documento(self, arquivo_gerado):
#         document = Document(arquivo_gerado)
#         buffer = io.BytesIO()
#         document.save(buffer)
#         buffer.seek(0)

#         # GRAVAR NOTA DEVOLUCAO BANCO

#         return buffer


# # Exibir_minuta_imagem
def documento_arquivo_view(request, imovel_id, tipo="M") -> None: ...


#         raise Http404(images)
#     path_dir = get_caminho_do_arquivo(tipo, imovel_id)
#     ext = path_dir.split(".")[-1].lower()
#     file = None
#     try:
#         if ext != "pdf":
#             file = io.BytesIO()
#             images = []
#             diretorio = r"//192.168.1.195/IMAGENS/GED/Matriculas/007"
#             padrao = "007622"
#             arquivos = os.listdir(diretorio)
#             for arquivo in arquivos:
#                 print("caminho: ", arquivo)
#                 if padrao in arquivo:
#                     caminho_completo = os.path.join(diretorio, arquivo)
#                     with Image.open(caminho_completo) as image:
#                         print("image: ", image)
#                         for i, page in enumerate(ImageSequence.Iterator(image)):
#                             page = page.convert("RGB")
#                             images.append(page)
#                         print("page: ", page)
#             if len(images) == 0:
#                 # Nao encontrar imagem
#                 path_dir = get_caminho_do_arquivo(tipo, 0)
#                 for caminho in glob.glob(path_dir + ".*"):
#                     with Image.open(caminho) as image:
#                         for i, page in enumerate(ImageSequence.Iterator(image)):
#                             page = page.convert("RGB")
#                             images.append(page)
#                 images[0].save(file, format="PDF")
#             elif len(images) == 1:
#                 images[0].save(file, format="PDF")
#             else:
#                 images[0].save(file, format="PDF", save_all=True, append_images=images[1:])

#                 for image in images:
#                     image.close()

#             del images

#             file.seek(0)
#         else:
#             file = open(path_dir, "rb")

#         return FileResponse(file, content_type="application/pdf")

#     except Exception as e:
#         logger.error(e, "documento_arquivo_view")
#         if file:
#             file.close()


# BUSCAR IMAGENS PELO NUMERO DO IMOVEL


class Livro02ImagensListView(LoginRequiredMixin, DetailView):
    """Tenta obter um objeto Livro02 baseando-se primeiro nos parâmetros numero_registro e tipo_registro fornecidos na URL. Se esses parâmetros não estiverem disponíveis, ela recorre ao método padrão get_object para buscar o objeto pelo ID. Isso permite que a mesma view seja usada para ambos os casos, simplificando o código e mantendo a flexibilidade."""

    model = Livro02
    template_name = "imagens/imagens_list.html"

    def get_object(self, queryset=None):
        numero_registro = self.kwargs.get("numero_registro")
        tipo_registro = self.kwargs.get("tipo_registro")
        if numero_registro and tipo_registro:
            obj = Livro02.objects.filter(
                numero=numero_registro,
                tipo=tipo_registro,
            ).first()
        else:
            obj = super().get_object(queryset=queryset)

        if not obj:
            messages.info(self.request, "Registro não encontrado")
            msg = "Registro não encontrado"
            raise Http404(msg)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registro = self.object
        try:
            # Supondo que `imagens` seja um método que retorna uma lista de URLs
            urls_imagens = registro.imagens()
            if not urls_imagens:
                messages.info(
                    self.request,
                    "Registro não possui imagens ou houve um erro ao tentar obter as imagens",
                )
                return context

            # Baixar as imagens e salvar localmente
            local_urls = []
            for url in urls_imagens:
                local_url = self.download_and_save_image(url)
                if local_url:
                    local_urls.append(local_url)

            context["urls"] = local_urls
        except Exception as e:
            logger.exception(f"{e}")  # Ou use uma função de log apropriada
            messages.error(
                self.request,
                "Houve um problema ao tentar obter as imagens deste imóvel",
            )
            return context

        return context

    def download_and_save_image(self, url: str) -> str:
        """Baixa a imagem a partir da URL, converte se necessário, e salva localmente, retornando a URL local."""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                # Separar o nome do arquivo
                base_filename = os.path.basename(url)
                name = os.path.splitext(base_filename)[0]
                # Aplicar slugify ao nome
                safe_name = slugify(name)
                # Caminho onde a imagem será salva
                temp_images_dir = os.path.join(settings.MEDIA_ROOT, "temp_images")
                # Garantir que o diretório exista
                if not os.path.exists(temp_images_dir):
                    os.makedirs(temp_images_dir)
                # Definir a extensão final da imagem
                final_extension = ".jpg"
                filename = f"{safe_name}{final_extension}"
                filepath = os.path.join(temp_images_dir, filename)

                # Abrir a imagem para verificar o formato
                image = Image.open(BytesIO(response.content))
                # Convertendo a imagem para RGB se for TIFF ou qualquer outro formato
                if image.format == "TIFF":
                    image = image.convert("RGB")
                # Salvar a imagem no formato JPEG
                image.save(filepath, format="JPEG")

                # Construir a URL relativa ao MEDIA_URL
                relative_filepath = os.path.relpath(filepath, settings.MEDIA_ROOT)
                return os.path.join(settings.MEDIA_URL, relative_filepath)
            else:
                logger.error(f"Erro ao baixar a imagem: {response.status_code}")
                return None
        except Exception as e:
            logger.exception(f"Erro ao baixar a imagem: {e}")
            return None


# Atualizar arquivos importados
class ImportarTitulosProtocolosView(View):
    def get(self, request, *args, **kwargs):
        # Listar e processar os arquivos PDF dos TITULOS
        processar_importar_titulo()

        return redirect(reverse("home:protocolo_search"))


class DownloadPDFFileView(View):
    def get(self, request, pedido_item_id):
        # Gerar o nome da nota de devolucao - DOCX
        nota_devolucao = self.gerar_nota_de_devolucao(pedido_item_id, 0)

        if not nota_devolucao:
            msg = "Erro ao gerar arquivo nota_devolucao"
            raise Http404(msg)

        # Gerar o nome da nota de devolucao - PDF
        filename = self.criar_nota_de_devolucao_em_pdf(nota_devolucao)
        # print("arquivo_gerado ", filename)
        # filename = 'Modelo.pdf'

        if filename:
            # Abre o arquivo para leitura do conteúdo
            with open(filename, "rb") as path:
                # Define o tipo mime
                mime_type, _ = mimetypes.guess_type(filename)

                # Define o valor de retorno do HttpResponse
                response = HttpResponse(path.read(), content_type=mime_type)

                # Define o cabeçalho HTTP para envio ao navegador
                response["Content-Disposition"] = f"attachment; filename={filename}"

                # Retorna o valor da resposta
                return response
        else:
            msg = "Erro ao criar arquivo PDF"
            raise Http404(msg)


# Baixar CSV dados
def download_csv_data(request):
    # response content type
    response = HttpResponse(content_type="text/csv")

    # decide the file name
    response["Content-Disposition"] = 'attachment; filename= "ThePythonDjango.csv"'

    # write the headers
    response.write("\ufeff".encode())
    writer = csv.writer(response, csv.excel)

    writer.writerow(
        [
            smart_str("Event Name"),
            smart_str("Start Date"),
            smart_str("End Date"),
            smart_str("Notes"),
        ],
    )

    # get data from database or from text file....
    events = "1;13;12;12"
    for event in events:
        writer.writerow(
            [
                smart_str(event),
                smart_str(event),
                smart_str(event),
                smart_str(event),
            ],
        )

    return response


# Baixar EXCELL dados
def download_excel_data(request):
    # content-type of response
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename= "ThePythonDjango.xls"'
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("sheet1")
    row_num = 0
    font_style = xlwt.XFStyle()
    columns = [
        "Column 1",
        "Column 2",
        "Column 3",
        "Column 4",
    ]
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    font_style = xlwt.XFStyle()
    data = [["1", "13", "12", "12"]]  # dummy method to fetch data.
    for my_row in data:
        row_num = row_num + 1
        ws.write(row_num, 0, my_row, font_style)
        ws.write(row_num, 1, my_row, font_style)
        ws.write(row_num, 2, my_row, font_style)
        ws.write(row_num, 3, my_row, font_style)
    wb.save(response)
    return response


# Creating a class based view
class GeneratePdf2(View):
    def get(self, request, *args, **kwargs):
        # getting the template
        template_name = "result_html_to_pdf.html"

        pdf = services.html_to_pdf(template_name)
        # pdf = html_to_pdf('checklist_resultado_list.html')

        # rendering the template
        return HttpResponse(pdf, content_type="application/pdf")
        # response['Content-Disposition'] = 'attachment; filename= "' + filename + '"'
        # return response


def generate_pdf(request):
    data = {}
    data["name"] = "https://www.pythoncircle.Com"
    data["DOB"] = "Jan 10, 2015"

    template = loader.get_template("result_html_to_pdf.html")
    html = template.render(data)

    # https://pypi.org/project/pdfkit/
    path_wkhtmltopdf = (
        r"D:\TESTE_12\django-datta-able-master\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    pdf = pdfkit.from_string(
        html,
        configuration=config,
        options={
            "quiet": "",
            "page-size": "A4",
            "margin-top": "0.75in",
            "margin-right": "0.75in",
            "margin-bottom": "0.75in",
            "margin-left": "0.75in",
            "encoding": "UTF-8",
            "javascript-delay": "550",
            "no-outline": None,
        },
    )

    filename = "out.pdf"

    """ assim baixa """
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename= "' + filename + '"'
    return response

    """ assim abre na tela automaticamente """
    return None
    # return HttpResponse(pdf, content_type='application/pdf')


# FILTRANDO PELA PRIMARY KEY
class BookDetailView(DetailView):
    """Por padrão, o DetailView exibirá apenas os campos de uma tabela. Se alguém quiser modificar esses."""

    " dados de contexto antes de enviá-los para o modelo ou adicionar algum campo extra, os dados de contexto  "
    " podem ser substituídos. Em geeks/views.py,"

    model = CheckListRealizado

    # override context data - OBTENDO PELO ID DO BOOK
    # path('book/<int:pk>', views.BookDetailView.as_view(), name='book-detail'),
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        # add extra field
        context["category"] = "MISC"
        context["categoryxx"] = "xxxMISC"
        return context


@login_required
def checklist_realizado_list(request, id):
    queryset = CheckListRealizado.objects.filter(pedido_item_id=id)

    context = {
        "pedido_item_id": id,
        "object_list": queryset,
    }

    return render(request, "checklist_resultado_list", context)


# class CheckListRealizadoListView(LoginRequiredMixin, ListView):
#     global current_user_atual

#     model = CheckListRealizado
#     template_name = "checklist_resultado_list.html"

#     # current_user_atual = str(request.user).upper()

#     # OBTER O PARAMETRO DA http://127.0.0.1:8000/books/388914/ e filtrar o
#     # id path('books/<id>/', views.BookListView.as_view(), name='books_correto_list_View'), trazendo apenas os dados do item 388914
#     def get_queryset(self):
#         # Atualizando pedido item atual
#         pedido_item_atual = self.kwargs["id"]

#         # Gravar o checklist realizado
#         # checklist_ato(self.request, self.kwargs['id'])

#         # return checkList_realizado.objects.filter(pedido_item_id=293736)
#         # template_name = "checklist_resultado_list.html"
#         return CheckListRealizado.objects.filter(pedido_item_id=self.kwargs["id"])
#         # return CheckListRealizado.objects.filter(pedido_item_id=self.kwargs['id']).order_by('-pub_date', 'headline')

#     def get_context_data(self, *args, **kwargs):
#         context = super(CheckListRealizadoListView, self).get_context_data(*args, **kwargs)
#         # template_name = "checklist_resultado_list.html"
#         # add extra field
#         context["pedido_item_id"] = self.kwargs["id"]

#         return context


# Filtrar e exibir pedidos_itens_imovel
class ChecklistImovelView(LoginRequiredMixin, ListView):
    model: CheckListRealizado = CheckListRealizado
    template_name = "checklist_resultado_list.html"
    tipo_registro_atual = None
    numero_matricula_atual = None

    def get_queryset(self: "ChecklistImovelView"):
        pedido_item_id = self.kwargs["id"]

        # Apagar o TRANSMITENTE
        self.model.objects.deletar_por_estado_civil(
            pedido_item_id,
            TipoParte.TRANSMITENTE,
        )

        # Apagar o IMOVEL
        self.model.objects.deletar_por_estado_civil(pedido_item_id, "I")

        # Filtrar os dadodod do imovel
        pedido_item: PedidoItem = PedidoItem.objects.get(pk=pedido_item_id)
        dados_do_registro_auxiliar = pedido_item.get_dados_do_registro_auxiliar()

        classe_id = dados_do_registro_auxiliar["classe_id"]
        self.tipo_registro_atual = dados_do_registro_auxiliar["tipo_registro"]
        self.numero_matricula_atual = dados_do_registro_auxiliar["numero_registro"]

        print("Salvar os Transmitentes no Checklist")

        # Listar todos os Transmitentes
        partes_transmitente = PedidoParteAto.objects.filter(
            pedido_item_id=pedido_item_id,
            status="T",
            vinculo__isnull=False,
        ).order_by("id")

        # print(len(partes_transmitente))
        # for item in partes_transmitente:
        #    print(item)

        for transmitente in partes_transmitente:
            print("# CPF = 10001")
            # CPF = 10001
            CheckListRealizado.objects.gravar(
                estado_civil_id="T",
                item_id=0,
                pergunta_id=10001,
                pessoa_id=transmitente.pessoa_id,
                funcionario_id=self.request.user.id,
                pedido_item_id=pedido_item_id,
                resposta=transmitente.pessoa.cpf,
                resposta_enviada_correta=transmitente.vinculos.pessoa.cpf,
                tabela_origem_id=transmitente.id,
                nome_tabela_origem="pedido_item_transmitente",
                coluna_tabela_origem="cpf",
            )

            # NOME = 10002
            CheckListRealizado.objects.gravar(
                estado_civil_id="T",
                item_id=0,
                pergunta_id=10002,
                pessoa_id=transmitente.pessoa_id,
                funcionario_id=self.request.user.id,
                pedido_item_id=pedido_item_id,
                resposta=transmitente.pessoa.nome,
                resposta_enviada_correta=transmitente.vinculos.pessoa.nome,
                tabela_origem_id=transmitente.id,
                nome_tabela_origem="pedido_item_transmitente",
                coluna_tabela_origem="nome",
            )

            # ESTADO CIVIL = 10003
            CheckListRealizado.objects.gravar(
                estado_civil_id="T",
                item_id=0,
                pergunta_id=10003,
                pessoa_id=transmitente.pessoa_id,
                funcionario_id=self.request.user.id,
                pedido_item_id=pedido_item_id,
                resposta=str(
                    transmitente.vinculos.estado_civil.descricao_estado_civil,
                ).upper(),
                resposta_enviada_correta=str(
                    transmitente.estado_civil.descricao_estado_civil,
                ).upper(),
                tabela_origem_id=transmitente.id,
                nome_tabela_origem="pedido_item_transmitente",
                coluna_tabela_origem="estado_civil",
            )

            # LANCAR O ENDERECO DO TRANSMITENTE
            if str(transmitente.estado_civil.descricao_estado_civil).upper() in [
                "JURIDICO",
                "JURÍDICO",
            ]:
                # print("ENDERECO JURIDICO DA SEDE DA EMPRESA")

                CheckListRealizado.objects.gravar(
                    categoria_id="T",
                    item_id=0,
                    pergunta_id=10033,
                    pessoa_id=transmitente.pessoa_id,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=transmitente.pessoa.endereco,
                    resposta_enviada_correta=transmitente.vinculos.pessoa.endereco,
                    tabela_origem_id=transmitente.id,
                    nome_tabela_origem="pedido_item_transmitente",
                    coluna_tabela_origem="endereco_pessoa",
                )

            # REGIME DE BENS = 10004
            regime1 = str(transmitente.tipo_regime_casamento.descricao_regime).upper()
            if str(regime1) == "NONE":
                regime1 = "".strip()

            try:
                if isinstance(
                    transmitente.vinculos.tipo_regime_casamento.id,
                    type(None),
                ):
                    regime2 = ""
                else:
                    regime2 = str(
                        transmitente.vinculos.tipo_regime_casamento.descricao_regime,
                    ).upper()

                    regime2 = "" if str(regime2) == "NONE" else str(regime2).strip()
            except Exception:
                logger.exception("ERRO")
                regime2 = ""

            # Limpar os itens
            regime1 = str(regime1).strip()
            regime2 = str(regime2).strip()

            CheckListRealizado.objects.gravar(
                categoria_id="T",
                item_id=0,
                pergunta_id=10004,
                pessoa_id=transmitente.pessoa_id,
                funcionario_id=self.request.user.id,
                pedido_item_id=pedido_item_id,
                resposta=regime1,
                resposta_enviada_correta=regime2,
                tabela_origem_id=transmitente.id,
                nome_tabela_origem="pedido_item_transmitente",
                coluna_tabela_origem="regime_bens",
            )

        # Listar todos os Endereco
        # Gerar Verificar ENDERECO - URBANO
        partes_imovel_urbano = PedidoItemImovel.objects.filter(
            pedido_item_id=pedido_item_id,
            opcao_imovel="U",
        )

        # Gerar Verificar ENDERECO - RURAL
        partes_imovel_rural = PedidoItemImovel.objects.filter(
            pedido_item_id=pedido_item_id,
            opcao_imovel="R",
        )

        # NAO FOR URBANO
        if classe_id != "R":
            # OBTER DADOS DO ENDERECO - URBANO
            dados_do_registro = pedido_item.get_dados_do_registro()
            # imoveis_urbano = filtrar_imovel_pedidos_itens(pedido_item_id)

            # ID do REGISTRO
            registro_id = str(dados_do_registro["imovel_id"])

            if str(registro_id) == "":
                registro_id = 0

            # Filtrar as Medidas do Imovel
            imovel_medida = ImovelMedida.objects.filter(imovel_id=registro_id).exists()

            if not imovel_medida:
                print("Não tem medidas")
                ImovelMedida.objects.criar_medidas_do_imovel(registro_id)

            for imovel_urbano in partes_imovel_urbano:
                print("VENDO URBANO ...........................")

                # Filtrar as Medidas do Imovel
                imovel_medida = ImovelMedida.objects.filter(
                    imovel_id=registro_id,
                ).first()

                # Filtrando as medidas de confrontacoes

                m_frente_metros = imovel_medida.m_frente_metros
                p_frente_metros = imovel_medida.p_frente_metros
                m_direito_metros = imovel_medida.m_direito_metros
                p_direito_metros = imovel_medida.p_direito_metros
                m_esquerdo_metros = imovel_medida.m_esquerdo_metros
                p_esquerdo_metros = imovel_medida.p_esquerdo_metros
                m_fundo_metros = imovel_medida.m_fundo_metros
                p_fundo_metros = imovel_medida.p_fundo_metros

                # SETOR = 10005
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10005,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.setor).upper(),
                    resposta_enviada_correta=str(dados_do_registro["setor_id"]).upper(),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="setor",
                )

                # QUADRA = 10006
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10006,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.quadra).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["quadra_id"],
                    ).upper(),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="quadra",
                )

                # LOTE = 10007
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10007,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.lote).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["numero_unidade_id"],
                    ).upper(),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="lote",
                )

                # NOME DA RUA = 10008
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10008,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.nome_rua).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["nome_rua_id"],
                    ).upper(),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="nome_rua",
                )

                # NUMERO DA RUA = 10009
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10009,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.numero_casa).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["numero_rua_id"],
                    ).upper(),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="numero_casa",
                )

                # AREA DO IMOVEL = 10010
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10010,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.area).upper(),
                    resposta_enviada_correta=str(dados_do_registro["area_id"]).upper(),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="area",
                )

                # IMOVEL COMERCIAL = 10011
                comercial = (
                    "Sim"
                    if str(dados_do_registro["comercial_id"]).upper() == "COMERCIAL"
                    else "Não"
                )
                urbano_comercial = (
                    "SIM" if str(imovel_urbano.comercial).upper() == "S" else "NÃO"
                )

                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10011,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=urbano_comercial,
                    resposta_enviada_correta=comercial,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="comercial",
                )

                # IMOVEL RESIDENCIAL = 10012
                residencial = (
                    "SIM"
                    if str(dados_do_registro["comercial_id"]).upper() == "RESIDENCIAL"
                    else "NÃO"
                )

                urbano_residencial = (
                    "NÃO" if str(imovel_urbano.residencial).upper() == "N" else "SIM"
                )

                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10012,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=urbano_residencial,
                    resposta_enviada_correta=residencial,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="residencial",
                )

                # MUNICIPIO = 10013
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10013,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.municipio).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["municipio_id"],
                    ).upper(),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="municipio",
                )

                # m_frente_metros = 10025
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10025,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.m_frente_metros).upper(),
                    resposta_enviada_correta=m_frente_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="m_frente_metros",
                )
                # para esquerdo = 10029
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10029,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.p_frente_metros).upper(),
                    resposta_enviada_correta=p_frente_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="p_frente_metros",
                )
                # m_direito_metros = 10026
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10026,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.m_direito_metros).upper(),
                    resposta_enviada_correta=m_direito_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="m_direito_metros",
                )
                # para direito = 10030
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10030,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.p_direito_metros).upper(),
                    resposta_enviada_correta=p_direito_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="p_direito_metros",
                )
                # m_esquerdo_metros = 10028
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10028,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.m_esquerdo_metros).upper(),
                    resposta_enviada_correta=m_esquerdo_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="m_esquerdo_metros",
                )
                # para esquerdo = 10032
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10032,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.p_esquerdo_metros).upper(),
                    resposta_enviada_correta=p_esquerdo_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="p_esquerdo_metros",
                )
                # m_fundo_metros = 10027
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10027,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.m_fundo_metros).upper(),
                    resposta_enviada_correta=m_fundo_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="m_fundo_metros",
                )
                # para fundo = 10031
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10031,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.p_fundo_metros).upper(),
                    resposta_enviada_correta=p_fundo_metros,
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="p_fundo_metros",
                )

                area_construida_residencial_id = str(
                    dados_do_registro.get("area_construida_residencial_id", ""),
                ).upper()

                # AREA CONSTRUIDA DO IMOVEL = 10034
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10034,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_urbano.area_construida_residencial).upper(),
                    resposta_enviada_correta=str(area_construida_residencial_id),
                    tabela_origem_id=imovel_urbano.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="area_construida_residencial",
                )

        # IMOVEL RURAL
        if classe_id == "R":
            # OBTER DADOS DO ENDERECO - RURAL
            for imovel_rural in partes_imovel_rural:
                print("VENDO RURAL ...........................")
                # NOME DA FAZENDA = 10014
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10014,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.nome_fazenda).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["nome_fazenda_rural_id"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="nome_fazenda",
                )

                # CARACTERISTA DA FAZENDA = 10015
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10015,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.caracteristica_fazenda).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["caracteristica_rural_id"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="caracteristica_fazenda",
                )

                # AREA DA FAZENDA = 10016
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10016,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.area_fazenda).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["area_rural_id"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="area_fazenda",
                )

                # RESERVA LEGAL
                reserva_legal_id = str(
                    dados_do_registro.get("reserva_florestal_id", ""),
                ).upper()
                reserva_legal = str(imovel_rural.reserva_legal).upper()
                reserva_legal = (
                    "NÃO" if reserva_legal in ["NONE", "N", "NÃO"] else "SIM"
                )

                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10017,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=reserva_legal,
                    resposta_enviada_correta=reserva_legal_id,
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="reserva_legal",
                )

                # GEOREFERENCIAMENTO
                georefenciada = str(imovel_rural.georefenciada).upper()
                georefenciada = "NÃO" if georefenciada in ["NONE", "N"] else "SIM"

                georeferencial_id = str(
                    dados_do_registro.get("georeferencial_id", ""),
                ).upper()
                georeferencial_id = (
                    "NÃO"
                    if georeferencial_id in ["NONE", "N", "NÃO"]
                    else georeferencial_id
                )

                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10018,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=georefenciada,
                    resposta_enviada_correta=georeferencial_id,
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="georefenciada",
                )

                # NUMERO NIR
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10019,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.numero_nirf).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["numero_nirf"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="numero_nirf",
                )

                # NUMERO CCIRR
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10020,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.numero_ccirr).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["numero_ccirr"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="numero_ccirr",
                )

                # NUMERO CAR
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10021,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.numero_car).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["numero_car"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="numero_car",
                )

                # NUMERO INCRA
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10022,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.numero_incra).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["numero_incra"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="numero_incra",
                )

                # DATA VALIDADE NIRF (ITR)
                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10024,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=str(imovel_rural.data_validade_itr).upper(),
                    resposta_enviada_correta=str(
                        dados_do_registro["data_validade_itr"],
                    ).upper(),
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="data_validade_itr",
                )

                # Remanescente
                remanescente = str(imovel_rural.remanescente).upper()
                remanescente = str(remanescente).replace("NONE", "N")
                remanescente = "Sim" if remanescente == "S" else "Não"

                remanescente_id = str(dados_do_registro["remanescente_id"]).upper()
                remanescente_id = str(remanescente_id).replace("NÄO", "NÃO")

                CheckListRealizado.objects.gravar(
                    categoria_id="I",
                    item_id=0,
                    pergunta_id=10023,
                    pessoa_id=0,
                    funcionario_id=self.request.user.id,
                    pedido_item_id=pedido_item_id,
                    resposta=remanescente,
                    resposta_enviada_correta=remanescente_id,
                    tabela_origem_id=imovel_rural.id,
                    nome_tabela_origem="pedido_item_imovel",
                    coluna_tabela_origem="remanescente",
                )

        return CheckListRealizado.objects.filter(pedido_item_id=self.kwargs["id"])
        # ).order_by("pessoa__nome")

    def get_context_data(self, *args, **kwargs):
        # global tipo_registro_atual, numero_matricula_atual, classe_id, current_user_atual

        tipo_registro_protocolo = TipoRegistroProtocolo.objects.all().order_by("ordem")
        tipo_titulo_protocolo = Titulo.objects.filter(exibir="S").order_by(
            "tipo_titulo",
        )
        tipo_tributacao_protocolo = TipoTributacao.objects.filter(
            utilizado="S",
        ).order_by("outros_codigo_trib_tj")
        tabela_emolumentos = Emolumentos.objects.filter(utilizado="S").order_by("nome")

        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "protocolo": protocolo_atual,
                "current_user": current_user_atual,
                "ato_praticado": ato_praticado_atual,
                "tipo_registro": self.tipo_registro_atual,
                "numero_matricula": self.numero_matricula_atual,
                "numero_ato": numero_ato_praticado_atual,
                "codigo_tabela": codigo_tabela_atual,
                "classe_id": "L",
                "tipo_registro_protocolo": tipo_registro_protocolo,
                "tipo_titulo_protocolo": tipo_titulo_protocolo,
                "tipo_ato_protocolo": AtoPratica.objects.all(),
                "tipo_tributacao_protocolo": tipo_tributacao_protocolo,
                "tabela_emolumentos": tabela_emolumentos,
                "pedido_item_id": self.kwargs["id"],
            },
        )

        return context


def estado_civil_view(request):
    if request.method == "POST":
        form1 = forms.EstadoCivilForm(request.POST)
        if form1.is_valid():
            post = form1.save(commit=False)
            # post.author = request.user
            # post.published_date = timezone.now()
            post.save()

            return redirect("home:estado_civil", pk=post.pk)
    else:
        form = forms.EstadoCivilForm()

    return render(request, "contact-us.html", {"form": form})


###############################         UPDATE          ###############################
class PessoaUpdate2(UpdateView):
    model = Livro05
    fields = [
        "cpf",
        "nome",
        "documento",
        "sexo",
        "estado_civil",
        "nacionalidade",
        "profissao",
        "criado_em",
        "nome_pai",
        "nome_mae",
        "endereco",
        "data_nascimento",
        "email",
        "naturalidade",
    ]

    def get_queryset(self):
        return Livro05.objects.all()

    template_name = "exibir_item.html"
    # success_url = reverse_lazy("home:atualizar_protocolo")


###############################         INSERT          ###############################
class PessoaCreate(CreateView):
    model = Livro05
    fields = [
        "id",
        "cpf",
        "nome",
        "documento",
        "sexo",
        "estado_civil",
        "nacionalidade",
        "profissao",
        "criado_em",
        "nome_pai",
        "nome_mae",
        "endereco",
        "data_nascimento",
        "email",
        "naturalidade",
    ]

    template_name = "form-inserir-pessoa.html"
    # success_url = reverse_lazy("atualizar_protocolo")


###############################         UPDATE          ###############################
class PessoaUpdate(UpdateView):
    # print("pessoa_editar")

    model = Livro05
    fields = [
        "documento",
        "sexo",
        "estado_civil",
        "nacionalidade",
        "profissao",
        "criado_em",
        "nome_pai",
        "nome_mae",
        "endereco",
        "data_nascimento",
        "email",
        "naturalidade",
    ]

    template_name = "formulario.html"
    # success_url = reverse_lazy("atualizar_protocolo")


# Atualizar pessoas MODAL
# def atualizar_pessoa_update(request, pk):
def atualizar_pessoa_update(request):
    global current_user_atual
    # Pegando o usuario atual
    current_user_atual = str(request.user).upper()

    # print("update_pessoa:", request.method)

    # PASSANDO PARA O HTML QUAL DEVE SER O FOCO - AQUIRENTE, TRANSMITENTE, TITULO

    # id                    = request.POST.get('parte_id')
    # pedido_item_id = str(request.POST.get('pedido_item_id')).split(',')[0]

    if request.method == "POST":
        d = request.POST.dict()

        id_a, _id_t = 0, 0

        # Pegando a chave ID
        for item, value in zip(d.keys(), d.values(), strict=False):
            if str(item) == "ed_item_parte_id" or str(item) == "pessoa_id":
                id_a = str(value)

                # PASSANDO PARA O HTML QUAL DEVE SER O FOCO - AQUIRENTE, TRANSMITENTE, TITULO

            if str(item) == "ed_item_parte_idT":
                str(value)

                # PASSANDO PARA O HTML QUAL DEVE SER O FOCO - AQUIRENTE, TRANSMITENTE, TITULO

        # REGIME INICIAL
        _estado_civil, tipo_regime_id = 0, 0

        form1 = forms.Livro05Form(request.POST)
        if form1.is_valid():
            # Pegando os parametros passados para atualizar
            pessoa = Livro05.objects.get(id=id_a)

            for item, value in zip(d.keys(), d.values(), strict=False):
                if str(item) == "ed_documento" or str(item) == "documento":
                    pessoa.documento = str(value)

                if str(item) == "ed_nacionalidade" or str(item) == "nacionalidade":
                    pessoa.nacionalidade = str(value)

                if str(item) == "ed_sexo" or str(item) == "sexo":
                    pessoa.sexo = str(value)

                if str(item) == "ed_profissao" or str(item) == "profissao":
                    pessoa.profissao = str(value)

                if str(item) == "ed_naturalidade" or str(item) == "naturalidade":
                    pessoa.naturalidade = str(value)

                if str(item) == "ed_endereco" or str(item) == "endereco":
                    pessoa.endereco = str(value)

                if str(item) == "nome":
                    pessoa.nome = str(value)

                if str(item) == "nome_pai":
                    pessoa.nome_pai = str(value)

                if str(item) == "nome_mae":
                    pessoa.nome_mae = str(value)

                if str(item) == "email":
                    pessoa.email = str(value)

                # Data de Nascimento
                data_nascimento = ""

                try:
                    if str(item) == "data_nascimento":
                        pessoa.data_nascimento = str(formatar_data(str(value)))
                except Exception:
                    data_minima = datetime.min.date()
                    logger.exception("ERRO")
                    if data_nascimento == "":
                        pessoa.data_nascimento = data_minima

                if str(item) == "tipo_regime_casamento":
                    pessoa.tipo_regime_id = str(value).split(",")[0]
                    tipo_regime_id = str(value).split(",")[0]

                # DADOS PARA ATUALIZAR NO ATO
                if str(item) == "estado_civil":
                    pessoa.estado_civil = str(value).split(",")[0]
                    # estado_civil = str(value).split(",")[0]

                # ATUALIZAR O ESTADO CIVIL DO ATO TEMPORARIO
                """
                try:
                    pedidos_partes_ato = PedidoParteAto.objects.get(pedido_item_id=pedido_item_id, pessoa=id_a)
                    pedidos_partes_ato.estado_civil           = estado_civil
                    pedidos_partes_ato.estado_civil_regime_id    = estado_civil_regime_id
                    pedidos_partes_ato.save()
                except Exception as e:
                    logger.exception("ERRO")
                    pass
                """

            # DADOS PARA ATUALIZAR NO ATO
            salvar = "S"
            # VERIFICAR SE O REGIME NAO E OBRIGATORIO - CASO NAO SEJA ELE E RETIRADO
            estado_civil = EstadoCivil.objects.filter(
                id=pessoa.estado_civil,
                requerer_tipo_regime="S",
            )
            if estado_civil.exists() and int(tipo_regime_id) == 0:
                salvar = "N"
                context = {
                    "Regime": "Campos Obrigatórios - Regime de Bens deve ser informado",
                }
                return render(request, "Validar_Pessoa.html", context)

            if salvar != "N":
                pessoa.save()
                print("Pessoa salva !!")

    return redirect(reverse("home:protocolo_search"))


class FuncionarioUpdate(UpdateView):
    model = Funcionario
    fields = ["nome", "sobrenome", "tempo_de_servico"]
    template_name = "update.html"
    # success_url = reverse_lazy("atualizar_protocolo")


###############################         SERVICOS          ###############################
"""
class IntimacaoOnrView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "servicos_livro01.html"
    #print("Passou aqui")
    #

    def get(self, request, *args, **kwargs):
        # Pegando do configuracao - SITE ONR E PASTA DOS XMLS SALVOS
        url_intimacao_onr = Configuracao.get_lista('url_intimacao_onr_id',            '')[0]
        dir_intimacao_onr = Configuracao.get_lista('diretorio_xml_intimacao_onr_id',  '')[0]

        # Listar os arquivos e gravar no BANCO DE DADOS E EVENTOS
        arquivos_onr(dir_intimacao_onr, url_intimacao_onr, request.user)

        events         = int(1)
        running_events = int(1)
        latest_events  = int(1)

        context = {
            "total_event": events,
            "running_events": running_events,
            "latest_events": latest_events,
        }

        return render(request, self.template_name, context)
"""


@login_required()
def base_conhecimento_protocolo_view(
    request,
    pedido_item_id=0,
    ato_id=0,
    numero_protocolo_pesquisar=0,
    numero_registro="0",
    tipo_registro="M",
    cartorio_imovel="0",
    classe="U",
):
    print(
        ato_id,
        pedido_item_id,
        numero_registro,
        tipo_registro,
        cartorio_imovel,
        classe,
    )

    classe = str(classe)
    if classe != TipoClasseRegistro.RURAL:
        classe = TipoClasseRegistro.URBANO

    pedidos_ids = PedidoItem.objects.filter(ato=ato_id).values_list("pedido", flat=True)

    # ato = AtoPratica.objects.get(id=ato_id)
    ato = AtoPratica.objects.filter(id=ato_id).first()

    checklist_balcao_ato = ChecklistBalcao.objects.filter(atos_id=ato_id).order_by(
        "ordem",
    )

    ordem_digitalizar_balcao = OrdemDigitalizarBalcaoAto.objects.filter(
        atos_id=ato_id,
    ).order_by(
        "ordem",
    )

    minutas = MinutaLigacaoAto.objects.filter(ato_id=ato_id).order_by("minuta__titulo")
    exigencias = MinutaExigenciaAto.objects.filter(ato_id=ato_id).order_by(
        "minuta__titulo",
    )

    protocolos_lista_registrados = Livro01Protocolo.objects.filter(
        pedido_id__in=pedidos_ids,
        status_id=3,
    ).order_by(
        "-numero_protocolo",
    )[:50]

    numero_protocolo = protocolos_lista_registrados.first()

    descricao_ato = str(ato.tipo_ato).upper() if ato else ""

    context = {
        "pedido_item_id": pedido_item_id,
        "ato_id": ato_id,
        "classe_imovel": classe,
        "numero_protocolo_pesquisar": numero_protocolo_pesquisar,
        "numero_protocolo": numero_protocolo,
        "total_protocolos_registrados": len(protocolos_lista_registrados),
        "protocolos_lista_registrados": protocolos_lista_registrados,
        "descricao_ato": descricao_ato,
        "checklist_balcao_ato": checklist_balcao_ato,
        "ordem_digitalizar_balcao": ordem_digitalizar_balcao,
        "minutas": minutas,
        "notas_tecnicas": [],
        "exigencias": exigencias,
        "total_checklist": checklist_balcao_ato.count(),
        "total_ordem_digitalizar": ordem_digitalizar_balcao.count(),
        "total_exigencias": exigencias.count(),
        "total_minutas": minutas.count(),
        "total_notas_tecnicas": len([]),
    }
    return render(request, "relatorios/base_conhecimento_protocolo.html", context)


@login_required()
def minutas_view(
    request,
    pedido_item_id=0,
    ato_id=0,
):
    from apps.pedidos.models import Ato as AtoPrime

    pedido_item = AtoPrime.objects.get(id=pedido_item_id)
    minutas = MinutaLigacaoAto.objects.filter(ato_id=ato_id).order_by("minuta__titulo")
    descricao_ato = str(pedido_item.ato_praticavel.nome).upper() if pedido_item else ""
    pedido_item_id = pedido_item.pk

    context = {
        "pedido_item_id": pedido_item_id,
        "ato_id": ato_id,
        "descricao_ato": descricao_ato,
        "minutas": minutas,
        "total_minutas": minutas.count(),
    }
    return render(request, "relatorios/minutas_protocolo.html", context)


class PendenciasView(LoginRequiredMixin, View):
    template_name = "relatorios/pendencias_protocolo.html"

    def get(self, request, colaborador_id=None, *args, **kwargs):
        protocolos_nao_digitalizados = (
            Livro01Protocolo.objects.filtrar_pendentes_de_digitalizacao()
        )

        context = {
            "total_protocolos_nao_digitalizados": len(protocolos_nao_digitalizados),
            "protocolos_nao_digitalizados": protocolos_nao_digitalizados,
        }
        return render(request, self.template_name, context)


@login_required()
def painel_eventos_view(request, colaborador_id=None):
    events = Event.objects.get_all_events(user=request.user, opcao="T")
    running_events = Event.objects.get_running_events(user=request.user)
    latest_events = Event.objects.filter(user=request.user).order_by("-id")

    context = {
        "total_event": events.count(),
        "running_events": running_events,
        "latest_events": latest_events,
        "current_user": request.user,
    }
    return render(request, "relatorios/painel_eventos.html", context)


###############################         DASHBOARD CALENDARIO          ###############################
class DashboardCartorioView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard_cartorio.html"

    def get(self, request, *args, **kwargs):
        start_date = timezone.now().date() - timedelta(0)
        end_date = timezone.now().date() + timedelta(0)

        # PROTOCOLOS NO PERIODO
        protocolos: Livro01ProtocoloQuerySet = (
            Livro01Protocolo.objects.filtrar_por_data(start_date, end_date)
        )

        # PROTOCOLOS CONCLUIDOS
        protocolos_concluidos = protocolos.filtrar_concluidos()

        # PROTOCOLOS CANCELADOS
        protocolos_cancelados = protocolos.filtrar_cancelados()

        # # PROTOCOLOS CONCLUIDOS E CANCELADOS
        protocolos.filtrar_concluidos_e_cancelados()

        # PROTOCOLOS COM EXIGENCIA
        protocolos_em_exigencia = protocolos.filtrar_em_exigencia()

        # Tirar da lista os cancelados e registrados
        protocolos_em_andamento = protocolos.filtrar_em_andamento()

        protocolos_em_exigencia_positiva = protocolos.filtrar_em_exigencia_positiva()

        # PROTOCOLOS DO PERIODO - PROTOCOLOS REGISTRADOS - CANCELADOS
        eventos_periodo = protocolos
        eventos_exigencia = protocolos_em_exigencia
        eventos_concluidos = protocolos_concluidos
        eventos_cancelados = protocolos_cancelados
        eventos_em_andamento = protocolos_em_andamento
        eventos_exigencia_positiva = protocolos_em_exigencia_positiva

        # QUANTIDADE DE EVENTOS DOS PROTOCOLOS
        total_protocolos_exigencia = eventos_exigencia.count()
        total_protocolos_exigencia_positiva = eventos_exigencia_positiva.count()
        total_protocolos_registrados = eventos_concluidos.count()
        total_protocolos_periodo = eventos_periodo.count()
        total_protocolos_cancelados = eventos_cancelados.count()
        total_protocolos_em_andamento = eventos_em_andamento.count()
        total_event = protocolos.count()

        context = {
            "total_protocolos_exigencia": total_protocolos_exigencia,
            "total_protocolos_exigencia_positiva": total_protocolos_exigencia_positiva,
            "total_protocolos_periodo": total_protocolos_periodo,
            "total_protocolos_registrados": total_protocolos_registrados,
            "total_protocolos_cancelados": total_protocolos_cancelados,
            "total_protocolos_em_andamento": total_protocolos_em_andamento,
            "total_event": total_event,
            "eventos_exigencia": eventos_exigencia,
            "eventos_periodo": eventos_periodo,
            "eventos_concluidos": eventos_concluidos,
            "eventos_cancelados": eventos_cancelados,
            "eventos_em_andamento": eventos_em_andamento,
            "data_inicio": str(start_date),
            "data_fim": str(end_date),
        }

        return render(request, self.template_name, context)


###############################         CALENDARIO          ###############################


@login_required
def calendar_view_new(request):
    if request.method == "POST":
        form = forms.EventForm(request.POST)
        if form.is_valid():
            # Obter o encaminhado_id e is_staff a partir do username do colaborador
            colaborador = form.cleaned_data["auth_user"]
            encaminhado_id, is_staff = helpers.get_user_id_2(colaborador)

            new_event = form.save(commit=False)
            new_event.user = request.user
            new_event.auth_user_id = encaminhado_id
            new_event.save()
            return redirect("home:calender")

        return render(request, "calendar.html", {"form": form})

    else:
        form = forms.EventForm()
        events = Event.objects.get_all_events(user=request.user, opcao="A")

        event_list = [
            {
                "title": event.title,
                "start": timezone.localtime(event.start_time).strftime(
                    "%Y-%m-%dT%H:%M:%S",
                ),
                "end": timezone.localtime(event.end_time).strftime("%Y-%m-%dT%H:%M:%S"),
                "auth_user_id": event.auth_user_id,
                "url": event.url,
            }
            for event in events
        ]

        data_atual = timezone.now()  # Chamada única para a função now

        context = {
            "form": form,
            "events": event_list,
            "events_month": Event.objects.get_running_events(user=request.user),
            "data_atual": data_atual,
        }
        return render(request, "calendar.html", context)


###############################         DELETE          ###############################


def pessoa_delete(request, pk):
    pessoa = get_object_or_404(Livro05, pk=pk)
    if request.method == "POST":
        pessoa.delete()
        return redirect(reverse("home:atualizar_protocolo"))
    else:
        return render(request, "form-excluir-pessoa.html", {"object": pessoa})


"""
# Desvincular a pessoa do protocolo
def Desvincular_Pessoa(request, pk):
    pessoa_parte = PedidoParte.objects.get(pk=pk)
    pessoa_parte.delete()

    success_url = reverse_lazy('atualizar_protocolo')
    return redirect(reverse("home:protocolo_search"))
"""


# Gerar as MINUTAS DO LIVRO 2
def aplicar_list_lv2(request, pedido_item_id):
    global pedido_atual, pedido_item_atual, current_user_atual
    # Pegando o usuario atual
    current_user_atual = str(request.user).upper()

    context = {"segment": "index"}
    html_template = loader.get_template("custom-index.html")
    return HttpResponse(html_template.render(context, request))


# Gerar as MINUTAS DO LIVRO 3
def livro03_minutas_list(request, pk):
    # global \
    #     pedido_atual, \
    #     pedido_item_atual, \
    #     minuta_atual_id, \
    #     current_user_atual, \
    #     percentual_proprietario_atual

    try:
        Livro03.objects.get(pk=pk)
    except Livro03.DoesNotExist:
        redirect(Livro03.get_list_url())

    # print("INICIO 7: ", minuta_atual_id)

    if request.POST.get("cbxMinuta") is not None:
        minuta_atual_id = request.POST.get("cbxMinuta")

    # print("Minuta escolhida: ", minuta_atual_id)

    # Atualizando pedido item atual
    pedido_item_id = pedido_item_atual = 0

    if request.method == "POST":
        print("RECEBENDO Checklist LV3 .............")

        # Exibir os dados -  BIERLEY
        for item in request.POST:
            atual = get_apenas_numeros(str(item).split(",")[0])

            # print("ATUAL", atual + "  =   " + request.POST.get(item))

            if atual != "":
                # print(atual + "  =   " + request.POST.get(item))
                lista_indice_temporaria.append(atual)
                lista_variaveis_temporaria.append(request.POST.get(item))

        # print("INICIO 8: ", minuta_atual_id)

        # Qual minuta foi escolhida
        if request.POST.get("cbxMinuta") is not None:
            minuta_atual_id = request.POST.get("cbxMinuta")

        # Gerar as perguntas olhando o modelo escolhido
        lista_perguntas_atuais = get_perguntas_vinculadas_minuta(
            minuta_atual_id,
            pedido_item_atual,
            minuta_atual_id,
        )

        if len(lista_perguntas_atuais) > 0:
            return exibir_perguntas_minuta_lv3(
                request,
                pedido_item_atual,
                minuta_atual_id,
            )
        else:
            return exibir_direto_minuta_lv3(request, pedido_item_atual, minuta_atual_id)
    else:
        print("ENVIANDO Checklist LV3 ............." + request.method)

    # Pegando o usuario atual
    current_user = str(request.user).upper()

    # Iniciar as variaveis
    _ato_id, _pedido_id, _numero_registro_auxiliar = 0, 0, 0
    _ato_praticado, _codigo_tabela, _numero_ri, _numeroato, _tipo_registro = (
        "",
        "",
        "",
        "",
        "",
    )

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

    # Obter a sub pasta do ATO DO LIVRO 02
    sub_pasta = get_sub_pasta_ato_livro02(pedido_item.ato_id)

    # Listar os tipos de minutas
    list_de_minutas = helpers.get_arquivos_de_minutas(
        pedido_item.tipo_registro,
        str(sub_pasta),
    )

    # SELECIONAR AS CHAVES PELO PEDIDOS
    protocolo = Livro01Protocolo.objects.filter(pedido_id=pedido_item.pedido_id).first()

    dados_do_imovel_no_livro03 = pedido_item.get_dados_do_registro_auxiliar()

    # OBTER A ID IMOVEIS
    registro_auxiliar_id = dados_do_imovel_no_livro03["registro_auxiliar_id"]

    # PEGANDO OS DADOS DAS GARANTIAS
    garantias = Livro03Garantia.objects.filter(
        registro_auxiliar_id=registro_auxiliar_id,
    )

    ligacoes = Livro03Ligacao.objects.filter(registro_auxiliar_id=registro_auxiliar_id)

    # Proprietarios Atuais
    partes_atual = Livro03Ligacao.objects.filter(
        registro_auxiliar_id=registro_auxiliar_id,
    )

    # Proprietarios Atuais
    proprietario_atual = []

    percentual_proprietario_atual = 0

    # Filtrando os vinculos - PROPRIETARIO
    for item in partes_atual:
        # nome_atual = Livro05.objects.filter(Q(id=item.pessoa))
        nome_atual = Livro05.objects.filter(id=item.pessoa_id)

        # Formatar o percentual
        try:
            percentual_proprietario_atual += Decimal(item.area_pecentual)
        except Exception:
            logger.exception("ERRO")

        # Filtrando o nome das pessoas
        proprietario_atual.append(
            f"({item.figuras.tipo_figura}) {formatar_documento(nome_atual[0].cpf)} - {nome_atual[0].nome} ({item.estado_civil.descricao_estado_civil})",
        )

    return render(
        request,
        "livro03_minutas.html",
        {
            "registro_auxiliar": dados_do_imovel_no_livro03,
            "ligacoes": ligacoes,
            "garantias": garantias,
            "proprietario_atual": proprietario_atual,
            "list_de_minutas": list_de_minutas,
            "numero_registro_auxiliar": pedido_item.numero_registro,
            "ato_praticado": pedido_item.tipo_ato,
            "tipo_registro": pedido_item.tipo_registro,
            "codigo_tabela": pedido_item.codigo_tabela,
            "numero_ri": pedido_item.numero_ri,
            "numero_ato": pedido_item.numero_ato,
            "current_user": current_user,
            "protocolo": protocolo.numero_protocolo,
            "pedido_item_id": pedido_item_atual,
        },
    )


# Gerar o texto do LIVRO 2
class TextoListView(LoginRequiredMixin, ListView):
    model = Livro02Texto
    template_name = "texto.html"

    def get_queryset(self):
        # return Livro02Texto.objects.filter(id=self.kwargs['id'])
        return Livro02Texto.objects.all().order_by("pk")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["category"] = "MISC"
        context["categoryxx"] = "xxxMISC"
        # context["id"] = self.kwargs['id']

        return context


# Gerar o texto do LIVRO 2 - Editar
class NotaDevolucaoDetailView(LoginRequiredMixin, DetailView):
    model = NotaDevolucaoTexto
    template_name = "nota_de_devolucao/nota_de_devolucao_detail.html"

    def get_queryset(self):
        pedido_item_id = self.kwargs["pedido_item_id"]
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        return pedido_item.texto_nota_devolucao

    def get_context_data(self, *args, **kwargs):
        pedido_item_id = self.kwargs["pedido_item_id"]
        pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

        context = super().get_context_data(*args, **kwargs)
        context["imoveis"] = []
        context["vinculos"] = []
        context["imagens_nota_devolucao"] = pedido_item.protocolo.imagens_nota_devolucao
        context["numero"] = pedido_item_id
        context["opcao_pasta"] = "D"
        context["proprietario_atual"] = []
        context["assinar_nota_devolucao_digital"] = (
            self.request.user.assinar_nota_devolucao_digital
        )

        return context


class AndamentoTextoDetailView(LoginRequiredMixin, UpdateView):
    model = Livro01Andamento
    template_name = "andamentos/andamento_texto_detail.html"
    form_class = forms.AndamentoUpdateForm


class MinutaExigenciaTextoDetailView(LoginRequiredMixin, DetailView):
    model = MinutaExigencia
    template_name = "minuta_exigencia_texto_detail.html"


class MinutaModeloAtoTextoView(LoginRequiredMixin, UpdateView):
    model = MinutaModeloAto
    template_name = "minuta_modelo_ato_texto_detail.html"
    form_class = forms.MinutaModeloAtoTextoForm


class Livro02TextoUpdateView(LoginRequiredMixin, UpdateView):
    model = Livro02
    template_name = "livro02/livro02_texto_detail.html"
    form_class = forms.Livro02Form

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)


# class AnaliseTextoView(View):
#     def post(self, request, *args, **kwargs):
#         # Extrai o texto do corpo da requisição
#         data = json.loads(request.body)
#         texto = data.get("texto", "")

#         if not texto:
#             return JsonResponse({"resultado": "Texto não fornecido."}, status=400)

#         # Chama a função analisar_texto_da_ficha do arquivo openai.py
#         resultado = analisar_texto_da_ficha(texto)

#         # Retorna o resultado como uma resposta JSON
#         return JsonResponse({"resultado": resultado})


class AnaliseTextoView(View):
    def post(self, request, *args, **kwargs):
        # Extrai o texto do corpo da requisição
        data = json.loads(request.body)
        texto = data.get("texto", "")
        user = request.user

        if not texto:
            return JsonResponse({"resultado": "Texto não fornecido."}, status=400)

        # Cria o gerador
        resultado_generator = analisar_texto_da_ficha(texto, user) or ""

        # Usa StreamingHttpResponse para enviar o resultado à medida que é gerado
        return StreamingHttpResponse(resultado_generator, content_type="text/plain")


# BUSCAR O ID DO LIVRO 3 E REDIRECIONAR PARA O TEXTO DO LIVRO 03
@login_required
def livro03_texto_pelo_numero_view(request, numero_livro03):
    if not numero_livro03:
        return HttpResponse("Número do livro não pode ser zero.", status=400)
    livro03 = Livro03.objects.filter(numero=numero_livro03).first()
    return redirect("home:livro03_texto", pk=livro03.id)


class Livro03TextoDetailView(LoginRequiredMixin, DetailView):
    model = Livro03
    # template_name = "livro03/livro03_detail_pelo_numero_texto.html"
    # template_name = "livro03/livro03_texto_detail.html"
    template_name = "livro03/livro03_detail_texto.html"
    # template_name = "livro03/livro03_detail.html"

    def get_context_data(self, *args, **kwargs):
        descricao_tipo_registro_imovel = Livro02.get_descricao_tipo_registro("A")

        context = super().get_context_data(*args, **kwargs)
        context["tipo_registro"] = descricao_tipo_registro_imovel

        return context


class TextoLv2View(LoginRequiredMixin, DetailView):
    model = Livro02Texto
    template_name = "texto_detail.html"


class TextoCreateView(LoginRequiredMixin, CreateView):
    model = Livro02Texto
    template_name = "texto_create.html"
    fields = "__all__"

    def get_queryset(self):
        return Livro02Texto.objects.all()


# Gerar o texto do LIVRO 2 - UPDATE TEXTO


class TtextoUpdateView(LoginRequiredMixin, UpdateView):
    # global \
    #     pedido_atual, \
    #     protocolo_atual, \
    #     pedido_item_atual, \
    #     ato_praticado_atual, \
    #     numero_matricula_atual, \
    #     tipo_registro_atual, \
    #     current_user_atual, \
    #     codigo_tabela_atual, \
    #     numero_ato_praticado_atual, \
    #     ato_praticado_atual_id

    model = Livro02Texto

    template_name = "texto_update.html"
    fields = ["texto"]

    def get_queryset(self):
        return Livro02Texto.objects.all()

    def get_context_data(self, *args, **kwargs):
        # global current_user_atual

        content = super().get_context_data(*args, **kwargs)
        content["protocolo"] = protocolo_atual
        content["current_user"] = self.request.user
        content["ato_praticado"] = ato_praticado_atual
        content["tipo_registro"] = tipo_registro_atual
        content["numero_registro_auxiliar"] = numero_matricula_atual
        content["numero_ato"] = numero_ato_praticado_atual
        content["codigo_tabela"] = codigo_tabela_atual

        return content


# Gerar as PESSOAS DO LIVRO 2
@login_required
def pessoal_list_lv2(request, pedido_item_id):
    # DADOS DO PEDIDO ITENS
    pedido_item: PedidoItem = PedidoItem.objects.filter(pk=pedido_item_id).first()

    pedido_id = int(pedido_item.pedido_id)
    str(pedido_item.ato.tipo_ato)
    numero_ato = str(pedido_item.numero_ato)
    numero_matricula = str(pedido_item.numero_registro)
    tipo_registro = str(pedido_item.tipo_registro)
    ato_praticado = str(pedido_item.ato.tipo_ato)
    codigo_tabela = str(pedido_item.codigo_tabela)

    # SELECIONAR AS CHAVES PELO PEDIDOS
    protocolo = Livro01Protocolo.objects.filter(pedido_id=pedido_id).first()

    # Filtrar o IMOVEL
    try:
        imoveis = pedido_item.get_dados_do_registro()

        # OBTER A ID IMOVEL - Caso o imovel exista
        imovel_id = imoveis["imovel_id"]
        classe_id = imoveis["classe_id"]
    except Exception:
        logger.exception("ERRO")
        imovel_id = 0
        classe_id = "L"

    vinculos = ""
    if tipo_registro != "A":  # Vinculos - LIVRO 2
        vinculos = (
            Vinculo.objects.select_related("pessoa", "tipo_vinculo")
            .filter(imovel_id=imovel_id)
            .order_by("numero_ato")
        )

    ligacoes = ""
    if tipo_registro == "A":  # Proprietarios Atuais do livro 3
        # Filtrar Registro Auxiliar
        # registro_auxiliar = filtrar_imovel_pedidos_itens_LV3(pedido_item_id)
        dados_do_imovel_no_livro03 = pedido_item.get_dados_do_registro_auxiliar()

        # OBTER A ID IMOVEIS
        registro_auxiliar_id = dados_do_imovel_no_livro03["registro_auxiliar_id"]

        # TODOs os vinculos - LIVRO 3
        ligacoes = Livro03Ligacao.objects.filter(
            registro_auxiliar_id=registro_auxiliar_id,
        )

    return render(
        request,
        "pessoal_lv2.html",
        {
            "pedido_item_id": pedido_item_id,
            "tipo_registro": tipo_registro,
            "numero_matricula": numero_matricula,
            "numero_ato": numero_ato,
            "ato_praticado": ato_praticado,
            "codigo_tabela": codigo_tabela,
            "classe_id": classe_id,
            "protocolo": protocolo.numero_protocolo,
            "vinculos": vinculos,
            "ligacoes": ligacoes,
        },
    )


# Pesquisar as PESSOAS
@login_required
def pessoal_por_id(request, vinculo_id):
    vinculo = Vinculo.objects.get(id=vinculo_id)
    ligacoes = Vinculo.objects.get(id=vinculo_id)
    quantidade_pessoas = 1

    return render(
        request,
        "pessoal_detail_id.html",
        {
            "cpf_cnpj": vinculo.pessoa.cpf,
            "nome": vinculo.pessoa.nome,
            "pessoas": vinculo.pessoa,
            "vinculos": vinculo,
            "ligacoes": ligacoes,
            "quantidade_pessoas": quantidade_pessoas,
            "quantidade_livro_02": len(vinculo),
            "quantidade_livro_03": len(ligacoes),
        },
    )


class Livro05DetailView(LoginRequiredMixin, DetailView):
    """Visão Detalhada de um Cadastro Pessoal."""

    model = Livro05
    template_name = "livro05/livro05_detail.html"
    context_object_name = "pessoa"

    def get_table_pagination(self):
        return {"per_page": self.request.user.paginate_by if self.request.user else 10}


class Livro05ListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    """Lista os registros do Livro 05: Cadastro de Pessoas."""

    model = Livro05
    template_name = "livro05/livro05_list.html"
    table_class = Livro05Table
    filterset_class = filters.Livro05Filter
    paginate_by = 10

    # def get_table_pagination(self, request):
    #     return {"per_page": self.request.user.paginate_by if self.request.user else 10}


@login_required
def livro05_pessoal_view(request):
    pessoa_ids = request.GET.getlist("pessoa_id")

    pessoas = Livro05.objects.filter(id__in=pessoa_ids).prefetch_related(
        "vinculos_pessoa",
        "livro03_ligacao_pessoa",
    )

    vinculos = []
    ligacoes = []
    for pessoa in pessoas:
        vinculos.extend(pessoa.vinculos_pessoa.all())
        ligacoes.extend(pessoa.livro03_ligacao_pessoa.all())
    # vinculo = Vinculo.objects.filter(pessoa__in=pessoa_ids)
    # ligacoes = Livro03Ligacao.objects.filter(pessoa__in=pessoa_ids)

    return render(
        request,
        "pessoal_detail.html",
        {
            "cpf_cnpj": "cpf_cnpj",
            "nome": "nome",
            "pessoas": pessoas,
            "vinculos": vinculos,
            "ligacoes": ligacoes,
            "quantidade_pessoas": pessoas.count(),
            "quantidade_livro_02": len(vinculos),
            "quantidade_livro_03": len(ligacoes),
        },
    )


@login_required
def pessoal(request, cpf_cnpj="0", nome="%"):
    # print(cpf_cnpj, nome)
    if nome == "%":
        nome = None

    nome = str(nome).upper()
    pessoas, ligacoes, vinculos = [], [], []

    # Pesquisar usando CPF
    pessoas = (
        # Livro05.objects.filter(cpf__contains=cpf_cnpj, nome__contains=nome)
        Livro05.objects.annotate(nome_upper=Upper("nome")).filter(
            cpf__contains=cpf_cnpj,
            nome_upper__contains=nome,
        )
        if cpf_cnpj and nome
        else (
            Livro05.objects.filter(cpf=cpf_cnpj)
            if cpf_cnpj
            else Livro05.objects.filter(nome__contains=nome)
        )
    )

    # Supondo que cpf_cnpj e nome são as variáveis contendo os dados a serem filtrados
    pessoas_cpf_cnpj_igual = (
        Livro05.objects.annotate(nome_upper=Upper("nome"))
        .filter(cpf__contains=cpf_cnpj)
        .exclude(nome_upper__contains=nome)
    )

    pessoas_nome_igual = (
        Livro05.objects.annotate(nome_upper=Upper("nome"))
        .filter(nome_upper__contains=nome)
        .exclude(cpf__contains=cpf_cnpj)
    )

    (
        indisponibilidades,
        quantidade_aberto_indisponibilidade,
        quantidade_finalizado_indisponibilidade,
    ) = ([], 0, 0)

    # ACESSAR O PRIMEIRO REGISTRO DA
    if pessoas:
        for pessoa in pessoas:
            pessoa_id = pessoa.id

        # Query para obter os vínculos ordenados pelo número do registro da Livro02
        vinculos = (
            Vinculo.objects.select_related("pessoa", "tipo_vinculo")
            .filter(pessoa_id=pessoa_id)
            .order_by("-imovel__numero", "-numero_ato")
        )

        # Todas as ligacoes
        ligacoes = Livro03Ligacao.objects.filter(pessoa_id=pessoa_id).order_by(
            "-registro_auxiliar__numero",
        )

        # Todas as Indisponibilidades do CPF/CNPJ
        indisponibilidades = Livro05.pessoas_pelo_cpf_cnpj_com_indisponibilidade(
            pessoa.cpf,
        )

        if indisponibilidades:
            id_envovidos = indisponibilidades.values_list("id", flat=True)
            quantidade_aberto_indisponibilidade = (
                Livro05.quantidade_aberto_indisponibilidade_pelo_id(id_envovidos)
            )
            quantidade_finalizado_indisponibilidade = (
                Livro05.quantidade_finalizado_indisponibilidade_pelo_id(
                    id_envovidos,
                )
            )
        else:
            indisponibilidades = []
            quantidade_aberto_indisponibilidade = 0
            quantidade_finalizado_indisponibilidade = 0

    return render(
        request,
        "pessoal_detail.html",
        {
            "cpf_cnpj": cpf_cnpj,
            "nome": nome,
            "pessoas": pessoas,
            "vinculos": vinculos,
            "ligacoes": ligacoes,
            "pessoas_cpf_cnpj_igual": pessoas_cpf_cnpj_igual,
            "pessoas_nome_igual": pessoas_nome_igual,
            "indisponibilidades": indisponibilidades,
            "quantidade_pessoas": pessoas.count(),
            "quantidade_livro_02": len(vinculos),
            "quantidade_livro_03": len(ligacoes),
            "quantidade_cpf_cnpj_igual": pessoas_cpf_cnpj_igual.count(),
            "quantidade_pessoas_nome_igual": pessoas_nome_igual.count(),
            "quantidade_indisponibilidades": len(indisponibilidades),
            "quantidade_aberto_indisponibilidade": quantidade_aberto_indisponibilidade,
            "quantidade_finalizado_indisponibilidade": quantidade_finalizado_indisponibilidade,
        },
    )


@login_required
def livro05_por_id_view(request, id=0):
    # Pesquisar usando CPF
    pessoas = Livro05.objects.filter(id=id)
    for pessoa in pessoas:
        cpf = pessoa.cpf
        nome = str(pessoa.nome).upper()
        pessoa_id = pessoa.id

    # Supondo que cpf_cnpj e nome são as variáveis contendo os dados a serem filtrados
    pessoas_cpf_cnpj_igual = Livro05.objects.filter(cpf__contains=cpf).exclude(
        nome__icontains=nome,
    )

    pessoas_nome_igual = Livro05.objects.filter(nome__icontains=nome).exclude(
        cpf__contains=cpf,
    )

    # Iniciar Variaveis
    (
        indisponibilidades,
        quantidade_aberto_indisponibilidade,
        quantidade_finalizado_indisponibilidade,
    ) = ([], 0, 0)

    # ACESSAR O PRIMEIRO REGISTRO DA
    if pessoas:
        # Query para obter os vínculos ordenados pelo número do registro da Livro02
        vinculos = (
            Vinculo.objects.select_related("pessoa", "tipo_vinculo")
            .filter(pessoa_id=pessoa_id)
            .order_by("-imovel__numero", "-numero_ato")
        )

        # Todas as ligacoes
        ligacoes = Livro03Ligacao.objects.filter(pessoa_id=pessoa_id).order_by(
            "-registro_auxiliar__numero",
        )

        # Todas as Indisponibilidades
        indisponibilidades = Livro05.pessoas_pelo_cpf_cnpj_com_indisponibilidade(cpf)

        if indisponibilidades:
            id_envovidos = indisponibilidades.values_list("id", flat=True)
            quantidade_aberto_indisponibilidade = (
                Livro05.quantidade_aberto_indisponibilidade_pelo_id(id_envovidos)
            )
            quantidade_finalizado_indisponibilidade = (
                Livro05.quantidade_finalizado_indisponibilidade_pelo_id(
                    id_envovidos,
                )
            )
        else:
            indisponibilidades = []
            quantidade_aberto_indisponibilidade = 0
            quantidade_finalizado_indisponibilidade = 0

    return render(
        request,
        "pessoal_detail.html",
        {
            "cpf_cnpj": cpf,
            "nome": nome,
            "pessoas": pessoas,
            "vinculos": vinculos,
            "ligacoes": ligacoes,
            "pessoas_cpf_cnpj_igual": pessoas_cpf_cnpj_igual,
            "pessoas_nome_igual": pessoas_nome_igual,
            "indisponibilidades": indisponibilidades,
            "quantidade_pessoas": pessoas.count(),
            "quantidade_livro_02": len(vinculos),
            "quantidade_livro_03": len(ligacoes),
            "quantidade_cpf_cnpj_igual": pessoas_cpf_cnpj_igual.count(),
            "quantidade_pessoas_nome_igual": pessoas_nome_igual.count(),
            "quantidade_indisponibilidades": len(indisponibilidades),
            "quantidade_aberto_indisponibilidade": quantidade_aberto_indisponibilidade,
            "quantidade_finalizado_indisponibilidade": quantidade_finalizado_indisponibilidade,
        },
    )


@login_required
def protocolos_distribuidos_por_colaborador_list_view(request, colaborador_id):
    logger.debug(f"protocolos_distribuidos_por_colaborador_list_view({colaborador_id})")

    template_name = "distribuicao_protocolo_por_colaborador.html"

    # Pesquisar por data
    start_date = timezone.now().date() + timedelta(0)
    end_date = timezone.now().date() + timedelta(0)

    colaborador: Colaborador = Colaborador.objects.get(pk=colaborador_id)

    protocolos = colaborador.protocolos

    # PROTOCOLOS COM REENTRADA
    protocolos_com_reentrada = colaborador.protocolos_em_reentrada

    # Protocolos distribuídos no período
    protocolos_distribuidos = (
        Livro01Protocolo.objects.filtrar_distribuidos_para_colaborador_no_periodo(
            colaborador_id=colaborador_id,
            start_date=start_date,
            end_date=end_date,
        )
    )

    # Convertendo querysets para sets
    protocolos_com_reentrada_set = set(protocolos_com_reentrada)
    protocolos_set = set(protocolos)

    # Subtraindo sets para obter os protocolos sem reentrada
    protocolos_set = protocolos_set - protocolos_com_reentrada_set

    # Convertendo de volta para uma lista de IDs
    protocolos_ids = [protocolo.id for protocolo in protocolos_set]

    # Filtrando os protocolos sem reentrada a partir dos IDs
    Livro01Protocolo.objects.filter(id__in=protocolos_ids)

    (
        protocolos_distribuidos.values("fases_protocolo_colaborador")
        .annotate(quantidade=Count("fases_protocolo_colaborador"))
        .order_by()
    )

    context = {
        "colaborador": colaborador,
        # "protocolos_com_reentrada": colaborador.protocolos_em_reentrada,
        # "protocolos_sem_reentrada": colaborador.protocolos_abertos_sem_reentrada,
        # "protocolos_distribuidos": protocolos_distribuidos,
        # "distribuido_detail": distribuido_detail,
        "data_inicio": start_date,
        "data_fim": end_date,
    }

    return render(request, template_name, context)


# Criar um novo lembrete para o IMOVEL
@login_required
def criar_lembrete_imovel(request, imovel_id=0, numero_registro=0):
    # Ordenando as fases do protocolo pelo nome
    NivelAlerta.objects.all().order_by("descricao")

    # Filtrando apenas os títulos principais e ordenando pelo tipo de título
    titulo_principal_protocolo = Titulo.objects.filter(ato_principal="S").order_by(
        "tipo_titulo",
    )

    # Obtendo a observação do pedido
    # pedidos = Pedido.objects.get(pk=238922)
    # observacao = pedidos.observacao
    observacao = ""

    # Obtendo apenas os colaboradores ativos e exibindo seus nomes
    colaborador = sorted(
        [
            [
                get_nome_colaborador_pelo_id(colab.colaborador),
                str(colab.colaborador),
            ]
            for colab in Colaborador.objects.filtrar_por_ativos()
        ],
    )

    # Formatando a data para distribuir
    data_distribuir = helpers.get_data_util_em_x_dias(timezone.now().date(), 1)
    # data_distribuir = (
    #     data_distribuir.split("/")[2]
    #     + "-"
    #     + data_distribuir.split("/")[1]
    #     + "-"
    #     + data_distribuir.split("/")[0]
    # )
    data_distribuir = data_distribuir.strftime("%Y-%m-%d")

    return render(
        request,
        "criar_lembrete_imovel.html",
        {
            "numero_registro": numero_registro,
            "imovel_id": imovel_id,
            "observacao": observacao,
            "NivelAlerta": NivelAlerta,
            "colaborador": colaborador,
            "titulo_principal_protocolo": titulo_principal_protocolo,
            "data_distribuir": data_distribuir,
        },
    )


# Listar para enviar
@login_required
def reentrada_protocolo_numero(request, numero_protocolo):
    template_name = "form-reentrada-protocolo.html"

    if request.method == "POST":
        colaborador_encaminhado_id = request.POST.get("colaborador_id")

        # Verifique se o colaborador_id não é vazio
        if not colaborador_encaminhado_id:
            messages.warning(request, "Colaborador não foi informado!")
            # retorna para origem
            return redirect(request.headers.get("referer"))

        if not numero_protocolo:
            messages.warning(request, "Protocolo informado não foi encontrado!")
            return redirect(request.headers.get("referer"))

        protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)

        protocolo.executar_reentrada(
            opcao_reentrada="R",
            colaborador_id=request.user.id,
            colaborador_encaminhado_id=colaborador_encaminhado_id,
        )

        request.session["numero_protocolo"] = numero_protocolo

        messages.success(
            request,
            f"Reentrada do protocolo {numero_protocolo} executada!",
        )

        return redirect("home:distribuicao_protocolo")

    elif request.method == "GET":
        opcao_reentrada = "P"

        """Gerar a Reentrada protocolo com base no número fornecido e outros parâmetros."""
        protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)
        # colaboradores = Colaborador.objects.filtrar_por_ativos()
        colaboradores = (
            Colaborador.objects.filtrar_por_pode_receber_protocolos_do_balcao()
        )

        # Formatando a data para distribuir
        data_distribuir = helpers.get_data_util_em_x_dias(timezone.now().date(), 0)
        data_distribuir = data_distribuir.strftime("%Y-%m-%d")

        # Verificar a opção de reentrada - Exibir o caption
        if opcao_reentrada == "P":
            caption = "Pagamento e Reentrada de Protocolo"
        elif opcao_reentrada == "R":
            caption = "Reentrada de Protocolo"
        else:
            caption = "Reentrada de Protocolo"

        context = {
            "protocolo": protocolo,
            "colaboradores": colaboradores,
            "data_distribuir": data_distribuir,
            "opcao_reentrada": opcao_reentrada,
            "caption": caption,
        }

        template_name = "form-reentrada-protocolo.html"

        return render(request, template_name, context)
    else:
        # Retorne uma resposta adequada para métodos não suportados
        return HttpResponseNotAllowed(["GET", "POST"])


# Listar para enviar
@login_required
def reentrada_pagamento_protocolo_numero(
    request,
    numero_protocolo,
    opcao_reentrada="P",
):
    template_name = "form-reentrada-pagamento-protocolo.html"

    if request.method == "POST":
        colaborador_encaminhado_id = request.POST.get("colaborador_id")
        valor_diferenca = request.POST.get("input_valor_diferenca_receber", "0.0")
        valor_diferenca = Decimal(valor_diferenca.replace(",", "."))
        referer = request.headers.get("referer")

        if not valor_diferenca or valor_diferenca == "0":
            messages.warning(request, "Valor da diferença não foi informado!")
            return redirect(referer)

        # Verifique se o colaborador_id não é vazio
        if not colaborador_encaminhado_id:
            messages.warning(request, "Colaborador não foi informado!")
            return redirect(referer)

        if not numero_protocolo:
            messages.warning(request, "Protocolo informado não foi encontrado!")
            return redirect(referer)

        protocolo: Livro01Protocolo = Livro01Protocolo.objects.get(
            numero_protocolo=numero_protocolo,
        )

        if not protocolo:
            messages.warning(request, "Protocolo informado não foi encontrado!")
            return redirect(referer)

        financeiro = protocolo.executar_reentrada(
            opcao_reentrada=opcao_reentrada,
            valor_diferenca=valor_diferenca,
            colaborador_id=request.user.id,
            colaborador_encaminhado_id=colaborador_encaminhado_id,
        )

        request.session["numero_protocolo"] = numero_protocolo

        if financeiro:
            return redirect(financeiro.get_absolute_url())

        messages.warning(request, "Erro ao executar a reentrada do protocolo!")

        return redirect(referer)

    if request.method == "GET":
        opcao_reentrada = "P"

        protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)

        colaboradores = (
            Colaborador.objects.filtrar_por_pode_receber_protocolos_do_balcao()
        )

        # Formatando a data para distribuir
        data_distribuir = helpers.get_data_util_em_x_dias(timezone.now().date(), 0)
        data_distribuir = data_distribuir.strftime("%Y-%m-%d")

        # Verificar a opção de reentrada - Exibir o caption
        if opcao_reentrada == "P":
            caption = "Pagamento e Reentrada de Protocolo"
        elif opcao_reentrada == "R":
            caption = "Reentrada de Protocolo"
        else:
            caption = "Reentrada de Protocolo"

        # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
        valor_atual_protocolo = protocolo.valor_total_caixa
        valor_total_pago_protocolo = protocolo.valor_total_protocolo
        valor_diferenca = protocolo.valor_diferenca

        context = {
            "protocolo": protocolo,
            "colaboradores": colaboradores,
            "data_distribuir": data_distribuir,
            "opcao_reentrada": opcao_reentrada,
            "caption": caption,
            "valor_atual_protocolo": valor_atual_protocolo,
            "valor_total_pago_protocolo": valor_total_pago_protocolo,
            "valor_diferenca": valor_diferenca,
        }

        return render(request, template_name, context)
    return None


def impressao_recibo_reentrada(request, numero_protocolo):
    """Imprime o recibo de reentrada de protocolo."""
    protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)

    context = {
        "protocolo": protocolo,
        "colaborador": protocolo.colaborador,
    }

    return render(request, "recibo_reentrada.html", context)


# Listar para enviar
@login_required
def distribuicao_protocolo_numero(request, numero_protocolo):
    """Distribui um protocolo com base no número fornecido."""
    try:
        protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)
    except Livro01Protocolo.DoesNotExist:
        db = firebird.FbConnection()
        db.begin_transaction()
        try:
            protocolo, _ = firebird.importar_protocolo_por_numero_fb(
                numero_protocolo=numero_protocolo,
                tipo_importacao=None,
                db=db,
            )
            db.commit()
        except Exception as e:
            db.rollback()
            messages.error(
                request,
                f"Erro ao importar o protocolo {numero_protocolo}: {e}",
            )
            return redirect("home:distribuicao_protocolo")
        finally:
            db.close()

    fases = TipoFaseProtocolo.objects.filtrar_ordenadas_por_nome()
    titulos = Titulo.objects.filtrar_por_principais()
    colaboradores = Colaborador.objects.filtrar_por_pode_receber_protocolos_do_balcao()

    # Formatando a data para distribuir
    data_distribuir = helpers.get_data_util_em_x_dias(timezone.now().date(), 1)
    data_distribuir = data_distribuir.strftime("%Y-%m-%d")

    context = {
        "protocolo": protocolo,
        "fases": fases,
        "colaboradores": colaboradores,
        "titulos": titulos,
        "data_distribuir": data_distribuir,
    }

    return render(request, "form-distribuir-protocolo.html", context)


# Listar para enviar
@login_required
def reprotocolar_protocolo_numero(request, numero_protocolo):
    """Reprotocola um protocolo com base no número fornecido e outros parâmetros."""
    protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)
    fases = TipoFaseProtocolo.objects.filtrar_ordenadas_por_nome()
    titulos = Titulo.objects.filtrar_por_principais()
    colaboradores = Colaborador.objects.filtrar_por_pode_receber_protocolos_do_balcao()
    tipo_tributacao_protocolo = TipoTributacao.objects.filter(utilizado="S").order_by(
        "outros_codigo_trib_tj",
    )

    # FILTrAR O TITULO E PEGA O TITULO INICIAL
    titulo_id_inicial, titulo_id_inicial_descricao = 0, ""
    for titulo_principal in protocolo.titulos_principais:
        titulo_id_inicial = titulo_principal.titulo_id
        titulo_id_inicial_descricao = titulo_principal.titulo.tipo_titulo

    # Formatando a data para distribuir
    data_distribuir = helpers.get_data_util_em_x_dias(
        timezone.now().date(),
        1,
    ).strftime("%Y-%m-%d")

    # Pegar os valores Selados
    # valores_selados = (
    #     protocolo.selos_pedidos_itens_valores
    #     if protocolo.selos_pedidos_itens_valores is not None
    #     else 0
    # )
    valores_selados = Decimal(protocolo.valor_prenotacao_mg)

    # Pegar os valores Pagos no Caixa
    valor_pagos_caixa = getattr(protocolo, "valor_total_caixa", 0)

    # valor_atual_protocolo = getattr(protocolo, "valor_total_protocolo", 0)
    valor_atual_protocolo = protocolo.valor_atual_protocolo_sistema_antigo()

    valores_complementares = Decimal(valor_atual_protocolo) - Decimal(valor_pagos_caixa)

    # Pegar os valores Pagos no Caixa
    valor_transportar = valor_pagos_caixa - valores_selados

    # Gerar o valor para nova prenotacao
    valor_novo_deposito = Decimal(protocolo.valor_prenotacao_mg)
    valor_novo_deposito = valor_novo_deposito.quantize(
        Decimal("0.00"),
        rounding=ROUND_HALF_UP,
    )

    # VALOR DA NOVA DIFERENCA
    valor_nova_diferenca = valores_complementares.quantize(
        Decimal("0.00"),
        rounding=ROUND_HALF_UP,
    ) + valor_novo_deposito.quantize(
        Decimal("0.00"),
        rounding=ROUND_HALF_UP,
    )

    template_name = "form-reprotocolar_protocolo_numero.html"

    context = {
        "protocolo": protocolo,
        "observacao": protocolo.observacao,
        "fases": fases,
        "colaboradores": colaboradores,
        "titulos": titulos,
        "data_distribuir": data_distribuir,
        "valores_selados": valores_selados,
        "valor_pagos_caixa": valor_pagos_caixa,
        "valor_atual_protocolo": valor_atual_protocolo,
        "valor_transportar": valor_transportar,
        "valor_novo_deposito": valor_novo_deposito,
        "valor_nova_diferenca": valor_nova_diferenca,
        "valores_complementares": valores_complementares,
        "tipo_tributacao_protocolo": tipo_tributacao_protocolo,
        "titulo_inicial": titulo_id_inicial,
        "titulo_inicial_descricao": titulo_id_inicial_descricao,
    }

    return render(request, template_name, context)


# Gerar as PESSOAS DO LIVRO 2
# @login_required
# def livro02_pessoas_list(request, numero_registro, tipo_registro, cartorio_imovel):
#     registro = Livro02.objects.filter(
#         numero=numero_registro,
#         tipo=tipo_registro,
#         cartorio=cartorio_imovel,
#     ).first()

#     # TODOs os vinculos - LIVRO 2
#     vinculos = (
#         (
#             Vinculo.objects.select_related("estado_civil", "pessoa", "tipo_vinculo")
#             .filter(imovel_id=registro.pk)
#             .order_by("numero_ato")
#         )
#         if registro.tipo != "A"
#         else []
#     )

#     # Filtrar Registro Auxiliar
#     (
#         (Livro03.objects.select_related("estado_civil", "pessoa", "figuras").filter(numero=numero_registro).fisrt())
#         if registro.tipo == "A"
#         else []
#     )

#     # TODOs os vinculos - LIVRO 3
#     # ligacoes = Livro03Ligacao.objects.filter(registro_auxiliar_id=registro_auxiliar.pk) if registro_auxiliar else []
#     ligacoes = vinculos

#     template_name = "livro02_pessoas_list.html"

#     context = (
#         {
#             "imovel": registro,
#             "vinculos": vinculos,
#             "ligacoes": ligacoes,
#         },
#     )

#     return render(request, template_name, context)


@login_required
def livro02_pessoas_list(request, numero_registro, tipo_registro, cartorio_imovel):
    registro = Livro02.objects.filter(
        numero=numero_registro,
        tipo=tipo_registro,
        cartorio=cartorio_imovel,
    ).first()

    # TODOs os vínculos - LIVRO 2
    vinculos = (
        Vinculo.objects.select_related("estado_civil", "pessoa", "tipo_vinculo")
        .filter(imovel_id=registro.pk)
        .order_by("-numero_ato", "-id")
        if registro and registro.tipo != "A"
        else []
    )

    # Filtrar Registro Auxiliar
    registro_auxiliar = (
        Livro03.objects.select_related("estado_civil", "pessoa", "figuras")
        .filter(numero=numero_registro)
        .first()
        if registro and registro.tipo == "A"
        else None
    )

    # TODOs os vínculos - LIVRO 3
    ligacoes = (
        Livro03Ligacao.objects.filter(registro_auxiliar_id=registro_auxiliar.pk)
        if registro_auxiliar
        else []
    )

    template_name = "livro02_pessoas_list.html"

    context = {
        "imovel": registro,
        "vinculos": vinculos,
        "ligacoes": ligacoes,
    }

    return render(request, template_name, context)


# Gerar as MINUTAS DO LIVRO 2
def minuta_list_lv2_texto(request, pedido_item_id):
    print("minuta_list_lv2_texto - ", pedido_item_id)

    # Verificar se existe o texto ja gravado na tabela
    if Livro02Texto.objects.filter(pedido_item_id=pedido_item_id).exists():
        return redirect(
            "home:texto_lv2",
            pk=pedido_item_id,
            pedido_item_id=pedido_item_id,
        )
    else:
        return redirect("home:minuta_lv2", pedido_item_id=pedido_item_id)


# Gerar as MINUTAS DO LIVRO 2
@login_required
def minuta_list_lv2(request, pedido_item_id, opcao=0):
    # global \
    #     pedido_atual, \
    #     protocolo_atual, \
    #     pedido_item_atual, \
    #     minuta_atual_id, \
    #     current_user_atual

    if request.POST.get("cbxMinuta") is not None:
        minuta_atual_id = request.POST.get("cbxMinuta")

    # print("Minuta escolhida: ", minuta_atual_id)

    # Atualizando pedido item atual
    # pedido_item_atual = pedido_item_id

    pedido_item: PedidoItem = PedidoItem.objects.filter(pk=pedido_item_id).first()

    # Verificar se existe pessoa para vincular ao ATO ESPECIFICO
    # PedidoParteAto.vincular_pedido_parte_ato(pedido_id=pedido_item.pedido_id, pedido_item_id=pedido_item.pk)
    with contextlib.suppress(Exception):
        PedidoParteAto.vincular_pedido_parte_ato(pedido_item_id=pedido_item.pk)

    if request.method == "POST":
        print("RECEBENDO Checklist LV2 .............")

        # Exibir os dados -  BIERLEY
        for item in request.POST:
            atual = get_apenas_numeros(str(item).split(",")[0])

            # print("ATUAL", atual + "  =   " + request.POST.get(item))

            if atual != "":
                # print(atual + "  =   " + request.POST.get(item))
                lista_indice_temporaria.append(atual)
                lista_variaveis_temporaria.append(request.POST.get(item))

        # print("INICIO 10: ", minuta_atual_id, minuta_atual)

        # Qual minuta foi escolhida
        if request.POST.get("cbxMinuta") is not None:
            minuta_atual_id = request.POST.get("cbxMinuta")

        # caminho_requisicao = request

        # Gerar as perguntas olhando o modelo escolhido
        lista_perguntas_atuais = get_perguntas_vinculadas_minuta(
            minuta_atual_id,
            pedido_item.pk,
            minuta_atual_id,
        )

        # EXIBIR AS VARIAVEIS DAS perguntas da MINUTA
        # print(lista_perguntas_atuais)

        # Retonar as pesquisas a serem feitas
        # return exibir_perguntas_minuta_lv2(request, pedido_item_atual)
        if len(lista_perguntas_atuais) > 0:
            return exibir_perguntas_minuta_lv2(request, pedido_item.pk, minuta_atual_id)
        else:
            return exibir_direto_minuta_lv2(request, pedido_item.pk, minuta_atual_id)

    else:
        print("ENVIANDO Checklist LV2 ............." + request.method)

    # Pegando o usuario atual
    current_user = str(request.user).upper()
    # current_user_atual = current_user

    # Iniciar as variaveis
    ato_id, pedido_id, numero_matricula = 0, 0, 0
    ato_praticado, codigo_tabela, numero_ri, numero_ato, tipo_registro = (
        "",
        "",
        "",
        "",
        "",
    )

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

    pedido_id = int(pedido_item.pedido_id)
    ato_id = int(pedido_item.ato_id)
    ato_praticado = str(pedido_item.ato.tipo_ato)
    numero_matricula = str(pedido_item.numero_registro)
    tipo_registro = str(pedido_item.tipo_registro)
    codigo_tabela = str(pedido_item.codigo_tabela)
    numero_ri = str(pedido_item.numero_ri)
    numero_ato = str(pedido_item.numero_ato)

    # Listar os tipos de minutas
    # print("Ler minuta .............")
    # Obter a sub pasta do ATO DO LIVRO 02
    sub_pasta = get_sub_pasta_ato_livro02(ato_id)

    list_de_minutas = helpers.get_arquivos_de_minutas(
        str(tipo_registro),
        str(sub_pasta),
    )

    partes = PedidoParte.objects.filter(pedido_id=pedido_id).order_by("id")
    (
        partes_adquirente,
        partes_transmitente,
        partes_imovel_rural,
        partes_imovel_urbano,
    ) = partes, partes, partes, partes

    with contextlib.suppress(Exception):
        partes_adquirente = PedidoParteAto.objects.filter(
            pedido_item_id=pedido_item_id,
            status=TipoParte.ADQUIRENTE,
        ).order_by("id")

    with contextlib.suppress(Exception):
        partes_transmitente = PedidoParteAto.objects.filter(
            pedido_item_id=pedido_item_id,
            status=TipoParte.TRANSMITENTE,
        ).order_by("id")

    with contextlib.suppress(Exception):
        partes_imovel_rural = PedidoItemImovel.objects.filter(
            pedido_item_id=pedido_item_id,
            opcao_imovel=TipoClasseRegistro.RURAL,
        )

    with contextlib.suppress(Exception):
        partes_imovel_urbano = PedidoItemImovel.objects.filter(
            pedido_item_id=pedido_item_id,
            opcao_imovel=TipoClasseRegistro.URBANO,
        )

    cidades = Cidade.objects.all()

    protocolo = Livro01Protocolo.objects.filter(pedido_id=pedido_id).first()

    try:
        imovel = pedido_item.get_dados_do_registro()

        # OBTER A ID IMOVEIS
        imovel_id = imovel["imovel_id"]
        classe_id = imovel["classe_id"]
    except Exception:
        logger.exception("ERRO")
        imovel_id = 0
        classe_id = ""

    if str(imovel_id) == "":
        imovel_id = 0

    # TODOs os vinculos
    vinculos = (
        Vinculo.objects.select_related("pessoa", "tipo_vinculo")
        .filter(imovel_id=imovel_id)
        .order_by("numero_ato")
    )

    # print(imovel_id)
    #

    # Proprietarios Atuais
    try:
        imovel_id_int = int(imovel_id)  # Tentativa de converter imovel_id para inteiro
        if imovel_id_int > 0:
            partes_atual = (
                Vinculo.objects.select_related("pessoa", "tipo_vinculo")
                .filter(
                    imovel_id=imovel_id_int,
                    situacao="F",
                    tipo_vinculo_id__in=[Configuracao.obter("proprietario_id")],
                )
                .order_by("numero_ato")
            )
        else:
            partes_atual = None
    except ValueError:
        # imovel_id não é um número, trata o caso aqui
        partes_atual = None

    # Proprietarios Atuais
    proprietario_atual = []
    percentual_proprietario_atual = 0

    # Filtrando os vinculos - PROPRIETARIO
    if partes_atual:
        for item in partes_atual:
            nome_atual = Livro05.objects.filter(Q(id=item.pessoa.id))

            # Formatar o percentual
            try:
                if item.area_pecentual is not None:
                    percentual_proprietario_atual += item.area_pecentual
            except Exception:
                logger.exception("ERRO")
                percentual_proprietario_atual = 0

            # Filtrando o nome das pessoas
            proprietario_atual.append(
                str(item.tipo_ato)
                + "."
                + str(item.numero_ato).split(".")[0]
                + " - "
                + str(item.area_pecentual).replace(".", ",")
                + "% - "
                + str(formatar_documento(nome_atual[0].cpf))
                + " - "
                + str(nome_atual[0].nome)
                + " ("
                + item.estado_civil.descricao_estado_civil
                + ") ",
            )

    # fields = "__all__"

    # Minuta a ser exibida
    nome_minuta = "checklist_lv2.html" if int(opcao) == 1 else "checklist_lv2.html"

    return render(
        request,
        nome_minuta,
        {
            "imoveis": imovel,
            "vinculos": vinculos,
            "partes": partes,
            "partes_atual": partes_atual,
            "partes_adquirente": partes_adquirente,
            "partes_transmitente": partes_transmitente,
            "partes_imovel_rural": partes_imovel_rural,
            "partes_imovel_urbano": partes_imovel_urbano,
            "cidades": cidades,
            "proprietario_atual": proprietario_atual,
            "list_de_minutas": list_de_minutas,
            "numero_matricula": numero_matricula,
            "ato_praticado": ato_praticado,
            "tipo_registro": tipo_registro,
            "codigo_tabela": codigo_tabela,
            "numero_ri": numero_ri,
            "numero_ato": numero_ato,
            "current_user": current_user,
            "protocolo": protocolo.numero_protocolo if protocolo else "",
            "pedido_item_id": pedido_item_atual,
            "exibir_Tab_Minuta_Atual": "",
            "classe_imovel": classe_id,
        },
    )


# Gerar as perguntas para o LIVRO 3 - MINUTAS
def exibir_direto_minuta_lv2(request, pedido_item_id, minuta_atual):
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
    pedido_id = int(pedido_item.pedido_id)

    # SELECIONAR AS CHAVES PELO PEDIDOS
    protocolo = Livro01Protocolo.objects.filter(pedido_id=pedido_id).first()

    context = {
        "protocolo": protocolo,
        "pedido_item": pedido_item,
    }

    # LISTAR AS PERGUNTAS NO MODELO
    return render(request, "exibir_direto_minuta_lv2.html", context)


# Gerar as perguntas para o LIVRO 3 - MINUTAS
def exibir_direto_minuta_lv3(request, pedido_item_id, minuta_atual):
    # pedido_atual, protocolo_atual, pedido_item_atual, minuta_atual_id, ato_praticado_atual, tipo_registro_atual, codigo_tabela_atual, numero_ato_praticado_atual, ato_praticado_atual_id

    # print("INICIO 11: ", minuta_atual_id, minuta_atual)

    # Atualizando a minuta escolhida

    # Atualizar_Protocolo_Atual(pedido_item_id)
    # print("Atual: ", pedido_item_atual, "exibir_direto_minuta_lv3.html", "minuta atual", minuta_atual_id)

    # Pegando o usuario atual
    current_user = str(request.user).upper()

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
    pedido_id = int(pedido_item.pedido_id)
    int(pedido_item.pedido_id)
    int(pedido_item.ato_id)
    str(pedido_item.tipo_ato)
    ato_praticado_atual = str(pedido_item.tipo_ato)
    numero_registro_auxiliar = str(pedido_item.numero_registro)
    str(pedido_item.numero_registro)
    str(pedido_item.tipo_registro)
    tipo_registro_atual = str(pedido_item.tipo_registro)
    codigo_tabela = str(pedido_item.codigo_tabela)
    str(pedido_item.codigo_tabela)
    numero_ri = str(pedido_item.numero_ri)
    numero_ato = str(pedido_item.numero_ato)
    str(pedido_item.numero_ato)

    # SELECIONAR AS CHAVES PELO PEDIDOS
    protocolo = Livro01Protocolo.objects.filter(pedido_id=pedido_id).first()

    protocolo = protocolo.numero_protocolo
    protocolo_atual = protocolo.numero_protocolo

    # LISTAR AS PERGUNTAS NO MODELO
    return render(
        request,
        "exibir_direto_minuta_lv3.html",
        {
            "numero_registro_auxiliar": numero_registro_auxiliar,
            "ato_praticado": ato_praticado_atual,
            "tipo_registro": tipo_registro_atual,
            "codigo_tabela": codigo_tabela,
            "numero_ri": numero_ri,
            "numero_ato": numero_ato,
            "current_user": current_user,
            "protocolo": protocolo_atual,
            "pedido_item_id": pedido_item_id,
        },
    )


# Gerar as perguntas para o LIVRO 3 - MINUTAS
def exibir_perguntas_minuta_lv3(request, pedido_item_id, minuta_atual):
    # global pedido_atual, protocolo_atual, pedido_item_atual, minuta_atual_id, lista_perguntas_atuais, ato_praticado_atual, tipo_registro_atual, numero_matricula_atual, codigo_tabela_atual, numero_ato_praticado_atual, ato_praticado_atual_id

    # print("INICIO 12: ", minuta_atual_id, minuta_atual)

    # Atualizando a minuta escolhida
    minuta_atual_id = minuta_atual

    # Pegando o usuario atual
    current_user = str(request.user).upper()

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

    pedido_id = int(pedido_item.pedido_id)
    int(pedido_item.pedido_id)
    int(pedido_item.ato_id)
    str(pedido_item.ato.tipo_ato)
    ato_praticado_atual = str(pedido_item.ato.tipo_ato)
    numero_registro_auxiliar = str(pedido_item.numero_registro)
    str(pedido_item.numero_registro)
    str(pedido_item.tipo_registro)
    tipo_registro_atual = str(pedido_item.tipo_registro)
    codigo_tabela = str(pedido_item.codigo_tabela)
    str(pedido_item.codigo_tabela)
    numero_ri = str(pedido_item.numero_ri)
    numero_ato = str(pedido_item.numero_ato)
    str(pedido_item.numero_ato)

    # SELECIONAR AS CHAVES PELO PEDIDOS
    protocolo = Livro01Protocolo.objects.filter(pedido_id=pedido_id).first()

    protocolo = protocolo.numero_protocolo
    protocolo_atual = protocolo.numero_protocolo

    # Selecionar as perguntas do ATO
    perguntas_t = PerguntaMinuta.objects.all().order_by("id")
    perguntas_t = PerguntaMinuta.objects.filter(corrans__in=lista_perguntas_atuais)

    # LISTAR AS PERGUNTAS NO MODELO
    return render(
        request,
        "exibir_perguntas_minuta_lv3.html",
        {
            "perguntas_t": perguntas_t,
            "numero_registro_auxiliar": numero_registro_auxiliar,
            "ato_praticado": ato_praticado_atual,
            "tipo_registro": tipo_registro_atual,
            "codigo_tabela": codigo_tabela,
            "numero_ri": numero_ri,
            "numero_ato": numero_ato,
            "current_user": current_user,
            "protocolo": protocolo_atual,
            "pedido_item_id": pedido_item_id,
            "perguntas_auxiliares": minuta_atual_id,
        },
    )


# Gerar as perguntas para o LIVRO 2 - MINUTAS
def exibir_perguntas_minuta_lv2(request, pedido_item_id, minuta_atual):
    # global pedido_atual, protocolo_atual, pedido_item_atual, minuta_atual_id, lista_perguntas_atuais

    # print("INICIO 13: ", minuta_atual_id, minuta_atual)

    # Atualizando a minuta escolhida
    minuta_atual_id = minuta_atual

    # EXIBIR O NOME DA MINUTA ATUAL
    # print(minuta_atual_id)

    # Pegando o usuario atual
    current_user = str(request.user).upper()

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
    pedido_id = int(pedido_item.pedido_id)
    int(pedido_item.ato_id)
    ato_praticado = str(pedido_item.ato.tipo_ato)
    numero_matricula = str(pedido_item.numero_registro)
    tipo_registro = str(pedido_item.tipo_registro)
    codigo_tabela = str(pedido_item.codigo_tabela)
    numero_ri = str(pedido_item.numero_ri)
    numero_ato = str(pedido_item.numero_ato)

    # SELECIONAR AS CHAVES PELO PEDIDOS
    protocolo = Livro01Protocolo.objects.filter(pedido_id=pedido_id).first()

    # Selecionar as perguntas do ATO
    perguntas_t = PerguntaMinuta.objects.all().order_by("id")
    perguntas_t = PerguntaMinuta.objects.filter(corrans__in=lista_perguntas_atuais)

    # EXIBIR AS PERGUNTAS A FAZER
    # print(perguntas_t)

    # LISTAR AS PERGUNTAS NO MODELO
    return render(
        request,
        "exibir_perguntas_minuta_lv2.html",
        {
            "perguntas_t": perguntas_t,
            "numero_matricula": numero_matricula,
            "ato_praticado": ato_praticado,
            "tipo_registro": tipo_registro,
            "codigo_tabela": codigo_tabela,
            "numero_ri": numero_ri,
            "numero_ato": numero_ato,
            "current_user": current_user,
            "protocolo": protocolo.numero_protocolo,
            "pedido_item_id": pedido_item_id,
            "perguntas_auxiliares": minuta_atual_id,
        },
    )


# Gerar as perguntas do Checklist PELO ATO ESCOLHIDO
def checklist_ato(request, pedido_item_id, protocolo_numero):
    # Checklist do protocolo pega o 1 item inserido - NO CASO PRENOTACAO
    if protocolo_numero:
        print("Protocolo: ", protocolo_numero)

        # print(request.method)

        # iniciar o checklist
        # limpar_checlist = "S"

    # Atualizando pedido item atual
    # pedido_item_atual = pedidos_itens

    # Limpar ChecklistInicio
    limpar_checlist = "S"

    if request.method == "POST":
        # print("RECEBENDO Checklist ATO .............")

        # Pegando as respostas da TEMPLATE checklist_ato.html
        d = request.POST.dict()

        # Gerando um dicionario para interagir
        for pk, value in zip(d.keys(), d.values(), strict=False):
            # print(id)

            try:
                lista = str(pk).split("-")
                # print(lista)

                origem_id, item_id, pergunta_id, pessoa_id = (
                    lista[0],
                    lista[1],
                    lista[2],
                    lista[3],
                )
            except Exception:
                logger.exception("ERRO")
                origem_id, item_id, pergunta_id, pessoa_id = "", "", "", ""

            if value != "" and origem_id != "":
                # Pegando o usuario atual
                current_user = str(request.user).upper()

                # Limpar ChecklistInicio para manter semppre o ultimo rgistro
                if limpar_checlist == "S":
                    CheckListRealizado.objects.deletar_por_pedido_item_id(
                        pedido_item_id,
                    )
                    limpar_checlist = "N"

                # Remover espaco e passar para maiuscula
                resposta = str(str(value).upper()).strip()

                # print("Gravar checklist realizado: ", pedido_item_id)
                # Grando o checllist feito no banco de dados
                CheckListRealizado.objects.gravar(
                    estado_civil_id=origem_id,
                    item_id=item_id,
                    pergunta_id=pergunta_id,
                    pessoa_id=pessoa_id,
                    funcionario_id=request.user.pk,
                    pedido_item_id=pedido_item_id,
                    resposta=resposta,
                    resposta_enviada_correta="",
                )

                # print("ERRO fim ", pedido_item_id)

            # Verificar se existe pessoa para vincular ao ATO ESPECIFICO
            PedidoParteAto.vincular_pedido_parte_ato(pedido_item_id=pedido_item_id)
            print("Anexando as partes envolvidas: ", pedido_atual, pedido_item_atual)

        # success_url = reverse_lazy("checklist_resultado")
        # return CheckListRealizado.objects.filter(pedido_item_id=pedido_item_atual)

    else:
        # LIMPAR PARA CRIAR NOVO Checklist
        # limpar_checlist = 'S'
        print("Limpar checklist: ", pedido_item_id)

        # Limpar ChecklistInicio para manter semppre o ultimo rgistro
        if limpar_checlist == "S":
            CheckListRealizado.objects.deletar_por_pedido_item_id(
                pedido_item_id=pedido_item_id,
            )
            limpar_checlist = "N"

        print("ENVIANDO  Checklist ATO ............." + request.method)

    # Pegando o usuario atual
    current_user = str(request.user).upper()

    # Iniciar as variaveis
    ato_id, _pedido_id, numero_matricula, protocolo = 0, 0, 0, 0
    ato_praticado, codigo_tabela, numero_ri, numero_ato, tipo_registro = (
        "",
        "",
        "",
        "",
        "",
    )

    # Atualizando pedido item atual

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
    pedido = int(pedido_item.pedido)
    ato_id = int(pedido_item.ato_id)
    ato_praticado = str(pedido_item.ato.tipo_ato) + ' "SEM GRUPO DEFINIDO DE Checklist"'
    numero_matricula = str(pedido_item.numero_registro)
    tipo_registro = str(pedido_item.tipo_registro)
    codigo_tabela = str(pedido_item.codigo_tabela)
    numero_ri = str(pedido_item.numero_ri)
    numero_ato = str(pedido_item.numero_ato)

    # Atualizando numero da matricula atual

    # Atualizando pedido atual
    # pedido_atual = pedido_id

    # SELECIONAR AS CHAVES PELO PEDIDOS
    protocolo = Livro01Protocolo.objects.filter(pedido=pedido).first()
    protocolo = protocolo.numero_protocolo

    # SELECIONAR AS PERGUNTAS PELO ATO
    grupo_atos = PerguntaGrupo.objects.filter(ato=ato_id)

    # Lista a ser gerada pelo grupo do ATO informado
    list_grupo = []
    for grupo in grupo_atos:
        list_grupo.append(grupo.perguntas_id)
        ato_praticado = str(grupo.atos.tipo_ato)

    # Selecionar as perguntas do ATO
    perguntas_e = Pergunta.objects.filter(id__in=list_grupo, categoria="E").order_by(
        "questions",
    )
    perguntas_t = Pergunta.objects.filter(id__in=list_grupo, categoria="T").order_by(
        "questions",
    )

    # Filtrar os ADQUIRENTES
    partes_a = PedidoParte.objects.filter(pedido=pedido, papel="A")
    perguntas_a = Pergunta.objects.filter(categoria="E", setores=2, pergunta_ativa="S")
    perguntas_a_t = Pergunta.objects.filter(
        categoria="T",
        setores=2,
        pergunta_ativa="S",
    ).order_by(
        "questions",
    )

    # Filtrar os TRANSMITENTES
    partes_t = PedidoParte.objects.filter(pedido=pedido, papel="T")

    perguntas_r = Pergunta.objects.filter(categoria="E", setores=3, pergunta_ativa="S")

    perguntas_r_t = Pergunta.objects.filter(
        categoria="T",
        setores=3,
        pergunta_ativa="S",
    ).order_by(
        "questions",
    )

    # Filtrar os CREDORES
    partes_c = PedidoParte.objects.filter(pedido=pedido, papel="C")
    perguntas_c = Pergunta.objects.filter(
        categoria="E",
        setores=2,
        pergunta_ativa="S",
    )

    perguntas_c_c = Pergunta.objects.filter(
        categoria="T",
        setores=2,
        pergunta_ativa="S",
    ).order_by(
        "questions",
    )

    # Filtrar os DEVEDORES
    partes_d = PedidoParte.objects.filter(pedido=pedido, papel="D")
    perguntas_d = Pergunta.objects.filter(categoria="E", setores=3, pergunta_ativa="S")
    perguntas_d_d = Pergunta.objects.filter(
        categoria="T",
        setores=3,
        pergunta_ativa="S",
    ).order_by(
        "questions",
    )

    print("Itens ENVIADO para checklist:", pedido_item_id)

    return render(
        request,
        "checklist_ato.html",
        {
            "perguntas_e": perguntas_e,
            "perguntas_t": perguntas_t,
            "partes_a": partes_a,
            "perguntas_a": perguntas_a,
            "perguntas_a_t": perguntas_a_t,
            "partes_t": partes_t,
            "perguntas_r": perguntas_r,
            "perguntas_r_t": perguntas_r_t,
            "partes_c": partes_c,
            "perguntas_c": perguntas_c,
            "perguntas_c_c": perguntas_c_c,
            "partes_d": partes_d,
            "perguntas_d": perguntas_d,
            "perguntas_d_d": perguntas_d_d,
            "numero_matricula": numero_matricula,
            "ato_praticado": ato_praticado,
            "tipo_registro": tipo_registro,
            "codigo_tabela": codigo_tabela,
            "numero_ri": numero_ri,
            "numero_ato": numero_ato,
            "current_user": current_user,
            "protocolo": protocolo,
            "pedido_item_id": pedido_item_id,
        },
    )


# Gerar as perguntas do Checklist PELO ATO ESCOLHIDO
def checklist_ato_resultado(request, pedido_item_id):
    perguntas_e = {"AAA": "xxx", "BBB": "xxx", "ccc": "xxx"}
    numero_matricula = "AA"
    ato_praticado = "AA"
    tipo_registro = "AA"
    codigo_tabela = "AA"
    numero_ri = "AA"
    numero_ato = "AA"
    current_user = "AA"
    protocolo = 0
    pedido_item_id = 0

    return render(
        request,
        "checklist_ato_resultado.html",
        {
            "perguntas_e": perguntas_e,
            "numero_matricula": numero_matricula,
            "ato_praticado": ato_praticado,
            "tipo_registro": tipo_registro,
            "codigo_tabela": codigo_tabela,
            "numero_ri": numero_ri,
            "numero_ato": numero_ato,
            "current_user": current_user,
            "protocolo": protocolo,
            "pedido_item_id": pedido_item_id,
        },
    )


def retornar_estado_do_registro(numero) -> str:
    """Formate o número para seis casas decimais."""
    return f"{int(numero):06d}"


def importar_registro_auxiliar(
    request,
    numero_registro,
    tipo_registro,
    cartorio_imovel,
):
    # Obter protocolo informado
    try:
        importar_livro03_do_fb(
            {
                "NUMERO_IMOVEL": numero_registro,
                "TIPO_IMOVEL": tipo_registro,
                "NUMERO_RI": cartorio_imovel,
            },
        )
    except Exception as e:
        logger.exception(f"ERRO IMPORTACAO DE REGISTRO AUXILIAR DO LIVRO 3 {e!s}")

    return redirect(reverse("home:livro03_list"))


def importar_imovel_pelo_id_view(request, imovel_id):
    with transaction.atomic(), firebird.FbConnection() as db:
        try:
            db.begin_transaction()
            numero_registro, numero_registro, tipo_registro, cartorio_imovel = (
                converter_livro02_pelo_id_do_fb(
                    imovel_id,
                    db,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            numero_registro = None
            logger.exception("ERRO")

    if numero_registro:
        # Redireciona com os parâmetros obtidos
        return redirect(
            "home:livro04_detail",
            numero_registro=numero_registro,
            tipo_registro=tipo_registro,
            cartorio_imovel=cartorio_imovel,
        )
    else:
        return redirect(
            "home:livro04_detail",
            numero_registro=0,
            tipo_registro=TipoRegistro.MATRICULA,
            cartorio_imovel="1",
        )


def importar_imovel_view(request, pedido_item_id):
    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
    db = firebird.FbConnection()
    db.begin_transaction()
    with transaction.atomic():
        try:
            converter_livro02_do_fb(pedido_item, db)
            db.commit()
            db.close()
        except Exception:
            db.rollback()
            db.close()
            logger.exception("ERRO")

    # Redireciona com os parâmetros obtidos
    return redirect(
        "home:livro04_detail",
        numero_registro=pedido_item.numero_registro,
        tipo_registro=pedido_item.tipo_registro,
        cartorio_imovel=pedido_item.numero_ri,
    )


# Gerar as perguntas do Checklist PELO ATO ESCOLHIDO
class ImportarProtocoloDiretoView(View):
    def get(self, request, numero_protocolo):
        referer_url = request.META.get("HTTP_REFERER", reverse("home:protocolo_search"))

        if not numero_protocolo:
            messages.error(request, "Número do protocolo não informado.")
            return redirect(referer_url)

        with firebird.FbConnection() as db:
            db.begin_transaction()
            try:
                protocolo, _ = firebird.importar_protocolo_por_numero_fb(
                    numero_protocolo=numero_protocolo,
                    tipo_importacao=None,
                    db=db,
                )
            except Exception as e:
                logger.exception(f"ERRO IMPORTACAO DE PROTOCOLO: {e!s}")
                messages.error(
                    request,
                    f"Não foi possível importar o protocolo informado. {numero_protocolo!s}: {e!s}",
                )
                db.rollback()
                return redirect(referer_url)

            db.commit()

        if protocolo:
            messages.info(
                request,
                f"Protocolo {protocolo.numero_protocolo} atualizado!",
            )
            return redirect(referer_url)
        else:
            messages.error(
                request,
                f"Não foi possível importar o protocolo informado. {numero_protocolo!s}",
            )

        return redirect(referer_url)


def corrigir_protocolo_certidao():
    # Obtém a data atual
    hoje = timezone.now().date()
    print(hoje)

    categorida_financeira_id = 2
    categorida_financeira_certidao_id = 3

    # Filtra objetos com ambos pedido_id e numero_pedido_certidao não nulos
    resultados = Financeiro.objects.filter(
        pedido_id__isnull=False,
        numero_pedido_certidao__isnull=False,
    )

    # Consulta usando Django ORM - PROTOCOLO
    resultados_categoria = Financeiro.objects.filter(
        data_transacao__gte=hoje,
        pedido_id__isnull=False,
    ).exclude(
        tipo_categoria_financeira_id=categorida_financeira_id,
    )

    # Consulta usando Django ORM - PEDIDO DE CERTIDAO
    resultados_certidao_categoria = Financeiro.objects.filter(
        data_transacao__gte=hoje,
        pedido_certidao_id__isnull=False,
    ).exclude(
        tipo_categoria_financeira_id=categorida_financeira_certidao_id,
    )

    # Itera sobre os resultados filtrados
    for item in resultados:
        logger.info(
            f"Duplicado numero do pedido certidao: {item.pedido_id}, {item.numero_pedido_certidao}",
        )

        # Se o numero_pedido_certidao não for vazio, remove seu valor
        if item.numero_pedido_certidao:
            item.numero_pedido_certidao = None
            item.save()

    # Itera sobre os resultados filtrados - CORRIGINDO PARA CATEGORIA DE PROTOCOLO
    for pedido in resultados_categoria:
        logger.info(f"Corrigindo categoria de protocolo: {pedido.pedido_id} ")

        # Atualizar categoriaa
        if pedido.pedido_id:
            finaceiro = Financeiro.objects.get(pk=pedido.id)
            finaceiro.tipo_categoria_financeira_id = categorida_financeira_id
            finaceiro.save()

    # Itera sobre os resultados filtrados - CORRIGINDO PARA CATEGORIA DE PEDIDO DE CERTIDAO
    for pedido_certidao in resultados_certidao_categoria:
        logger.info(
            f"Corrigindo categoria de certidao: {pedido_certidao.pedido_certidao_id} ",
        )

        # Atualizar categoriaa
        if pedido_certidao.pedido_certidao_id:
            finaceiro = Financeiro.objects.get(pk=pedido_certidao.id)
            finaceiro.tipo_categoria_financeira_id = categorida_financeira_certidao_id
            finaceiro.save()

    # TEMPORARIO CORRIGIR EXPORTACAO NO SQL SERVER
    user = User.get_usuario_sistema()
    if user.cartorio.usar_selo_sql_server == "S":
        Certidao.atualizar_valores_selo_sqlserver()

    # # VERIFICAR SE HOUVE MUDANCANCA DE NUMERO DE PEDIDO DE CERTIDAO - CAIXA recber DIFERENCA
    # Subquery to get numero_pedido from PedidoCertidao
    subquery_pedido_certidao = PedidoCertidao.objects.filter(
        id=Cast(OuterRef("pedido_certidao_id"), IntegerField()),
    ).values("numero_pedido")[:1]

    # Query to get Financeiro records with different numero_pedido_certidao and numero_pedido
    query_set_certidao_financeiro = (
        Financeiro.objects.filter(
            pedido_certidao_id__isnull=False,
            numero_pedido_certidao__isnull=False,
        )
        .annotate(
            pedido_certidao_int=Cast("pedido_certidao_id", IntegerField()),
            numero_pedido_certidao_int=Cast("numero_pedido_certidao", IntegerField()),
            numero_pedido=Subquery(subquery_pedido_certidao),
        )
        .exclude(
            numero_pedido_certidao_int=F("numero_pedido"),
        )
        .order_by(
            "-pedido_certidao_int",
        )
        .values(
            "pedido_certidao_id",
            "numero_pedido_certidao",
            "numero_pedido",
            "data_transacao",
        )
    )
    try:
        # Atualiza o número de pedido se houve diferença
        if query_set_certidao_financeiro.exists():
            # Cria uma lista de objetos para serem atualizados em massa
            certidoes_para_atualizar = []
            for item_certidao in query_set_certidao_financeiro:
                pedido_certidao = PedidoCertidao.objects.get(
                    id=item_certidao["pedido_certidao_id"],
                )
                pedido_certidao.numero_pedido = item_certidao["numero_pedido_certidao"]
                certidoes_para_atualizar.append(pedido_certidao)

            # Atualiza os objetos em massa
            PedidoCertidao.objects.bulk_update(
                certidoes_para_atualizar,
                ["numero_pedido"],
            )
    except Exception as e:
        logger.exception(f"ERRO AO ATUALIZAR NUMERO DE PEDIDO DE CERTIDAO: {e!s}")

    # ATUALIZAR A CATEGORIA DE FINANCEIRO PROTOCOLO     # Negando o filtro de igualdade
    Financeiro.objects.filter(
        Q(pedido_id__isnull=False) & ~Q(tipo_categoria_financeira_id=2),
    ).update(tipo_categoria_financeira_id=2)

    # Atualizar os registros filtrados
    Financeiro.objects.filter(
        Q(numero_pedido_certidao__isnull=False) & ~Q(tipo_categoria_financeira_id=3),
    ).update(tipo_categoria_financeira_id=3)

    # CORRECOES NO FIREBIRD
    command = """
        UPDATE PEDIDOS_ITENS
        SET CODIGO_TIPO_TRIBUTACAO = 1
        WHERE ANO_REFERENCIA_TABELA = 2024
        AND CODIGO_TIPO_TRIBUTACAO IS NULL
        AND ANO_REFERENCIA_TABELA IS NOT NULL;
    """
    firebird.executar_em_thread(command)

    command = """
        UPDATE PEDIDOS_ITENS
        SET CUSTAS = 1,
        CODIGO_TIPO_TRIBUTACAO = 4
        WHERE CODIGO_TIPO_TRIBUTACAO = 5;
    """
    firebird.executar_em_thread(command)

    command = """
        UPDATE PEDIDOS_ITENS
        SET VALOREMOLUMENTO = VALOREMOLUMENTO + VALOR_FUNDOESTADO
        WHERE ANO_REFERENCIA_TABELA = 2024
        AND VALOREMOLUMENTO = EMOLUMENTOLIQ
        AND VALOREMOLUMENTO >= 0
        AND VALOR_FUNDOESTADO >= 0
        AND EMOLUMENTOLIQ >= 0
    """
    firebird.executar_em_thread(command)

    # Atualizando os registros que atendem às condições
    colaboradores_ids = [59, 1, 85]
    data_limite = datetime(2024, 8, 1)
    nova_data = datetime(2000, 1, 1)

    # Atualizando os registros que atendem às condições
    Financeiro.objects.filter(
        data_transacao__gte=data_limite,
        colaborador_id__in=colaboradores_ids,
    ).update(data_transacao=nova_data)

    Financeiro.objects.filter(
        pedido_certidao_id__isnull=False,
        numero_pedido_certidao__isnull=True,
    ).delete()


# VERIFICAR OS ULTIMOS
def verificar_protocolos_nao_importado(
    request,
    tipo_importacao: TipoImportacao = TipoImportacao.Total,
):
    from apps.cartorios.models import Cartorio

    atualizar_somente_caixa = Cartorio.objects.all().values_list(
        "atualizar_somente_caixa",
        flat=True,
    )[0]
    if str(atualizar_somente_caixa) == "S":
        # Pegar enviados para o caixa
        with transaction.atomic(), firebird.FbConnection() as db:
            try:
                # SINCRONIZAR CAIXA SISTEMA ANTERIOR - COMENTADO
                db.begin_transaction()
                firebird.importar_caixa_faltantes(db=db)
                db.commit()

                # ATUALIZAR DATA DE SINCRONISMO
                firebird.atualizar_data_sincronismo()
                if request:
                    messages.info(request, " caixa atualizado !")
            except Exception:
                db.rollback()
                if request:
                    messages.error(request, "Não foi possível importar o caixa.")
                logger.exception("ERRO IMPORTACAO CAIXA ")

        # CORRIGIR CAIXA PROTOCOLO E PEDIDO NO MESMO LUGAR.
        corrigir_protocolo_certidao()
    else:
        # Pegar protocolo informado
        with transaction.atomic(), firebird.FbConnection() as db:
            try:
                db.begin_transaction()

                # Importar apenas os adicionados recentemente
                protocolos = firebird.importar_protocolos_faltantes(
                    tipo_importacao=tipo_importacao,
                    db=db,
                )
                db.commit()

                # ATUALIZAR DATA DE SINCRONISMO
                firebird.atualizar_data_sincronismo()

                # VERIFICAR SE EXISTEM DISTRIBUICOES FALTANTES
                Livro01Protocolo.atualizar_distribuicao_protocolos()

                if request:
                    messages.info(request, f"{len(protocolos)} protocolos atualizados!")
            except Exception:
                db.rollback()

                if request:
                    messages.error(request, "Não foi possível importar os protocolos.")
                logger.exception("ERRO IMPORTACAO DE PROTOCOLOS")
                raise

    # RETORNAR PARA O MESMO COLABORADOR
    if request:
        if str(atualizar_somente_caixa) == "S":
            # Obtém a data atual
            hoje = timezone.now().date()
            colaborador = request.user.id

            # Cria a URL com os parâmetros de data
            url = f"{reverse('home:financeiro_listar_por_colaborador')}?data_transacao_inicio={hoje}&data_transacao_fim={hoje}&colaborador={colaborador}"
            return redirect(url)
        else:
            return redirect(reverse("home:protocolos_list"))
    return None


# Gerar as perguntas do Checklist PELO ATO ESCOLHIDO
def importar_protocolo_por_colaborador(request, colaborador_id):
    colaborador: Colaborador = Colaborador.objects.filter(pk=colaborador_id).first()
    if not colaborador:
        messages.error(request, "Colaborador não encontrado.")
        return redirect(reverse("home:protocolos_list"))

    # Obter protocolo informado
    with transaction.atomic(), firebird.FbConnection() as db:
        try:
            db.begin_transaction()
            colaborador.importar_protocolos_do_fb(db)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception("ERRO IMPORTACAO DE PROTOCOLOS POR COLABORADOR")
            messages.error(
                request,
                f"Não foi possível importar os protocolos: Erro: {e!s}",
            )

    # RETORNAR PARA O MESMO COLABORADOR
    return redirect(colaborador.get_distribuidos_url())


# FILTrAR A PESQUISA E RELATORIO
def relatorio_previo_data(request):
    # print("Imprimir Relatorio Previo")

    # Use request.GET.get para obter os parâmetros da URL
    start_date = request.GET.get("data_pesquisa_i")
    end_date = request.GET.get("data_pesquisa_f")
    saldo_inicial = 0

    # Inicial o Saldo Inicial
    comandos_sql.saldo_inicial = Decimal(saldo_inicial)
    resumo.saldo_inicial = Decimal(saldo_inicial)

    # VERIFICAR SE EXISTEM REGISTROS NESTE PERIODO
    if (
        comandos_sql.gerar_Relatorio(
            "Completo",
            start_date,
            end_date,
        )
        > 0
    ):
        resumo.gerar_Relatorio(start_date, end_date)
        planilhas.gerar_Relatorio()
    else:
        messages.error(request, "Não encontrou registros neste período")
        # print("Não encontrou registros neste período")

    return redirect(reverse("home:financeiro_previo"))


# INICIAR A PESQUISA
def financeiro_previo(request):
    # print("Iniciar - Relatorio Previo")
    template_name = "financeiro_previo.html"

    # Use request.GET.get para obter os parâmetros da URL
    start_date_str = request.GET.get("data_pesquisa_i")
    end_date_str = request.GET.get("data_pesquisa_f")

    # Valores padrão para as datas
    default_start_date = timezone.now().date() - timedelta(0)
    default_end_date = timezone.now().date() + timedelta(0)

    try:
        # Se as datas forem fornecidas, converte-as para objetos de data
        start_date = (
            datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if start_date_str
            else default_start_date
        )
        end_date = (
            datetime.strptime(end_date_str, "%Y-%m-%d").date() + timedelta(0)
            if end_date_str
            else default_end_date
        )
    except ValueError:
        # Se houver erro na conversão, use os valores padrão
        start_date = default_start_date
        end_date = default_end_date

    context = {
        "data_inicio": str(start_date),
        "data_fim": str(end_date),
        "parent": "Financeiro",
        "segment": "Prévio",
    }

    return render(request, template_name, context)


def importar_protocolo_por_numero_view(request, numero_protocolo: int):
    # Receber o número de protocolo informado via get:
    numero_protocolo = request.GET.get("numero_protocolo_importar")

    if not numero_protocolo:
        messages.error(request, "Número de protocolo não informado.")
        return redirect(reverse("home:protocolo_search"))

    with firebird.FbConnection() as db:
        db.begin_transaction()
        protocolo, _ = firebird.importar_protocolo_por_numero_fb(
            numero_protocolo,
            tipo_importacao=None,
            db=db,
        )
        db.commit()

    if protocolo:
        # Redireciona para a URL do protocolo
        return redirect(protocolo.get_absolute_url())
    else:
        messages.error(request, "Não foi possível importar o protocolo informado.")

    # Redireciona para a lista de itens do protocolo se o número do protocolo não for fornecido
    # ou a importação falhar
    return redirect(reverse("home:protocolo_search"))


# IMPORTAR O PROTOCOLO PARA PEGAR AS DIFERENCAS
def importar_protocolo_caixa_diferenca_view(request):
    # Receber o número de protocolo informado via POST
    numero_protocolo = request.POST.get("numero_protocolo_importar")
    protocolo_anterior = numero_protocolo

    if not numero_protocolo:
        messages.error(request, "Número de protocolo não informado.")
        return redirect(reverse("home:protocolo_search"))

    with transaction.atomic(), firebird.FbConnection() as db:
        # VERIFICAR SE NAO FOI REPROTOCOLADO
        texto_base = "Prot. Posterior:"
        texto_localizar = "'%" + texto_base + "%'"
        message = "0"

        protocolo_posterior = firebird.protocolo_posterior_existe_fb(
            numero_protocolo,
            texto_localizar,
            db,
        )

        #  REPROTOCOLADO - FORMATAR PARA SER O NOVO PROTOCOLO A IMPORTAR
        if protocolo_posterior:
            protocolo_posterior = (
                str(protocolo_posterior)
                .replace(texto_base, "")
                .replace(" ", "")
                .replace(".", "")
            )

            message = f"Protocolo {numero_protocolo} foi reprocolado para {protocolo_posterior}"
            messages.warning(request, message)
            numero_protocolo = str(protocolo_posterior)

        try:
            db.begin_transaction()
            firebird.importar_protocolo_por_numero_fb(
                numero_protocolo=numero_protocolo,
                tipo_importacao="P",
                db=db,
            )
            db.commit()

            # Atualizar no prime os protocolos ANTERIOR E POSTERIOR
            if protocolo_posterior:
                atualizar_protocolo_anterior(protocolo_anterior, protocolo_posterior)

            # # FILTRAR PEDIDO - ORIGINAL - CALCULAR DIFERENCA
            protocolo = Livro01Protocolo.objects.filter(
                numero_protocolo=numero_protocolo,
            ).first()

            valor_diferenca = protocolo.verificar_diferenca_sistema_antigo(db)

            url = reverse(
                "home:enviar_pedido_de_protocolo_ao_caixa",
                args=[numero_protocolo, valor_diferenca],
            )
            return redirect(url)

        except Exception:
            msg = "Não foi possível importar o protocolo informado"
            logger.exception(msg)
            logger.exception(msg)

    messages.error(request, "Não foi possível importar o protocolo informado.")

    print("Encerrado importação do livro 01")
    # Redireciona para a lista de itens do protocolo se o número do protocolo não for fornecido
    # ou a importação falhar
    return redirect(reverse("home:protocolo_search"))


def importar_protocolo_view(request):
    # Receber o número de protocolo informado via POST
    numero_protocolo = request.POST.get("numero_protocolo_importar")

    if not numero_protocolo:
        messages.error(request, "Número de protocolo não informado.")
        return redirect(reverse("home:protocolo_search"))

    with transaction.atomic(), firebird.FbConnection() as db:
        try:
            db.begin_transaction()
            protocolo, _ = firebird.importar_protocolo_por_numero_fb(
                numero_protocolo=numero_protocolo,
                tipo_importacao=None,
                db=db,
            )
            db.commit()

            protocolo = Livro01Protocolo.objects.filter(
                numero_protocolo=numero_protocolo,
            ).first()

            if protocolo:
                return redirect(protocolo.get_absolute_url())

            messages.error(request, "Não foi possível importar o protocolo informado.")

            return redirect(reverse("home:protocolo_search"))
        except Exception:
            protocolo = None
            msg = "Não foi possível importar o protocolo informado"
            logger.exception(msg)
            logger.exception(msg)

    messages.error(request, "Não foi possível importar o protocolo informado.")

    print("Encerrado importação do livro 01")
    # Redireciona para a lista de itens do protocolo se o número do protocolo não for fornecido
    # ou a importação falhar
    return redirect(reverse("home:protocolo_search"))


def importar_protocolos_do_dia_view(request):
    try:
        protocolos_de_hoje = firebird.importar_protocolos_de_hoje()
        quantidade = len(protocolos_de_hoje)
        if quantidade > 0:
            messages.info(request, f"{quantidade} protocolos atualizados!")
        else:
            messages.warning(request, "Nenhum protocolo para atualizar.")
    except Exception:
        logger.exception()
        messages.error(request, "Erro ao atualizar os protocolos do dia: ")

    # RETORNAR PARA O MESMO PROTOCOLO
    # success_url = reverse_lazy("atualizar_protocolo")
    return redirect(reverse("home:protocolo_search"))


def importar_andamentos_protocolo_view(request):
    with transaction.atomic():
        andamentos_importados = firebird.importar_andamentos_modificados()

    if andamentos_importados:
        messages.info(request, f"{len(andamentos_importados)} andamentos atualizados!")
    else:
        messages.warning(request, "Nenhum andamento para importar.")

    # recupera o usuario logado
    request.user.cartorio.atualizar_hora_do_sincronismo()

    return redirect(reverse("home:protocolo_search"))


def importar_protocolos_modificados_2_dias_view(request):
    protocolo_importados = firebird.importar_protocolos_modificados_ultimos_2_dias()

    if protocolo_importados:
        messages.info(request, f"{len(protocolo_importados)} protocolos atualizados!")
    else:
        messages.warning(request, "Nenhum protocolo para importar.")

    return redirect(reverse("home:protocolo_search"))


def importar_protocolos_modificados_view(request):
    # protocolo_importados = firebird.importar_protocolos_modificados_ultimos_2_dias()
    protocolo_importados = firebird.importar_protocolos_modificados_30_dias()

    if protocolo_importados:
        messages.info(request, f"{len(protocolo_importados)} protocolos atualizados!")
    else:
        messages.warning(request, "Nenhum protocolo para importar.")

    return redirect(reverse("home:protocolo_search"))


def importar_imovel_numero_view(request):
    numero_i = int(request.POST["numero_i"])
    numero_f = int(request.POST["numero_f"]) + 1
    cartorio_ri = request.POST["cartorio_ri"]
    tipo_registro = request.POST["tipo_registro"]

    # CONVERTER PARA INTEIRO
    numero_i = int(numero_i)
    numero_f = int(numero_f)

    # Validando a entrada
    if numero_i > numero_f:
        # Talvez adicionar uma mensagem de erro para o usuário
        return redirect(reverse("home:livro02_list"))

    # with transaction.atomic():
    if tipo_registro == "A":
        for numero in range(numero_i, numero_f):
            importar_registro_auxiliar(request, str(numero), "A", str(cartorio_ri))
    else:
        # IMPORTAR NO FIREBIRD

        for numero in range(numero_i, numero_f):
            db = firebird.FbConnection()
            db.begin_transaction()

            # Inicio das conversoes - iMOVEL
            imovel_fb = get_registro_do_fb(
                numero_registro=str(numero),
                tipo_registro=str(tipo_registro),
                cartorio_registro=str(cartorio_ri),
                db=db,
            )

            if imovel_fb:
                # criar_registro_da_unidade(imovel_fb[0], True)
                # GRAVANDO O IMOVEL
                gravar_registro_importado_do_fb(imovel_fb, db)

                try:
                    importar_ficha_do_fb_e_gravar_no_livro02(
                        imovel_id=imovel_fb[0]["CHAVE_IMOVEIS"],
                        db=db,
                    )
                except Exception:
                    logger.exception("Erro para importar o texto:")

            # converter_livro02_pelo_id_do_fb(imovel_fb[0])
            db.commit()

    if tipo_registro == "A":
        return redirect(reverse("home:livro03_list"))
    else:
        return redirect(reverse("home:livro02_list"))


# Gerar as perguntas do Checklist PELO ATO ESCOLHIDO
@login_required
def importar_protocolo_data_view(request):
    data_protocolo_i = request.POST.get(
        "data_protocolo_i",
        timezone.now().date() - timedelta(1),
    )
    data_protocolo_f = request.POST.get(
        "data_protocolo_f",
        timezone.now().date() + timedelta(1),
    )
    user_id = request.user.id

    with firebird.FbConnection() as db:
        numeros_protocolos = firebird.importar_protocolos_por_data_entrada(
            data_protocolo_i,
            data_protocolo_f,
            user_id,
            db,
        )

    if numeros_protocolos:
        try:
            messages.info(request, f"{len(numeros_protocolos)} protocolos atualizados!")
        except:
            messages.info(request, "protocolos atualizados!")
    else:
        messages.warning(request, "Nenhum protocolo para importar.")

    return redirect(reverse("home:protocolo_search"))


# Acessar Imagem
def exibir_imagem(request):
    # PEGA DA TEMPLATE O NUMERO INFORMADO
    numero_registro = request.POST["numero_informado"]
    # cartorio_id = request.POST["numero_cartorio"]
    tipo_registro = request.POST["tipo_registro"]

    imovel = Livro02.objects.filter(
        numero_registro=numero_registro,
        tipo=tipo_registro,
    ).first()

    # return redirect("home:gerar_minuta_imagem", id=numero_id, tipo=tipo_registro)
    return redirect("home:registro_imagens", pk=imovel.pk)


@login_required
def protocolos_list(request: HttpRequest):
    queryset = Livro01Protocolo.objects.all()
    filter = filters.Livro01ProtocoloFilter(request.GET, queryset=queryset)
    tabela = Livro01ProtocoloTable(filter.qs)

    # Configura a paginação da tabela
    RequestConfig(
        request,
        paginate={
            "per_page": request.user.paginate_by
            if hasattr(request.user, "paginate_by")
            else 10,
        },
    ).configure(tabela)

    context = {
        "filter": filter,
        "protocolos": filter.qs,
        "table": tabela,
        "segment": "livro01_list",
        "parent": "livro01",
    }

    return render(request, "protocolo/protocolos_list.html", context)


class PedidoPartesListView(LoginRequiredMixin, ListView):
    model = PedidoParte
    template_name = "livro01/partes/livro01_partes_list.html"
    context_object_name = "partes"
    extra_context = {"segment": "Partes", "parent": "partes"}

    def get_table_pagination(self):
        return {"per_page": self.request.user.paginate_by if self.request.user else 10}

    def get_queryset(self) -> None:
        super().get_queryset().order_by("-numero_protocolo")
        PedidoParte.objects.exclude(papel=SIM).filter(pedido_id=self.pedido).order_by(
            "papel",
            "id",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["table"] = PedidoPartesTable(self.get_queryset())

        if "export" not in self.request.GET:
            RequestConfig(self.request).configure(context["table"])

        return context

    def get(self, request, *args, **kwargs):
        if "export" in request.GET:
            table = PedidoPartesTable(self.get_queryset())
            return exportar_table(table)
        return super().get(request, *args, **kwargs)


@login_required
def protocolos_doi_list_view(request):
    # CAPTURANDO O 1 DIA DO MES
    start_date = timezone.now().replace(day=1)
    end_date = timezone.now().date()

    andamentos = Livro01Andamento.objects.filtrar_por_data_andamento_registrado(
        start_date,
        end_date,
    )

    pedidos = [andamento.protocolo.pedido for andamento in andamentos]

    # Lista pelo os pedidos itens
    queryset = PedidoItem.objects.filter(
        pedido__in=pedidos,
        ato_id__in=AtoPratica.objects.get_atos_doi(),
        numero_registro__isnull=False,
        tipo_registro=TipoRegistro.MATRICULA,
    ).order_by("-numero_registro")

    # queryset = Livro01Protocolo.objects.order_by("-numero_protocolo")

    doi_filter = filters.DoiFilter(request.GET, queryset=queryset)
    doi_table = DoiTable(filter.qs)
    if "export" not in request.GET:
        RequestConfig(request, paginate={"per_page": 10}).configure(doi_table)

    # Tratar a exportação separadamente para evitar processamento desnecessário
    if "export" in request.GET:
        return exportar_table(doi_table)

    context = {
        "filter": doi_filter,
        "table": doi_table,
    }

    return render(request, "protocolo/protocolos_doi_list.html", context)


# GERAR DOI
def LivroDOI(request):
    from apps.home.services.doi import gerar_declaracoes_json

    gerar_declaracoes_json(request)

    context = {}
    return render(request, "index.html", context)


class Livro02ListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = Livro02
    context_object_name = "livro02_list"
    template_name = "livro02/livro02_list.html"
    table_class = Livro02Table
    filterset_class = filters.Livro02Filter
    paginate_by = 10
    extra_context = {
        "segment": "livro02_list",
        "parent": "livros",
        "title": "Livro 02 - Registro Geral",
    }

    def render_to_response(self, context, **response_kwargs):
        if "export" in self.request.GET:
            return exportar_table(context["table"])
        return super().render_to_response(context, **response_kwargs)


class Livro03ListView(LoginRequiredMixin, ListView):
    model = Livro03
    context_object_name = "livro03_list"
    template_name = "livro03/livro03_list.html"
    paginate_by = 10
    extra_context = {
        "segment": "livro03",
        "parent": "livros",
        "title": "Livro 03 - Registro Auxiliar",
    }

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-data_abertura")
        self.filter = filters.Livro03Filter(self.request.GET, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table = Livro03Table(self.get_queryset())
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(
            table,
        )
        context["filter"] = self.filter
        context["table"] = table

        return context

    def render_to_response(self, context, **response_kwargs):
        if "export" in self.request.GET:
            exporter = TableExport("xlsx", context["table"], exclude_columns=("ação"))
            response = HttpResponse(
                exporter.export(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="protocolos.xlsx"'
            return response
        return super().render_to_response(context, **response_kwargs)


@login_required
def protocolo_search_view(request):
    numero_protocolo = request.GET.get("numero_protocolo")
    protocolo = Livro01Protocolo.objects.filter(
        numero_protocolo=numero_protocolo,
    ).first()

    if protocolo:
        return redirect(protocolo.get_absolute_url())
    else:
        messages.error(request, "Protocolo não encontrado.")
        return redirect(reverse("home:protocolos_list"))


@login_required
def livro01_protocolo_detail(request, pk):
    protocolo = get_object_or_404(Livro01Protocolo, pk=pk)

    tipos_tributacao_protocolo = TipoTributacao.objects.filter(utilizado="S").order_by(
        "outros_codigo_trib_tj",
    )

    tipos_imoveis_protocolos = TipoRegistroProtocolo.objects.all().order_by("ordem")

    partes_a = []
    partes_c = []
    partes_lri = []
    partes_t = []
    partes_d = []
    quantidade_lri = []
    alienacoes_atuais = []
    vinculado_imovel_atual = []

    for item_l2 in protocolo.livro_02:
        registros_l2 = Livro02.objects.filter(
            numero=item_l2.numero_registro,
            tipo=item_l2.tipo_registro,
            cartorio=item_l2.numero_ri,
        )
        for _imovel in registros_l2:
            for alienacao in alienacoes_atuais:
                pessoa = get_pessoa(alienacao.pessoa)
                if pessoa:
                    info_alienacao = formatar_informacao_alienacao(alienacao, pessoa)
                    alienacoes_atuais.append(info_alienacao)

    for imovel_vinculado_l3 in vinculado_imovel_atual:
        cancelado_em_formatada = formatar_data(
            imovel_vinculado_l3.registro_auxiliar.data_vencimento,
            1,
        )
        status = "ABERTO" if not cancelado_em_formatada else "CANCELADO"
        vinculado_imovel_atual.append(status)
        vinculado_imovel_atual.extend(
            [
                get_info_imovel(imovel_vinculado_l3),
                get_info_produto(imovel_vinculado_l3),
                get_info_datas(imovel_vinculado_l3, cancelado_em_formatada),
            ],
        )

    data_ultima_indisponibilidade = timezone.now()
    data_ultima_indisponibilidade_c = ""
    andamentos_agrupados_por_status = Livro01Andamento.objects.agrupar_por_status(
        [protocolo.pk],
    )

    total_protocolos_em_andamento, total_protocolos_vinculados = 0, 0

    if protocolo.status_id not in helpers.get_servicos_finalizar_status():
        total_protocolos_em_andamento, total_protocolos_vinculados = (
            helpers.gerar_lista_numero_pesquisar(
                protocolo.titulos_principais,
                protocolo.pedido_id,
            )
        )

    existem_protocolos_em_andamento = total_protocolos_em_andamento > 0

    pendencias = ChecklistRealizadoHistorico.objects.filter(pedidos=protocolo.pedido.pk)

    is_reprotocolable = (
        protocolo.numero_protocolo_anterior_id is None
        and protocolo.numero_protocolo_posterior_id is None
    )

    # verificar se os andamentos estao sincronizados com sistema antigo
    if protocolo:
        protocolo.verificar_andamentos_sistema_antigo()

    context = {
        "existem_protocolos_em_andamento": existem_protocolos_em_andamento,
        "total_protocolos_em_andamento": total_protocolos_em_andamento,
        "total_protocolos_vinculados": total_protocolos_vinculados,
        "protocolo": protocolo,
        "estado": protocolo.pedido.estado,
        "fases": protocolo.fases,
        "quantidade_titulo_principal": protocolo.quantidade_titulo_principal,
        "livro_2": protocolo.livro_02,
        "livro_3": protocolo.livro_03,
        "imagens_protocolo": protocolo.imagens_protocolo,
        "livro_4": [],
        "partes_a": partes_a,
        "partes_t": partes_t,
        "partes_c": partes_c,
        "partes_d": partes_d,
        "partes_lri": partes_lri,
        "quantidade_lri": quantidade_lri,
        "data_ultima_indisponibilidade": data_ultima_indisponibilidade,
        "data_ultima_indisponibilidade_c": data_ultima_indisponibilidade_c,
        "pendencias": pendencias,
        "exigencia": andamentos_agrupados_por_status["exigencia"],
        "exigencia_positivas": andamentos_agrupados_por_status["exigencia_positiva"],
        "tipo_ato_protocolo": AtoPratica.objects.all(),
        "tipo_tributacao_protocolo": tipos_tributacao_protocolo,
        "tipo_registro_protocolo": tipos_imoveis_protocolos,
        "imagens_nota_devolucao": protocolo.imagens_nota_devolucao,
        "numero": protocolo.numero_protocolo,
        "assinar_nota_devolucao_digital": request.user.assinar_nota_devolucao_digital,
        "protocolo_content_type": protocolo.content_type,
        "parent": "livro01",
        "segment": "protocolo_detail",
        "is_reprotocolable": is_reprotocolable,
    }

    return render(request, "livro01/protocolo_detail.html", context)


# @login_required(login_url="/login/")
# def index(request):
#     context = {"segment": "index"}

#     html_template = loader.get_template("index.html")
#     return HttpResponse(html_template.render(context, request))


# @login_required(login_url="/login/")
# def pages(request):
#     context = {}
#     # All resource paths end in .html.
#     # Pick out the html file name from the url. And load that template.
#     try:
#         load_template = request.path.split("/")[-1]

#         if load_template == "admin":
#             return redirect(reverse("admin:index"))
#         context["segment"] = load_template

#         html_template = loader.get_template("" + load_template)
#         return HttpResponse(html_template.render(context, request))

#     except template.TemplateDoesNotExist:
#         html_template = loader.get_template("page-404.html")
#         return HttpResponse(html_template.render(context, request))

#     except Exception as e:
#         logger.exception("ERRO")
#         html_template = loader.get_template("page-500.html")
#         return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
def event_details_name(request, event_name):
    # event = Event.objects.get(title=event_name)
    event = Event.objects.filter(Q(title=event_name)).first()
    eventmember = EventMember.objects.filter(Q(event=event) & Q(is_deleted=False))
    data_atual = timezone.now()

    context = {
        "event": event,
        "eventmember": eventmember,
        "data_atual": data_atual,
    }
    return render(request, "event-details.html", context)


# @login_required(login_url="/login/")
# def event_details(request, event_id):
#     event = Event.objects.get(id=event_id)
#     eventmember = EventMember.objects.filter(Q(event=event) & Q(is_deleted=False))
#     context = {"event": event, "eventmember": eventmember}
#     return render(request, "event-details.html", context)


@login_required(login_url="/login/")
def create_event(request):
    form = forms.EventForm(request.POST or None)

    if request.POST and form.is_valid():
        title = form.cleaned_data["title"]
        description = form.cleaned_data["description"]
        start_time = form.cleaned_data["start_time"]
        end_time = form.cleaned_data["end_time"]
        auth_user_id = form.cleaned_data["auth_user_id"]
        url = form.cleaned_data["url"]
        numero = form.cleaned_data["numero"]
        origem = form.cleaned_data["origem"]

        Event.objects.update_or_create(
            user_id=request.user.pk,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            auth_user_id=auth_user_id,
            url=url,
            numero=numero,
            origem=origem,
        )
        return redirect(reverse("home:calender"))
    return render(request, "event.html", {"form": form})


class EventEdit(UpdateView):
    model = Event
    fields = [
        "title",
        "description",
        "start_time",
        "end_time",
        "auth_user",
        "url",
        "numero",
        "origem",
    ]
    template_name = "event.html"


@login_required(login_url="/login/")
def event_details(request, event_id):
    event = Event.objects.get(id=event_id)
    eventmember = EventMember.objects.filter(Q(event=event) & Q(is_deleted=False))
    data_atual = timezone.now()

    context = {
        "event": event,
        "eventmember": eventmember,
        "data_atual": data_atual,
    }
    return render(request, "event-details.html", context)


def add_eventmember(request, event_id):
    from apps.home.forms import AddMemberForm

    forms = AddMemberForm()

    if request.method == "POST":
        forms = AddMemberForm(request.POST)
        if forms.is_valid():
            member = EventMember.objects.filter(event=event_id)
            event = Event.objects.get(id=event_id)

            if member.count() <= 1000:
                user = forms.cleaned_data["user"]
                EventMember.objects.create(event=event, user=user)

                # Gravar no evento do calendario - NOVO MEMBRO
                try:
                    data_evento = timezone.now()
                    # usuario = get_usuario_do_sistema_pelo_username_no_fb(username)

                    # Gravando o evento
                    Event.criar_evento_no_calendario(
                        user=user,
                        auth_user=user,
                        numero=str(event.numero),
                        title=str(event.title),
                        description=str(event.description),
                        url="",
                        origem="P",
                        horas_adicionais=1,
                        data_futura_inicio=data_evento,
                        data_futura_fim=data_evento,
                        gravar_apenas_data="N",
                        fase_agenda_id=1,
                        exibir_agenda="S",
                    )
                except Exception as e:
                    logger.exception(f"ERRO ao gravar no calendario: {e!s}")

                # return redirect("home:calender")
                return event_details(request, event_id)
            else:
                print("--------------User limit exceed!-----------------")

    context = {"form": forms}
    return render(request, "add_member.html", context)


class EventDeleteCompleteView(DeleteView):
    model = Event
    template_name = "event_delete_completo.html"

    def get_success_url(self):
        """Retorna a URL para redirecionar após o formulário ser válido."""
        return reverse("home:calender")


# CONFIRMAR QUE O EVENTO FOI LIDO
def event_finalizado(request, event_id):
    # Selecionar o evento e alocar como LIDO
    event = Event.objects.get(pk=event_id)
    event.end_time_checked = datetime.now().strftime("%Y-%m-%d %H:%M")

    if event.start_time_checked is None:
        event.start_time_checked = datetime.now().strftime("%Y-%m-%d %H:%M")

    event.save()

    # MARCAR PEDIDO DE CERTIDAO COMO RECEBIDO - CASO NAO ESTA

    """Retorna a URL para redirecionar após o formulário ser válido."""
    url = reverse("home:event-detail", args=[event_id])
    return redirect(url)


# CONFIRMAR QUE O EVENTO FOI LIDO
def event_lido(request, event_id):
    # Selecionar o evento e alocar como LIDO
    event = Event.objects.get(pk=event_id)
    event.start_time_checked = datetime.now().strftime("%Y-%m-%d %H:%M")
    event.save()

    # MARCAR PEDIDO DE CERTIDAO COMO RECEBIDO - CASO NAO ESTA

    """Retorna a URL para redirecionar após o formulário ser válido."""
    url = reverse("home:event-detail", args=[event_id])
    return redirect(url)


# Update iniciar o EVENT - colocar o membro selecionado
def event_member_start(request, event_id, member_id):
    # Selecionar o evento e alocar para o membro
    event = Event.objects.get(pk=event_id)
    event.auth_user_id = member_id
    event.member_checked_user = member_id
    event.start_time_checked = datetime.now().strftime("%Y-%m-%d %H:%M")
    event.save()

    # Desativar os outros membros do evento
    EventMember.objects.filter(Q(event=event_id)).exclude(user=member_id).update(
        is_deleted=True,
    )

    # Ativar no grupo de membros do evento
    return event_details(request, event_id)


# Update no EVENT - colocar o membro selecionado
def event_member_select(request, event_id, member_id):
    # Selecionar o evento e alocar para o membro
    event = Event.objects.get(pk=event_id)
    event.auth_user_id = member_id
    event.member_checked_user = member_id
    event.save()

    # Desativar os outros membros do evento
    EventMember.objects.filter(Q(event=event_id)).exclude(user=member_id).update(
        is_deleted=True,
    )
    return event_details(request, event_id)


class EventMemberDeleteView(DeleteView):
    model = EventMember
    template_name = "event_delete.html"

    def get_success_url(self):
        """Retorna a URL para redirecionar após o formulário ser válido."""
        return reverse("home:calender")


class AllEventsListView(ListView):
    """All event list views."""

    login_url = "/login/"
    template_name = "relatorios/painel_eventos.html"

    def get(self, request, *args, **kwargs):
        events = Event.objects.all()
        running_events = Event.objects.all()
        latest_events = Event.objects.all().order_by("-id")
        current_user = "Todos"

        context = {
            "total_event": events.count(),
            "running_events": running_events,
            "latest_events": latest_events,
            "current_user": current_user,
        }
        return render(request, self.template_name, context)


class RunningEventsListView(ListView):
    """Running events list view."""

    template_name = "events_list.html"
    model = Event

    def get_queryset(self):
        return Event.objects.get_running_events(user=self.request.user)


# PESQUISAR DATA DE
def dashboard_resumo(request):
    template_name = "dashboard_cartorio.html"

    context = {}
    return render(request, template_name, context)


# PESQUISAR DATA DE DISTRIBUICAO PELA DATA
def dashboard_data(request):
    template_name = "dashboard_cartorio.html"

    # Tipo de Relatorio -       A (data do andamento)     E (data de entrada)
    tipo_relatorio = request.GET.get("tipo_relatorio")

    # Use request.GET.get para obter os parâmetros da URL
    start_date_str = request.GET.get("data_pesquisa_i")
    end_date_str = request.GET.get("data_pesquisa_f")

    # Valores padrão para as datas
    default_start_date = timezone.now().date() - timedelta(0)
    default_end_date = timezone.now().date() + timedelta(0)

    try:
        # Se as datas forem fornecidas, converte-as para objetos de data
        start_date = (
            datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if start_date_str
            else default_start_date
        )
        end_date = (
            datetime.strptime(end_date_str, "%Y-%m-%d").date() + timedelta(0)
            if end_date_str
            else default_end_date
        )
    except ValueError:
        # Se houver erro na conversão, use os valores padrão
        start_date = default_start_date
        end_date = default_end_date

    # PROTOCOLOS NO PERIODO
    if tipo_relatorio == "A":
        lista_andamento = Livro01Andamento.objects.filtrar_por_data_andamento(
            start_date,
            end_date,
        )
        # Você também pode acessar outros campos do modelo aqui
        andamento_protocolos_ids = [
            andamento.protocolo_id for andamento in lista_andamento
        ]

        # Lista pelo andamento
        lista_protocolos = Livro01Protocolo.objects.filtrar_por_id(
            andamento_protocolos_ids,
        )
    else:
        lista_protocolos = Livro01Protocolo.objects.filtrar_por_data(
            start_date,
            end_date,
        )

    # Verifica se há protocolos no período
    if len(lista_protocolos) == 0:
        context = {
            "data_inicio": str(start_date),
            "data_fim": str(end_date),
            "parent": "Livro01Protocolo",
            "segment": "dashboard",
        }
        return render(request, template_name, context)

    protocolos_ids = [protocolo.pk for protocolo in lista_protocolos]

    # PROTOCOLOS NO PERIODO
    andamentos = Livro01Andamento.objects.agrupar_por_status(protocolos_ids)

    # Desempacotar os resultados em conjuntos
    # concluidos, cancelados, exigencia, _, subjudice, exigencia_positiva, em_registro_completo = [
    #     set(lst) for lst in andamentos[:7]
    # ]
    # Desempacotar os resultados em conjuntos
    concluidos = set(andamentos["registrados"])
    cancelados = set(andamentos["cancelados"])
    exigencia = set(andamentos["exigencias"])
    subjudice = set(andamentos["subjudices"])
    exigencia_positiva = set(andamentos["exigencias_positivas"])
    em_registro = set(andamentos["em_registro"])

    # VERIFICAR OS PRAZOS EM REGISTRO
    em_registro = set(
        Livro01Protocolo.get_status_ids_por_protocolos_ids(em_registro, [5]),
    )

    # Tirar da lista os cancelados e registrados - DO SUBJUDICE
    subjudice -= cancelados
    subjudice -= concluidos
    subjudice -= em_registro

    # Criar a lista de cancelados e registrados
    cancelados_concluidos = cancelados | concluidos | subjudice | em_registro

    # PROTOCOLOS DE EXIGENCIA
    exigencia -= cancelados_concluidos

    # Atualizar a lista de PROTOCOLOS DE EXIGENCIA POSITIVA
    exigencia_positiva -= cancelados_concluidos

    # Extrair 'id' de cada item na lista
    em_andamento_ids = {protocolo.pk for protocolo in lista_protocolos}

    # Calcular a diferença de conjuntos
    em_andamento = (
        em_andamento_ids - exigencia - cancelados_concluidos - exigencia_positiva
    )

    # PROTOCOLOS DO PERIODO - PROTOCOLOS REGISTRADOS - CANCELADOS
    eventos = Livro01Protocolo.objects.filtrar_por_multiplas_listas(
        ("periodo", protocolos_ids),
        ("exigencia", exigencia),
        ("concluidos", concluidos),
        ("cancelados", cancelados),
        ("em_andamento", em_andamento),
        ("subjudice", subjudice),
        ("exigencia_positiva", exigencia_positiva),
        ("em_registro", em_registro),
    )

    # # QUANTIDADE DE EVENTOS DOS PROTOCOLOS
    # total_protocolos_exigencia = len(eventos["exigencia"])
    # total_protocolos_registrados = len(eventos["concluidos"])
    # total_protocolos_periodo = len(eventos["periodo"])
    # total_protocolos_cancelados = len(eventos["cancelados"])
    # total_protocolos_em_andamento = len(eventos["em_andamento"])
    # total_protocolos_subjudice = len(eventos["subjudice"])
    # total_protocolos_exigencia_positiva = len(eventos["exigencia_positiva"])
    # total_event = len(lista_protocolos_ids)

    # grafico = grafico_view.get_data()
    # context["grafico"] = grafico

    context = {
        "total_protocolos_exigencia": len(eventos["exigencia"]),
        "total_protocolos_periodo": len(eventos["periodo"]),
        "total_protocolos_registrados": len(eventos["concluidos"]),
        "total_protocolos_cancelados": len(eventos["cancelados"]),
        "total_protocolos_em_andamento": len(eventos["em_andamento"]),
        "total_protocolos_subjudice": len(eventos["subjudice"]),
        "total_protocolos_exigencia_positiva": len(eventos["exigencia_positiva"]),
        "total_protocolos_em_registro": len(eventos["em_registro"]),
        "total_event": len(protocolos_ids),
        "eventos_exigencia": exigencia,
        "eventos_periodo": lista_protocolos,
        "eventos_concluidos": concluidos,
        "eventos_cancelados": cancelados,
        "eventos_em_andamento": em_andamento,
        "eventos_exigencia_positiva": exigencia_positiva,
        "data_inicio": str(start_date),
        "data_fim": str(end_date),
    }

    # context = {
    #     # "grafico": grafico,
    #     "total_protocolos_exigencia": total_protocolos_exigencia,
    #     "total_protocolos_periodo": total_protocolos_periodo,
    #     "total_protocolos_registrados": total_protocolos_registrados,
    #     "total_protocolos_cancelados": total_protocolos_cancelados,
    #     "total_protocolos_em_andamento": total_protocolos_em_andamento,
    #     "total_protocolos_subjudice": total_protocolos_subjudice,
    #     "total_protocolos_exigencia_positiva": total_protocolos_exigencia_positiva,
    #     "total_event": total_event,
    #     "eventos_exigencia": exigencia,
    #     "eventos_periodo": lista_protocolos,
    #     "eventos_concluidos": concluidos,
    #     "eventos_cancelados": cancelados,
    #     "eventos_em_andamento": em_andamento,
    #     "eventos_exigencia_positiva": exigencia_positiva,
    #     "data_inicio": str(start_date),
    #     "data_fim": str(end_date),
    # }

    return render(request, template_name, context)


@login_required
def dashboard_cartorio2_view(request):
    quantidade_protocolo_hoje = Livro01Protocolo.objects.filtrar_por_data(
        timezone.now().date(),
        timezone.now().date(),
    ).count()

    quantidade_protocolo_ontem = Livro01Protocolo.objects.filtrar_por_data(
        timezone.now().date() - timedelta(1),
        timezone.now().date() - timedelta(1),
    ).count()

    quantidade_protocolos_ultimos_30_dias = (
        Livro01Protocolo.objects.filtrar_por_periodo(
            timezone.now().date() - timedelta(30),
            timezone.now().date(),
        ).count()
    )

    quantidade_protocolos_utimos_7_dias = Livro01Protocolo.objects.filtrar_por_periodo(
        timezone.now().date() - timedelta(7),
        timezone.now().date(),
    ).count()

    quantidade_protocolo_este_mes = Livro01Protocolo.objects.filtrar_por_periodo(
        timezone.now().replace(day=1).date(),
        timezone.now().date(),
    ).count()

    quantidade_protocolos_30_dias_anteriores = (
        Livro01Protocolo.objects.filtrar_por_periodo(
            timezone.now().date() - timedelta(60),
            timezone.now().date() - timedelta(30),
        ).count()
    )

    diferenca_ultimos_30_dias_e_30_dias_anteriores = (
        quantidade_protocolos_ultimos_30_dias - quantidade_protocolos_30_dias_anteriores
    )

    diferenca_percentual_30_dias_e_30_dias_anteriores = (
        diferenca_ultimos_30_dias_e_30_dias_anteriores
        / quantidade_protocolos_30_dias_anteriores
        if quantidade_protocolos_30_dias_anteriores > 0
        else 0
    )

    hoje = timezone.now().date()
    ontem = hoje - timedelta(1)
    dias_30_antes = hoje - timedelta(30)

    contexto = {
        "quantidade_protocolo_hoje": quantidade_protocolo_hoje,
        "quantidade_protocolo_ontem": quantidade_protocolo_ontem,
        "quantidade_protocolos_ultimos_30_dias": quantidade_protocolos_ultimos_30_dias,
        "quantidade_protocolos_utimos_7_dias": quantidade_protocolos_utimos_7_dias,
        "quantidade_protocolo_este_mes": quantidade_protocolo_este_mes,
        "quantidade_protocolos_30_dias_anteriores": quantidade_protocolos_30_dias_anteriores,
        "diferenca_ultimos_30_dias_e_30_dias_anteriores": diferenca_ultimos_30_dias_e_30_dias_anteriores,
        "diferenca_percentual_30_dias_e_30_dias_anteriores": diferenca_percentual_30_dias_e_30_dias_anteriores,
        "hoje": hoje,
        "ontem": ontem,
        "dias_30_antes": dias_30_antes,
    }

    return render(request, "dashboard/dashboard.html", contexto)


# PESQUISAR DATA DE DISTRIBUICAO PELA DATA
def distribuicao_protocolo_data(request):
    numero_protocolo = request.POST.get("numero_protocolo", 0)
    start_date = datetime.strptime(request.POST["data_pesquisa_i"], "%Y-%m-%d").date()
    end_date = datetime.strptime(
        request.POST["data_pesquisa_f"],
        "%Y-%m-%d",
    ).date() + timedelta(0)

    # CASO TENHA INFORMADO O PROTOCOLO - SE NAO PESQUISA PELA DATA
    if int(numero_protocolo) > 0:
        protocolos = Livro01Protocolo.objects.filtrar_por_numero(numero_protocolo)
    else:
        protocolos = Livro01Protocolo.objects.filtrar_distribuir_por_periodo(
            start_date=start_date,
            end_date=end_date,
        )

    protocolos_distribuidos = Livro01Protocolo.objects.filtrar_distribuidos_por_periodo(
        start_date,
        end_date,
    )

    context = {
        "protocolos": protocolos,
        "protocolos_distribuidos": protocolos_distribuidos,
        "data_inicio": start_date,
        "data_fim": end_date,
    }

    return render(request, "distribuicao_protocolo.html", context)


class DistribuicaoProtocoloColaboradoresListView(LoginRequiredMixin, ListView):
    template_name = "distribuicao_protocolo_colaboradores.html"
    model = Colaborador
    context_object_name = "colaboradores"
    # filterset_class = filters.ColaboradorFilter
    export_param = "_export"  # Parâmetro para identificar a exportação

    def get_queryset(self):
        """Retorna os colaboradores ativos que possuem protocolos em aberto."""
        return Colaborador.objects.filter(
            andamentos_do_colaborador_destino__protocolo__data_finalizado__isnull=True,
            usuario__is_active=True,
        ).distinct()

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     # filterset = self.filterset_class(self.request.GET, queryset=self.get_queryset())
    #     # context["filter"] = filterset
    #     context["colaboradores"] = self.get_queryset()
    #     return context

    def export_data(self, request):
        # Obtém os dados filtrados
        # filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        queryset = self.get_queryset()

        # Cria o arquivo Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Colaboradores"

        # Cabeçalhos das colunas
        columns = ["Nome", "protocolos_em_aberto", "protocolos_em_reentrada"]
        ws.append(columns)

        # Adiciona os dados das colunas
        for colaborador in queryset:
            row = [
                colaborador.nome,
                colaborador.protocolos_em_aberto.count(),
                colaborador.protocolos_em_reentrada.count(),
            ]
            ws.append(row)

        # Salva o arquivo em um BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        # Configura a resposta HTTP para download do arquivo Excel
        response = HttpResponse(
            content=excel_file.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="colaboradores.xlsx"'
        return response

    def get(self, request, *args, **kwargs):
        if self.export_param in request.GET:
            return self.export_data(request)
        return super().get(request, *args, **kwargs)


@login_required
def protocolo_distribuicao_list_view(request):
    data_entrada_inicio_str = request.GET.get("data_entrada_inicio")
    data_entrada_fim_str = request.GET.get("data_entrada_fim")
    numero_protocolo = request.GET.get("numero_protocolo_id")

    start_date = (
        date.fromisoformat(data_entrada_inicio_str)
        if data_entrada_inicio_str
        else timezone.now().date() - timedelta(0)
    )

    end_date = (
        date.fromisoformat(data_entrada_fim_str)
        if data_entrada_fim_str
        else timezone.now().date() + timedelta(0)
    )

    if numero_protocolo:
        protocolos_a_distribuir = Livro01Protocolo.objects.filter(
            numero_protocolo=numero_protocolo,
        )

        if not protocolos_a_distribuir:
            # importar_protocolo_direto_view(request, numero_protocolo)
            try:
                with firebird.FbConnection() as db:
                    db.begin_transaction()
                    protocolo, _ = firebird.importar_protocolo_por_numero_fb(
                        numero_protocolo=numero_protocolo,
                        tipo_importacao=None,
                        db=db,
                    )
                    db.commit()
            except Exception:
                mensagem = "Erro ao importar protocolo."
                messages.error(request, mensagem)
                logger.exception(mensagem)
                raise

            protocolos_a_distribuir = [protocolo] if protocolo else None
            # protocolos_a_distribuir = Livro01Protocolo.objects.filter(numero_protocolo=numero_protocolo)
    else:
        # NAO E MAIS NECESSARIO VERIFICAR PROTOCOLOS FALTANTES
        # try:
        #     importar_protocolos_por_data_entrada_nao_importado(start_date, end_date)
        # except Exception:
        #     print("Erro ao verificar para importar o protocolo faltantes")

        protocolos_a_distribuir = (
            Livro01Protocolo.objects.filtrar_distribuir_por_periodo(
                start_date,
                end_date,
            )
        )

    protocolos_distribuidos = Livro01Protocolo.objects.filtrar_distribuidos_por_periodo(
        start_date,
        end_date,
    )

    grafico_view = ProtocoloChartView(
        start_date_param=data_entrada_inicio_str,
        end_date_param=data_entrada_fim_str,
    )
    grafico = grafico_view.get_data()

    context = {
        "grafico": grafico,
        "protocolos": protocolos_a_distribuir,
        "protocolos_distribuidos": protocolos_distribuidos,
        "data_inicio": str(start_date),
        "data_fim": str(end_date),
    }

    return render(request, "distribuicao_protocolo.html", context)


def funcionario_list_view(request):
    funcionarios = Funcionario.objects.all()
    return render(request, "lista.html", {"funcionarios": funcionarios})


# INICIO - CAMPOS NECESSARIO PARA EDITAR E EXCLUIR MODAL
def homecrud(request):
    template = "homemodal.html"
    partes = Livro05.objects.all().order_by("id")
    context = {"partes": partes}
    return render(request, template, context)


# Salvar o lembrete do IMOVEL
def salvar_lembrete_imovel(request):
    if not request.POST:
        raise Http404

    # print(request.POST)
    # https://chat.openai.com/c/83f107ae-6527-43f4-8bd3-c02e770cbd76

    if request.method == "POST":
        data_distribuicao_i = request.POST.get("data_distribuicao_i")
        setor_enviar_id = str(request.POST.get("setor_enviar_id")).split(",")[0]
        colaborador_id = str(request.POST.get("colaborador_id")).split(".")[0]
        imovel_id = str(request.POST.get("imovel_id")).split(".")[0]
        lembrete_id = request.POST.get("lembrete_id")
        colaborador_create_id, _ = get_user_id(str(request.user).upper())

        # CONFERIR
        colaborador_id = colaborador_create_id

        # GRAVANDO O LEMBRE NO CADASTRO REAL
        b = Lembrete(
            created_at=data_distribuicao_i,
            updated_at=data_distribuicao_i,
            nivel_alerta_id=setor_enviar_id,
            funcionarios_create_id=colaborador_create_id,
            funcionarios_update_id=colaborador_id,
            imovel_id=imovel_id,
            descricao=lembrete_id,
        )

        b.save(force_insert=True)
        print("Lembrete criado.")

        # messages.success(request, "Dados salvos!")
        url = reverse("home:livro04_imovel", args=[imovel_id]) + "#card_lembretes"
        return redirect(url)
        # return redirect("home:livro04_imovel", pk=imovel_id)
    else:
        messages.error(request, "Dados não salvos!")
        return redirect(reverse("home:protocolo_search"))


def create_modal(request):
    if not request.POST:
        raise Http404
    if request.method == "POST":
        nome = request.POST.get("nome")
        documento = request.POST.get("documento")
        Livro05.objects.create(nome=nome, documento=documento)
        messages.success(request, "Dados salvos!")
        return redirect("home:home")
    else:
        messages.error(request, "Dados não salvos!")
        return redirect(reverse("home:protocolo_search"))


def edit_modal(request):
    # print('GRAVANDO')

    if not request.POST:
        raise Http404

    pk = request.POST.get("pessoa_id")
    pessoa = get_object_or_404(PedidoParteAto, id=pk)

    if request.method == "POST":
        # print(request.POST.get('sexo'))
        #

        pessoa.nome_mae = request.POST.get("nome_mae")
        pessoa.nome_pai = request.POST.get("nome_pai")
        pessoa.endereco = request.POST.get("endereco")
        pessoa.profissao = request.POST.get("profissao")
        pessoa.naturalidade = request.POST.get("naturalidade")
        pessoa.nacionalidade = request.POST.get("nacionalidade")
        pessoa.documento = request.POST.get("documento")
        pessoa.categoria = request.POST.get("estado_civil").split(",")[0]
        pessoa.sexo = request.POST.get("sexo")
        pessoa.data_nascimento = str(
            formatar_data(str(request.POST.get("data_nascimento"))),
        )
        pessoa.email = request.POST.get("email")
        pessoa.save()

        messages.success(request, "Dados salvos!")
        return redirect("home:protocolo_search")
    else:
        messages.error(request, "Dados não salvos!")
        return redirect(reverse("home:protocolo_search"))


def delete_modal(request):
    if not request.POST:
        raise Http404

    pk = request.POST.get("parte_id")
    pessoadelete = get_object_or_404(Livro05, id=pk)
    pessoadelete.delete()
    messages.success(request, "Dados excluídos!")
    return redirect(reverse("home:protocolo_search"))


# FIM - CAMPOS NECESSARIO PARA EDITAR E EXCLUIR MODAL


# Gravar Pedidos de Partes Ato
def gravar_pedidos_partes_ato(
    pedido_id,
    pedido_item_id,
    pessoa,
    status,
    estado_civil,
    total,
    ato_baixa_id,
    percentual_ato,
) -> None:
    PedidoParteAto.create(
        pedido_item_id=pedido_item_id,
        pessoa=pessoa,
        status=status,
        percentual_doi=str(100 / total),
        estado_civil=estado_civil,
        percentual_ato=percentual_ato if percentual_ato else 0,
        vinculo_id=ato_baixa_id,
    )


@login_required
def livro04_imovel_view(request, pk):
    item = get_object_or_404(Livro02, pk=pk)

    # ENDERECO DO IMOVEL ESTA VINDO INCOMPLETO
    # return render(request, "livro04/livro04_detail.html", {"item": item})
    return redirect(
        "home:livro04_detail",
        numero_registro=item.numero,
        tipo_registro=item.tipo,
        cartorio_imovel=item.cartorio,
    )


class Livro02DetailView(LoginRequiredMixin, DetailView):
    model = Livro02
    template_name = "livro02/livro02_detail.html"


def agenda_protocolo_relatorio(request, data_i, data_f):
    # Use uma compreensão de lista para criar a lista de protocolos convertendo numero_protocolo para int
    lista_protocolos = list(
        Livro01Protocolo.objects.filter(data_protocolo__range=[data_i, data_f])
        .order_by("numero_protocolo")
        .values_list(
            "numero_protocolo",
            flat=True,
        ),  # flat=True para obter uma lista plana
    )

    # RETORNAR TODOS OS CAMPOS INTEIROS
    lista_protocolos_int = [int(item) for item in lista_protocolos]

    return redirect(
        reverse("home:agenda_protocolo", kwargs={"protocolos": lista_protocolos_int}),
    )


# Agenda pelo colaborador
def agenda_protocolo_colaborador(request, colaborador_id):
    lista_protocolos = list(
        Livro01Protocolo.objects.filter(
            (Q(fases_protocolo_colaborador_atual_id=colaborador_id))
            & Q(data_finalizado__isnull=True),
        )
        .order_by("numero_protocolo")
        .values_list("numero_protocolo", flat=True),
    )  # flat=True para obter uma lista plana

    # RETORNAR TODOS OS CAMPOS INTEIROS
    lista_protocolos_int = [int(item) for item in lista_protocolos]

    return redirect(
        reverse("home:agenda_protocolo", kwargs={"protocolos": lista_protocolos_int}),
    )


def agenda_protocolo_itens(origem="P", numero_protocolo=0):
    return Event.objects.get_por_numeros(origem=origem, numeros=[numero_protocolo])


def agenda_protocolo_view(request, protocolos):
    # Processa a string de entrada para obter uma lista de números de protocolo.
    protocolos = str(protocolos).replace("[", "").replace("]", "")

    if "," in protocolos:
        # Converte uma string com vírgulas em uma lista de inteiros.
        protocolos = [int(p) for p in protocolos.split(",")]
    elif protocolos:
        protocolos = [0] if str(protocolos).strip() == "[]" else [int(protocolos)]

    # Obtém os eventos ordenados pelo número do protocolo.
    eventos = Event.objects.get_por_numeros(origem="P", numeros=protocolos).order_by(
        "numero",
    )

    # Cria uma lista única e ordenada dos números de protocolo dos eventos.
    protocolos = sorted({evento.numero for evento in eventos})

    # Prepara a lista final de protocolos e seus respectivos detalhes.
    resultado = []
    for protocolo in protocolos:
        # Obtém eventos específicos para o protocolo atual.
        eventos_protocolo = Event.objects.get_por_numeros(
            origem="P",
            numeros=[protocolo],
        )

        # Prepara detalhes dos eventos do protocolo.
        lista_andamento = [
            [
                evento.title,
                converter_data_para_formato_de_modelo(evento.start_time),
                converter_data_para_formato_de_modelo(evento.end_time),
                (
                    "A"
                    if not evento.end_time_checked
                    and timezone.now().date() > evento.start_time.date()
                    else ""
                ),
                (
                    "A"
                    if evento.end_time_checked
                    and evento.end_time_checked.date() > evento.start_time.date()
                    else ""
                ),
            ]
            for evento in eventos_protocolo
        ]

        # Recupera o objeto Protocolo correspondente ao número do protocolo.
        protocolo_obj = Livro01Protocolo.objects.filter(
            numero_protocolo=protocolo,
        ).first()

        # Adiciona os detalhes do protocolo ao resultado.
        resultado.append(
            [
                [int(protocolo)],
                lista_andamento,
                [protocolo_obj.pk if protocolo_obj else None],
            ],
        )

    # Prepara o contexto para o template.
    context = {"lista_protocolos": resultado}

    # Renderiza o template com o contexto.
    return render(request, "agenda_protocolo.html", context)


def protocolo_timeline_view(request, ids):
    """Exibe uma linha do tempo baseada nos andamentos do protocolo."""
    # Simplifica a conversão da string de entrada em uma lista de inteiros
    protocolos_ids = [int(pk) for pk in ids.split(",")]

    # Obtém todos os eventos em uma única consulta, ordenados pelo número do protocolo
    protocolos = Livro01Protocolo.objects.filter(pk__in=protocolos_ids).order_by("id")
    numeros = protocolos.values_list("numero_protocolo", flat=True)
    eventos = Event.objects.filter(numero__in=numeros, origem="P").order_by("numero")

    resultado = []

    for protocolo in protocolos:
        eventos_protocolo = [
            evento for evento in eventos if evento.numero == protocolo.numero_protocolo
        ]
        andamentos = [
            [
                evento.title,
                converter_data_para_formato_de_modelo(evento.start_time),
                converter_data_para_formato_de_modelo(evento.end_time),
                (
                    "A"
                    if not evento.end_time_checked
                    and timezone.now().date() > evento.start_time.date()
                    else ""
                ),
                (
                    "A"
                    if evento.end_time_checked
                    and evento.end_time_checked.date() > evento.start_time.date()
                    else ""
                ),
            ]
            for evento in eventos_protocolo
        ]
        resultado.append(
            [[(protocolo)], andamentos, [protocolo.pk if protocolo else None]],
        )

    context = {"protocolos": resultado}

    return render(request, "livro01/protocolo_timeline.html", context)


@login_required
def livro04_detail_view(request, numero_registro, tipo_registro, cartorio_imovel):
    try:
        imovel = Livro04.objects.get(
            numero=numero_registro,
            tipo=tipo_registro,
            cartorio=cartorio_imovel,
        )
    except Livro04.DoesNotExist:
        messages.error(
            request,
            f"O imóvel solicitado não foi encontrado. Numero Informado: {numero_registro}",
        )
        return redirect("home:livro04_list")

    context = {
        "numero_registro": imovel.numero_registro,
        "tipo_registro": imovel.tipo_registro,
        "cartorio_imovel": imovel.cartorio_registro,
        "imovel": imovel,
        "ruas": imovel.ruas,
        "acoes_onus_atual": imovel.acoes_e_onus,
        "lotes": imovel.lotes,
        "acoes_onus_atual_quantidade": imovel.quantidade_acoes_e_onus,
        "livro03_atual_quantidade": len(imovel.registros_no_livro03),
        "loteamento_Quantidade": imovel.quantidade_de_lotes_no_loteamento,
        "quantidade_de_unidades_no_condominio": imovel.quantidade_de_unidades_no_condominio,
        "condominio_de_origem": (
            imovel.condominio_de_origem if imovel.condominio_de_origem else []
        ),
        "loteamento_origem": imovel.loteamento if imovel.loteamento else [],
        "unidade_no_condominio": (
            imovel.get_unidade_no_condominio if imovel.get_unidade_no_condominio else []
        ),
        "registros_no_livro03": imovel.registros_no_livro03,
    }

    return render(request, "livro04/livro04_detail.html", context)
    # return render(request,
    #     "home:livro04_detail",
    #     numero_registro=imovel.numero,
    #     tipo_registro=imovel.tipo,
    #     cartorio_imovel=imovel.cartorio,

    # )


# class Livro04DetailView(LoginRequiredMixin, DetailView):
#     model = Livro02
#     template_name = "livro04/livro04_detail.html"
#     context_object_name = "item"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         imovel = self.object

#         # PEGANDO DAS (ACOES E ONUS, LIVRO 3) VINCULADOS AO IMOVEL
#         acoes_onus_atual = get_acoes_e_onus(imovel.imovel)
#         # acoes_onus_atual = imovel.get_acoes_e_onus

#         livro03_quantidade_atual = get_quantidade_de_registros_no_livro03(imovel.numero, imovel.tipo)
#         # livro03_quantidade_atual = imovel.ficha_condominio

#         condominio_origem = []
#         lote = ""
#         loteamento_quantidade = 0
#         condominio_quantidade = 0

#         lote = get_lotes_pelo_imovel(imovel.imovel)
#         # lote = imovel.lote_associado  # get_lotes_pelo_imovel(imovel.imovel)

#         # condominio_origem = imovel.get_condominio_origem

#         #loteamento_origem = imovel.get_loteamento

#         # condominio_quantidade = imovel.ficha_condominio

#         # loteamento_quantidade = imovel.total_lotes_associados

#         if imovel.classe != "R":
#             if imovel.classe == "C":
#                 condominio_origem = get_condominio_pelo_imovel(
#                     imovel.registro_anterior, 0, imovel.tipo_unidade, imovel.imovel
#                 )
#             else:
#                 condominio_quantidade = FichaAuxiliar.get_quantidade_de_unidades_no_condominio(imovel.imovel)
#                 # imovel.get

#                 loteamento_quantidade = get_quantidade_de_lotes_no_loteamento(imovel.imovel)
#                 # lote.get_total_lotes_associados

#         condominio_origem = []
#         loteamento_origem = []

#         context.update(
#             {
#                 "acoes_onus_atual": acoes_onus_atual,
#                 "lotes": lote,
#                 "acoes_onus_atual_quantidade": len(acoes_onus_atual),
#                 "livro03_atual_quantidade": livro03_quantidade_atual,
#                 "loteamento_Quantidade": loteamento_quantidade,
#                 "quantidade_de_unidades_no_condominio": condominio_quantidade,
#                 "condominio_de_origem": condominio_origem,
#                 "loteamento_origem": loteamento_origem,
#                 "imovel": imovel,
#             }
#         )

#         return context

#     def get_object(self, queryset=None):
#         queryset = queryset or self.get_queryset()
#         numero_registro = self.kwargs.get("numero_registro")
#         tipo_registro = self.kwargs.get("tipo_registro")
#         cartorio_imovel = self.kwargs.get("cartorio_imovel", "1")
#         return get_object_or_404(
#             queryset, numero=numero_registro, tipo=tipo_registro, cartorio=cartorio_imovel
#         )


class Livro04DetailViewLivro03(LoginRequiredMixin, DetailView):
    model = Livro02
    template_name = "livro04/livro04_detail.html"
    context_object_name = "item"

    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)
        imovel = self.object

        livro03_atual = get_livro03(imovel.numero, imovel.tipo)
        return {"livro03_atual": livro03_atual, "imovel": imovel}


@login_required
def livro04_detail_unidade_loteamento(request, pk):
    imovel = get_object_or_404(Livro02, pk=pk)

    unidade_mae = Unidade.objects.filter(imovel_id=imovel.pk).first()
    ficha_auxiliar = FichaAuxiliar.objects.filter(id=imovel.pk).first()
    # unidades = Unidade.objects.select_related("lote").filter(
    unidades = (
        Unidade.objects.select_related("imovel")
        .filter(registro_anterior=unidade_mae.imovel)
        .order_by("quadra", "id")
    )
    # imovel(imovel_id=0):

    context = {
        "unidade_mae": unidade_mae,
        "ficha_auxiliar": ficha_auxiliar,
        "unidades": unidades,
    }

    return render(request, "livro04_detail_Unidade_Loteamento.html", context)


# def imovel(imovel_id=0):
#     # Obtendo a unidade diretamente pelo imóvel
#     unidade = Unidade.objects.get(imovel_id=imovel_id)

#     # Obtendo lotes usando lookups de chave estrangeira
#     lotes = Lote.objects.filter(unidade__imovel_id=imovel_id)

#     # Se registro_anterior_id é a mesma coisa que imovel_id, a consulta permanece a mesma
#     unidades_loteamento = Unidade.objects.filter(registro_anterior_id=imovel_id)

#     data = {
#         "unidade": unidade,
#         "lotes": lotes,
#         "unidades_loteamento": unidades_loteamento,
#     }

#     return data


@login_required
def livro04_detail_unidade_condominio(request, pk):
    imovel = get_object_or_404(Livro02, pk=pk)

    # condominio_origem = get_condominio_pelo_imovel(imovel.pk, 1, imovel.tipo_unidade, imovel.pk)

    context = {
        "imovel": imovel,
        "ficha_auxiliar": imovel.condominio_de_origem,
        "unidade_no_condominio": (
            imovel.get_ficha_das_unidades_no_condominio_pelo_id
            if imovel.get_ficha_das_unidades_no_condominio_pelo_id
            else []
        ),
    }

    # context = {
    #     "item": imovel,
    #     "lotes": imovel.lotes,
    #     "unidades_do_condominio": imovel.unidades_do_condominio,
    #     "quantidade_de_unidades_no_condominio": imovel.quantidade_de_unidades_no_condominio,
    #     "condominio_de_origem": condominio_origem,
    # }

    return render(request, "livro04_detail_Unidade_Condominio.html", context)


@login_required
def registro_auxiliar(request, pk):
    try:
        pedido_item = PedidoItem.object.get(pk=pk)
    except ObjectDoesNotExist:
        messages.error(request, "O regostro solicitado não foi encontrado.")
        return redirect("home:livro03_list")

    context = {
        "item": pedido_item,
    }

    return render(request, "registro_auxiliar.html", context)


class Livro03Detail(LoginRequiredMixin, DetailView):
    model = Livro03
    template_name = "livro03/livro03_detail.html"
    context_object_name = "registro_auxiliar"

    def get_object(self):
        numero = self.kwargs.get("numero")
        pk = self.kwargs.get("pk")
        try:
            if pk:
                return Livro03.objects.get(pk=pk)
            if numero:
                return Livro03.objects.get(numero=numero)
        except Livro03.DoesNotExist:
            messages.error(
                self.request,
                "O Registro Auxiliar solicitado não foi encontrado.",
            )
            return redirect(reverse("home:livro03_list"))


# BUSCAR LIVRO 3 PELO NUMERO
def livro03_numero_detail(request, numero, cartorio):
    print("livro03_numero_detail")

    try:
        registro = Livro03.objects.filter(numero=numero, cartorio=cartorio).first()
        if registro is None:
            messages.error(
                request,
                "O Registro Auxiliar solicitado não foi encontrado.",
            )
            return redirect("home:livro03_list")

        return redirect("home:livro03_detail", pk=registro.id)
    except Livro03.DoesNotExist:
        return redirect("home:livro03_list")


# EDITAR PESSOA
@login_required
def modal_detalhes_pessoa(request):
    # global pedido_item_atual

    print("Editando a pessoa do TRANSMITENTE:")

    if not request.POST:
        raise Http404

    request.POST.get("parte_id")
    pedido_item_id = str(request.POST.get("pedido_item_id")).split(",")[0]
    request.POST.get("opcao_parte")
    pessoa = get_object_or_404(Livro05, id=id)

    # Gravando os dados
    if request.method == "POST":
        if str(request.POST.get("nome")).upper() != "NONE":
            pessoa.nome = str(request.POST.get("nome")).upper()

        pessoa.nome_mae = request.POST.get("nome_mae")
        pessoa.nome_pai = request.POST.get("nome_pai")
        pessoa.endereco = request.POST.get("endereco")
        pessoa.profissao = request.POST.get("profissao")
        pessoa.data_nascimento = request.POST.get("data_nascimento")
        pessoa.naturalidade = request.POST.get("naturalidade")
        pessoa.nacionalidade = request.POST.get("nacionalidade")
        pessoa.documento = request.POST.get("documento")
        pessoa.sexo = request.POST.get("sexo")
        pessoa.email = request.POST.get("email")

        # DADOS PARA ATUALIZAR NO ATO
        estado_civil = request.POST.get("estado-civil").split(",")[0]
        tipo_regime_id = request.POST.get("regime").split(",")[0]

        # VERIFICAR SE O REGIME NAO E OBRIGATORIO - CASO NAO SEJA ELE E RETIRADO
        estado_civil = EstadoCivil.objects.filter(
            Q(id=estado_civil) & Q(requerer_tipo_regime="S"),
        )
        if estado_civil.exists():
            if int(tipo_regime_id) == 0:
                context = {
                    "Regime": "Campos Obrigatórios - Regime de Bens deve ser informado",
                }
                return render(request, "Validar_Pessoa.html", context)
        else:
            tipo_regime_id = 0

        # Estado Civil
        pessoa.estado_civil = estado_civil
        pessoa.tipo_regime_id = tipo_regime_id

        # salvar OS DADOS
        # pessoa.data_nascimento = str("1901-01-01")
        pessoa.save()

        # ATUALIZAR O ESTADO CIVIL DO ATO TEMPORARIO
        try:
            pedidos_partes_ato = PedidoParteAto.objects.get(
                pedido_item_id=pedido_item_id,
                pessoa=id,
            )
            pedidos_partes_ato.estado_civil = estado_civil
            pedidos_partes_ato.tipo_regime_id = tipo_regime_id
            pedidos_partes_ato.save()
        except Exception:
            logger.exception("ERRO")

        # Atualizar o item para retornar
        if pedido_item_id is None:
            return redirect(reverse("home:protocolo_search"))

        print("atualizar_protocolo - ", pedido_item_id)

        messages.success(request, "Dados salvos!")
        # success_url = reverse_lazy("atualizar_protocolo")
        return redirect(
            # "home:minuta_lv2", pedido_item_id=pedido_item_id
            "home:checklist_lv2",
            pedido_item_id=pedido_item_id,
            opcao="1",
        )
    else:
        messages.error(request, "Dados não salvos!")
        return redirect(reverse("home:protocolo_search"))


# EDITAR PESSOA
@login_required
def edit_modal_pessoa(request):
    # global pedido_item_atual

    print("Editando a pessoa do TRANSMITENTE:")

    if not request.POST:
        raise Http404

    parte_id = request.POST.get("parte_id")
    pedido_item_id = str(request.POST.get("pedido_item_id")).split(",")[0]
    request.POST.get("opcao_parte")
    pessoa = get_object_or_404(Livro05, id=id)

    # Gravando os dados
    if request.method == "POST":
        if str(request.POST.get("nome")).upper() != "NONE":
            pessoa.nome = str(request.POST.get("nome")).upper()

        pessoa.nome_mae = request.POST.get("nome_mae")
        pessoa.nome_pai = request.POST.get("nome_pai")
        pessoa.endereco = request.POST.get("endereco")
        pessoa.profissao = request.POST.get("profissao")

        data_nascimento_str = request.POST.get("data_nascimento")

        try:
            data_nascimento_obj = datetime.strptime(data_nascimento_str, "%m/%d/%Y")
            formatted_date = data_nascimento_obj.strftime("%Y-%m-%d")
            pessoa.data_nascimento = formatted_date
        except ValueError:
            # A string da data não estava no formato correto
            pass
        pessoa.naturalidade = request.POST.get("naturalidade")
        pessoa.nacionalidade = request.POST.get("nacionalidade")
        pessoa.documento = request.POST.get("documento")
        pessoa.sexo = request.POST.get("sexo")
        pessoa.email = request.POST.get("email")

        # DADOS PARA ATUALIZAR NO ATO
        estado_civil = request.POST.get("estado-civil").split(",")[0]
        tipo_regime_id = request.POST.get("regime").split(",")[0] or 0
        # tipo_regime_id = 0

        # VERIFICAR SE O REGIME NAO E OBRIGATORIO - CASO NAO SEJA ELE E RETIRADO
        estado_civil = EstadoCivil.objects.filter(
            Q(id=estado_civil) & Q(requerer_tipo_regime="S"),
        )
        if estado_civil.exists():
            if not estado_civil.tipo_regime:
                tipo_regime_id = 1

            if int(estado_civil.tipo_regime) == 0:
                context = {
                    "Regime": "Campos Obrigatórios - Regime de Bens deve ser informado.",
                }
                return render(request, "Validar_Pessoa.html", context)

        # Estado Civil
        pessoa.estado_civil = estado_civil
        pessoa.tipo_regime_id = tipo_regime_id

        # salvar OS DADOS
        # pessoa.data_nascimento = data_nascimento
        if pessoa.sexo is None:
            pessoa.sexo = "M"

        pessoa.save()

        # ATUALIZAR O ESTADO CIVIL DO ATO TEMPORARIO
        try:
            pedidos_partes_ato = PedidoParteAto.objects.get(
                pedido_item_id=pedido_item_id,
                pessoa_id=parte_id,
            )
            pedidos_partes_ato.estado_civil = estado_civil
            pedidos_partes_ato.tipo_regime_id = tipo_regime_id
            pedidos_partes_ato.save()
        except Exception:
            logger.exception("ERRO")
            raise

        # Atualizar o item para retornar
        if pedido_item_id is None:
            return redirect(reverse("home:protocolo"))

        print("atualizar_protocolo - ", pedido_item_id)

        messages.success(request, "Dados salvos!")
        # success_url = reverse_lazy("atualizar_protocolo")
        return redirect(
            # "home:minuta_lv2", pedido_item_id=pedido_item_id
            "home:checklist_lv2",
            pedido_item_id=pedido_item_id,
            opcao="1",
        )
    else:
        messages.error(request, "Dados não salvos!")
        return redirect(reverse("home:protocolo"))


@login_required
def delete_modal_pessoa(request):
    if not request.POST:
        raise Http404

    pedido_item_id = request.POST.get("pedido_item_id")
    pessoadelete = get_object_or_404(Livro05, id=pedido_item_id)
    pessoadelete.delete()
    messages.success(request, "Dados excluídos!")
    return redirect(reverse("home:protocolo_search"))


@login_required
def desvincular_protocolo_pessoa(request, pessoa_id, papel, protocolo_id):
    print("Desvinculando Pessoa: ", pessoa_id)

    # DESVINCULAR DO ATO ESPECIFICO
    if str(papel) != "None":
        pessoa_parte = PedidoParteAto.objects.filter(
            pessoa_id=pessoa_id,
            tipo_parte=papel,
        )
    else:
        pessoa_parte = PedidoParteAto.objects.filter(
            pessoa_id=pessoa_id,
            tipo_parte__isnull=True,
        )
        pessoa_parte.delete()

    # DESVINCULAR DO PROTOCOLO
    if str(papel) != "None":
        pessoa_parte = PedidoParte.objects.filter(pessoa_id=pessoa_id, papel=papel)
    else:
        pessoa_parte = PedidoParte.objects.filter(
            pessoa_id=pessoa_id,
            papel__isnull=True,
        )
    pessoa_parte.delete()

    messages.success(request, "Dados desvinculados!")

    url = reverse("home:protocolo_detail", args=[protocolo_id]) + "#itens_pedido_partes"
    return redirect(url)


@login_required
def desvincular_modal_pessoa(request, opcao_parte):
    print("Desvinculando Pessoa: ", opcao_parte)

    if not request.POST:
        raise Http404

    parte_id = request.POST.get("parte_id")
    pessoa_parte = PedidoParte.objects.get(id=parte_id)
    pessoa_parte.delete()

    # messages.success(request, "Dados desvinculados!")
    # success_url = reverse_lazy("atualizar_protocolo")
    # return redirect(reverse("home:protocolo_search"))
    return redirect(
        reverse("home:protocolo_search", kwargs={"opcao_parte": opcao_parte}),
    )


@login_required
def desvincular_modal_pessoa_minuta(request):
    print("Desvinculando Pessoa Minuta")

    if not request.POST:
        raise Http404

    parte_id = request.POST.get("parte_id")
    pedido_item_id = str(request.POST.get("pedido_item_id")).split(",")[0]
    request.POST.get("opcao_parte")

    try:
        pessoa_parte = PedidoParteAto.objects.get(id=parte_id)
        pessoa_parte.delete()
    except Exception:
        logger.exception("ERRO")
        raise

    print("desvincular_modal_pessoa_minuta - ", pedido_item_id)

    messages.success(request, "Dados desvinculados!")
    # = reverse("atualizar_protocolo")
    # return redirect("home:minuta_lv2", pedido_item_id=pedido_item_id)
    return redirect("home:checklist_lv2", pedido_item_id=pedido_item_id, opcao="1")


# Desvincular o Endereco da Minuta
@login_required
def desvincular_modal_endereco_minuta(request):
    if not request.POST:
        raise Http404

    parte_id = request.POST.get("parte_id")
    pedido_item_id = str(request.POST.get("pedido_item_id")).split(",")[0]
    endereco_parte = PedidoItemImovel.objects.get(id=parte_id)
    endereco_parte.delete()

    print("desvincular_modal_endereco_minuta - ", pedido_item_id)

    messages.success(request, "Dados desvinculados!")
    # success_url = reverse_lazy("atualizar_protocolo")
    # return redirect("home:minuta_lv2", pedido_item_id=pedido_item_id)
    return redirect("home:checklist_lv2", pedido_item_id=pedido_item_id, opcao="1")


# Alterar dados do ato da PARTE
@login_required
def edit_modal_texto_l2(request):
    if not request.POST:
        raise Http404

    parte_id = str(request.POST.get("id")).split(",")[0]
    pedido_item_id = str(request.POST.get("pedido_item_id")).split(",")[0]
    pessoa = get_object_or_404(Livro02Texto, id=parte_id)

    if request.method == "POST":
        pessoa.texto = request.POST.get("texto_id")
        pessoa.save()

        # messages.success(request, 'Dados salvos !')
        return redirect(
            "home:texto_lv2",
            pk=pedido_item_id,
            pedido_item_id=pedido_item_id,
        )
    else:
        messages.error(request, "Dados não salvos!")
        return redirect(
            reverse(
                "home:texto_lv2",
                pk=pedido_item_id,
                pedido_item_id=pedido_item_id,
            ),
        )


@login_required
def edit_modal_nota_devolucao(request):
    if not request.POST:
        raise Http404

    pk = str(request.POST.get("id")).split(",")[0]
    pedido_item_id = str(request.POST.get("pedido_item_id")).split(",")[0]
    pessoa = get_object_or_404(NotaDevolucaoTexto, id=pk)

    if request.method == "POST":
        pessoa.pedido_id = str(request.POST.get("pedido_id")).split(",")[0]
        pessoa.texto = request.POST.get("texto_id")
        pessoa.save()

        # messages.success(request, 'Dados salvos !')
        return redirect(
            "home:texto_devolucao",
            pk=pedido_item_id,
            pedido_item_id=pedido_item_id,
        )
    else:
        messages.error(request, "Dados não salvos!")
        return redirect(
            reverse(
                "home:texto_devolucao",
                pk=pedido_item_id,
                pedido_item_id=pedido_item_id,
            ),
        )


# Alterar dados do ato da PARTE
@login_required
def edit_modal_ato_parte_a(request):
    if not request.POST:
        raise Http404

    pk = request.POST.get("parte_idA")
    pedido_item_id = str(request.POST.get("pedido_item_idA")).split(",")[0]
    pessoa = get_object_or_404(PedidoParteAto, id=pk)

    if request.method == "POST":
        # Percentual DO ATO
        percentual_ato = str(request.POST.get("percentual_ato")).upper()
        if percentual_ato == "NONE":
            percentual_ato = 0

        # Percentual DA DOI
        percentual_doi = str(request.POST.get("percentual_doi")).upper()
        if percentual_doi == "NONE":
            percentual_doi = 0

        # Incluir a chave da pessoa
        pessoa_ids = pessoa.pessoa

        # Incluir a chave do conjuge
        # conjuge_id = str(request.POST.get('conjuge')).upper()
        conjuge_id = str(request.POST.get("conjuge")).replace(",", ".")
        conjuge_id = str(conjuge_id).split(".")[0]
        # if conjuge_id == 'NONE':
        #    conjuge_id = 0

        pessoa.percentual_doi = str(percentual_doi).replace(",", ".")
        pessoa.percentual_ato = str(percentual_ato).replace(",", ".")
        # pessoa.pessoa_conjuge_id  = str(conjuge_id).replace(',', '.')
        pessoa.pessoa_conjuge_id = str(request.POST.get("conjuge")).replace(
            ",",
            ".",
        )
        pessoa.save()

        # VINCULAR SE ESTA TEM CASADO
        if int(conjuge_id) > 0:
            try:
                pedidos_partes_ato = PedidoParteAto.objects.get(
                    pedido_item_id=pedido_item_id,
                    pessoa=conjuge_id,
                )
                pedidos_partes_ato.pessoa_conjuge_id = pessoa_ids
                pedidos_partes_ato.save()
            except Exception:
                logger.exception("ERRO")

        print("edit_modal_ato_parte_a - ", pedido_item_id)

        # messages.success(request, 'Dados salvos !')
        return redirect(
            # "home:minuta_lv2", pedido_item_id=pedido_item_id
            "home:checklist_lv2",
            pedido_item_id=pedido_item_id,
            opcao="1",
        )
    else:
        print("edit_modal_ato_parte_a - ", pedido_item_id)

        messages.error(request, "Dados não salvos!")
        return redirect(reverse("home:minuta_lv2", pedido_item_id=pedido_item_id))


# Alterar dados do ato da PARTE
@login_required
def edit_modal_ato_parte_t(request):
    if not request.POST:
        raise Http404

    parte_id = request.POST.get("parte_idT")
    pedido_item_id = str(request.POST.get("pedido_item_idT")).split(",")[0]
    pessoa = get_object_or_404(PedidoParteAto, id=parte_id)

    if request.method == "POST":
        # Percentual DO ATO
        percentual_ato = str(request.POST.get("percentual_ato")).upper()
        if percentual_ato == "NONE":
            percentual_ato = 0

        # Percentual DA DOI
        percentual_doi = str(request.POST.get("percentual_doi")).upper()
        if percentual_doi == "NONE":
            percentual_doi = 0

        # Incluir a chave da pessoa
        pessoa_ids = pessoa.pessoa
        conjuge_id = str(request.POST.get("conjuge")).replace(",", ".")

        nro_ato_transmitir = ""

        try:
            nro_ato_transmitir = str(request.POST.get("ato_transmitir")).replace(
                ",",
                ".",
            )
        except Exception:
            logger.exception("ERRO")

        # if (nro_ato_transmitir != ''):
        # try:
        pessoa.vinculo_id = nro_ato_transmitir
        # except Exception as e:
        # logger.exception("ERRO")
        # nro_ato_transmitir = str('')

        pessoa.percentual_doi = str(percentual_doi).replace(",", ".")
        pessoa.percentual_ato = str(percentual_ato).replace(",", ".")
        pessoa.pessoa_conjuge_id = str(request.POST.get("conjuge")).replace(
            ",",
            ".",
        )
        pessoa.save()

        # VINCULAR SE ESTA TEM CASADO
        try:
            pedidos_partes_ato = PedidoParteAto.objects.get(
                pedido_item_id=pedido_item_id,
                pessoa=conjuge_id,
            )
            pedidos_partes_ato.pessoa_conjuge_id = pessoa_ids
            pedidos_partes_ato.save()
        except Exception:
            logger.exception("ERRO")

        print("edit_modal_ato_parte_t - ATIVAR ATO ANTERIOR - ", pedido_item_id)

        # messages.success(request, 'Dados salvos !')
        return redirect(
            # "home:minuta_lv2", pedido_item_id=pedido_item_id
            "home:checklist_lv2",
            pedido_item_id=pedido_item_id,
            opcao="1",
        )
    else:
        print("ELSE - edit_modal_ato_parte_t - ", pedido_item_id)

        messages.error(request, "Dados não salvos!")
        return redirect(reverse("home:minuta_lv2", pedido_item_id=pedido_item_id))


# Alterar dados do ato da PARTE DO PROTOCOLO
@login_required
def edit_modal_ato_parte_t_partes_protocolo(request):
    pk = request.POST.get("parte_idT")
    # pedido_item_id = str(request.POST.get("pedido_item_idT")).split(",")[
    #     0
    # ]

    print("SALVO ", pk)

    # success_url = reverse_lazy("atualizar_protocolo")
    return redirect(reverse("home:protocolo_search"))


# Alterar dados do ato da PARTE - ENDERECO
@login_required
def edit_modal_ato_parte_endereco(request):
    if not request.POST:
        raise Http404

    parte_id = request.POST.get("parte_id")
    pedido_item_id = str(request.POST.get("pedido_item_id")).split(",")[0]
    pessoa = get_object_or_404(PedidoItemImovel, id=parte_id)

    if request.method == "POST":
        # DADOS DO IMÓVEL - URBANO
        pessoa.setor = request.POST.get("setor")
        pessoa.quadra = request.POST.get("quadra")
        pessoa.lote = request.POST.get("lote")
        pessoa.area = request.POST.get("area")
        pessoa.nome_rua = request.POST.get("nome_rua")
        pessoa.numero_casa = request.POST.get("numero_casa")
        pessoa.residencial = request.POST.get("residencial")
        pessoa.comercial = request.POST.get("comercial")
        pessoa.municipio = request.POST.get("municipio")
        pessoa.area_construida_residencial = request.POST.get(
            "area_construida_residencial",
        )

        # DADOS DO IMÓVEL - RURAL
        pessoa.nome_fazenda = request.POST.get("nome_fazenda")
        pessoa.caracteristica_fazenda = request.POST.get("caracteristica_fazenda")
        pessoa.area_fazenda = request.POST.get("area_fazenda")
        pessoa.georefenciada = request.POST.get("georefenciada")
        pessoa.reserva_legal = request.POST.get("reserva_legal")
        pessoa.numero_nirf = request.POST.get("numero_nirf")
        pessoa.numero_ccirr = request.POST.get("numero_ccirr")
        pessoa.numero_car = request.POST.get("numero_car")
        pessoa.numero_incra = request.POST.get("numero_incra")
        pessoa.data_validade_itr = str(
            request.POST.get("data_validade_itr"),
        ).replace("/", ".")

        # DADOS DO IMÓVEL - URBANO - MEDIDAS
        pessoa.m_frente_metros = request.POST.get("m_frente_metros")
        pessoa.p_frente_metros = request.POST.get("p_frente_metros")
        pessoa.m_direito_metros = request.POST.get("m_direito_metros")
        pessoa.p_direito_metros = request.POST.get("p_direito_metros")
        pessoa.m_esquerdo_metros = request.POST.get("m_esquerdo_metros")
        pessoa.p_esquerdo_metros = request.POST.get("p_esquerdo_metros")
        pessoa.m_fundo_metros = request.POST.get("m_fundo_metros")
        pessoa.p_fundo_metros = request.POST.get("p_fundo_metros")

        pessoa.save()

    print("edit_modal_ato_parte_endereco - ", pedido_item_id)
    # return redirect("home:minuta_lv2", pedido_item_id=pedido_item_id)
    return redirect(
        "home:checklist_lv2",
        pedido_item_id=pedido_item_id,
        opcao="1",
    )  # card_imoveis_rural


# Atualizar os dados do IMÓVEL
@login_required
def atualizar_imovel(imovel_id, coluna_tabela_origem, resposta_correta) -> None:
    # Filtrar o IMOVEIS
    b = Livro02.objects.get(imovel_ud=imovel_id)

    # Filtrar as Medidas do Imovel
    m = ImovelMedida.objects.get(imovel_id=imovel_id)

    # Atualizando a coluna RESIDENCIAL
    if str(coluna_tabela_origem).upper() == "MUNICIPIO":
        b.municipio = resposta_correta
        b.save()
    elif str(coluna_tabela_origem).upper() == "NUMERO_NIRF":
        b.numero_nirf = resposta_correta
        b.save()
    elif str(coluna_tabela_origem).upper() == "NUMERO_CCIRR":
        b.numero_ccirr = resposta_correta
        b.save()
    elif str(coluna_tabela_origem).upper() == "NUMERO_CAR":
        b.numero_car = resposta_correta
        b.save()
    elif str(coluna_tabela_origem).upper() == "NUMERO_INCRA":
        b.numero_incra = resposta_correta
        b.save()
    elif str(coluna_tabela_origem).upper() == "DATA_VALIDADE_ITR":
        b.data_validade_itr = str(resposta_correta).replace("/", ".")
        b.save()
    # Atualizar as medidas do imovel
    elif str(coluna_tabela_origem).upper() == "M_FRENTE_METROS":
        m.m_frente_metros = resposta_correta
        m.save()
    elif str(coluna_tabela_origem).upper() == "P_FRENTE_METROS":
        m.p_frente_metros = resposta_correta
        m.save()
    elif str(coluna_tabela_origem).upper() == "M_DIREITO_METROS":
        m.m_direito_metros = resposta_correta
        m.save()
    elif str(coluna_tabela_origem).upper() == "P_DIREITO_METROS":
        m.p_direito_metros = resposta_correta
        m.save()
    elif str(coluna_tabela_origem).upper() == "M_ESQUERDO_METROS":
        m.m_esquerdo_metros = resposta_correta
        m.save()
    elif str(coluna_tabela_origem).upper() == "P_ESQUERDO_METROS":
        m.p_esquerdo_metros = resposta_correta
        m.save()
    elif str(coluna_tabela_origem).upper() == "M_FUNDO_METROS":
        m.m_fundo_metros = resposta_correta
        m.save()
    elif str(coluna_tabela_origem).upper() == "P_FUNDO_METROS":
        m.p_fundo_metros = resposta_correta
        m.save()

    # Atualizar o FIREBIRD
    firebird.firebird_atualizar_imovel(
        imovel_id=imovel_id,
        unidade_id=0,
        coluna_tabela_origem=str(coluna_tabela_origem).upper(),
        resposta_correta=resposta_correta,
        opcao=1,
    )


# Atualiza os IMOVEIS URBANOS
@login_required
def atualizar_imovel_urbano(imovel_id, coluna_tabela_origem, resposta_correta) -> None:
    try:
        # Filtrar as Unidade
        unidades = Unidade.objects.filter(imovel_id=imovel_id)
        for item in unidades:
            unidade_id = item.id

        # Filtrar os Lote
        lote = Lote.objects.get(unidade=unidade_id)

        # Filtrar as Rua
        try:
            r = Rua.objects.get(unidade_id=unidade_id)
        except Exception:
            r = None

        # Filtrar as Medidas do Imovel
        m = ImovelMedida.objects.get(imovel_id=imovel_id)

        # Filtrar o Imovel
        i = Livro02.objects.get(pk=imovel_id)

        # Atualizando a coluna QUADRA
        if str(coluna_tabela_origem).upper() == "AREA":
            lote.area = resposta_correta
            lote.save()
        # Atualizando a coluna QUADRA
        elif str(coluna_tabela_origem).upper() == "QUADRA":
            lote.quadra = resposta_correta
            lote.save()
        # Atualizando a coluna LOTE
        elif str(coluna_tabela_origem).upper() == "LOTE":
            lote.numero_unidade = resposta_correta
            lote.save()
        # Atualizando a coluna LOTE
        elif str(coluna_tabela_origem).upper() == "SETOR":
            lote.setor = resposta_correta
            lote.save()
        # Atualizando a coluna COMERCIAL
        elif str(coluna_tabela_origem).upper() == "COMERCIAL":
            lote.comercial = str(resposta_correta)[0]
            lote.save()
        # Atualizando a coluna RESIDENCIAL
        elif str(coluna_tabela_origem).upper() == "RESIDENCIAL":
            lote.residencial = str(resposta_correta)[0]
            lote.save()
        # Atualizando a coluna NOME RUA
        elif str(coluna_tabela_origem).upper() == "NOME_RUA":
            if r is not None:
                r.nome = resposta_correta
                r.save()
        # Atualizando a coluna NUMERO CASA
        elif str(coluna_tabela_origem).upper() == "NUMERO_CASA":
            if r is not None:
                r.numero_edificacao = resposta_correta
                r.save()

        # Atualizar as medidas do imovel
        elif str(coluna_tabela_origem).upper() == "M_FRENTE_METROS":
            m.m_frente_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "P_FRENTE_METROS":
            m.p_frente_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "M_DIREITO_METROS":
            m.m_direito_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "P_DIREITO_METROS":
            m.p_direito_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "M_ESQUERDO_METROS":
            m.m_esquerdo_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "P_ESQUERDO_METROS":
            m.p_esquerdo_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "M_FUNDO_METROS":
            m.m_fundo_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "P_FUNDO_METROS":
            m.p_fundo_metros = resposta_correta
            m.save()

        elif str(coluna_tabela_origem).upper() == "AREA_CONSTRUIDA_RESIDENCIAL":
            i.area_construida_residencial = resposta_correta
            i.save()

        # Atualizar o FIREBIRD
        firebird.firebird_atualizar_imovel(
            imovel_id,
            unidade_id,
            str(coluna_tabela_origem).upper(),
            resposta_correta,
            3,
        )
    except Exception:
        logger.exception("ERRO")


# Atualiza os IMOVEIS RURAIS
@login_required
def atualizar_imovel_rural(imovel_id, coluna_tabela_origem, resposta_correta) -> None:
    q = Rural.objects.get(imovel_id=imovel_id)
    n = RuralNome.objects.get(imovel_id=imovel_id)

    if str(coluna_tabela_origem).upper() == "NOME_FAZENDA":
        n.nome = resposta_correta
        n.save()
    elif str(coluna_tabela_origem).upper() == "CARACTERISTICA_FAZENDA":
        q.caracteristica = resposta_correta
        q.save()
    elif str(coluna_tabela_origem).upper() == "AREA_FAZENDA":
        q.area = resposta_correta
        q.save()
    elif str(coluna_tabela_origem).upper() == "RESERVA_LEGAL":
        q.reserva_florestal = resposta_correta[0]
        q.save()
    elif str(coluna_tabela_origem).upper() == "GEOREFENCIADA":
        # Texto georeferencial
        resposta_correta_georeferencial = "T" if resposta_correta[0] == "S" else "N"

        q.georeferencial = resposta_correta_georeferencial
        q.save()
    elif str(coluna_tabela_origem).upper() == "REMANESCENTE":
        q.remanescente = resposta_correta[0]
        q.save()

    # Atualizar o FIREBIRD
    firebird.firebird_atualizar_imovel(
        imovel_id,
        0,
        str(coluna_tabela_origem).upper(),
        resposta_correta,
        2,
    )


# Atualizar tabela vinda do checklist - LIVRO 2 e 3
@login_required
def atualizar_livro02_03(
    request,
    pedido_item_id: int,
    perguntas_id: int,
    resposta_correta: str,
    coluna_tabela_origem="",
):
    # Filtrar os dadodod do imovel
    pedido_item: PedidoItem = PedidoItem.objects.get(id=pedido_item_id)
    imoveis = pedido_item.get_dados_do_registro_auxiliar()

    # OBTER A ID IMOVEL
    imovel_id = imoveis["imovel_id"]
    classe_id = imoveis["classe_id"]

    # Atualizando o imovel
    atualizar_imovel(imovel_id, coluna_tabela_origem, resposta_correta)

    # Atualizar Imovel Urbano
    if classe_id == "R":
        atualizar_imovel_rural(imovel_id, coluna_tabela_origem, resposta_correta)
    else:
        atualizar_imovel_urbano(imovel_id, coluna_tabela_origem, resposta_correta)

    return redirect("home:checklist_imovel", id=pedido_item_id)


# Atualizar tabela vinda do checklist - LIVRO 2 e 3
@login_required
def atualizar_checklist_partes(
    request,
    pedido_item_id: int,
    pessoa_id: int,
    resposta_correta: str,
    coluna_tabela_origem="",
):
    pessoa_id = str(pessoa_id).split(".")[0]

    try:
        pedidos_partes_ato = PedidoParteAto.objects.get(
            pedido_item_id=pedido_item_id,
            pessoa=pessoa_id,
        )

        # Atualizando a coluna QUADRA
        if str(coluna_tabela_origem).upper() == "ESTADO_CIVIL":
            pedidos_partes_ato.estado_civil = get_estado_civil_pela_descricao(
                resposta_correta,
            )
            pedidos_partes_ato.save()
        elif str(coluna_tabela_origem).upper() == "REGIME_BENS":
            pedidos_partes_ato.tipo_regime_id = str(get_regime_bens(resposta_correta))
            pedidos_partes_ato.save()

        print("Salvo ")
    except Exception:
        logger.exception("ERRO")

    return redirect("home:checklist_imovel", id=pedido_item_id)


def gravar_andamento_digitalizacao_no_fb(protocolo) -> None:
    tipo_digitalizar_ids = TipoAndamento.objects.get_ids_de_tipo_digitalizar()

    if not tipo_digitalizar_ids:
        msg = "Nenhum serviço para digitalizar foi encontrado."
        raise ValueError(msg)

    usuarios_para_notificar_digitalizacao = get_usuarios_para_notificar_digitalizacao()

    if not usuarios_para_notificar_digitalizacao:
        msg = "Nenhum usuário para notificar foi encontrado."
        raise ValueError(msg)

    colaborador = usuarios_para_notificar_digitalizacao.last()

    try:
        for tipo_digitalizar_id in tipo_digitalizar_ids:
            firebird.criar_andamento_fb(
                pedido_id=protocolo.pedido,
                colaborador_id=colaborador,
                tipo_andamento_id=tipo_digitalizar_id,
            )

    except Exception:
        logger.exception("Erro ao gravar andamento")


# Mover os itens "nao selaodos" para o novo protocolo
def mover_item_nao_selado_para_novo_protocolo(
    lista_pedido_item_nao_selados,
    pedido_reprotocolar_id,
    db: firebird.FbConnection,
) -> None:
    # MOVER OS ITENS PARA O PROTOCOLO NOVO
    for pedido_item in lista_pedido_item_nao_selados:
        print(pedido_item, pedido_reprotocolar_id)

        comando = (
            " UPDATE PEDIDOS_ITENS SET CHAVE_PEDIDOS = ?"
            " WHERE CHAVE_PEDIDOS_ITENS = ?"
        )

        parametros = (pedido_reprotocolar_id, pedido_item)

        # SALVANDO O COMANDO NO BANCO DE DADOS FIREBIRD
        try:
            db.execute_command(comando, parametros)
        except Exception:
            logger.exception("Erro ao mover item para o novo protocolo")


# Transferir os itens "nao selaodos" para o novo protocolo
def capturar_item_nao_selado_para_novo_protocolo(numero_protocolo):
    # BUSCAR O PROTOCOLO ORIGEM
    protocolo_origem = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)

    # TODOS OS ITENS DO PROTOCOLO ORIGEM
    protocolo_pedidos_itens = protocolo_origem.pedidos_itens
    # pedido_item_completos = [pedido_item.id for pedido_item in protocolo_pedidos_itens]

    pedido_item_completos = [
        pedido_item.id
        for pedido_item in protocolo_pedidos_itens
        if pedido_item.codigo_tabela != firebird.get_cod_prenotacao()
    ]

    # SELOS DO PROTOCOLO ORIGEM
    selo_origem = protocolo_origem.selos
    pedido_item_selados = [pedido_item.id for pedido_item in selo_origem]

    #  ITENS NAO SELADOS DO PROTOCOLO ORIGEM - Diferença entre os conjuntos
    return list(set(pedido_item_completos) - set(pedido_item_selados))


# GERAR CAIXA DO REPROTOCOLO
def gerar_caixa_reprotocolo(
    pedido_id,
    user_id,
    texto,
    valor,
    tipotransacao,
    tipodocumento,
    reprotocolo: False,
    db: firebird.FbConnection,
) -> None:
    # ENVIAR VALORES DO CAIXA DO PROTOCOLO NOVO
    caixa_id_fb = firebird.get_sequence_firebird("CAIXA_SEQ", db)["GEN_ID"]

    firebird.gravar_caixa_ped_protocolo_fb(
        pedido_id,
        user_id,
        texto,
        valor,
        "6",
        caixa_id_fb,
        tipotransacao,
        tipodocumento,
        reprotocolo,
        db,
    )


# CRIAR ANDAMENTO NO FIREBIRD - PROTOCOLO
def gerar_andamento_reprotocolo(
    protocolo_fb_id,
    user_id,
    tipo_andamento_id,
    db: firebird.FbConnection,
) -> None:
    andamentos_id_fb = firebird.get_sequence_firebird("ANDAMENTOS_SEQ", db)["GEN_ID"]

    firebird.gravar_protocolo_andamento_firebird(
        protocolo_id=protocolo_fb_id,
        funcionario_id=user_id,
        servico_id=tipo_andamento_id,
        andamento_id=andamentos_id_fb,
        db=db,
    )


@require_POST
@login_required
def reprotocolar_protocolo_view(request, numero_protocolo):
    from apps.home.services.sqlserver import selar_protocolo_sql_server_id

    # PEGAR OS VALORES PARA PROTOCOLOCAR
    numero_protocolo = str(request.POST.get("input_numero_protocolo_id")).replace(
        ".",
        "",
    )

    input_valores_complementares = request.POST.get("input_valores_complementares", "")
    input_valores_complementares = re.sub(
        r"[^\d,]",
        "",
        input_valores_complementares,
    ).replace(",", ".")
    input_valores_complementares = Decimal(input_valores_complementares)

    input_valor_atual_protocolo = request.POST.get("input_valor_atual_protocolo", "")
    input_valor_atual_protocolo = re.sub(
        r"[^\d,]",
        "",
        input_valor_atual_protocolo,
    ).replace(",", ".")

    input_valor_pagos_caixa = request.POST.get("input_valor_pagos_caixa", "")
    input_valor_pagos_caixa = re.sub(r"[^\d,]", "", input_valor_pagos_caixa).replace(
        ",",
        ".",
    )

    input_valores_selados = request.POST.get("input_valores_selados", "")
    input_valores_selados = re.sub(r"[^\d,]", "", input_valores_selados).replace(
        ",",
        ".",
    )

    input_valor_transportar = request.POST.get("input_valor_transportar", "")
    input_valor_transportar = re.sub(r"[^\d,]", "", input_valor_transportar).replace(
        ",",
        ".",
    )
    input_valor_transportar = Decimal(input_valor_transportar)

    input_valor_novo_deposito = request.POST.get("input_valor_novo_deposito", "")
    input_valor_novo_deposito = re.sub(
        r"[^\d,]",
        "",
        input_valor_novo_deposito,
    ).replace(",", ".")

    # DAR BAIXA NOS VALORES DO CAIXA DO PROTOCOLO ANTERIOR
    input_valor_transportar = Decimal(input_valor_transportar) or 0
    input_valor_novo_deposito = Decimal(input_valor_novo_deposito) or 0

    observacao = str(request.POST.get("input_observacao"))
    # str(request.POST.get("titulo_protocolo_id"))
    tipo_tributacao_id = str(request.POST.get("tipo_tributacao_protocolo"))
    # str(request.POST.get("colaborador_id"))
    user_id = request.user.id

    try:
        db = firebird.FbConnection()
        db.begin_transaction()

        # OBTER DADOS DO PROTOCOLO
        print("Buscar dados do Protocolo Origem")
        protocolo_fb = firebird.get_protocolo_fb(numero_protocolo, db) or None

        # GERAR NOVO PROTOCOLO
        if protocolo_fb:
            print("Gerar Novo Pedido")
            pedido_reprotocolar_id = firebird.gravar_pedido_firebird(
                protocolo_fb["CHAVE_PEDIDOS"],
                observacao,
                user_id,
                numero_protocolo,
                db,
            )

            # VALOR DA PRENOTACAO
            (
                valor_emolumento,
                valor_fundo_estado,
                valor_tfj,
                valor_issqn,
                valor_emolumento_liquido,
            ) = firebird.get_valor_prenotacao()

            # GRAVAR ITEM E GERAR O NOVO PROTOCOLO
            if pedido_reprotocolar_id:
                print("Gerar Novo Pedido Item")
                # Gerar Pedido Item no Firebird - Prenotacao e selar
                pedido_item_id = firebird.gravar_pedido_item_protocolo_fb(
                    pedido_id=pedido_reprotocolar_id["CHAVE_PEDIDOS"],
                    valor_itbi=0,
                    valor_avaliacao=0,
                    tipo_imovel="",
                    numero_imovel="",
                    emolumento_id=firebird.get_tipo_emolumento_prenotacao(),
                    quantidade="1",
                    numero_ri="1",
                    numero_titulo="1",
                    numero_ato="",
                    colaborador_id=(
                        user_id
                        if user_id not in [1]
                        else Configuracao.obter(
                            "funcionario_id_sistema_antigo",
                            1,
                        )
                    ),
                    ato_id=firebird.get_ato_praticavel_prenotacao(),
                    titulo_id=firebird.get_default_titulo_prenotacao(),
                    tipo_tributacao_id=tipo_tributacao_id,
                    codigo_tabela=firebird.get_cod_prenotacao(),
                    valor_emolumento=valor_emolumento,
                    valor_fundo_estado=valor_fundo_estado,
                    valor_tfj=valor_tfj,
                    valor_issqn=valor_issqn,
                    db=db,
                )

                # ITEM A SER SELADO

                # GRAVAR NOVO PROTOCOLO
                print("Gerar Novo Protocolo")
                numero_protocolo_novo, protocolo_id = (
                    firebird.gravar_protocolo_firebird(
                        pedido_id=pedido_reprotocolar_id["CHAVE_PEDIDOS"],
                        titulo_id=0,
                        observacao=observacao,
                        origem_pedido_id=protocolo_fb["CHAVE_PEDIDOS"],
                        numero_pedido_cri=None,
                        db=db,
                    )
                )

                # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
                cartorio_model = apps.get_model("cartorios", "Cartorio")
                usar_selo_sql_server = cartorio_model.objects.all().values_list(
                    "usar_selo_sql_server",
                    flat=True,
                )[0]

                # Selar DE PRENOTACAO PARA O NOVO PROTOCOLO
                if pedido_item_id:
                    # SELAR NO SQL SERVER PROTOCOLO
                    if usar_selo_sql_server == "S":
                        # selar_protocolo_sql_server_id(
                        #     numero_protocolo_novo,
                        #     pedido_item_id,
                        #     "S",
                        # )
                        pass
                    else:
                        (
                            numero_selo_firebird,
                            codigo_seguranca_firebird,
                            codigo_internet_firebird,
                        ) = firebird.selar_protocolo_no_firebird(
                            pedido_id=pedido_reprotocolar_id["CHAVE_PEDIDOS"],
                            pedidos_id_itens=pedido_item_id,
                            db=db,
                        )

                    # BUSCAR TODOS OS SELOS DO PROTOCOLO ORIGEM
                    lista_pedido_item_nao_selados = (
                        capturar_item_nao_selado_para_novo_protocolo(numero_protocolo)
                    )

                    # MOVER OS ITENS PARA O PROTOCOLO NOVO
                    if lista_pedido_item_nao_selados:
                        mover_item_nao_selado_para_novo_protocolo(
                            lista_pedido_item_nao_selados,
                            pedido_reprotocolar_id["CHAVE_PEDIDOS"],
                            db,
                        )

        # GRAVAR ANDAMENTOS - REPROTOCOLADO NO PROTOCOLO INICIAL
        tipo_andamento_fb = TipoAndamento.grupos.reprotocolar().first()
        tipo_andamento_prenotacao_fb = TipoAndamento.grupos.get_recepcao().first()

        if not tipo_andamento_fb:
            msg = "Tipo de andamento 'REPROTOCOLAR' não encontrado"
            raise ValueError(msg)

        if not tipo_andamento_prenotacao_fb:
            msg = "Tipo de andamento 'PRENOTACAO' não existe"
            raise ValueError(msg)

        # CRIAR ANDAMENTO NO FIREBIRD - ANTIGO PROTOCOLO
        gerar_andamento_reprotocolo(
            protocolo_fb["CHAVE_PROTOCOLOS"],
            user_id,
            tipo_andamento_fb.pk,
            db,
        )

        # CRIAR ANDAMENTO NO FIREBIRD - NOVOPROTOCOLO
        gerar_andamento_reprotocolo(
            protocolo_id,
            user_id,
            tipo_andamento_prenotacao_fb.pk,
            db,
        )

        # Enviar ao caixa - PROTOCOLO ANTIGO
        gerar_caixa_reprotocolo(
            pedido_id=protocolo_fb["CHAVE_PEDIDOS"],
            user_id=user_id,
            texto="'Reprotocolado'",
            valor=input_valor_transportar * -1,
            tipotransacao=2,
            tipodocumento=1,
            reprotocolo=True,
            db=db,
        )

        # Enviar ao caixa - PROTOCOLO NOVO
        gerar_caixa_reprotocolo(
            pedido_id=pedido_reprotocolar_id["CHAVE_PEDIDOS"],
            user_id=user_id,
            texto="'Valores Transportados do Protocolo Antigo'",
            valor=input_valor_transportar,
            tipotransacao=1,
            tipodocumento=1,
            reprotocolo=True,
            db=db,
        )

        # ATUALIZAR OS VALORES DO PROTOCOLO ANTIGO
        firebird.atualizar_valores_pedido_firebird(
            pedido_id=protocolo_fb["CHAVE_PEDIDOS"],
            db=db,
        )

        # ATUALIZAR OS VALORES DO PROTOCOLO NOVO
        firebird.atualizar_valores_pedido_firebird(
            pedido_id=pedido_reprotocolar_id["CHAVE_PEDIDOS"],
            db=db,
        )
        db.commit()

        # ATUALIZAR VALOR DO ACERTO DESCONTANDO O VALOR DA PRENOTACAO NOVA
        db.begin_transaction()
        firebird.descontar_valor_novo_deposito_firebird(
            pedido_id=pedido_reprotocolar_id["CHAVE_PEDIDOS"],
            valor_transacao=input_valor_novo_deposito,
            valor_complementar=input_valores_complementares,
        )

        # IMPORTAR PROTOCOLO ANTIGO
        firebird.importar_protocolo_por_numero_fb(
            numero_protocolo,
            tipo_importacao="P",
            db=db,
        )

        # IMPORTAR PROTOCOLO NOVO
        firebird.importar_protocolo_por_numero_fb(
            numero_protocolo_novo,
            tipo_importacao="P",
            db=db,
        )
        db.commit()

        # SELAR NO SQL SERVER PROTOCOLO
        if usar_selo_sql_server == "S":
            try:
                selar_protocolo_sql_server_id(
                    numero_protocolo_novo,
                    pedido_item_id,
                    "S",
                )
            except:
                pass

        # ADEQUACOES PARA PROTOCOLO ANTIGO E NOVO
        adqueacoes_reprotocolo(numero_protocolo, numero_protocolo_novo)

    except Exception as e:
        print(e)
        logger.exception("Erro ao reprotocolar o protocolo: ")
        if db:
            db.rollback()
        raise
    finally:
        db.close()

    # IMPORTAR OS PROTOCOLOS NOVAMENTE DO FIREBIRD
    return redirect(
        "home:abrir_livro01_por_numero_protocolo",
        numero_protocolo=numero_protocolo_novo,
    )


@require_POST
def encaminhar_protocolo_ao_colaborador_view(request, numero_protocolo):
    colaborador_encaminhado_id = str(request.POST.get("colaborador_id"))
    titulo_id = request.POST.get("titulo_protocolo_id")
    fase_id = request.POST.get("fase_id")
    colaborador_id = request.user.id
    referer = request.headers.get("referer")  # Obtém a URL de origem da requisição
    data_distribuicao = request.POST.get("data_distribuicao_i")

    if not data_distribuicao:
        msg = "Data de distribuição não foi informada!"
        logger.warning(msg)
        messages.warning(request, msg)
        if referer:
            return redirect(referer)
        return redirect("home:distribuicao_protocolo")

    if not colaborador_encaminhado_id:
        msg = "Colaborador informado não foi encontrado!"
        messages.warning(request, msg)
        logger.warning(msg)

        if referer:
            return redirect(referer)
        return redirect("home:distribuicao_protocolo")

    if not numero_protocolo:
        msg = "Um numero do protocolo precisa foi informado!"
        messages.warning(request, msg)
        logger.warning(msg)

        if referer:
            return redirect(referer)
        return redirect("home:distribuicao_protocolo")

    protocolo: Livro01Protocolo = Livro01Protocolo.objects.filter(
        numero_protocolo=numero_protocolo,
    ).first()
    if not protocolo:
        msg = "O protocolo solicitado não foi encontrado."
        messages.warning(request, msg)
        logger.warning(msg)
        if referer:
            return redirect(referer)
        return redirect("home:protocolo_search")

    db = firebird.FbConnection()
    db.begin_transaction()
    with transaction.atomic():
        try:
            protocolo.encaminhar_ao_colaborador(
                colaborador_id=colaborador_id,
                colaborador_encaminhado_id=colaborador_encaminhado_id,
                titulo_id=titulo_id,
                fase_id=fase_id,
                db=db,
            )

            protocolo.agendar_notificacao_digitalizacao(data_agenda=data_distribuicao)
            db.commit()
            db.close()
        except Exception:
            logger.exception("Erro ao encaminhar o protocolo ao colaborador")
            db.rollback()
            db.close()
            raise

    request.session["numero_protocolo"] = numero_protocolo

    return redirect("home:distribuicao_protocolo")


# Atualizar tabela vinda do checklist - LIVRO 2 e 3
def atualizar_checklist_livro02_03(
    request,
    pedido_item_id,
    perguntas_id,
    resposta_correta,
    coluna_tabela_origem="",
):
    perguntas_id = str(perguntas_id).split(".")[0]

    try:
        pedidos_itens_imovel = PedidoItemImovel.objects.get(
            pedido_item_id=pedido_item_id,
            id=perguntas_id,
        )
        if pedidos_itens_imovel:
            # Atualizando a coluna QUADRA
            if str(coluna_tabela_origem).upper() == "QUADRA":
                pedidos_itens_imovel.quadra = resposta_correta

            # Atualizando a coluna LOTE
            elif str(coluna_tabela_origem).upper() == "LOTE":
                pedidos_itens_imovel.lote = resposta_correta

            # Atualizando a coluna LOTE
            elif str(coluna_tabela_origem).upper() == "SETOR":
                pedidos_itens_imovel.setor = resposta_correta

            # Atualizando a coluna NOME RUA
            elif str(coluna_tabela_origem).upper() == "NOME_RUA":
                pedidos_itens_imovel.nome_rua = resposta_correta

            # Atualizando a coluna NUMERO CASA
            elif str(coluna_tabela_origem).upper() == "NUMERO_CASA":
                pedidos_itens_imovel.numero_casa = resposta_correta

            # Atualizando a coluna AREA
            elif str(coluna_tabela_origem).upper() == "AREA":
                pedidos_itens_imovel.area = resposta_correta

            # Atualizando a coluna COMERCIAL
            elif str(coluna_tabela_origem).upper() == "COMERCIAL":
                pedidos_itens_imovel.comercial = str(resposta_correta)[0]

            # Atualizando a coluna RESIDENCIAL
            elif str(coluna_tabela_origem).upper() == "RESIDENCIAL":
                pedidos_itens_imovel.residencial = str(resposta_correta)[0]

            # Atualizando a coluna RESIDENCIAL
            elif str(coluna_tabela_origem).upper() == "MUNICIPIO":
                pedidos_itens_imovel.municipio = resposta_correta

            elif str(coluna_tabela_origem).upper() == "NOME_FAZENDA":
                pedidos_itens_imovel.nome_fazenda = resposta_correta

            elif str(coluna_tabela_origem).upper() == "CARACTERISTICA_FAZENDA":
                pedidos_itens_imovel.caracteristica_fazenda = resposta_correta

            elif str(coluna_tabela_origem).upper() == "AREA_FAZENDA":
                pedidos_itens_imovel.area_fazenda = resposta_correta

            elif str(coluna_tabela_origem).upper() == "RESERVA_LEGAL":
                pedidos_itens_imovel.reserva_legal = resposta_correta[0]

            elif str(coluna_tabela_origem).upper() == "GEOREFENCIADA":
                pedidos_itens_imovel.georefenciada = resposta_correta[0]

            elif str(coluna_tabela_origem).upper() == "NUMERO_NIRF":
                pedidos_itens_imovel.numero_nirf = resposta_correta

            elif str(coluna_tabela_origem).upper() == "NUMERO_CCIRR":
                pedidos_itens_imovel.numero_ccirr = resposta_correta

            elif str(coluna_tabela_origem).upper() == "NUMERO_CAR":
                pedidos_itens_imovel.numero_car = resposta_correta

            elif str(coluna_tabela_origem).upper() == "NUMERO_INCRA":
                pedidos_itens_imovel.numero_incra = resposta_correta

            elif str(coluna_tabela_origem).upper() == "REMANESCENTE":
                pedidos_itens_imovel.remanescente = resposta_correta[0]

            elif str(coluna_tabela_origem).upper() == "DATA_VALIDADE_ITR":
                pedidos_itens_imovel.data_validade_itr = resposta_correta

            elif str(coluna_tabela_origem).upper() == "M_FRENTE_METROS":
                pedidos_itens_imovel.m_frente_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "P_FRENTE_METROS":
                pedidos_itens_imovel.p_frente_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "M_DIREITO_METROS":
                pedidos_itens_imovel.m_direito_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "P_DIREITO_METROS":
                pedidos_itens_imovel.p_direito_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "P_ESQUERDO_METROS":
                pedidos_itens_imovel.p_esquerdo_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "M_ESQUERDO_METROS":
                pedidos_itens_imovel.m_esquerdo_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "P_FUNDO_METROS":
                pedidos_itens_imovel.p_fundo_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "M_FUNDO_METROS":
                pedidos_itens_imovel.m_fundo_metros = resposta_correta

            elif str(coluna_tabela_origem).upper() == "AREA_CONSTRUIDA_RESIDENCIAL":
                pedidos_itens_imovel.area_construida_residencial = resposta_correta

            pedidos_itens_imovel.save()

            print("Salvo ")
    except Exception:
        logger.exception("ERRO")

    return redirect("home:checklist_imovel", id=pedido_item_id)


# Novo Item Complementar de Protocolo
def novo_item_protocolo_complementar(request, pedido_item_id):
    # Lógica para processar a confirmação

    # ENVIA O TIPO DE IMOVEL DO PROTOCOLO (MATRICULA, REGISTRO AUXILIAR... TRANSCRICAO)
    tipo_registro_protocolo = TipoRegistroProtocolo.objects.all().order_by("ordem")

    context = (
        {
            "id": pedido_item_id,
            "pedido_item_id": pedido_item_id,
            "tipo_registro_protocolo": tipo_registro_protocolo,
        },
    )

    return render(request, "solicitar_item_protocolo_complementar.html", context)


# Solicitar resposta se existe ato complementar
def solicitar_item_protocolo_complementar(request, pedido_item_id):
    # Lógica para processar a confirmação

    context = {"id": pedido_item_id}
    return render(request, "solicitar_item_protocolo_complementar.html", context)


# Buscar o titulo e Ato padrao dos Emolumentos
def get_titulo_ato_padrao_emolumento(pk):
    pk = str(pk).split(",")[0]

    emolummento = Emolumentos.objects.get(id=pk)
    return emolummento.titulos_id, emolummento.atos_id


# Criar ITEM no PROTOCOLO
def criar_item_protocolo(request):
    if not request.POST:
        raise Http404

    # PEGANDO OS PARAMETROS PARA INCLUIR O ITEM
    # protocolo_id = request.POST["numero_id_protocolo"]
    titulo_id = request.POST["tipo_titulo_protocolo"]
    ato_id = request.POST["tipo_ato_protocolo"]
    tipo_id = request.POST["tipo_registro_protocolo"]
    numero_id = request.POST["numero"]
    tributacao_id = request.POST["tipo_tributacao_protocolo"]
    emolumento_id = request.POST["tabela_emolumentos"]
    valor_documento = request.POST["valor_documento"]
    valor_avaliacao = request.POST["valor_avaliacao"]
    pedido_item_id = request.POST["pedido_item_id"]
    quantidade = request.POST["quantidade"]
    numero_ato_id = (
        str(request.POST["tipo_ato_texto"])[0] + "." + request.POST["numero_ato"]
    )

    # # Atualizar o protocolo atual
    # (
    #     pedido_item_atual,
    #     pedido_atual,
    #     protocolo_atual,
    #     ato_praticado_atual_id,
    #     titulo_atual_id,
    # ) = Atualizar_Protocolo_Atual(pedido_item_id)

    # Protocolo Atual
    # protocolo_id = protocolo_atual
    ri_id = 1

    # OBTER NOVO EMOUMENTO DA TRIBUTACAO DIFERENTE DE NORMAL
    tributacao_id = str(tributacao_id).split(",")[0]
    custas_id = tributacao_id
    emolumento_firebird_id, tributacao_firebird_id = firebird.get_novo_emolumento_do_fb(
        emolumento_id,
        tributacao_id,
    )

    # CRIAR o FIREBIRD
    pedidos_item_id, pedido_id = firebird.criar_pedido_item_no_fb(
        pedido_atual,
        ato_id,
        titulo_id,
        emolumento_firebird_id,
        numero_id,
        tipo_id,
        tributacao_firebird_id,
        valor_documento,
        valor_avaliacao,
        numero_ato_id,
        quantidade,
        custas_id,
        ri_id,
        Colaborador.objects.filtrar_por_default(),
    )

    # VOLTAR PARA O EMOLUMENTO COMPLEMENTAR
    context = {"id": pedido_item_id}
    return render(request, "solicitar_item_protocolo_complementar.html", context)


# Criar ITEM no PROTOCOLO
def criar_item_protocolo_principal(request):
    if not request.POST:
        raise Http404

    # PEGANDO OS PARAMETROS PARA INCLUIR O ITEM
    pedido_id = str(request.POST["pedido_id"]).split(",")[0]
    ato_id = str(request.POST["tipo_ato_protocolo"]).split(",")[0]
    tipo_id = request.POST["tipo_registro_protocolo"]
    numero_id = request.POST["numero"]
    tributacao_id = request.POST["tipo_tributacao_protocolo"]

    # protocolo_id = request.POST["numero_id_protocolo"]
    titulo_id = int(AtoPratica.objects.get(id=ato_id).titulos_id)
    emolumento_id = int(AtoPratica.objects.get(id=ato_id).emolumento_id)

    valor_documento = 0
    valor_avaliacao = 0
    quantidade = 1
    numero_ato_id = ""
    ri_id = 1

    # OBTER NOVO EMOUMENTO DA TRIBUTACAO DIFERENTE DE NORMAL
    tributacao_id = str(tributacao_id).split(",")[0]
    custas_id = tributacao_id
    emolumento_firebird_id, tributacao_firebird_id = firebird.get_novo_emolumento_do_fb(
        emolumento_id,
        tributacao_id,
    )

    pedido_atual = str(pedido_id).split(",")[0]

    db = firebird.FbConnection()
    db.begin_transaction()
    try:
        # CRIAR o FIREBIRD
        pedido_item_id, pedido_id = firebird.criar_pedido_item_no_fb(
            pedido_atual,
            ato_id,
            titulo_id,
            emolumento_firebird_id,
            numero_id,
            tipo_id,
            tributacao_firebird_id,
            valor_documento,
            valor_avaliacao,
            numero_ato_id,
            quantidade,
            custas_id,
            ri_id,
            Colaborador.objects.filtrar_por_default(),
            db,
        )

        # GRAVAR  - IMPORTADO
        firebird.importar_e_criar_pedido_item_do_fb(pedido_id, pedido_item_id, db)

        db.commit()
        db.close()
    except Exception:
        logger.exception("Erro ao criar item no protocolo principal")
        db.rollback()
        db.close()

    return redirect(reverse("home:protocolo_search"))


def visualizar_protocolo_complementar(request, pedido_item_id):
    if not request.POST:
        raise Http404

    # VOLTAR PARA O EMOLUMENTO COMPLEMENTAR
    return solicitar_item_protocolo_complementar(request, pedido_item_id=pedido_item_id)


# Criar ITEM no PROTOCOLO
def criar_item_protocolo_complementar(request):
    if not request.POST:
        raise Http404

    # PEGANDO OS PARAMETROS PARA INCLUIR O ITEM
    tributacao_id = request.POST["tipo_tributacao_protocolo"]
    emolumento_id = request.POST["tabela_emolumentos"]
    pedido_item_id = request.POST["pedido_item_id"]
    quantidade = request.POST["quantidade"]

    # Atualizar o protocolo atual
    # (
    #     pedido_item_atual,
    #     pedido_atual,
    #     protocolo_atual,
    #     ato_praticado_atual_id,
    #     titulo_atual_id,
    # ) = Atualizar_Protocolo_Atual(pedido_item_id)

    # Protocolo Atual
    # protocolo_id = protocolo_atual
    ri_id = 1

    # OBTER NOVO EMOUMENTO DA TRIBUTACAO DIFERENTE DE NORMAL
    tributacao_id = str(tributacao_id).split(",")[0]
    custas_id = tributacao_id

    db = firebird.FbConnection()
    db.begin_transaction()
    try:
        emolumento_firebird_id, tributacao_firebird_id = (
            firebird.get_novo_emolumento_do_fb(
                emolumento_id,
                tributacao_id,
                db,
            )
        )

        # Obter id para os emolumentos complentares
        titulo_id, ato_id = get_titulo_ato_padrao_emolumento(emolumento_id)
        numero_id, tipo_id, numero_ato_id = "", "", ""
        valor_documento, valor_avaliacao = 0, 0

        try:
            titulo_id = int(str(titulo_id))
        except Exception:
            logger.exception("ERRO")
            titulo_id = str(0)

        try:
            ato_id = str(int(ato_id))
        except Exception:
            logger.exception("ERRO")
            ato_id = str(ato_praticado_atual_id)

        ato_id = str(ato_id).split(".")[0]
        titulo_id = str(titulo_id).split(".")[0]

        # CRIAR o FIREBIRD
        pedidos_item_id, pedido_id = firebird.criar_pedido_item_no_fb(
            pedido_atual,
            ato_id,
            titulo_id,
            emolumento_firebird_id,
            numero_id,
            tipo_id,
            tributacao_firebird_id,
            valor_documento,
            valor_avaliacao,
            numero_ato_id,
            quantidade,
            custas_id,
            ri_id,
            Colaborador.objects.filtrar_por_default(),
            db,
        )

        # GRAVAR  - IMPORTADO
        firebird.importar_e_criar_pedido_item_do_fb(pedido_id, pedidos_item_id, db)

        db.commit()
        db.close()
    except Exception:
        logger.exception("Erro ao criar item no protocolo complementar")
        db.rollback()
        db.close()

    # VOLTAR PARA O EMOLUMENTO COMPLEMENTAR
    return solicitar_item_protocolo_complementar(request, pedido_item_id=pedido_item_id)


class FuncionarioCreateView(CreateView):
    template_name = "cria.html"
    model = Funcionario
    form_class = forms.InsereFuncionarioForm
    success_url = reverse_lazy("home:lista_funcionarios")


class FuncionarioUpdateView(UpdateView):
    model = Funcionario
    fields = ["nome", "sobrenome", "tempo_de_servico"]
    # form_class    = InsereFuncionarioForm
    # success_url = reverse_lazy("home:lista_funcionarios")
    template_name = "update.html"

    def form_valid(self, form):
        messages.success(self.request, "A tarefa foi atualizada.")
        return super().form_valid(form)

    def get_success_url(self):
        """Retorna a URL para redirecionar após o formulário ser válido."""
        return reverse("home:lista_funcionarios")


# Atualizar o Checklist PARA O ENDERECO
class UrbanoEnderecoCheckListCreateView(CreateView):
    template_name = "form-inserir-checklist-endereco.html"
    model = PedidoItemImovel
    form_class = forms.InsereEnderecoCheckListForm
    # success_url = reverse_lazy("home:minuta_lv2")
    success_url = reverse_lazy("home:checklist_lv2")

    pk = None
    pedido_item_id = 0

    def form_valid(self, form):
        pedido_item_id = self.kwargs.get("pedido_item_id", "")
        form.instance.pedido_item_id = pedido_item_id
        item = form.save()
        self.pk = item.pk

        print("Urbano 1")

        # Filtrar MUNICIPIO
        try:
            cidade = Cidade.objects.filter(id=item.municipio).first()
            item.municipio = cidade.nome
        except Exception:
            logger.exception("ERRO")

        return super().form_valid(form)

    # Item salvo - Finalizar
    def get_success_url(self):
        # Iterando sobre o DICIONARIO
        pedido_item_id, opcao_imovel = "0", ""

        print("Urbano 2")

        d = dict(self.kwargs)
        for item, value in d.items():
            if str(item) == "pedido_item_id":
                pedido_item_id = str(value)
            if str(item) == "opcao_imovel":
                opcao_imovel = str(value)

        # Atualizar o pedido item
        if pedido_item_id != "":
            atualizar_endereco_checklist(self.pk, pedido_item_id, opcao_imovel)

        return reverse(
            # "home:minuta_lv2",
            "home:checklist_lv2",
            kwargs={"pedido_item_id": pedido_item_id, "opcao": "1"},
        )


# Atualizar o Checklist PARA O ENDERECO
class RuralEnderecoCheckListCreateView(CreateView):
    template_name = "form-inserir-checklist-endereco-rural.html"
    model = PedidoItemImovel
    form_class = forms.InsereEnderecoCheckListForm
    success_url = reverse_lazy("home:minuta_lv2")
    pk = None
    pedido_item_id = 0

    def form_valid(self, form):
        pedido_item_id = self.kwargs.get("pedido_item_id", "")
        form.instance.pedido_item_id = pedido_item_id
        item = form.save()
        self.pk = item.pk

        print("Rural")

        # Filtrar MUNICIPIO
        try:
            cidade = Cidade.objects.filter(id=item.municipio).first()
            item.municipio = cidade.nome
        except Exception:
            logger.exception("ERRO")

        return super().form_valid(form)

    # Item salvo - Finalizar
    def get_success_url(self):
        # Iterando sobre o DICIONARIO
        pedido_item_id, opcao_imovel = "0", ""

        print("Rural")

        d = dict(self.kwargs)
        for item, value in d.items():
            if str(item) == "pedido_item_id":
                pedido_item_id = str(value)
            if str(item) == "opcao_imovel":
                opcao_imovel = str(value)

        # Atualizar o pedido item
        if pedido_item_id != "":
            atualizar_endereco_checklist(self.pk, pedido_item_id, opcao_imovel)

        return reverse(
            "home:minuta_lv2",
            kwargs={"pedido_item_id": pedido_item_id},
        )


class NovaPessoaCreateView(CreateView):
    template_name = "form-inserir-pessoa-adquirente-ato.html"
    model = Livro05
    form_class = forms.InserePessoaForm
    success_url = reverse_lazy("home:vincular_pessoa_protocolo")

    # Iterando sobre o DICIONARIO
    pk, pedido_item_id, opcao_parte, CPF_CNPJ, NOME, pedido_id = (
        None,
        "0",
        "",
        "",
        "",
        "",
    )

    # def form_valid(self, form):
    #     # PESQUISAR NOME, CPF.  IF NAO EXISTIR CADASTRAR - EXISTIR RETORNAR ID
    #     pk = get_maior_pessoa_id_por_cpf_e_nome(
    #         form["cpf"].value(),
    #         form["nome"].value(),
    #     )

    #     # Obter os dados da ultima ficha da pessoa
    #     atualizar_dados = ""

    #     # CADASTRAR NOVA PESSOA
    #     if pk == 0:
    #         # print("Cadastrar Nova Pessoa")
    #         item = form.save()
    #         self.pk = item.pk

    #         # PEGANDO OS DADOS DO FORMULARIO
    #         self.CPF_CNPJ = item.cpf
    #         self.NOME = item.nome
    #     else:
    #         # print("Já existe a Pessoa")
    #         self.pk = pk

    #         # PEGANDO OS DADOS DO FORMULARIO
    #         self.CPF_CNPJ = form["cpf"].value()
    #         self.NOME = form["nome"].value()

    #         atualizar_dados = "S"

    #     # PEGANDO OS CAMPOS CHAVE
    #     d = dict(self.kwargs)
    #     for item, value in d.items():
    #         if str(item) == "pedido_item_id":
    #             pedido_item_id = str(value)
    #         if str(item) == "opcao_parte":
    #             opcao_parte = str(value)

    #     # VINCULAR PESSOA.  TRANSMITENTE = opcao_parte T, ADQUIRENTE = opcao_parte A
    #     pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
    #     pedido_id = pedido_item.pedido

    #     # Incluir como parte do Protocolo
    #     if pedido_id:
    #         print("Vincular pessoa ", self.pk, pedido_id, opcao_parte)
    #         vincular_pessoa_protocolo(self.pk, pedido_id, opcao_parte)

    #     # Atualizar o pedido item
    #     if pedido_item:
    #         gravar_pedidos_partes_ato(
    #             pedido_id=pedido_id,
    #             pedido_item_id=pedido_item_id,
    #             pessoa=self.pk,
    #             status=opcao_parte,
    #             estado_civil=0,
    #             total=1,
    #             ato_baixa_id=None,
    #             percentual_ato=0,
    #         )

    #         # COPIAR O ENDERECO DA ULTIMA PESSOA
    #         if atualizar_dados == "S":
    #             print("TRABALHANDO - Atualizar Endereço", self.pk, pedido_item_id)

    #     # RETORNAR PARA O PEDIDO PARTE DO PROTOCOLO
    #     url = f"{reverse('home:update_pessoa', kwargs={'pk': pk})}?pedido_item_id={pedido_item_id}"
    #     return redirect(url)

    def form_valid(self, form):
        cpf = form.cleaned_data["cpf"]
        nome = form.cleaned_data["nome"]

        # cpf = form.get("cpf", "").value()
        # nome = form.get("nome", "").value()
        pk = get_maior_pessoa_id_por_cpf_e_nome(cpf, nome)

        if pk == 0:
            pessoa = form.save()
            self.pk = pessoa.pk
            self.CPF_CNPJ = pessoa.cpf
            self.NOME = pessoa.nome
        else:
            self.pk = pk
            self.CPF_CNPJ = cpf
            self.NOME = nome

        pedido_item_id = self.kwargs.get("pedido_item_id", "")
        tipo_parte = self.kwargs.get("opcao_parte", "")

        if pedido_item_id:
            pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

            if pedido_item:
                PedidoParte.vincular_pessoa_a_pedido(
                    pessoa_id=self.pk,
                    pedido_id=pedido_item.pedido_id,
                    papel=tipo_parte,
                )

                PedidoParteAto.criar(
                    pedido_item_id=pedido_item.pk,
                    pessoa_id=self.pk,
                    tipo_parte=tipo_parte,
                )

        url = f"{reverse('home:update_pessoa', kwargs={'pk': pk})}?pedido_item_id={pedido_item.pk}"
        return redirect(url)

    # Item salvo - Finalizar
    def get_success_url(self) -> None:
        pass


# Retornar o maior id da pessa
def get_maior_pessoa_id_por_cpf_e_nome(cpf, nome):
    logger.info(f"Procurando por CPF: {cpf} e Nome: {nome}")

    pessoas = Livro05.objects.filter(
        nome=nome,
        cpf=cpf,
    ).order_by("-data_alteracao")

    pessoa = pessoas.first()

    return pessoa.id if pessoa else 0


# Atualizar o Vinculo da Pessoa checklist
def atualizar_vincular_pessoa_ato_checklist(pk, pedido_item_id, opcao_pessoa) -> None:
    PedidoParteAto.objects.filter(id=pk).update(
        pedido_item_id=pedido_item_id,
        status=opcao_pessoa,
        percentual_ato=0,
        percentual_doi=0,
        percentual_incra=0,
    )


# Atualizar o Endereco do checklist
def atualizar_endereco_checklist(pk, pedido_item_id, opcao_imovel) -> None:
    PedidoItemImovel.objects.filter(id=pk).update(
        pedido_item_id=pedido_item_id,
        opcao_imovel=opcao_imovel,
    )


# Vincular a parte da pessoa ao protocolo
def vincular_pessoa_protocolo(pessoa_id, pedido_id, opcao) -> None:
    pedido_parte = PedidoParte(pessoa_id=pessoa_id, pedido_id=pedido_id, papel=opcao)
    pedido_parte.save()


class PessoaCreateView(CreateView):
    template_name = "cria_pessoa.html"
    model = Livro05
    form_class = forms.InserePessoaForm
    success_url = reverse_lazy("home:vincular_pessoa_protocolo")

    def form_valid(self, form):
        print("Criando uma nova pessoa")

        self.kwargs.get("pedido_item_id", "")
        self.kwargs.get("opcao_parte", "")

        pessoa = Livro05.get_ultima_pessoa_por_cpf(form["cpf"].value())

        if pessoa is None:
            novo_item = form.save()
            self.pk = novo_item.pk
            logger.info(f"Salvou novo registro: {novo_item.pk}")
        else:
            self.pk = pessoa.id
            logger.info(f"Encontrou pessoa já cadastrada: {pessoa.id}")

        return super().form_valid(form)

    # Item salvo - Finalizar

    def get_success_url(self):
        print("****************************** SALVANDO A NOVA PESSOA ")

        pedido_id = self.kwargs.get("pedido_id", "0")
        opcao_parte = self.kwargs.get("opcao_parte", "")

        protocolo = Livro01Protocolo.objects.filter(numero_protocolo=pedido_id)
        pedido_id = next(
            (str(protocolo.pedido_id) for protocolo in protocolo),
            "",
        )

        if pedido_id:
            vincular_pessoa_protocolo(self.pk, pedido_id, opcao_parte)
            logger.info(f"VINCULOU ID: {self.pk}")

            return reverse("home:vincular_pessoa_protocolo")
        return None


# Atualizar o Checklist PARA O ENDERECO
class ParteCheckListCreateView(CreateView):
    template_name = "form-vincular-adquirente-ato.html"
    model = PedidoParteAto
    form_class = forms.VinculaPessoaCheckListForm
    success_url = reverse_lazy("home:minuta_lv2")
    pk = None
    pedido_item_id = 0

    def form_valid(self, form):
        item = form.save()
        self.pk = item.pk

        # print(item.pessoa)

        return super().form_valid(form)

    # Item salvo - Finalizar
    def get_success_url(self):
        # Iterando sobre o DICIONARIO
        pedido_item_id, opcao_pessoa = "0", ""

        d = dict(self.kwargs)
        for item, value in d.items():
            if str(item) == "pedido_item_id":
                pedido_item_id = str(value)
            if str(item) == "opcao_pessoa":
                opcao_pessoa = str(value)

        # Atualizar o pedido item
        if pedido_item_id != "":
            atualizar_vincular_pessoa_ato_checklist(
                self.pk,
                pedido_item_id,
                opcao_pessoa,
            )

        return reverse(
            "home:minuta_lv2",
            kwargs={"pedido_item_id": pedido_item_id},
        )


# Retornar da hipoteca
def get_acoes_e_onus(imovel_id):
    try:
        # Hipotecas Atuais
        hipoteca_atual = []

        hipoteca_atual = (
            Vinculo.objects.select_related("pessoa", "tipo_vinculo")
            .filter(
                imovel_id=imovel_id,
                situacao="F",
                # tipo_vinculo_id__in=Configuracao.obter("hipoteca_id"),
                tipo_vinculo_id__in=Configuracao.obter("acoes_onus_id"),
            )
            .order_by("numero_ato")
        )

        # Filtrando os vinculos HIPOTECA
        ordem_penhor, percentual_hipoteca_atual = 0, 0
        nro_ato_atual = ""

        # Filtrando os vinculos - HIPOTECAS
        for hipoteca in hipoteca_atual:
            pessoa: Livro05 = Livro05.objects.filter(pk=hipoteca.pessoa.id).first()

            # Formatar o percentual
            try:
                percentual_hipoteca_atual += Decimal(hipoteca.area_pecentual)
            except Exception:
                logger.exception("ERRO")
                percentual_hipoteca_atual = 0

            numero_ato_temp = (
                str(hipoteca.tipo_ato) + "." + str(hipoteca.numero_ato).split(".")[0]
            )
            str(hipoteca.area_pecentual).replace(".", ",") + "%"
            nome = pessoa.nome
            cpf = pessoa.documento_formatado
            percentual = (
                "(" + str(percentual_hipoteca_atual).replace(".", ",") + "%" + ")"
            )

            # Se mudar o numero do ato a ordem do penhor e acrescida de 1
            if str(nro_ato_atual) != str(hipoteca.numero_ato):
                nro_ato_atual = str(hipoteca.numero_ato)
                ordem_penhor = int(ordem_penhor) + 1

            grau_penhor = "(Grau: " + str(ordem_penhor) + ")"

            # Filtrando o nome das pessoas
            hipoteca_atual.append([numero_ato_temp, grau_penhor, cpf, nome, percentual])

        return hipoteca_atual
    except Exception:
        logger.exception("ERRO")
        return ""


# Retornar da Livro 3 Vinculados - Quantidade
def get_quantidade_de_registros_no_livro03(
    numero_registro=0,
    tipo_registro="",
) -> int:
    # PEGANDO OS DADOS DAS GARANTIAS - Filtrar as garantias do LIVRO 3 - Vinculadas ao IMOVEL
    return Livro03Garantia.objects.filter(
        numero_registro=numero_registro,
        tipo_registro=tipo_registro,
    ).count()


# Retornar da Livro 3 Vinculados
def get_livro03(numero_registro=0, tipo_registro=""):
    try:
        # PEGANDO OS DADOS DAS GARANTIAS - Filtrar as garantias do LIVRO 3 - Vinculadas ao IMOVEL
        vinculado_imovel_atual = Livro03Garantia.objects.filter(
            numero_registro=numero_registro,
            tipo_registro=tipo_registro,
        ).order_by("-registro_auxiliar")

        # vinculado_imovel Atuais
        vinculado_imovel_atual = []

        # Filtrando os vinculado_imovel l3
        for garantia in vinculado_imovel_atual:
            # Obter os dados do LIVRO 3
            registro_auxiliar = Livro03.objects.get(id=garantia.registro_auxiliar_id)

            # print('numero:', registro_auxiliar.numero)

            # for registro in registro_auxiliar:
            numero = formatar_numero_registro(str(registro_auxiliar.numero))
            numero_cedula = str(registro_auxiliar.numero_cedula)
            nome = str(registro_auxiliar.tipo_registro_auxiliar.nome)
            data_abertura = formatar_data(str(registro_auxiliar.data_abertura), 1)
            cancelado_em = formatar_data(
                str(registro_auxiliar.cancelado_em),
                1,
            )
            data_vencimento = formatar_data(str(registro_auxiliar.data_vencimento), 1)
            descricao = str(registro_auxiliar.descricao)

            grau_penhor = garantia.grau_penhor
            area = garantia.area

            # TODOs os vinculos
            envolvidos = []
            ligacoes = Livro03Ligacao.objects.filter(
                registro_auxiliar_id=garantia.registro_auxiliar_id,
            )
            for envolvidos in ligacoes:
                envolvidos.append(
                    [
                        envolvidos.pessoa.nome,
                        envolvidos.pessoa.cpf,
                        envolvidos.figuras.tipo_figura,
                    ],
                )

            # Filtrando o nome das pessoas
            vinculado_imovel_atual.append(
                [
                    numero,
                    nome,
                    numero_cedula,
                    grau_penhor,
                    data_abertura,
                    cancelado_em,
                    data_vencimento,
                    descricao,
                    area,
                    envolvidos,
                ],
            )

        return vinculado_imovel_atual
    except Exception:
        logger.exception("ERRO")
        return ""


# Acessar Registro Auxiliar - Livro 3
def abrir_lv04(request):
    # PEGA DA TEMPLATE O NUMERO INFORMADO
    numero_id = request.POST["numero_informado"]
    return redirect("home:livro04_detail", pk=numero_id)


# Acessar Registro Auxiliar - Livro 3
def abrir_livro03(request):
    # PEGA DA TEMPLATE O NUMERO INFORMADO
    numero_informado = request.POST["numero_informado"]

    try:
        return redirect(
            "home:livro03_detail_pelo_numero",
            numero=numero_informado,
            cartorio="1",
        )
    except Livro03.DoesNotExist:
        return redirect("home:livro03_list")


# Acessar Registro Auxiliar - Livro 3
def abrir_livro05(request):
    from urllib.parse import quote_plus

    # PEGA DA TEMPLATE DA PESQUISA PESSOA
    numero_id = request.POST["numero_informado"]
    nome_informado = request.POST["nome_informado"]

    # Verificar se o numero esta vazio
    if str(numero_id) == "":
        numero_id = 0

    # NOME INFORMADO FOI COLOCADO
    if str(nome_informado) == "":
        nome_informado = "%"

    # Verificar se o item e vazio
    # if str(nome_informado).split("") == "":
    #     nome_informado = "%"

    print(numero_id)
    nome_codificado = quote_plus(nome_informado)

    return redirect("home:pessoal", cpf_cnpj=numero_id, nome=nome_codificado)


# Acessar Registro Auxiliar - Livro 3
class Livro02View(View):
    def get(self, request, *args, **kwargs):
        # Primeiro tenta obter do GET, senão pega do POST, e usa um valor padrão para cartorio_imovel
        numero_id = request.GET.get(
            "numero_informado",
            request.POST.get("numero_informado"),
        )
        tipo_registro_id = request.GET.get(
            "tipo_registro",
            request.POST.get("tipo_registro"),
        )
        cartorio_imovel_id = request.GET.get(
            "cartorio_imovel",
            request.POST.get("cartorio_imovel", "1"),
        )

        # Filtrar o LIVRO 2
        imoveis = Livro02.objects.filter(
            numero=numero_id,
            tipo=tipo_registro_id,
            cartorio=cartorio_imovel_id,
        )

        if imoveis.exists():
            # Redireciona com os parâmetros obtidos
            return redirect(
                "home:livro04_detail",
                numero_registro=numero_id,
                tipo_registro=tipo_registro_id,
                cartorio_imovel=cartorio_imovel_id,
            )
        else:
            return redirect("home:livro02_list")

    # Como o comportamento é o mesmo para GET e POST, podemos simplesmente
    # chamar o método get dentro do post para reutilizar a lógica
    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


# Acessar Registro Protocolo ou Examae - Livro 1
def abrir_livro01(request):
    # Recebe os dados informados pelo usuario
    numero_protocolo = request.POST["numero_informado"]
    if numero_protocolo:
        protocolo = Livro01Protocolo.objects.filter(
            numero_protocolo=numero_protocolo,
        ).first()

        if protocolo:
            url = f"{reverse('home:protocolo_search')}?numero_protocolo={numero_protocolo}"
            return redirect(url)

    messages.error(request, f"Protocolo {numero_protocolo} não encontrado.")
    return redirect("home:protocolo_search")


def abrir_livro01_por_numero_protocolo(request, numero_protocolo):
    # Recebe os dados informados pelo usuario
    if numero_protocolo:
        protocolo = Livro01Protocolo.objects.filter(
            numero_protocolo=numero_protocolo,
        ).first()

        if protocolo:
            url = reverse("home:protocolo_detail", args=[protocolo.id])
            return redirect(url)
            # return redirect(protocolo.get_absolute_url())

    messages.error(request, f"Protocolo {numero_protocolo} não encontrado.")
    return redirect("home:protocolo_search")


def abrir_livro01_por_numero(request):
    # Recebe os dados informados pelo usuario
    numero_protocolo = request.GET["numero_informado"]
    if numero_protocolo:
        protocolo = Livro01Protocolo.objects.filter(
            numero_protocolo=numero_protocolo,
        ).first()

        if protocolo:
            return redirect(protocolo.get_absolute_url())

    messages.error(request, f"Protocolo {numero_protocolo} não encontrado.")
    return redirect("home:protocolo_search")


@login_required
def calendario_redirect_view(request):
    """
    Redireciona o usuário para a página do calendário.
    Esta view exige que o usuário esteja autenticado.
    """
    return redirect("home:calender")


def pessoa_update_view(request):
    if request.method == "POST":
        d = request.POST.dict()

        id_a, _id_t = 0, 0

        # Pegando a chave ID
        for item, value in zip(d.keys(), d.values(), strict=False):
            if str(item) == "ed_item_parte_id" or str(item) == "pessoa_id":
                id_a = str(value)

            if str(item) == "ed_item_parte_idT":
                str(value)

        # REGIME INICIAL
        _estado_civil, tipo_regime_id = 0, 0

        form1 = forms.Livro05Form(request.POST)
        if form1.is_valid():
            # Pegando os parametros passados para atualizar
            pessoa = Livro05.objects.get(id=id_a)

            for item, value in zip(d.keys(), d.values(), strict=False):
                if str(item) == "ed_documento" or str(item) == "documento":
                    pessoa.documento = str(value)

                if str(item) == "ed_nacionalidade" or str(item) == "nacionalidade":
                    pessoa.nacionalidade = str(value)

                if str(item) == "ed_sexo" or str(item) == "sexo":
                    pessoa.sexo = str(value)

                if str(item) == "ed_profissao" or str(item) == "profissao":
                    pessoa.profissao = str(value)

                if str(item) == "ed_naturalidade" or str(item) == "naturalidade":
                    pessoa.naturalidade = str(value)

                if str(item) == "ed_endereco" or str(item) == "endereco":
                    pessoa.endereco = str(value)

                if str(item) == "nome":
                    pessoa.nome = str(value)

                if str(item) == "nome_pai":
                    pessoa.nome_pai = str(value)

                if str(item) == "nome_mae":
                    pessoa.nome_mae = str(value)

                if str(item) == "email":
                    pessoa.email = str(value)

                # Data de Nascimento
                data_nascimento = ""

                try:
                    if str(item) == "data_nascimento":
                        pessoa.data_nascimento = str(formatar_data(str(value), 1))
                except Exception:
                    logger.exception("ERRO")
                    if data_nascimento == "":
                        pessoa.data_nascimento = "1901-01-01"

                if str(item) == "tipo_regime_casamento":
                    pessoa.tipo_regime_id = str(value).split(",")[0]
                    tipo_regime_id = str(value).split(",")[0]

                # DADOS PARA ATUALIZAR NO ATO
                if str(item) == "estado_civil":
                    pessoa.estado_civil = str(value).split(",")[0]
                    str(value).split(",")[0]

                # ATUALIZAR O ESTADO CIVIL DO ATO TEMPORARIO
                """
                try:
                    pedidos_partes_ato = PedidoParteAto.objects.get(pedido_item_id=pedido_item_id, pessoa=id_a)
                    pedidos_partes_ato.estado_civil           = estado_civil
                    pedidos_partes_ato.estado_civil_regime_id    = estado_civil_regime_id
                    pedidos_partes_ato.save()
                except Exception as e:
                    logger.exception("ERRO")
                    pass
                """

            # DADOS PARA ATUALIZAR NO ATO
            salvar = "S"

            # VERIFICAR SE O REGIME NAO E OBRIGATORIO - CASO NAO SEJA ELE E RETIRADO
            estado_civil = EstadoCivil.objects.filter(
                id=pessoa.estado_civil,
                requerer_tipo_regime="S",
            )
            if estado_civil.exists() and int(tipo_regime_id) == 0:
                salvar = "N"
                context = {
                    "Regime": "Campos Obrigatórios - Regime de Bens deve ser informado",
                }
                return render(request, "Validar_Pessoa.html", context)

            # pessoa.published_date = timezone.now()

            if salvar != "N":
                pessoa.save()
                print("Pessoa salva !!")

                """
                # Atualizar Transmitente
                if str(id_a) != str(idT):
                    pessoa = Livro05.objects.get(id=idT)
                    for item, value in zip(d.keys(), d.values()):
                        if str(item) == 'ed_documentoT':
                            pessoa.documento = str(value)
                    pessoa.save()
                """

    # success_url = reverse_lazy("atualizar_protocolo")
    return redirect(reverse("home:protocolo_search"))


def preparar_checklist_livro02_texto(request, pedido_item_id):
    print("preparar_checklist_livro02_texto - ", pedido_item_id)

    # Verificar se existe o texto ja gravado na tabela
    if Livro02Texto.objects.filter(pedido_item_id=pedido_item_id).exists():
        return redirect(
            "home:texto_lv2",
            pk=pedido_item_id,
            pedido_item_id=pedido_item_id,
        )
    else:
        return redirect("home:minuta_lv2", pedido_item_id=pedido_item_id)


def preparar_checklist_livro02(request, pedido_item_id, opcao=0):
    PedidoParteAto.vincular_pedido_parte_ato(
        pedido_id=pedido_atual,
        pedido_item_id=pedido_item_id,
    )

    if request.method == "POST":
        for item in request.POST:
            atual = get_apenas_numeros(str(item).split(",")[0])

            if atual != "":
                lista_indice_temporaria.append(atual)
                lista_variaveis_temporaria.append(request.POST.get(item))

        # Qual minuta foi escolhida
        if request.POST.get("cbxMinuta") is not None:
            minuta_selecionada = request.POST.get("cbxMinuta")

        # Gerar as perguntas olhando o modelo escolhido
        lista_perguntas_atuais = get_perguntas_vinculadas_minuta(
            minuta_selecionada,
            pedido_item_id,
            minuta_selecionada,
        )

        # EXIBIR AS VARIAVEIS DAS perguntas da MINUTA
        # print(lista_perguntas_atuais)

        # Retonar as pesquisas a serem feitas
        # return exibir_perguntas_minuta_lv2(request, pedido_item_atual)
        if len(lista_perguntas_atuais) > 0:
            # return ExportDocx_lv2(request, pedido_item_id, minuta_selecionada)
            print("ExportDocx_lv2")
        else:
            return exibir_direto_minuta_lv2(request, pedido_item_id, minuta_selecionada)

    pedido_item: PedidoItem = PedidoItem.objects.get(pk=pedido_item_id)

    sub_pasta = get_sub_pasta_ato_livro02(pedido_item.ato_id)

    minutas = helpers.get_arquivos_de_minutas(pedido_item.tipo_registro, sub_pasta)

    partes = PedidoParte.objects.filter(pedido_id=pedido_item.pedido_id)

    adquirentes = PedidoParteAto.objects.filter(
        pedido_item_id=pedido_item.id,
        status="A",
    ).order_by("id")

    transmitentes = PedidoParteAto.objects.filter(
        pedido_item_id=pedido_item.id,
        status="T",
    ).order_by("id")

    imoveis_rurais = PedidoItemImovel.objects.filter(
        pedido_item_id=pedido_item.id,
        opcao_imovel="R",
    )

    imoveis_urbanos = PedidoItemImovel.objects.filter(
        pedido_item_id=pedido_item.id,
        opcao_imovel="U",
    )

    cidades = Cidade.objects.all()

    protocolo = Livro01Protocolo.objects.get(pedido_id=pedido_item.pedido_id)

    registro = pedido_item.get_dados_do_registro()

    imovel_id = registro["imovel_id"]

    classe_id = registro["classe_id"]

    registro: Livro02 = Livro02.objects.get(id=imovel_id)

    vinculos = registro.vinculos

    partes = registro.partes

    proprietarios_atuais = registro.proprietarios_atuais_formatados

    context = {
        "imoveis": registro,
        "vinculos": vinculos,
        "partes": partes,
        "partes_atual": partes,
        "partes_adquirente": adquirentes,
        "partes_transmitente": transmitentes,
        "partes_imovel_rural": imoveis_rurais,
        "partes_imovel_urbano": imoveis_urbanos,
        "cidades": cidades,
        "proprietario_atual": proprietarios_atuais,
        "list_de_minutas": minutas,
        "pedido_item": pedido_item,
        "protocolo": protocolo,
        "pedido_item_id": pedido_item_id,
        "classe_imovel": classe_id,
    }

    return render(request, "preparar_checklist_livro02.html", context)


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split("-"))
        return date(year, month, day=1)
    return datetime.now(tz=datetime.UTC).date()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    return "month=" + str(prev_month.year) + "-" + str(prev_month.month)


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    return "month=" + str(next_month.year) + "-" + str(next_month.month)


def try_or_empty(dado):
    try:
        return dado
    except Exception:
        logger.exception("ERRO")
        return ""


def formatar_endereco_urbano(imovel_id, data_abertura, municipio) -> str:
    return (
        f"Urbano: {imovel_id} - Data abertura: {data_abertura}  Municipio: {municipio}"
    )


def get_pessoa(pk):
    try:
        return Livro05.objects.get(pk=pk)
    except Livro05.DoesNotExist:
        logger.exception(f"Pessoa com id {pk} não encontrada.")
        return None


def formatar_percentual(percentual) -> str | None:
    try:
        return f"({Decimal(percentual):.2f}%)"
    except ValueError as e:
        logger.exception(f"ERRO ao converter percentual: {e!s}")
        return "(0.00%)"


def formatar_informacao_hipoteca(item, ordem_penhor, pessoa) -> str:
    numero_ato = str(item.numero_ato).split(".")[0]
    return f"{item.tipo_ato}.{numero_ato} - (Grau: {ordem_penhor}) - {formatar_documento(pessoa.cpf)} - {pessoa.nome}"


def formatar_informacao_alienacao(alienacao, pessoa) -> str:
    numero_ato = str(alienacao.numero_ato).split(".")[0]
    return f"{alienacao.tipo_ato}.{numero_ato} - {formatar_documento(pessoa.cpf)} - {pessoa.nome}"


def get_info_imovel(item) -> str:
    registro = f"Registro: {formatar_numero_registro(item.registro_auxiliar.numero)}"
    nome = str(item.registro_auxiliar.tipo_registro_auxiliar.nome)
    numero_cedula = f"Número da Cédula: {item.registro_auxiliar.numero_cedula}"
    grau = f"Grau: {item.grau_penhor}"
    return f"{registro} - {nome} - {numero_cedula} - {grau}"


def get_info_produto(item) -> str:
    produto_safra = f"Produto/Safra: {item.registro_auxiliar.descricao}"
    area_plantada = f"Área Plantada: {item.area}"
    return f"{produto_safra} - {area_plantada}"


def get_info_datas(item, cancelado_em) -> str:
    data_abertura_formatada = formatar_data(item.registro_auxiliar.data_abertura, 1)
    data_vencimento_formatada = formatar_data(
        item.registro_auxiliar.cancelado_em,
        1,
    )
    return f"Data Abertura: {data_abertura_formatada} - Data Vencimento: {data_vencimento_formatada} - Data Cancelamento: {cancelado_em}"


class PessoaUpdateView(LoginRequiredMixin, UpdateView):
    model = Livro05
    form_class = forms.PessoaUpdateForm
    template_name = "criar_editar_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_item_id = self.request.GET.get("pedido_item_id", None)
        ancora_origem = self.request.GET.get("ancora_origem", None)

        context["pedido_item_id"] = pedido_item_id
        context["ancora_origem"] = ancora_origem
        context["form_action"] = "."

        return context

    def get_success_url(self) -> str:
        pedido_item_id = self.request.POST.get("pedido_item_id", None)
        ancora_retorno = self.request.POST.get("ancora", None)

        if pedido_item_id != "None":
            if ancora_retorno == "itens_pedido_partes":
                url = reverse(
                    "home:protocolo_detail",
                    kwargs={"pk": pedido_item_id},
                )
            else:
                url = reverse(
                    "home:checklist_lv2",
                    kwargs={"pedido_item_id": pedido_item_id, "opcao": 1},
                )

            return f"{url}#{ancora_retorno}"
        else:
            return None

    def form_valid(self, form):
        # Chame o form_valid da superclasse para salvar a instância do modelo atual
        response = super().form_valid(form)
        pessoa = self.object
        pessoa.save()

        pedido_item_id = self.request.POST.get("pedido_item_id", None)
        ancora_retorno = self.request.POST.get("ancora", None)

        if pedido_item_id != "None":
            # Atualizar o pedido item CASO NAO VENHA APENAS DO PROTOCOLO
            if ancora_retorno != "itens_pedido_partes":
                pedidos_partes_ato = (
                    PedidoParteAto.objects.filter(
                        pedido_item_id=pedido_item_id,
                        pessoa=pessoa.pk,
                    )
                    .order_by("-pk")
                    .first()
                )

                if pedidos_partes_ato is not None:
                    pedidos_partes_ato.estado_civil = str(pessoa.estado_civil.id)
                    pedidos_partes_ato.tipo_regime_id = str(
                        pessoa.tipo_regime_casamento.id,
                    )
                    pedidos_partes_ato.save()

            # Retorne a resposta
            return response
        else:
            # return None
            # return render(self.request, pedido_certidao_pessoas_list_view)

            # url = reverse(
            #     "home:pedido_certidao_pessoas_list",
            #     kwargs={"pedido_id": 6},
            # )
            # return f"{url}"
            return response


def get_apenas_numeros(variavel):
    from apps.home.helpers import get_apenas_numeros

    return get_apenas_numeros(variavel)


class RelatorioDashboardTemplateView(TemplateView):
    template_name = "relatorios/relatorio_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # DATA DO RELATORIO DE DISTRIBUICAO
        if str(kwargs["data_inicio"]) is not None:
            start_date = kwargs["data_inicio"]
            end_date = kwargs["data_fim"]
        else:
            # Filtragem para Protocolo
            start_date = timezone.now().date() - timedelta(0)
            end_date = timezone.now().date() + timedelta(0)

        protocolos_distribuidos = Livro01Protocolo.objects.filter(
            data_protocolo__range=[start_date, end_date],
            # , fases_protocolo_id__isnull=False,
        ).order_by("numero_protocolo")

        # MONTAR A LISTA PARA IMPRESSAO
        lista_protocolos = [
            [
                item.numero_protocolo,
                item.data_protocolo,
                item.pedido_id,
                item.pedido.nome_solicitante_formatado,
                item.pedido.observacao,
                item.numero_protocolo,
            ]
            for item in list(protocolos_distribuidos)
        ]

        # context["protocolos"] = protocolos
        context["lista_protocolos"] = lista_protocolos
        context["hoje"] = timezone.now().date()

        return context


# DISTRIBUICAO DE PROTOCOLO EXIBE TODOS - EXIBE TODOS OS COLABORARES SEPARADOS


class RelatorioProtocolosDistribuidosTemplateView(TemplateView):
    template_name = "relatorios/relatorio_protocolos_distribuidos.html"
    # template_name = "relatorios/relatorio_protocolos_distribuidos_colaborador.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # colaborador_id = kwargs.get("colaborador_id", None).split(".")[0]

        # DATA DO RELATORIO DE DISTRIBUICAO
        if str(kwargs["data_inicio"]) != "None":
            start_date = kwargs["data_inicio"]
            end_date = kwargs["data_fim"]
        else:
            # Filtragem para Protocolo
            start_date = timezone.now().date()
            end_date = timezone.now().date() + timedelta(0)

        # Prefetch_related é usado para otimizar a recuperação de objetos relacionados.
        # Isso reduz o número de consultas ao banco de dados quando acessamos o objeto relacionado.
        # prefetch = Prefetch(
        #     "colaborador", queryset=Colaborador.objects.all()
        # )

        # # Verifica se o id do colaborador é 0, o que pode indicar que queremos todos os colaboradores.
        # if int(colaborador_id) == 0:
        #     # Filtra protocolos que ainda não foram atribuídos a uma fase (fases_protocolo_id is null)
        #     # e estão dentro do intervalo de datas especificado.
        #     # Os resultados são ordenados pelo id do colaborador e pelo número de ordem.
        #     protocolos = (
        #         Livro01Protocolo.objects.prefetch_related(prefetch)
        #         .filter(
        #             data_protocolo__range=[start_date, end_date],
        #             #fases_protocolo_id__isnull=True,
        #         )
        #         .order_by("fases_protocolo_colaborador_id", "numero_protocolo")
        #     )
        # else:
        #     # Caso um id de colaborador específico seja fornecido, filtra os protocolos
        #     # baseado no id do colaborador e no intervalo de datas.
        #     # Os resultados são ordenados pelo número de ordem.
        #     protocolos = (
        #         Livro01Protocolo.objects.prefetch_related(prefetch)
        #         .filter(
        #             colaborador=colaborador_id,
        #             # fases_protocolo_colaborador_id=colaborador_id,
        #             # data_protocolo__range=[start_date, end_date],
        #         )
        #         .order_by("numero_protocolo")
        #     )

        # Aqui estamos obtendo todos os protocolos distribuídos dentro do intervalo de datas
        # sem considerar se o id do colaborador é 0 ou não, já que queremos esta informação
        # de qualquer maneira para fazer o agrupamento a seguir.
        protocolos_distribuidos = Livro01Protocolo.objects.filter(
            data_distribuicao__range=[start_date, end_date],
            # colaborador=colaborador_id,
        ).order_by("fases_protocolo_colaborador", "numero_protocolo")

        # Agrupamento de protocolos distribuídos por id do colaborador.
        # Utilizamos o método `setdefault` para inicializar uma lista vazia para cada colaborador,
        # se ainda não existir, e em seguida, anexamos o protocolo a esta lista.
        protocolos_distribuidos_por_colaborador = {}

        for p in protocolos_distribuidos:
            # p.fases_protocolo_colaborador_id é o ID do colaborador associado ao protocolo.
            # A lista de protocolos distribuídos para esse colaborador é atualizada.
            protocolos_distribuidos_por_colaborador.setdefault(
                p.fases_protocolo_colaborador,
                [],
                # p.colaborador
            ).append(p)

        context["protocolos_distribuidos_por_colaborador"] = (
            protocolos_distribuidos_por_colaborador
        )

        context["hoje"] = timezone.now().date()

        return context


class RelatorioProtocolosDistribuidosUnicoTemplateView(TemplateView):
    template_name = "relatorios/relatorio_protocolos_distribuidos_unico.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        colaborador_id = int(kwargs.get("colaborador_id", 0))

        # DATA DO RELATORIO DE DISTRIBUICAO
        start_date = (
            kwargs["data_inicio"]
            if kwargs["data_inicio"]
            else timezone.now().date() - timedelta(0)
        )
        end_date = (
            kwargs["data_fim"]
            if kwargs["data_fim"]
            else timezone.now().date() + timedelta(0)
        )

        # PESQUISAR PELO COLABORADOR
        if colaborador_id == 0:
            protocolos = Livro01Protocolo.get_protocolos_a_distribuir_no_periodo(
                start_date,
                end_date,
            )
            protocolos_distribuidos = (
                Livro01Protocolo.get_protocolos_distribuidos_no_periodo(
                    start_date,
                    end_date,
                )
            )
        else:
            protocolos = Livro01Protocolo.objects.filtrar_por_colaborador(
                colaborador_id,
            ).order_by(
                "numero_protocolo",
            )

            protocolos_distribuidos = (
                Livro01Protocolo.objects.filtrar_por_colaborador(colaborador_id)
                .filter(
                    data_distribuicao__range=[start_date, end_date],
                )
                .order_by("numero_protocolo")
            )

        context["protocolos"] = protocolos
        context["protocolos_distribuidos"] = protocolos_distribuidos
        context["hoje"] = timezone.now().date()

        return context


class RelatorioProtocolosDistribuidosColaboradorTemplateView(TemplateView):
    template_name = "relatorios/relatorio_protocolos_distribuidos_colaborador.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        colaborador_id = kwargs.get("colaborador_id", None).split(".")[0]

        # DATA DO RELATORIO DE DISTRIBUICAO
        if str(kwargs["data_inicio"]) is not None:
            start_date = kwargs["data_inicio"]
            end_date = kwargs["data_fim"]
        else:
            # Filtragem para Protocolo
            start_date = timezone.now().date() - timedelta(0)
            end_date = timezone.now().date() + timedelta(0)

        # PESQUISAR PELO COLABORADOR
        if int(colaborador_id) == 0:
            protocolos = Livro01Protocolo.objects.filter(
                data_protocolo__range=[start_date, end_date],
                fases_protocolo_id__isnull=True,
            ).order_by("numero_protocolo")

            protocolos_distribuidos = (
                Livro01Protocolo.objects.filtrar_sem_colaborador()
                .filter(
                    data_distribuicao__range=[start_date, end_date],
                    # fases_protocolo_id__isnull=False,
                )
                .order_by("numero_protocolo")
            )
        else:
            protocolos = Livro01Protocolo.objects.filtrar_por_colaborador(
                colaborador_id,
            ).order_by("numero_protocolo")

            protocolos_distribuidos = (
                Livro01Protocolo.objects.filtrar_por_colaborador(colaborador_id)
                .filter(
                    data_distribuicao__range=[start_date, end_date],
                )
                .order_by("numero_protocolo")
            )

        context["protocolos"] = protocolos
        context["protocolos_distribuidos"] = protocolos_distribuidos
        context["hoje"] = timezone.now().date()

        return context


# IMPRIMIR O RELATORIO APENAS DO COLABORADOR DENTRO DA FICHA DELE COM O QUE TEM PARA ELE FAZER


class RelatorioProtocolosDistribuidosTodosTemplateView(TemplateView):
    template_name = "relatorios/relatorio_protocolos_distribuidos_completo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        colaborador_id = kwargs.get("colaborador_id", None).split(".")[0]
        opcao_id = kwargs.get("opcao_id", None).split(".")[0]

        # DATA DO RELATORIO DE DISTRIBUICAO
        if str(kwargs["data_inicio"]) is not None:
            start_date = kwargs["data_inicio"]
            end_date = kwargs["data_fim"]
        else:
            # Filtragem para Protocolo
            start_date = timezone.now().date() - timedelta(0)
            end_date = timezone.now().date() + timedelta(0)

        # PESQUISAR PELO COLABORADOR
        if int(colaborador_id) == 0:
            protocolos = Livro01Protocolo.objects.filter(
                data_protocolo__range=[start_date, end_date],
                fases_protocolo_id__isnull=True,
            ).order_by("numero_protocolo")

            protocolos_distribuidos = Livro01Protocolo.objects.filter(
                data_distribuicao__range=[start_date, end_date],
                fases_protocolo_id__isnull=False,
            ).order_by("numero_protocolo")
        elif str(opcao_id) == "C":
            protocolos = Livro01Protocolo.objects.filter(
                Q(fases_protocolo_colaborador_atual_id=colaborador_id)
                & Q(data_finalizado__isnull=True),
            ).order_by("numero_protocolo")
            protocolos_distribuidos = Livro01Protocolo.objects.filter(
                fases_protocolo_colaborador_atual_id=colaborador_id,
            ).order_by("numero_protocolo")
        else:
            protocolos = Livro01Protocolo.objects.filter(
                (
                    Q(fases_protocolo_colaborador_id=colaborador_id)
                    | Q(colaborador=colaborador_id)
                )
                & Q(data_finalizado__isnull=True),
            ).order_by("numero_protocolo")

            protocolos_distribuidos = Livro01Protocolo.objects.filter(
                data_distribuicao__range=[start_date, end_date],
                fases_protocolo_colaborador_id=colaborador_id,
            ).order_by("numero_protocolo")

        context["colaborador_id"] = colaborador_id

        context["protocolos"] = protocolos
        context["protocolos_distribuidos"] = protocolos_distribuidos
        context["hoje"] = timezone.now().date()

        return context


class ProtocoloChartView(HighChartsView):
    def __init__(
        self,
        start_date_param=None,
        end_date_param=None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.start_date = (
            start_date_param if start_date_param else timezone.now().date()
        )
        self.end_date = end_date_param if end_date_param else timezone.now().date()

    def get_data(self):
        from apps.home.templatetags.home_formatos import mapear_nome_colaborador

        # start_date = kwargs["start_date"]
        # # Obter as datas da query string ou usar o padrão
        # data_entrada_inicio_str = self.request.GET.get("data_entrada_inicio")
        # data_entrada_fim_str = self.request.GET.get("data_entrada_fim")
        # Obtendo os dados como você já fez na sua view
        # start_date = timezone.now().date() - timedelta(0)
        # end_date = timezone.now().date() + timedelta(0)

        protocolos_distribuidos = (
            Livro01Protocolo.objects.filter(
                data_distribuicao__range=[self.start_date, self.end_date],
                fases_protocolo_id__isnull=False,
            )
            .order_by("numero_protocolo")
            .select_related("fases_protocolo_colaborador")
        )

        # Utilizando annotate e values para obter o nome do colaborador diretamente
        distribuido_detail = (
            protocolos_distribuidos.values(
                nome_colaborador=F("fases_protocolo_colaborador__nome"),
            )
            .annotate(quantidade=Count("fases_protocolo_colaborador"))
            .order_by()
        )

        # Preparando os dados para o gráfico
        colaboradores = [
            mapear_nome_colaborador(item["nome_colaborador"])
            for item in distribuido_detail
        ]
        quantidades = [item["quantidade"] for item in distribuido_detail]

        return {
            "labels": colaboradores,
            "datasets": [
                {
                    "label": "Quantidade de Protocolo por Colaborador",
                    "data": quantidades,
                },
            ],
        }


@login_required(login_url="/login/")
def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return redirect(reverse("admin:index"))
        context["segment"] = load_template

        html_template = loader.get_template(load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template("page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception:
        html_template = loader.get_template("page-500.html")
        return HttpResponse(html_template.render(context, request))


# VISUALIZAR O ARQUIVO PDF
def visualizar_pdf(request, opcao_pasta, numero, arquivo):
    filename = ""

    # VERIFICAR PASTA DE NOTA DE DEVOLUCAO
    if opcao_pasta == "D":
        filename = (
            Configuracao.obter("diretorio_ged_nota_devolucao") + numero + "/" + arquivo
        )
    # VERIFICAR PASTA DE NOTA DE DEVOLUCAO
    elif opcao_pasta == "P":
        # filename = Configuracao.obter("diretorio_ged_protocolos") + numero + "//" + arquivo
        filename = arquivo

    if filename != "":
        # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = Path(settings.BASE_DIR) / filename

        try:
            with open(file_path, "rb") as file:
                arquivo = file.read()
        except FileNotFoundError:
            # Tratar o caso em que o arquivo não é encontrado
            return HttpResponseNotFound("Arquivo não encontrado")

        mime_type, _ = mimetypes.guess_type(file_path)
        response = HttpResponse(arquivo, content_type=mime_type)
        response["Content-Disposition"] = "inline; filename=" + os.path.basename(
            file_path,
        )

        # return JsonResponse({"url": response})
        return response
    return None


def view_pdf(request, filename):
    if filename != "":
        # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = Path(settings.BASE_DIR) / filename

        try:
            with open(file_path, "rb") as file:
                path = file
        except FileNotFoundError:
            # Tratar o caso em que o arquivo não é encontrado
            return HttpResponseNotFound("Arquivo não encontrado")

        mime_type, _ = mimetypes.guess_type(file_path)
        response = HttpResponse(path, content_type=mime_type)
        response["Content-Disposition"] = "inline; filename=" + os.path.basename(
            file_path,
        )

        # return JsonResponse({"url": response})
        return response
    return None


def gravar_emolumentos(emolumento):
    from apps.pedidos.models import TipoEmolumento as PedidosEmolumento

    pk = UUIDPrimaryKeyField().generate_uuid()

    # EMOLUMENTOS
    pedido_emolumento, created = PedidosEmolumento.objects.get_or_create(
        id=pk,
        defaults={
            "home_emolumento_id": emolumento["CHAVE_EMOLUMENTOS"],
            "tipo_emolumento_isento_id": pk,
            "nome": emolumento["DESCRICAO"],
            "descricao": emolumento["DESCRICAO"],
        },
    )

    if not created:
        print("Não criado")
    else:
        print("Criado")


# def gravar_emolumentos_itens(id, emolumento_item):
#     from apps.home.services.firebird import firebird_get_todos_emolumento
#     from apps.pedidos.models import Tabela
#     from apps.pedidos.models import TipoEmolumento as PedidosEmolumento

#     codigo_tabela = "4701"

#     # GRAVAR ITEM VALOR VINDO DO FIREBIRD
#     # emolumento_valor = EmolumentoValor.objects.all()
#     emolumento_ano = Tabela.objects.all().last()
#     emolumento_item_firebird = firebird_get_todos_emolumento(codigo_tabela)

#     # EI.EMOLUMENTO, EI.VALOR, EI.ADIC_EMOLUMENTO, EI.CHAVE_EMOLUMENTOS_ITENS, TAXA1

#     # GERA LISTA PARA GRAVAR
#     for _item_valor in emolumento_item:
#         pedido_emolumento, created = PedidosEmolumento.objects.get_or_create(
#             id=emolumento_item["CHAVE_EMOLUMENTOS_ITENS"],
#             defaults={
#                 "faixa_valor_inicio": emolumento_item_firebird["VL_INICIO"],
#                 "faixa_valor_fim": emolumento_item_firebird["VL_FIM"],
#                 "codigo": emolumento_item_firebird["CODIGO_TABELA"],
#                 "valor": emolumento_item_firebird["VALOR_EMOLUMENTO"],
#                 "tabela_id": emolumento_ano.id,
#                 "tipo_emolumento_id": emolumento_item_firebird["CHAVE_EMOLUMENTOS"],
#             },
#         )


def check_value_limits(value, max_value=VALOR_MAXIMO):
    if value and value > max_value:
        return max_value
    return value or 0


# Gerar as tarefas para a AGENDA COLABORADOR
@login_required
def importar_emolumentos_itens(request):
    from apps.home.services import sqlserver
    from apps.pedidos.models import Emolumento, Tabela, TipoEmolumento

    with transaction.atomic():
        try:
            with firebird.FbConnection() as db:
                query = " SELECT INICIO, DESCRICAO, FIM, CHAVE_VIGOR FROM EMOLUMENTOS_VIGOR "
                vigencia_dos_emolumentos = db.execute_query(query)

            logger.info("EMOLUMENTOS VIGOR: Anos ")
        except Exception:
            logger.exception("ERRO na vigencia_dos_emolumentos")
            raise

        try:
            with firebird.FbConnection() as db:
                query = " SELECT CHAVE_EMOLUMENTOS, NOME, TIPO, ANOVIGOR, DESCONTO, UTILIZADO FROM EMOLUMENTOS "
                emolumentos = db.execute_query(query)

            logger.info("EMOLUMENTOS: ")
        except Exception:
            logger.exception("ERRO no list_emolumentos")
            raise

        try:
            with firebird.FbConnection() as db:
                query = """
                            SELECT VL_INICIO, VL_FIM, EMOLUMENTO, VALOR, ADIC_EMOLUMENTO, CODIGO_TABELA, CHAVE_EMOLUMENTOS_ITENS, CHAVE_EMOLUMENTOS, CHAVE_VIGOR, TAXA1
                            FROM EMOLUMENTOS_ITENS
                            WHERE CHAVE_VIGOR = (SELECT MAX(CHAVE_VIGOR) FROM EMOLUMENTOS_VIGOR)
                        """
                list_emolumentos_itens = db.execute_query(query)

            print("EMOLUMENTOS ITENS: ")
        except Exception:
            logger.exception("ERRO no list_emolumentos_itens")
            raise

        # CRIAR A TABELA DE VIGENCIA
        for vigencia in vigencia_dos_emolumentos:
            pk = UUIDPrimaryKeyField().generate_uuid()

            Tabela.objects.create(
                id=pk,
                id_sistema_antigo=vigencia["CHAVE_VIGOR"],
                data_inicio_validade=vigencia["INICIO"],
                data_fim_validade=vigencia["FIM"],
            )

        # CRIAR A TABELA DE EMOLUMENTOS
        for emolumento in emolumentos:
            try:
                obj = TipoEmolumento.objects.create(
                    nome=emolumento["NOME"],
                    descricao=emolumento["NOME"],
                    home_emolumento_id=emolumento["CHAVE_EMOLUMENTOS"],
                )

                logger.info(f"Salvando {obj}")
            except Exception as e:
                logger.exception(
                    f"Erro ao inserir {emolumento['NOME']}, {emolumento['CHAVE_EMOLUMENTOS']}{e}",
                )
                raise

        # IMPORTAR APENAS SE A TABELA ESTIVER VAZIA
        if True:
            for emolumento_itens in list_emolumentos_itens:
                try:
                    tabela, _ = Tabela.objects.get_or_create(
                        id_sistema_antigo=emolumento_itens["CHAVE_VIGOR"],
                    )
                except MultipleObjectsReturned:
                    tabela = Tabela.objects.filter(
                        id_sistema_antigo=emolumento_itens["CHAVE_VIGOR"],
                    ).first()

                try:
                    from apps.home.models import Emolumentos as HomeEmolumento

                    home_emolumento, _ = HomeEmolumento.objects.get_or_create(
                        pk=emolumento_itens["CHAVE_EMOLUMENTOS"],
                    )

                    tipo_emolumento, _ = TipoEmolumento.objects.get_or_create(
                        home_emolumento_id=home_emolumento.pk,
                    )
                except MultipleObjectsReturned:
                    tipo_emolumento = TipoEmolumento.objects.filter(
                        home_emolumento_id=home_emolumento.pk,
                    ).first()

                emolumento_itens["EMOLUMENTO"] = check_value_limits(
                    emolumento_itens["EMOLUMENTO"],
                )
                emolumento_itens["VL_INICIO"] = check_value_limits(
                    emolumento_itens["VL_INICIO"],
                )
                emolumento_itens["VL_FIM"] = check_value_limits(
                    emolumento_itens["VL_FIM"],
                )
                emolumento_itens["VALOR"] = check_value_limits(
                    emolumento_itens["VALOR"],
                )

                try:
                    obj = Emolumento.objects.create(
                        valor=emolumento_itens["EMOLUMENTO"],
                        codigo=emolumento_itens["CODIGO_TABELA"],
                        faixa_valor_inicio=emolumento_itens["VL_INICIO"] or 0,
                        faixa_valor_fim=emolumento_itens["VL_FIM"] or VALOR_MAXIMO,
                        taxa_fiscal_judiciaria=emolumento_itens["VALOR"] or 0,
                        fundo1_valor=emolumento_itens["ADIC_EMOLUMENTO"] or 0,
                        issqn_percentual=emolumento_itens["TAXA1"] or 0,
                        tipo_emolumento_id=tipo_emolumento.pk,
                        tabela=tabela,
                        fundo1_descricao="",
                        fundo1_tipo_valor="",
                        fundo2_nome="",
                        fundo2_valor=0,
                        fundo2_tipo_valor=0,
                    )

                    logger.info(f"Salvando Item: {obj}")
                except Exception as e:
                    logger.exception(
                        f"Erro ao inserir {emolumento_itens['VALOR']}, {emolumento_itens['CODIGO_TABELA']}{e}",
                    )
                    raise

        # VERIFICAR EMOLUMENTOS ITENS DO SQL SERVER
        if request.user.cartorio.usar_selo_sql_server == "S":
            emolumentos = Emolumento.objects.all()

            for emolumento_item in emolumentos:
                codigo = emolumento_item.codigo
                id_principal = emolumento_item.id

                print(
                    "Pesquisar codigo do emolumento a atualizar vindo do SQL SERVER:",
                    codigo,
                    id_principal,
                )

                with sqlserver.SqlServerConnection() as db:
                    # EMOLUMENTOS NO SQL SERVER TAXAS
                    valor_recompe, valor_issqn = get_valores_taxas(db, sqlserver)

                    # COMANDO PARA PEGAR OS EMOLUMENTOS ITENS
                    comando = get_comando_emolumentos_itens()
                    comando = str(comando).replace(":codigo_emolumento", codigo[:4])

                    # EMOLUMENTOS NO SQL SERVER ATUALIZAR
                    emolumentos_sqlserver = sqlserver.selecionar_emolumentos_sql_server(
                        db,
                        comando,
                    )

                    for emolumento_sqlserver in emolumentos_sqlserver:
                        # Atualizar valor no PRIME
                        atualizar_valores_prime(
                            id_principal,
                            emolumento_sqlserver["VALOR_EMOLUMENTO"],
                            emolumento_sqlserver["VALOR_TAXA_JUDICIARIA"],
                            emolumento_sqlserver["VALOR_EMOLUMENTO"] * valor_recompe,
                        )

        return redirect(reverse("home:calender"))


# EMOLUMENTOS NO SQL SERVER TAXAS
def get_valores_taxas(db, sqlserver):
    comando = get_comando_emolumentos_taxas()

    # CONECTAR AO SQL SERVER
    emolumentos_taxas_sqlserver = sqlserver.selecionar_emolumentos_sql_server(
        db,
        comando,
    )

    # Dicionário para armazenar os valores
    valores = {"RECOMPE": None, "ISSQN": None}

    # Itera uma única vez para preencher o dicionário
    for emolumento_sqlserver in emolumentos_taxas_sqlserver:
        nome = emolumento_sqlserver["NOME"]
        if nome in valores:
            valores[nome] = emolumento_sqlserver["VALOR"]

    # Acessa os valores
    return valores["RECOMPE"], valores["ISSQN"]


def get_comando_emolumentos_taxas():
    return """
                    SELECT NOME, VALOR
                    FROM EMOLUMENTOS_TAXAS
                """


def get_comando_emolumentos_itens():
    return """
                    SELECT E.DESCRICAO, EI.*
                    FROM EMOLUMENTOS_ITENS EI, EMOLUMENTOS E
                    WHERE EI.CHAVE_EMOLUMENTOS = E.CHAVE_EMOLUMENTOS
                    AND   EI.CODIGO_EMOLUMENTO = :codigo_emolumento
                    AND   EI.CHAVE_EMOLUMENTOS_VIGOR = (SELECT MAX(CHAVE_EMOLUMENTOS_VIGOR) FROM EMOLUMENTOS_VIGOR)
                """


# Atualizar valor no PRIME
def atualizar_valores_prime(
    id_principal,
    valor_emolumento,
    valor_tfj,
    valor_emolumento_liquido,
):
    from apps.pedidos.models import Emolumento
    from apps.pedidos.utils import arredondar_decimal_bancario

    # CALCULAR REMCOMPE
    valor_emolumento_liquido = arredondar_decimal_bancario(valor_emolumento_liquido)
    valor_emolumento = valor_emolumento - valor_emolumento_liquido

    # Atualizar valor no PRIME
    emolumento_atualizar = Emolumento.objects.get(id=id_principal)
    emolumento_atualizar.valor = valor_emolumento
    emolumento_atualizar.taxa_fiscal_judiciaria = valor_tfj
    emolumento_atualizar.fundo1_valor = valor_emolumento_liquido
    emolumento_atualizar.save()


# Gerar as tarefas para a AGENDA COLABORADOR
def tarefas_agenda(request):
    # TRABALHANDO

    print("Encerrado. Gerando os eventos")

    return redirect(reverse("home:calender"))


# Gerar tarefa na Agenda
def tarefa_pronto_registrar(
    request,
    colaborador_id,
    protocolo_id,
    data_andamento=None,
    dias_uteis=1,
    titulo="",
    texto_titulo="",
) -> None:
    # Gravar_Evento na AGENDA DO COLABORADOR - AUTOMATICO
    pass


# # Listar protocolos distribuidos
# def tarefa_protocolo_distribuido(request, dias_relatorio=1, numero_ordem_id=0) -> None:
#     pass


# Gerar eventos de reentrada
def tarefa_protocolo_reentrada(protocolo_id, numero_id, origem) -> None:
    pass


# Obter a data de entrada dos protocolos
def tarefa_protocolo_nota_devolucao_anexada(
    request,
    protocolo_id,
    caption_titulo,
    caption_descricao,
) -> None:
    pass


# Gerar tarefa na Agenda
def tarefa_protocolo_qualificar(
    request,
    colaborador_id,
    protocolo_id,
    dias_qualificar,
    data_entrada=None,
) -> None:
    pass


# Atraves da string de resposta localizar a pergunta no banco de dados
def localicar_tabela_resposta(perguntas_respondidas, resposta):
    # PEGANDO A TABELA ORIGEM DA RESPOSTA
    tabela = str(perguntas_respondidas).split("_")

    # Pegaando o último elemento da lista resultante que e o ID da Tabela
    tabela_id = tabela[-1]

    # Removendo o último elemento da lista resultante
    tabela = tabela[:-1]  # Isso cria uma nova lista sem o último ite

    # Concatenando os elementos da lista em uma string, separados por underscore
    tabela = "_".join(tabela)

    # Inicializando as variáveis
    resposta, pergunta, observacao, impeditivo = "", "", "", ""

    if tabela == "checklist_balcao_ato":
        resultado = (
            ChecklistBalcaoAto.objects.filter(
                id=resposta,
                checklist_balcao_id=tabela_id,
            )
            .values_list("texto_escolha", "observacao", "impeditivo")
            .first()
        )

        resposta, observacao, impeditivo = (
            resultado if resultado else (None, None, None)
        )
    elif tabela == "checklist_balcao_ato_texto":
        resultado = (
            ChecklistBalcaoAtoTexto.objects.filter(id=resposta)
            .values_list("texto_escolha", "observacao", "impeditivo")
            .first()
        )
        resposta, observacao, impeditivo = (
            resultado if resultado else (None, None, None)
        )

    pergunta = (
        ChecklistBalcao.objects.filter(id=tabela_id)
        .values_list("text", flat=True)
        .first()
    )

    # Obter a resposta
    return pergunta, resposta, observacao, impeditivo


# RETORNA A LISTA COM AS QUESTOES DO CHECKLIST
def get_questions(classe_imovel="U", ato_id=0, lista_titulo_informacao=None):
    # TODAS AS PERGUNTAS DA CLASSE IMOVEL
    if lista_titulo_informacao is None:
        lista_titulo_informacao = ["N", "S"]
    lista_tipo_do_imovel = ["T", classe_imovel] if classe_imovel else []

    # PERGUNTAS
    return (
        ChecklistBalcao.objects.filter(
            Q(atos_id=ato_id)
            & Q(tipo_do_imovel__in=lista_tipo_do_imovel)
            & Q(titulo_informacao__in=lista_titulo_informacao),
        )
        # .values_list("text", flat=True)
        .order_by("ordem")
    )


# CHECKLIST BALCAO APRESENTAR NA TELA
def checklist_balcao_view(request, numero_protocolo=0, classe_imovel="U", ato_id=0):
    from apps.home.forms import QuestionForm

    form = QuestionForm(request.POST if request.method == "POST" else None)
    descricao_ato = (
        AtoPratica.objects.filter(id=ato_id).values_list("tipo_ato", flat=True).first()
    )

    if request.method in ("POST", "GET"):
        if request.method == "POST":
            selected_options = [
                (key, value)
                for key, value in request.POST.items()
                if key != "csrfmiddlewaretoken"
            ]
            (
                quantidade_nao_respondida,
                perguntas_nao_respondidas,
                questions_respondidas_lista,
            ) = salvar_checklist_balcao(
                request,
                selected_options,
                classe_imovel,
                ato_id,
            )

            if quantidade_nao_respondida > 0:
                context = {
                    "questions": perguntas_nao_respondidas,
                    "quantidade": quantidade_nao_respondida,
                    "descricao_ato": descricao_ato,
                    "numero_protocolo": numero_protocolo,
                }
                return render(request, "checklist_balcao_nao_respondida.html", context)
            else:
                return render(
                    request,
                    "checklist_balcao_respondida.html",
                    {
                        "questions": questions_respondidas_lista,
                        "descricao_ato": descricao_ato,
                        "numero_protocolo": numero_protocolo,
                    },
                )

        questions = get_questions(classe_imovel, ato_id, ["N", "S"])
        lista_opcoes = {
            item["id"]: item
            for item in ChecklistBalcaoAtoTexto.objects.values(
                "id",
                "texto_escolha",
                "checklist_balcao_ato_id",
            )
        }
        context = {
            "form": form,
            "questions": questions,
            "lista_opcoes": lista_opcoes,
            "descricao_ato": descricao_ato,
            "numero_protocolo": numero_protocolo,
        }
        return render(request, "checklist_balcao.html", context)

    # Tratamento para caso o formulário não seja válido (se aplicável)
    return render(
        request,
        "checklist_balcao.html",
        {
            "form": form,
            "descricao_ato": descricao_ato,
            "numero_protocolo": numero_protocolo,
        },
    )


# salvar O CHECKLIST APOS A RESPOSTA SER GRAVADA
def salvar_checklist_balcao(
    request,
    selected_options_respondidas,
    classe_imovel="U",
    ato_id=0,
):
    # Carregando as perguntas uma única vez e de forma eficiente
    questions = get_questions(classe_imovel, ato_id, ["N"])
    questions_text_set = {objeto.text for objeto in questions}

    # Utilizando dict comprehension para mapear respostas diretamente, eliminando a necessidade de duas listas
    questions_respondidas_dict = {
        item[0]: {
            "pergunta": resultado[0],
            "resposta": resultado[1],
            "observacao": resultado[2],
            "impeditivo": resultado[3],
        }
        for item in selected_options_respondidas
        if str(item[1]).isdigit()
        for resultado in [
            localicar_tabela_resposta(item[0], item[1]),
        ]  # Chama a função uma vez por item
    }

    # Usando sets para calcular perguntas não respondidas de forma eficiente
    perguntas_respondidas_set = {
        valor["pergunta"] for valor in questions_respondidas_dict.values()
    }
    perguntas_nao_respondidas = sorted(questions_text_set - perguntas_respondidas_set)

    return (
        len(perguntas_nao_respondidas),
        perguntas_nao_respondidas,
        questions_respondidas_dict,
    )


class ProtocoloAndamentosListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    template_name = "andamentos/andamentos_list.html"
    model = Livro01Andamento
    table_class = ProtocoloAndamentosTable
    filterset_class = filters.ProtocoloAndamentosFilter

    def get_context_data(self, **kwargs):
        """Sobrescreve o método get_context_data para adicionar o protocolo_id ao contexto."""
        context = super().get_context_data(**kwargs)
        protocolo_id = self.kwargs.get("protocolo_id")
        protocolo = Livro01Protocolo.objects.filter(pk=protocolo_id).first()

        # verificar se os andamentos estao sincronizados com sistema antigo
        if protocolo:
            protocolo.verificar_andamentos_sistema_antigo()

        context.update(
            {
                "protocolo": protocolo,
                "title": "Andamentos do Protocolo",
                "segment": "andamentos_list",
                "parent": "livro01",
            },
        )
        return context

    def get(self, request, *args, **kwargs):
        if "export" in request.GET:
            table = ProtocoloAndamentosTableExport(self.get_queryset())
            return exportar_table(table)
        return super().get(request, *args, **kwargs)


def anexo_create(request, protocolo_pk):
    # Busca o protocolo pelo seu 'pk'. Se não encontrar, retorna um erro 404.
    protocolo = Livro01Protocolo.objects.filter(pk=protocolo_pk).first()
    if not protocolo:
        return JsonResponse(
            {"error": f"Protocolo {protocolo_pk} não encontrado."},
            status=404,
        )

    content_type = ContentType.objects.get_for_model(protocolo)

    # Se o método for POST, processa os dados do formulário
    if request.method == "POST":
        form = forms.AnexoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.content_type = content_type
            anexo.object_id = protocolo.pk
            anexo.save()
            # Redireciona para a página de detalhes do protocolo ou outra página de sucesso
            return redirect(protocolo.get_absolute_url())
    else:
        # Se não for um método POST, cria um formulário em branco
        form = forms.AnexoForm()

    # Renderiza o template com o formulário
    return render(
        request,
        "anexos/anexo_create.html",
        {"form": form, "protocolo": protocolo},
    )


@require_POST
@csrf_exempt
def file_upload_view(request, protocolo_pk):
    try:
        protocolo = Livro01Protocolo.objects.filter(pk=protocolo_pk).first()
        if not protocolo:
            logging.warning(f"Protocolo {protocolo_pk} não encontrado.")
            return JsonResponse(
                {"error": f"Protocolo {protocolo_pk} não encontrado."},
                status=404,
            )

        content_type = ContentType.objects.get_for_model(protocolo)
        errors = []
        for file in request.FILES.getlist("arquivo"):
            anexo = Anexo(
                content_type=content_type,
                object_id=protocolo.pk,
                nome=file.name,
                arquivo=file,
            )
            if request.user.is_authenticated:
                anexo.uploaded_by = request.user

            try:
                anexo.save()
                logging.info(
                    f"Arquivo {file.name} salvo com sucesso para o protocolo {protocolo_pk}.",
                )
                # Verifica se o arquivo foi salvo corretamente
                if not anexo.arquivo:
                    errors.append(f"Falha ao salvar o arquivo {file.name}")
            except ValueError as e:
                logging.exception(f"Erro ao salvar o arquivo {file.name}: {e}")
                errors.append(str(e))

        if errors:
            return JsonResponse({"errors": errors}, status=400)
        else:
            return JsonResponse({"message": "Arquivos enviados com sucesso."})
    except Exception as e:
        logging.exception(f"Erro inesperado no upload do arquivo: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_POST
@csrf_exempt
def file_upload_view_por_numero_protocolo(
    request,
    numero_protocolo: int,
) -> JsonResponse:
    """
    Processa o upload de arquivos com base no número de protocolo.
    Se o protocolo não existir, tenta importá-lo.
    Se o protocolo ainda assim não for encontrado, retorna um erro 404.
    Se encontrado, redireciona para a view de upload de arquivo.
    """
    try:
        protocolo = Livro01Protocolo.objects.filter(
            numero_protocolo=numero_protocolo,
        ).first()
        if not protocolo:
            logging.info(
                f"Protocolo {numero_protocolo} não encontrado no banco de dados local. Tentando importar.",
            )
            with firebird.FbConnection() as db:
                db.begin_transaction()
                try:
                    protocolo, _ = firebird.importar_protocolo_por_numero_fb(
                        numero_protocolo,
                        tipo_importacao=None,
                        db=db,
                    )
                    db.commit()
                    logging.info(f"Protocolo {numero_protocolo} importado com sucesso.")
                except Exception as e:
                    db.rollback()
                    logging.exception(
                        f"Erro ao importar protocolo {numero_protocolo}: {e}",
                    )
                    return JsonResponse({"error": str(e)}, status=500)

        if not protocolo:
            logging.warning(
                f"Protocolo {numero_protocolo} não encontrado após tentativa de importação.",
            )
            return JsonResponse({"error": "Protocolo não encontrado."}, status=404)

        return file_upload_view(request, protocolo.pk)
    except Exception as e:
        logging.exception(
            f"Erro inesperado no processamento do upload por número de protocolo: {e}",
        )
        return JsonResponse({"error": str(e)}, status=500)


def anexo_update(request, protocolo_pk, anexo_pk):
    # Busca o protocolo pelo seu 'pk'. Se não encontrar, retorna um erro 404.
    protocolo = get_object_or_404(Livro01Protocolo, pk=protocolo_pk)

    # Busca o anexo pelo seu 'pk'. Se não encontrar, retorna um erro 404.
    anexo = get_object_or_404(Anexo, pk=anexo_pk)

    # Se o método for POST, processa os dados do formulário
    if request.method == "POST":
        form = forms.AnexoUpdateForm(request.POST, instance=anexo)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.save()
            # Redireciona para a página de detalhes do protocolo ou outra página de sucesso
            return redirect("home:protocolo_detail", pk=protocolo_pk)

    else:
        # Se não for um método POST, cria um formulário preenchido com os dados do anexo
        form = forms.AnexoUpdateForm(instance=anexo)

    # Renderiza o template com o formulário
    return render(
        request,
        "anexos/anexo_update.html",
        {"form": form, "protocolo": protocolo, "anexo": anexo},
    )


@login_required
def protected_media(request, file_path):
    logging.debug(f"file_path: {file_path}")
    # Caminho completo para o arquivo dentro de MEDIA_ROOT
    full_file_path = Path(settings.MEDIA_ROOT) / file_path

    # Verifique se o arquivo existe
    if not os.path.exists(full_file_path):
        msg = "O arquivo não existe."
        raise Http404(msg)

    # Abra o arquivo para leitura em modo binário
    with open(full_file_path, "rb") as f:
        file_content = f.read()

    # Determine o tipo de conteúdo do arquivo (pode ser necessário ajustar isso com base no tipo do arquivo)
    content_type = "application/pdf"

    # Crie uma resposta com o conteúdo do arquivo
    response = HttpResponse(content=file_content, content_type=content_type)
    response["Content-Disposition"] = (
        f'attachment; filename="{os.path.basename(file_path)}"'
    )

    return response


def buscar_protocolo(protocolo_pk: int) -> Livro01Protocolo:
    """Busca o protocolo pelo seu 'pk'. Se não encontrar, retorna None."""
    return Livro01Protocolo.objects.filter(pk=protocolo_pk).first()


def buscar_anexos(protocolo: Livro01Protocolo) -> list:
    """Busca os anexos relacionados ao protocolo."""
    return Anexo.objects.filter(
        content_type=ContentType.objects.get_for_model(protocolo),
        object_id=protocolo.pk,
    )


def listar_arquivos_do_protocolo_no_diretorio(
    anexos_dir: str,
    numero_protocolo: str,
) -> list[str]:
    """
    Lista todos os arquivos no diretório especificado cujo nome contém o número do protocolo,
    retornando seus caminhos completos.

    Args:
    ----
        anexos_dir (str): O diretório onde os anexos estão armazenados.
        numero_protocolo (str): O número do protocolo, para possíveis filtragens.

    Returns:
    -------
        list[str]: Lista de caminhos completos dos arquivos.

    """
    try:
        arquivos = []
        for root, _, files in os.walk(anexos_dir):
            for file in files:
                if numero_protocolo in file:
                    arquivos.append(os.path.join(root, file))
        return arquivos
    except Exception:
        logger.exception(f"Erro ao listar arquivos no diretório: {anexos_dir}")
        return []


def obter_diretorio_anexos(protocolo_numero: str) -> str:
    """
    Obtém o diretório onde os anexos estão armazenados.

    :param protocolo_numero: Número do protocolo
    :return: Caminho do diretório dos anexos
    """
    diretorio_base = Configuracao.obter(
        "diretorio_ged_protocolos",
        os.path.join(settings.MEDIA_ROOT, "anexos/protocolos/"),
    )
    return os.path.join(diretorio_base, str(protocolo_numero)[:3])


def buscar_imagens_protocolo(protocolo_numero: str) -> list[str]:
    """
    Busca todas as imagens de um protocolo específico conforme a estrutura de diretórios.

    :param protocolo_numero: Número do protocolo (6 dígitos)
    :return: Lista de caminhos das imagens encontradas
    """
    # Obtém o diretório base dos anexos
    diretorio_anexos = obter_diretorio_anexos(protocolo_numero)

    # Lista para armazenar os caminhos dos arquivos encontrados
    caminhos_arquivos = []

    # Caminho completo do diretório onde os arquivos estão armazenados
    caminho_diretorio_protocolo = os.path.join(diretorio_anexos, protocolo_numero)

    # Verifica se o diretório existe
    if not os.path.exists(caminho_diretorio_protocolo):
        return caminhos_arquivos

    # Itera sobre os arquivos no diretório
    for arquivo in os.listdir(caminho_diretorio_protocolo):
        if arquivo.startswith(protocolo_numero) and (arquivo.endswith(("F", "V"))):
            caminhos_arquivos.append(os.path.join(caminho_diretorio_protocolo, arquivo))

    return caminhos_arquivos


class Livro01ProtocoloAnexosListView(ListView):
    model = Anexo
    template_name = "anexos/anexos_list.html"
    context_object_name = "anexos"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        protocolo_pk = self.kwargs.get("protocolo_pk")
        protocolo = get_object_or_404(Livro01Protocolo, pk=protocolo_pk)

        anexos_dir = obter_diretorio_anexos(protocolo.numero_protocolo)
        anexos_da_rede = listar_arquivos_do_protocolo_no_diretorio(
            anexos_dir,
            protocolo.numero_protocolo,
        )

        # Substituir as barras invertidas por barras normais
        urls_dos_anexos_da_rede = [
            download_and_save_image(anexo).replace("\\", "/")
            for anexo in anexos_da_rede
        ]

        context.update(
            {
                "protocolo": protocolo,
                "anexos_da_rede": anexos_da_rede,
                "urls_dos_anexos_da_rede": urls_dos_anexos_da_rede,
            },
        )
        return context

    def get_queryset(self):
        protocolo_pk = self.kwargs.get("protocolo_pk")
        protocolo = get_object_or_404(Livro01Protocolo, pk=protocolo_pk)
        return protocolo.anexos.all()


def download_and_save_image(network_path: str) -> str:
    """Copia a imagem a partir de um caminho de rede, converte se necessário, e salva localmente, retornando a URL local."""
    try:
        filename = get_safe_filename(network_path)
        temp_images_dir = os.path.join(settings.MEDIA_ROOT, "temp_images")
        garantir_existencia_diretorio(temp_images_dir)
        filepath = os.path.join(temp_images_dir, filename)

        copiar_e_converter_imagem(network_path, filepath)

        relative_filepath = os.path.relpath(filepath, settings.MEDIA_ROOT)
        return os.path.join(settings.MEDIA_URL, relative_filepath)
    except Exception as e:
        logger.exception(
            f"""Erro ao copiar e salvar a imagem:
            ERRO: {e}:
            Origem: {network_path}
            Detino: {filepath}
            """,
        )
        return None


def get_safe_filename(network_path: str) -> str:
    """Gera um nome de arquivo seguro a partir de um caminho de rede."""
    base_filename = os.path.basename(network_path)
    name = os.path.splitext(base_filename)[0]
    safe_name = slugify(name)
    unique_id = uuid.uuid4().hex
    return f"{safe_name}_{unique_id}.jpg"


def garantir_existencia_diretorio(directory_path: str):
    """Garante que o diretório existe, criando-o se necessário."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def copiar_e_converter_imagem(source_path: str, dest_path: str):
    """Copia a imagem do caminho de origem para o destino, convertendo se necessário."""
    shutil.copy2(source_path, dest_path)
    image = Image.open(dest_path)
    if image.format == "TIFF":
        image = image.convert("RGB")
        image.save(dest_path, format="JPEG")


@login_required
def escolher_certificado(request, andamento_id):
    if request.method == "POST":
        form = forms.EscolherCertificadoForm(request.user, request.POST)
        if form.is_valid():
            certificado_id = form.cleaned_data["certificado"].id
            request.session["motivo_id"] = form.cleaned_data["certificado"].id
            # Redirecionar para a função de assinatura, passando o certificado_id e exigencia_id
            return redirect(
                "home:assinar_andamento",
                andamento_id=andamento_id,
                certificado_id=certificado_id,
            )
    else:
        form = forms.EscolherCertificadoForm(request.user)

    return render(
        request,
        "escolher_certificado.html",
        {"form": form, "andamento_id": andamento_id},
    )


class CertificadoDigitalCreate(CreateView):
    model = CertificadoDigital
    form_class = forms.CertificadoDigitalForm
    template_name = "certificados/certificado_form.html"  # O caminho para o seu template de formulário
    # success_url = reverse_lazy("nome_da_sua_url_para_certificados")  # URL de redirecionamento após o sucesso

    def form_valid(self, form):
        # Este método é chamado quando os dados do formulário são válidos
        certificado_digital = form.save(commit=False)
        senha = form.cleaned_data.get("senha", None)
        if senha:
            certificado_digital.set_senha(senha)
        certificado_digital.save()
        return super().form_valid(form)


class CertificadoDigitalListView(ListView):
    model = CertificadoDigital
    template_name = "certificado_digital/certificado_list.html"  # O caminho para o seu template de listagem
    context_object_name = "certificados"  # Nome do contexto no template
    paginate_by = 10  # Opcional: adicione paginação para lidar com muitos objetos

    def get_queryset(self):
        """
        Permite a customização da query. Por exemplo, você pode querer alterar isso para filtrar
        os certificados por algum critério, como certificados de um usuário específico.

        """
        return CertificadoDigital.objects.all().order_by("-usuario")


class CertificadoDigitalDetailView(DetailView):
    model = CertificadoDigital
    template_name = "certificado_digital/certificado_detail.html"  # O caminho para o seu template de detalhes
    context_object_name = "certificado"  # Nome do contexto no template

    def get_context_data(self, **kwargs):
        """Você pode sobrescrever este método se precisar adicionar mais contexto para o seu template."""
        return super().get_context_data(**kwargs)
        # Adicione mais contexto aqui, se necessário


class AndamentosListView(LoginRequiredMixin, ListView):
    model = Livro01Andamento
    template_name = "andamentos/andamentos_list.html"
    paginate_by = 10
    andamentos_filter = None
    extra_context = {
        "title": "Andamentos do Protocolo",
        "segment": "andamentos_list",
        "parent": "livro01",
    }
    queryset_cache = None  # Cache para armazenar o queryset

    def dispatch(self, request, *args, **kwargs):
        self.andamentos_filter = filters.Livro01AndamentoFilter(
            request.GET,
            queryset=self.get_filtered_queryset(),
        )
        return super().dispatch(request, *args, **kwargs)

    def get_filtered_queryset(self):
        # Usar cache para evitar múltiplas consultas ao banco
        if self.queryset_cache is None:
            today = timezone.now()
            date_30_days_ago = today - timedelta(days=30)
            self.queryset_cache = (
                super().get_queryset().filter(data__range=(date_30_days_ago, today))
            )
        return self.queryset_cache

    def get(self, request, *args, **kwargs):
        if "export" in request.GET:
            print("Livro01Andamento sem valores")
            table = AndamentosTableExport(self.andamentos_filter.qs)
            return exportar_table(table)

        elif "export_andamento_valores" in request.GET:
            print("Livro01Andamento com valores")
            table = AndamentosValoresTableExport(self.andamentos_filter.qs)
            return exportar_table(table)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        andamentos_table = Livro01AndamentoTable(self.andamentos_filter.qs)
        # print("DEBUG: QuerySet final:", self.evento_filter.qs.query)
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(
            andamentos_table,
        )
        context.update(
            {
                "filter": self.andamentos_filter,
                "table": andamentos_table,
            },
        )
        return context

    # def export_to_excel(self):
    #     evento_table = AndamentosTableExport(self.evento_filter.qs)
    #     exporter = TableExport("xlsx", evento_table, exclude_columns=("ação"))
    #     return FileResponse(
    #         exporter.export(),
    #         filename="eventos.xlsx",
    #         content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    #     )


# class AndamentosListView(LoginRequiredMixin, ListView):
#     model = Livro01Andamento
#     template_name = "andamentos/andamentos_list.html"
#     paginate_by = 5
#     evento_filter = None

#     def dispatch(self, request, *args, **kwargs):
#         self.evento_filter = Livro01AndamentoFilter(request.GET, queryset=self.get_queryset())
#         return super().dispatch(request, *args, **kwargs)

#     def get_queryset(self):
#         # Obtém o momento atual
#         today = timezone.now()
#         # Calcula a data de 30 dias atrás
#         date_30_days_ago = today - timedelta(days=30)
#         # Chama o método original para obter o QuerySet completo
#         initial_queryset = super().get_queryset()
#         # Filtra pelo intervalo de datas
#         return initial_queryset.filter(data__range=(date_30_days_ago, today))

#     def get(self, request, *args, **kwargs):
#         if "export" in request.GET:
#             return exportar_table(AndamentosTableExport(self.evento_filter.qs))
#         return super().get(request, *args, **kwargs)

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         evento_table = Livro01AndamentoTable(self.evento_filter.qs)
#         RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(evento_table)
#         context.update(
#             {
#                 "filter": self.evento_filter,
#                 "table": evento_table,
#             },
#         )
#         return context

#     def export_to_excel(self):
#         evento_table = AndamentosTableExport(self.evento_filter.qs)
#         exporter = TableExport("xlsx", evento_table, exclude_columns=("ação"))
#         return FileResponse(
#             exporter.export(),
#             filename="eventos.xlsx",
#             content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         )


def andamentos_por_colaborador(request, colaborador_id):
    # Busca o colaborador pelo seu 'id'. Se não encontrar, retorna um erro 404.
    colaborador = get_object_or_404(Colaborador, pk=colaborador_id)

    # Busca os andamentos relacionados ao colaborador
    andamentos = Livro01Andamento.objects.filter(colaborador=colaborador)

    # Renderiza o template com os andamentos
    return render(
        request,
        "andamentos/andamentos_por_colaborador.html",
        {"colaborador": colaborador, "andamentos": andamentos},
    )


@login_required
def importar_protocolos(request):
    return render(request, "importacao/importar_protocolos.html", {})


@login_required
def caixa_verificar_diferenca(request):
    return render(
        request,
        "importacao/importar_protocolos_caixa_verificar_diferenca.html",
        {},
    )


@login_required
def caixa_verificar_diferenca_direto(request, numero_protocolo):
    # Receber o número de protocolo informado
    with transaction.atomic(), firebird.FbConnection() as db:
        try:
            db.begin_transaction()
            firebird.importar_protocolo_por_numero_fb(
                numero_protocolo=numero_protocolo,
                tipo_importacao="P",
                db=db,
            )
            db.commit()

            # # FILTRAR PEDIDO - ORIGINAL - CALCULAR DIFERENCA
            protocolo = Livro01Protocolo.objects.filter(
                numero_protocolo=numero_protocolo,
            ).first()

            valor_diferenca = protocolo.verificar_diferenca_sistema_antigo(db)

            # DATA FICTICIA PARA NAO ATRAPALHAR OS RELATORIOS
            data_pagamento = "2000-01-01"

            # FINALIZAR NO PRIME PARA NAO TER PROBLEMAS ENQUANTO SINCRONIZA O SISTEMA ANTIGO
            financeiro = Financeiro.criar_financeiro_despesa_receita(
                pedido_id=protocolo.pedido.id,
                pedido_certidao_id=None,
                tipo_transacao_id=4,
                tipo_categoria_financeira_id=1,
                tipo_operacao_financeira_id=1,
                colaborador_id=1,
                colaborador_confirmado_id=None,
                data_transacao=data_pagamento,
                data_original_transacao=None,
                valor_transacao=protocolo.valor_diferenca,
                dadp="N",
                imposto_renda="N",
                descricao="FINALIZACAO INTERNA",
                user_id=1,
                quantidade_parcelas=1,
                recorrencia_id=1,
            )
            print(financeiro)

            url = reverse(
                "home:enviar_pedido_de_protocolo_ao_caixa",
                args=[numero_protocolo, valor_diferenca],
            )
            return redirect(url)

        except Exception:
            msg = "Não foi possível importar o protocolo informado"
            logger.exception(msg)


class AndamentosExigenciasListView(LoginRequiredMixin, ListView):
    model = Livro01Andamento
    template_name = "andamentos/andamentos_list.html"
    paginate_by = 10
    extra_context = {
        "segment": "exigencias",
        "parent": "protocolo_e_exame",
        "title": "Exigências",
    }

    def get_queryset(self):
        today = timezone.now()
        date_30_days_ago = today - timedelta(days=30)

        # Obtém o queryset base da classe e aplica o filtro de data e tipo de andamento
        queryset = (
            super()
            .get_queryset()
            .filter(
                data__range=(date_30_days_ago, today),
                tipo_andamento=TipoAndamento.grupos.exigencia().first(),
            )
            .order_by("-data")
        )

        # Aplica o filtro baseado nos parâmetros GET
        self.filter = filters.AndamentosExigenciasFilter(
            self.request.GET,
            queryset=queryset,
        )
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Aqui, self.get_queryset() já retorna o queryset filtrado
        table = AndamentosExigenciasTable(self.get_queryset())
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(
            table,
        )
        context["filter"] = self.filter
        context["table"] = table
        return context

    def render_to_response(self, context, **response_kwargs):
        if "export" in self.request.GET:
            # Aqui usamos self.get_queryset() para garantir que estamos exportando os dados filtrados
            table = AndamentosExigenciasTable(self.get_queryset())
            return exportar_table(table)
        return super().render_to_response(context, **response_kwargs)


class AndamentosRegistradosListView(LoginRequiredMixin, ListView):
    model = Livro01Andamento
    template_name = "andamentos/andamentos_list.html"
    paginate_by = 10
    extra_context = {
        "segment": "registrados",
        "parent": "protocolo_e_exame",
        "title": "Registrados",
    }

    def get_queryset(self):
        today = timezone.now()
        date_30_days_ago = today - timedelta(days=30)

        # Obtém o queryset base da classe e aplica o filtro de data e tipo de andamento
        queryset = (
            super()
            .get_queryset()
            .filter(tipo_andamento=TipoAndamento.grupos.registrado().first())
            .filter(data__range=(date_30_days_ago, today))
            .order_by("-data")
        )

        # Aplica o filtro baseado nos parâmetros GET
        self.filter = filters.AndamentosRegistradosFilter(
            self.request.GET,
            queryset=queryset,
        )
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Aqui, self.get_queryset() já retorna o queryset filtrado
        table = AndamentosRegistradosTable(self.get_queryset())
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(
            table,
        )
        andamentos_filter = filters.AndamentosRegistradosFilter(
            self.request.GET,
            queryset=self.get_queryset(),
        )
        context["filter"] = andamentos_filter
        context["table"] = table

        # Construindo a URL de impressão
        protocolos_ids = list(
            andamentos_filter.qs.values_list("protocolo_id", flat=True),
        )
        base_url = reverse("home:impressao_registrados")
        query_string = urlencode({"protocolo_id": protocolos_ids}, doseq=True)
        impressao_url = f"{base_url}?{query_string}"

        context["impressao_url"] = impressao_url

        return context

    def render_to_response(self, context, **response_kwargs):
        if "export" in self.request.GET:
            # Aqui usamos self.get_queryset() para garantir que estamos exportando os dados filtrados
            table = AndamentosRegistradosTable(self.get_queryset())
            return exportar_table(table)
        return super().render_to_response(context, **response_kwargs)


class AndamentosPrenotadosListView(LoginRequiredMixin, ListView):
    model = Livro01Andamento
    template_name = "andamentos/andamentos_list.html"
    paginate_by = 10
    extra_context = {
        "segment": "prenotados",
        "parent": "protocolo_e_exame",
        "title": "Prenotados",
    }

    def get_queryset(self):
        today = timezone.now()
        date_30_days_ago = today - timedelta(days=5)

        # Obtém o queryset base da classe e aplica o filtro de data e tipo de andamento
        queryset = (
            super()
            .get_queryset()
            .filter(tipo_andamento=TipoAndamento.grupos.get_recepcao().first())
            .filter(data__range=(date_30_days_ago, today))
            .order_by("-data")
        )

        # Aplica o filtro baseado nos parâmetros GET
        self.filter = filters.AndamentosPrenotadosFilter(
            self.request.GET,
            queryset=queryset,
        )
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Aqui, self.get_queryset() já retorna o queryset filtrado
        table = AndamentosPrenotadosTable(self.get_queryset())
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(
            table,
        )
        andamentos_filter = filters.AndamentosPrenotadosFilter(
            self.request.GET,
            queryset=self.get_queryset(),
        )

        context["filter"] = andamentos_filter
        context["table"] = table

        # Construindo a URL de impressão
        protocolos_ids = list(
            andamentos_filter.qs.values_list("protocolo_id", flat=True),
        )
        base_url = reverse("home:impressao_prenotados")
        query_string = urlencode({"protocolo_id": protocolos_ids}, doseq=True)
        impressao_url = f"{base_url}?{query_string}"

        # print(impressao_url)

        context["impressao_url"] = impressao_url

        return context

    def render_to_response(self, context, **response_kwargs):
        if "export" in self.request.GET:
            # Aqui usamos self.get_queryset() para garantir que estamos exportando os dados filtrados
            table = AndamentosPrenotadosTable(self.get_queryset())
            return exportar_table(table)
        return super().render_to_response(context, **response_kwargs)


class DocumentoAssinarView(FormView):
    template_name = "modelo_form.html"
    form_class = forms.AssinarDocumentoForm
    success_url = reverse_lazy(
        "documento_list",
    )  # Substitua pelo nome da URL para a lista de documentos

    def form_valid(self, form):
        documento = form.cleaned_data["documento"]
        certificado_path = form.cleaned_data["certificado_path"]
        senha = form.cleaned_data["senha"]
        assinatura = services.assinar_documento(
            documento.conteudo,
            certificado_path,
            senha,
        )
        documento.assinatura = assinatura
        documento.save()
        messages.success(self.request, "Documento assinado .")
        return super().form_valid(form)


class DocumentoVerificarAssinaturaView(LoginRequiredMixin, FormView):
    template_name = (
        "modelo_form.html"  # Adapte para um template específico se necessário
    )
    form_class = forms.VerificarAssinaturaForm
    success_url = reverse_lazy(
        "documento_list",
    )  # Substitua pelo nome da URL para a lista de documentos

    def form_valid(self, form):
        documento = form.cleaned_data["documento"]
        certificado_publico_path = form.cleaned_data["certificado_publico_path"]
        assinatura_verificada = services.verificar_assinatura(
            documento.conteudo,
            documento.assinatura,
            certificado_publico_path,
        )
        if assinatura_verificada:
            messages.success(self.request, "A assinatura do documento é válida.")
        else:
            messages.error(self.request, "A assinatura do documento não é válida.")
        return super().form_valid(form)


def exportar_table(table, filename="export.xlsx", exclude_columns: tuple = ()):
    """
    Exporta os dados de uma tabela do Django-Tables2 para um arquivo Excel (XLSX), excluindo colunas específicas e
    limpando qualquer HTML dos valores das células.

    :param table: Instância da tabela a ser exportada.
    :param filename: Nome do arquivo que será exportado.
    :param exclude_columns: Tupla com os nomes das colunas a serem excluídas da exportação.
    :return: Resposta HTTP com o arquivo Excel para download.
    """
    # Adiciona as colunas padrão que devem ser excluídas
    exclude_columns = set(exclude_columns).union(
        {"acoes", "opções", "ação", "ações", "opcoes"},
    )

    # Filtra as colunas que não devem ser excluídas e que têm um accessor válido
    colunas_para_exportar = [
        col
        for col in table.columns
        if col.name not in exclude_columns
        and not isinstance(col, tables.TemplateColumn)
        and col.accessor
    ]

    # Cria um workbook e uma sheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Exportação"

    # Escreve o cabeçalho com base nas colunas filtradas
    sheet.append([col.header for col in colunas_para_exportar])

    # Escreve os dados do queryset associado à tabela
    for obj in table.data:
        linha = []
        for col in colunas_para_exportar:
            try:
                valor = col.accessor.resolve(obj)
            except ValueError:
                valor = None  # Se o accessor falhar, define como None
            linha.append(valor)
        sheet.append(linha)

    # Configura a resposta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    workbook.save(response)

    return response


def limpar_html(texto):
    """
    Remove todas as tags HTML de um texto, se o texto for uma string.

    :param texto: String possivelmente contendo HTML.
    :return: String sem HTML ou o valor original se não for string.
    """
    if isinstance(texto, str):
        # Remove todas as tags HTML usando BeautifulSoup
        texto_limpo = BeautifulSoup(texto, "html.parser").get_text()
        return texto_limpo.strip()
    return texto


class Livro04ListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = Livro04
    context_object_name = "Livro04_list"
    template_name = "livro04/livro04_list.html"
    table_class = Livro04Table
    filterset_class = filters.Livro04Filter
    paginate_by = 10
    extra_context = {"segment": "livro04", "parent": "livros"}

    # def get_queryset(self):
    #     queryset = super().get_queryset().order_by("-data_abertura")
    #     self.filter = Livro04Filter(self.request.GET, queryset=queryset)
    #     return self.filter.qs

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     table = Livro04Table(self.get_queryset())
    #     RequestConfig(self.request).configure(table)
    #     context["filter"] = self.filter
    #     context["table"] = table
    #     return context

    def render_to_response(self, context, **response_kwargs):
        if "export" in self.request.GET:
            return exportar_table(context["table"])
        return super().render_to_response(context, **response_kwargs)


class ProtocolosDistribuidosPorColaboradorListView(ListView):
    model = Livro01Protocolo
    template_name = "distribuicao_protocolo_por_colaborador.html"
    context_object_name = "protocolos"

    def dispatch(self, *args, **kwargs):
        self.colaborador = get_object_or_404(
            Colaborador,
            pk=self.kwargs.get("colaborador_id"),
        )
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        # Utiliza o colaborador buscado no dispatch
        return Livro01Protocolo.objects.filter(
            fases_protocolo_colaborador_atual=self.colaborador,
            data_finalizado__isnull=True,
        ).order_by("numero_protocolo")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Reutiliza o colaborador do dispatch
        context.update(
            {
                "colaborador_id": self.kwargs.get("colaborador_id"),
                "colaborador": self.colaborador,
                "protocolos_com_reentrada": Livro01Protocolo.objects.filtrar_com_reentrada_por_colaborador(
                    self.colaborador.pk,
                ),
                "protocolos_sem_reentrada": Livro01Protocolo.objects.filtrar_sem_reentrada_por_colaborador(
                    self.colaborador.pk,
                ),
                "protocolos_distribuidos": Livro01Protocolo.objects.get_protocolos_distribuidos_pelo_colaborador(
                    self.colaborador.pk,
                ),
                "distribuido_detail": [],
                "data_inicio": timezone.now().replace(hour=0, minute=0, second=0),
                "data_fim": timezone.now().replace(hour=23, minute=59, second=59),
            },
        )

        return context


class AndamentoCreateView(LoginRequiredMixin, FormView):
    template_name = "andamentos/andamentos_form.html"
    form_class = forms.AndamentoCreateForm
    context_object_name = "andamento"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        protocolo = self.get_protocolo()
        print(
            "Protocolo:",
            protocolo,
        )  # Debug: Verificar se o protocolo está sendo carregado corretamente
        kwargs["user"] = self.request.user
        kwargs["protocolo"] = protocolo
        print("Form kwargs:", kwargs)  # Imprime os kwargs antes de enviar ao formulário
        return kwargs

    def form_valid(self, form):
        andamento = self.prepare_andamento(form)
        self.try_to_save_andamento(andamento)
        return super().form_valid(form)

    def prepare_andamento(self, form):
        """Prepara o objeto andamento antes de salvar."""
        protocolo = self.get_protocolo()
        andamento = form.save(commit=False)
        andamento.protocolo = protocolo
        andamento.colaborador = Colaborador.get_ou_criar_pelo_usuario(
            self.request.user,
        )
        return andamento

    def get_protocolo(self):
        """Retorna o objeto Protocolo verificado pelo id."""
        protocolo_id = self.kwargs["protocolo_id"]
        protocolo = get_object_or_404(Livro01Protocolo, pk=protocolo_id)
        print(
            "Carregando protocolo com ID:",
            protocolo_id,
        )  # Debug: Verificar se o ID está correto
        return protocolo

    def try_to_save_andamento(self, andamento: Livro01Andamento):
        """Tenta salvar o andamento, ajustando a sequência se necessário."""
        try:
            andamento.save()
            andamento.protocolo.atualizar_status_pelo_andamento(
                andamento_id=andamento.pk,
            )
        except IntegrityError:
            ajustar_sequence("home_livro01andamento", "home_livro01andamento_id_seq")
            andamento.save()

    def get_success_url(self):
        return reverse(
            "home:protocolo_andamentos",
            kwargs={"protocolo_id": self.kwargs["protocolo_id"]},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        protocolo_id = self.kwargs["protocolo_id"]
        context["protocolo"] = get_object_or_404(Livro01Protocolo, pk=protocolo_id)
        context["modelos_de_texto"] = Livro01Andamento.get_modelos_de_texto()
        return context


# Colaborador Confirmar Recebimento de Protocolo
class ConfirmarRecebimentoProtocoloView(LoginRequiredMixin, View):
    def get(self, request, protocolo_id, colaborador_id, opcao_recebimento):
        referer_url = request.META.get(
            "HTTP_REFERER",
            reverse(
                "home:distribuidos_por_colaborador",
                kwargs={"colaborador_id": colaborador_id},
            ),
        )

        with transaction.atomic(), firebird.FbConnection() as db:
            try:
                protocolo = Livro01Protocolo.objects.get(pk=protocolo_id)

                servico_recebido = TipoAndamento.get_recebido()
                if not servico_recebido:
                    messages.error(
                        request,
                        "Andamento de serviço recebido não encontrado.",
                    )
                    return redirect(referer_url)

                db.begin_transaction()
                protocolo_id_firebird = firebird.criar_andamento_fb(
                    pedido_id=protocolo.pedido_id,
                    colaborador_id=request.user.pk,
                    tipo_andamento_id=servico_recebido.pk,
                    colaborador_encaminhado_id=request.user.pk,
                    db=db,
                )

                andamentos_fb = firebird.get_andamentos_do_protocolo_no_fb(
                    protocolo_id=protocolo_id_firebird,
                    db=db,
                )

                if andamentos_fb:
                    protocolo.criar_andamentos_obtidos_do_fb(andamentos_fb, db)

                db.commit()
                messages.success(
                    request,
                    f"Protocolo {protocolo} recebido com sucesso.",
                )
            except Exception:
                db.rollback()
                msg = f"Erro ao confirmar recebimento do protocolo {protocolo_id} {colaborador_id}"
                messages.error(request, msg)
                logger.exception(msg)
                raise

            return redirect(referer_url)


class AndamentoDetailView(LoginRequiredMixin, DetailView):
    model = Livro01Andamento
    template_name = "andamentos/andamento_detail.html"
    context_object_name = "andamento"


class AndamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Livro01Andamento
    form_class = forms.AndamentoUpdateForm
    template_name = "andamentos/andamentos_form.html"
    extra_context = {
        "segment": "andamentos",
        "parent": "protocolo_e_exame",
        "title": "Editar Andamento",
    }

    # def get_success_url(self):
    #     return reverse("home:protocolo_andamentos", kwargs={"pk": self.object.protocolo.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modelos_de_texto"] = Livro01Andamento.get_modelos_de_texto()
        return context


class AndamentoTextoPrintView(LoginRequiredMixin, TemplateView):
    template_name = "andamentos/andamento_print.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        andamento = get_object_or_404(Livro01Andamento, pk=self.kwargs.get("pk"))
        context["andamento"] = andamento
        context["now"] = timezone.now()
        return context


class PedidoCertidaoAndamentoTextoPrintView(LoginRequiredMixin, TemplateView):
    template_name = "certidoes/pedido_certidao_andamento_print.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        andamento = get_object_or_404(PedidoCertidaoAndamento, pk=self.kwargs.get("pk"))

        # VERIFICAR SE O MODELO DE TEXTO TEM UM CARIMBO DIFERENTE
        nome_cabecalho, nome_rodape = None, None
        if andamento.modelo_id is not None and andamento.modelo.nome_cabecalho:
            self.template_name = (
                "certidoes/pedido_certidao_andamento_print_cabecalho_informado.html"
            )
            nome_cabecalho = (
                "certidoes/" + str(andamento.modelo.nome_cabecalho) + ".html"
            )
            nome_rodape = "certidoes/" + str(andamento.modelo.nome_rodape) + ".html"

        # VERIFICAR A QUANTIDADE SELOS
        quantidade_selos = (
            andamento.pedido.selo_sqlserver
            if self.request.user.cartorio.usar_selo_sql_server == "S"
            else []
        )

        context["nome_rodape"] = nome_rodape
        context["nome_cabecalho"] = nome_cabecalho
        context["quantidade_selos"] = quantidade_selos
        context["andamento"] = andamento
        context["now"] = timezone.now()
        context["user"] = self.request.user
        return context


# class PedidoCertidaoAndamentoTextoImovelPrintView(LoginRequiredMixin, TemplateView):
#     template_name = "certidoes/pedido_certidao_andamento_imovel_print.html"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         andamento = get_object_or_404(PedidoCertidaoAndamento, pk=self.kwargs.get("pk"))
#         context["andamento"] = andamento
#         context["now"] = timezone.now()
#         return context


# VERIFICAR SE O PEDIDO JA EXISTE
def pedido_certidao_andamento_texto_gerar_certidao_pessoa(request, pk):
    # VERIFICAR SE EXISTE ANDAMENTO DE PESSOA VINCULADA A ALGUMA CERTIDAO
    try:
        certidao = Certidao.objects.select_related("imovel", "pessoa").get(pk=pk)
    except Certidao.DoesNotExist:
        certidao = None

    if certidao:
        if certidao.imovel:
            pessoa_imovel = PedidoCertidaoImovel.objects.get(id=certidao.imovel.id)
        elif certidao.pessoa:
            pessoa_imovel = PedidoCertidaoPessoa.objects.get(id=certidao.pessoa.id)
        else:
            pessoa_imovel = None
    else:
        pessoa_imovel = None

    # Editar ou imprimir a certidao
    if pessoa_imovel:
        pedido_andamento = PedidoCertidaoAndamento.objects.filter(
            certidao_id=certidao.id,
        ).first()

        if pedido_andamento:
            print("Cadastrado vinculado ")

            url = reverse(
                "home:pedido_certidao_andamento_texto_print",
                kwargs={"pk": pedido_andamento.id},
            )
            return redirect(url)
        else:
            print("Não tem cadastrado vinculado a nenhum andamento de certidão pronta")

            pedido = get_object_or_404(PedidoCertidao, pk=pessoa_imovel.pedido.id)
            pedido_certidao_andamento = pedido.registrar_andamento_certidao(certidao)

            url = reverse(
                "home:pedido_certidao_andamento_editar",
                kwargs={"pk": pedido_certidao_andamento.id},
            )
            return redirect(url)

    return HttpResponse("Andamento não encontrado", status=404)


# VERIFICAR SE O PEDIDO JA EXISTE
def pedido_certidao_andamento_texto_gerar_certidao_imovel(request, pk):
    # VERIFICAR SE EXISTE ANDAMENTO DE PESSOA VINCULADA A ALGUMA CERTIDAO
    try:
        certidao = Certidao.objects.select_related("imovel", "pessoa").get(pk=pk)
    except Certidao.DoesNotExist:
        certidao = None

    if certidao:
        if certidao.imovel:
            pessoa_imovel = PedidoCertidaoImovel.objects.get(id=certidao.imovel.id)
        elif certidao.pessoa:
            pessoa_imovel = PedidoCertidaoPessoa.objects.get(id=certidao.pessoa.id)
        else:
            pessoa_imovel = None
    else:
        pessoa_imovel = None

    # Editar ou imprimir a certidao
    if pessoa_imovel:
        pedido_andamento = PedidoCertidaoAndamento.objects.filter(
            certidao_id=certidao.id,
        ).first()

        if pedido_andamento:
            print("Cadastrado vinculado ")

            url = reverse(
                "home:pedido_certidao_andamento_texto_print",
                kwargs={"pk": pedido_andamento.id},
            )
            return redirect(url)
        else:
            print("Não tem cadastrado vinculado a nenhum andamento de certidão pronta")

            pedido = get_object_or_404(PedidoCertidao, pk=pessoa_imovel.pedido.id)
            pedido_certidao_andamento = pedido.registrar_andamento_certidao(certidao)

            # NAO CONSEGUIU CRIAR O ANDAMENTO
            if pedido_certidao_andamento.id is None:
                pedido_certidao_andamento = PedidoCertidao.get_first_andamento(pedido)

            url = reverse(
                "home:pedido_certidao_andamento_editar",
                kwargs={"pk": pedido_certidao_andamento.id},
            )
            return redirect(url)

    return HttpResponse("Andamento não encontrado", status=404)


@login_required
def gerar_e_assinar_exigencia(request, andamento_id, certificado_id):
    from apps.home.utils.assinatura import assinar_pdf

    try:
        certificado_instance = CertificadoDigital.objects.get(id=certificado_id)
        andamento = Livro01Andamento.objects.get(id=andamento_id)
        motivo_id = request.session.get("motivo_id")
        del request.session["motivo_id"]
    except CertificadoDigital.DoesNotExist:
        logger.exception(f"CertificadoDigital com id {certificado_id} não encontrado.")
        return HttpResponse("Certificado não encontrado", status=404)
    except Livro01Andamento.DoesNotExist:
        logger.exception(f"Livro01Andamento com id {andamento_id} não encontrado.")
        return HttpResponse("Andamento não encontrado", status=404)

    # f"Documento criado em {timezone.now().strftime('%d/%m/%y %h:%m:%s')}, por {request.user.name} para assinatura digital"

    certificado_instance.usuario = request.user
    certificado_instance.motivo_uso = MotivoAssinaturaDigital.objects.filter(
        id=motivo_id,
    ).first()

    # Criar o PDF inicial em um arquivo temporário
    temp_pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    base_url = request.build_absolute_uri("/")
    html_content = andamento.texto_html_aprimorado

    with open("output.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    # converter o HTML para PDF
    HTML(filename="output.html", base_url=base_url).write_pdf(target=temp_pdf_file.name)

    # HTML(string=andamento.texto_html_aprimorado, base_url=request.build_absolute_uri()).write_pdf(
    #     target=temp_pdf_file.name,
    # )

    # Assinar o PDF
    pdf_assinado_path = assinar_pdf(temp_pdf_file, certificado_instance)

    # Extrair o nome do arquivo PDF assinado
    nome_arquivo = Path(pdf_assinado_path).name

    # Ler o arquivo PDF assinado
    with open(pdf_assinado_path, "rb") as pdf_assinado_file:
        pdf_assinado = pdf_assinado_file.read()

    # Atualizar o modelo com o arquivo PDF assinado
    andamento.arquivo_assinado.save(
        name=nome_arquivo,
        content=ContentFile(pdf_assinado),
        save=True,
    )

    # Preparar e enviar a resposta com o PDF assinado
    response = HttpResponse(pdf_assinado, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    return response


@login_required
def backup_database(request):
    from apps.home.services import backup

    try:
        backup.realizar_backup_database()
        return HttpResponse("Backup realizado .", content_type="text/plain")
    except ValueError as e:
        return HttpResponse(str(e), status=400)
    except subprocess.CalledProcessError:
        return HttpResponse(
            "Falha ao realizar backup.",
            status=500,
            content_type="text/plain",
        )


# views.py no seu aplicativo
def download_backup_view(request, filename):
    # Certifique-se de validar/limpar o filename para prevenir vulnerabilidades de segurança
    file_path = Path(settings.MEDIA_ROOT) / "backups" / filename

    if Path(file_path).exists:
        with open(file_path, "rb", encoding="utf_8") as f:
            return FileResponse(f, as_attachment=True, filename=filename)
    else:
        msg = "O arquivo não foi encontrado."
        raise Http404(msg)


@login_required
def gerar_pdf_de_htmlfield(request, andamento_id):
    try:
        andamento = Livro01Andamento.objects.get(id=andamento_id)
    except Livro01Andamento.DoesNotExist:
        return HttpResponse("Andamento não encontrado", status=404)

    # Converte o HTML para PDF
    html_content = andamento.texto
    pdf_file = HTML(string=html_content).write_pdf()

    # Cria uma resposta HTTP com o PDF
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="documento.pdf"'

    return response


# RETORNAR AS VARIAVEIS PARA O TEMPLATE DE ANDAMENTO - EXIGENCIA POR EXEMPLO
@login_required
def retonar_variaveis_andamento_pedido_certidao(
    request,
    pedido_certidao_andamento_id,
    modelo_id,
):
    # VINCULANDO O MODELO - ATUALIZANDO OS DADOS NO PROTOCOLO - MINUTAS
    pedido = PedidoCertidaoAndamento.objects.get(pk=pedido_certidao_andamento_id)
    pedido.modelo_id = modelo_id
    pedido.save()

    # ATUALIZANDO OS DADOS NO PROTOCOLO - MINUTAS
    pedido_certidao_id = pedido.pedido_id

    pedido_certidao = PedidoCertidao.objects.get(pk=pedido_certidao_id)
    pedido_pessoa = PedidoCertidaoPessoa.objects.filter(
        pedido_id=pedido_certidao_id,
    ).first()
    pedido_imovel = PedidoCertidaoImovel.objects.filter(
        pedido_id=pedido_certidao_id,
    ).first()

    # VARIAVEIS GERAIS
    protocolo_onr = (
        pedido_certidao.protocolo_onr if pedido_certidao.protocolo_onr else ""
    )
    nome_assina_digital = (
        # User.user_assina_digitalmente_default().fullname
        User.user_assina_digitalmente_default().first_name
        if User.user_assina_digitalmente_default()
        else ""
    )

    # VARIAVEIS DA PESSOA
    (
        nome,
        tipo_documento_pesquisado,
        documento_numero,
        nacionalidade,
        profissao,
        endereco,
        anotacoes,
        descricao_estado_civil,
    ) = (
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    )

    if pedido_pessoa:
        nome = pedido_pessoa.nome if pedido_pessoa.nome else ""

        # TEXTO E CNPJ OU CPF
        if pedido_pessoa.documento:
            documento_numero = get_apenas_numeros(pedido_pessoa.documento)
            tipo_documento_pesquisado = configurar_cpf_cnp_retornar_descricao(
                documento_numero,
            )

            if len(documento_numero) > 11:
                documento_numero = helpers.formatar_cnpj(documento_numero)
            else:
                documento_numero = helpers.formatar_cpf(documento_numero)
        else:
            documento_numero, tipo_documento_pesquisado = "", ""

        nacionalidade = (
            pedido_pessoa.nacionalidade if pedido_pessoa.nacionalidade else "brasileira"
        )
        profissao = (
            pedido_pessoa.profissao
            if pedido_pessoa.profissao
            else "profissão não informada"
        )
        endereco = pedido_pessoa.endereco if pedido_pessoa.endereco else ""
        anotacoes = (
            pedido_pessoa.anotacoes
            if pedido_pessoa.anotacoes
            else str(
                "nesta cidade de "
                + str(request.user.cartorio.municipio)
                + " - "
                + str(request.user.cartorio.municipio.uf.sigla),
            )
        )

        if pedido_pessoa.estado_civil:
            descricao_estado_civil = str(
                pedido_pessoa.estado_civil.descricao_estado_civil,
            ).lower()
        else:
            descricao_estado_civil = ""

    # VARIAVEIS DO IMOVEL
    (
        imovel_numero_registro,
        imovel_tipo_registro,
        imovel_cartorio,
        imovel_livro,
        imovel_descricao,
        imovel_tipo_imovel,
        imovel_anotacoes,
    ) = (
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    )
    if pedido_imovel:
        imovel_numero_registro = helpers.formatar_protocolo(
            pedido_imovel.numero_registro,
        )
        imovel_tipo_registro = pedido_imovel.tipo_registro
        imovel_cartorio = pedido_imovel.cartorio
        imovel_livro = pedido_imovel.livro
        imovel_descricao = pedido_imovel.descricao
        imovel_tipo_imovel = pedido_imovel.tipo_imovel
        imovel_anotacoes = pedido_imovel.anotacoes

    # Obter o pedido de certidao e tratar os valores de exemplo para substituir
    return {
        "numero_registro": str(imovel_numero_registro) or "",
        "tipo_registro": str(imovel_tipo_registro) or "",
        "cartorio": str(imovel_cartorio) or "",
        "livro": str(imovel_livro) or "",
        "descricao": str(imovel_descricao) or "",
        "tipo_imovel": str(imovel_tipo_imovel) or "",
        "anotacoes": str(imovel_anotacoes) or "",
        "cidade": str(request.user.cartorio.municipio),
        "estado": str(request.user.cartorio.estado),
        "data_hoje": helpers.Agora.extenso(),
        "nome_oficial": str(request.user.cartorio.responsavel),
        "protocolo_onr": str(protocolo_onr)[:18],
        "nome_pesquisado": str(nome) or "",
        "cpf_nome_pesquisado": str(documento_numero) or "",
        "tipo_documento_pesquisado": str(tipo_documento_pesquisado) or "",
        "nacionalidade_nome_pesquisado": str(nacionalidade) or "",
        "profissao_nome_pesquisado": str(profissao) or "",
        "estado_civil_nome_pesquisado": str(descricao_estado_civil) or "",
        "endereco_nome_pesquisado": str(anotacoes) or "",
        "endereco_imovel_pesquisado": str(endereco) or "",
        "nome_oficial_assina_eletronicamente": str(nome_assina_digital or ""),
        "valor_emolumento": str(
            helpers.real_br_money_mask(pedido_certidao.total_emolumentos_pedido),
        ),
        "valor_issqn": str(
            helpers.real_br_money_mask(pedido_certidao.total_issqn_pedido),
        ),
        "valor_tfj": str(
            helpers.real_br_money_mask(
                pedido_certidao.total_taxa_fiscal_judiciaria_pedido,
            ),
        ),
        "valor_recompe": str(
            helpers.real_br_money_mask(pedido_certidao.total_recompe_pedido),
        ),
        "valor_total": str(helpers.real_br_money_mask(pedido_certidao.total_pedido)),
    }


# RETORNAR AS VARIAVEIS PARA O TEMPLATE DE ANDAMENTO - EXIGENCIA POR EXEMPLO
@login_required
def retonar_variaveis_andamento(request, protocolo_id):
    from apps.comum.utils import formatar_moeda

    # ATUALIZANDO OS DADOS NO PROTOCOLO - MINUTAS
    protocolo: Livro01Protocolo = Livro01Protocolo.objects.get(pk=protocolo_id)

    # Convertendo diretamente para um conjunto e depois para string
    # titulos_principais_str = ", ".join({item.titulo.tipo_titulo for item in protocolo.titulos_principais})
    titulos_principais_str = protocolo.atos_principais_descritos_agrupados()

    with firebird.FbConnection() as db:
        vigencia_id = str(firebird.get_vigencia_atual_firebird(db))

        # BUSCANDO O CODIGO DA CERTIDAO POS REGISTRO
        valor_certidao = services.get_cod_certidao_pos_registro()
        codigo_tabela_pos_registro = valor_certidao.tipo_certidao.codigo
        certidao_id_sistema_antigo = (
            valor_certidao.tipo_certidao.certidao_id_sistema_antigo
        )

        # PEGANDO O VALOR QUE DEVER SER PAGO PELO CLIENTE
        valor_certidao_pos_registro = (
            firebird.get_valores_certidao_fb_2(
                vigencia_id=vigencia_id,
                codigo_tabela=codigo_tabela_pos_registro,
                categoria_id="1",
                certidao_id_sistema_antigo=certidao_id_sistema_antigo,
                db=db,
            )["valor_total"]
            or 0
        )

    # Gerar o valor para nova prenotacao
    valor_prenotacao = protocolo.valor_prenotacao_mg or 0

    # VALOR TOTAL PROTOCOLO, SEM PRENOTACAO E COM CERTIDAO DE POS REGISTRO
    valor_total_pagar_sem_prenotacao_e_com_certidao = formatar_moeda(
        protocolo.valor_total_protocolo
        - valor_prenotacao
        + valor_certidao_pos_registro,
    )
    valor_total_extenso = helpers.valor_por_extenso(
        protocolo.valor_total_protocolo
        - valor_prenotacao
        + valor_certidao_pos_registro,
    )

    # Obter o protocolo e tratar os valores de exemplo para substituir
    return {
        "numero_protocolo": str(protocolo.numero_protocolo_formatado),
        "nome_apresentante": str(protocolo.nome_apresentante),
        "nome_adquirente": str(protocolo.partes_adquirentes),
        "nome_transmitente": str(protocolo.partes_transmitentes),
        "data_protocolo": str(protocolo.data_entrada_protocolo_formatada),
        "titulo_principal": str(titulos_principais_str),
        "data_hoje": helpers.Agora.padrao(),
        "data_hoje_extenso": helpers.Agora.extenso(),
        "data_prevista": str(protocolo.data_prevista_formatada),
        "cidade": str(request.user.cartorio.municipio),
        "estado": str(request.user.cartorio.estado),
        "nome_oficial": str(request.user.cartorio.responsavel),
        "login_atual": str(request.user.first_name),
        "valor_total_pagar_sem_prenotacao_e_com_certidao": str(
            valor_total_pagar_sem_prenotacao_e_com_certidao,
        ),
        "valor_total_extenso": str(valor_total_extenso),
        "observacao": str(protocolo.pedido.observacao),
        "numeros_livro_02": str(protocolo.pedido.itens_de_livro02_numero),
        # "numeros_livro_03": str(protocolo.livro_03),
    }


def get_modelo_texto_conteudo(request, modelo_id: int, protocolo_id: int):
    try:
        modelo = ModeloTexto.objects.get(pk=modelo_id)

        # Obter as variáveis de contexto - ANDAMENTOS E EXIGENCIAS
        contexto = retonar_variaveis_andamento(request, protocolo_id)

        conteudo_renderizado = renderizar_conteudo(modelo.conteudo, contexto)

        return JsonResponse({"conteudo": conteudo_renderizado})
    except ModeloTexto.DoesNotExist:
        return JsonResponse({"error": "Modelo não encontrado"}, status=404)


def modelo_texto_pedido_certidao_view(
    request,
    modelo_id: int,
    pedido_certidao_andamento_id: int,
):
    try:
        modelo = ModeloTexto.objects.get(pk=modelo_id)

        # Obter as variáveis de contexto - ANDAMENTOS E EXIGENCIAS
        contexto = retonar_variaveis_andamento_pedido_certidao(
            request,
            pedido_certidao_andamento_id,
            modelo_id,
        )

        conteudo_renderizado = renderizar_conteudo(modelo.conteudo, contexto)

        return JsonResponse({"conteudo": conteudo_renderizado})
    except ModeloTexto.DoesNotExist:
        return JsonResponse({"error": "Modelo não encontrado"}, status=404)


def renderizar_conteudo(conteudo, contexto):
    template = Template(conteudo)
    contexto = Context(contexto)
    return template.render(contexto)


@login_required
def chat_room(request, room_name):
    return render(request, "chat/chat_room.html", {"room_name": room_name})


@login_required
def list_chat_rooms(request):
    rooms = ChatRoom.objects.all()  # Obter todas as salas de chat
    return render(request, "list_chat_rooms.html", {"rooms": rooms})


@login_required
def online_users(request):
    online_users = User.objects.filter(profile__is_online=True)
    return render(request, "online_users.html", {"online_users": online_users})


def financeiro_abrir_caixa(request) -> None:
    # Obtém a data atual
    hoje = datetime.now().strftime("%Y-%m-%d")

    # Atualiza os registros conforme a condição especificada
    Financeiro.objects.filter(
        Q(data_transacao__gte=hoje),
    ).update(
        colaborador_confirmado=None,
        data_transacao_colaborador_confirmado=None,
    )

    hoje = datetime.now().strftime("%Y-%m-%d")
    colaborador_id = request.user.id

    query_params = urllib.parse.urlencode(
        {
            "data_transacao_inicio": hoje,
            "data_transacao_fim": hoje,
            "colaborador_confirmado": colaborador_id,
        },
    )

    url = f"{reverse('home:financeiro_listar')}?{query_params}"
    return redirect(url)


def financeiro_fechar_caixa(request) -> None:
    # Confirmar o caixa para o usuário logado
    Financeiro.objects.filter(Q(colaborador_confirmado_id__isnull=True)).update(
        colaborador_confirmado=request.user.pk,
        data_transacao_colaborador_confirmado=timezone.now(),
    )
    hoje = datetime.now().strftime("%Y-%m-%d")
    colaborador_id = request.user.id

    query_params = urllib.parse.urlencode(
        {
            "data_transacao_inicio": hoje,
            "data_transacao_fim": hoje,
            "colaborador_confirmado": colaborador_id,
        },
    )

    url = f"{reverse('home:financeiro_listar')}?{query_params}"
    return redirect(url)
    # return HttpResponseRedirect(url)


# VERIFICAR SE EXISTEM DISTRIBUICOES FALTANTES
def atualizar_distribuicao_protocolos() -> None:
    # from django.utils import timezone
    """
    TODOS OS PROTOCOLOS QUE NAO TEM DATA DE DISTRIBUICAO E QUE JA TENHO PESSOA VINCULADA NA DISTRIBUICAO
    DATA DISTRIBUICAO = DATA DO PROTOCOLO.
    """
    # Filtrar os protocolos que atendem às condições especificadas
    # protocolos_a_atualizar = Livro01Protocolo.objects.filter(
    #     numero_protocolo__gte=0,
    #     data_distribuicao__isnull=True,
    #     colaborador_id__isnull=False,
    # )

    # print("Atualizar: QUE NAO TEM DATA DE DISTRIBUICAO")
    # Fazer o update usando F() para se referir ao valor atual do campo no banco de dados
    # if protocolos_a_atualizar:
    #     protocolos_a_atualizar.update(data_distribuicao=F("data_protocolo"))

    """
        TODOS OS PROTOCOLOS QUE TENHA COLABORADOR ATUAL MAS NAO TENHO COLABORADOR INICIAL.
        COLABORADOR INICIAL = COLABORADOR ATUAL
    """
    # Selecionar os protocolos que atendem às condições especificadas
    # protocolos_a_atualizar = Livro01Protocolo.objects.filter(
    #     fases_protocolo_colaborador_id__isnull=True,
    #     colaborador_id__isnull=False,
    #     data_distribuicao__isnull=False,
    # )

    # print("Atualizar: TODOS OS PROTOCOLOS QUE TENHA COLABORADOR ATUAL")
    # Fazer o update, atribuindo o valor de um campo a outro
    # if protocolos_a_atualizar:
    #     protocolos_a_atualizar.update(fases_protocolo_colaborador_id=F("colaborador_id"))

    """ SE TIVER REENTRADA NA DATA ATUAL - A DATA DE DISTRIBUICAO E A DATA DE REENTRADA SERAO A DATA ATUAL
        ATUALIZAR data REENTRADA E data DISTRIBUICAO
    """
    # Criar um queryset para selecionar os IDs dos protocolos que atendem às condições
    #  TipoAndamento.objects.filter(grupo_reentrada="S").values("id")

    # print("Atualizar: ATUALIZAR data REENTRADA E data DISTRIBUICAO")
    # if grupo_reentrada:
    #     protocolos_ids = Livro01Andamento.objects.filter(
    #         data__gte=timezone.now().date(),  # Assumindo que 'data' é comparável com a data atual
    #         tipo_andamento_id__in=grupo_reentrada,
    #     ).values("protocolo_id")

    #     if protocolos_a_atualizar:
    #         # Filtrar os protocolos cujos IDs estão na lista da subconsulta
    #         protocolos_a_atualizar = Livro01Protocolo.objects.filter(id__in=Subquery(protocolos_ids))

    #         # Atualizar os campos data_distribuicao e data_reentrada para a data atual
    #         protocolos_a_atualizar.update(data_distribuicao=timezone.now().date(), data_reentrada=timezone.now().date())

    """ VERIFICAR SE EXISTE ALGUMA DATA DE REENTRADA QUE NAO TENHA SIDO INFORMADA A DATA ATUAL
        ATUALIZAR data REENTRADA E data DISTRIBUICAO
    """

    # Filtrar os protocolos cujos ids estão na subconsulta e data_reentrada é nula
    # if grupo_reentrada:

    # USANDO CONSULTAS SEPARADAS
    #     protocolos_ids = Livro01Andamento.objects.filter(
    #         data__gte=timezone.now().date(),
    #         tipo_andamento__grupo_reentrada="S",
    #     ).values("protocolo_id")

    #     protocolos_a_atualizar = Livro01Protocolo.objects.filter(id__in=protocolos_ids) if protocolos_ids else None

    # USANDO RELATED NAME:
    # protocolos_a_atualizar = (
    Livro01Protocolo.objects.get_queryset().filter(
        id__in__andamentos_do_protocolo__tipo_andamento__grupo_reentrada="S",
        andamentos_do_protocolo__data__gte=timezone.now().date(),
    ).distinct().update(data_distribuicao=timezone.now().date())
    # )

    # # Atualizar os campos desejados para a data atual
    # if protocolos_a_atualizar:
    #     protocolos_a_atualizar.update(data_distribuicao=timezone.now().date())

    print("Atualizar: FINALIZADO")


@csrf_exempt
def tts_view(request):
    if request.method == "POST":
        html = request.POST.get("texto", "")
        text = limpar_texto_html(html)  # Supondo a existência dessa função.

        if text.strip() == "":
            return HttpResponse("Texto vazio fornecido.", status=400)

        client = openai.OpenAI()

        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )

            # Assumindo que existe um método para obter o stream binário diretamente
            # Como 'response.get_binary_stream()' ou similar.
            stream = response.get_binary_stream()  # O nome real do método pode variar

            return StreamingHttpResponse(
                streaming_content=stream,
                content_type="audio/mpeg",
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            return HttpResponse(f"Erro no servidor: {e}", status=500)

    return HttpResponse("Método não permitido", status=405)


def limpar_texto_html(texto_html):
    # Analisa o texto HTML usando BeautifulSoup
    soup = BeautifulSoup(texto_html, "html.parser")
    # Extrai o texto sem as tags HTML
    return soup.get_text()


# EXTRAIR ARQUIVO ZIP
def extract_zip_file(request, fs, uploaded_file):
    try:
        if uploaded_file.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
                # Definir o caminho onde você quer extrair os arquivos
                extract_path = fs.location + "\\arquivos_zipados\\"
                zip_ref.extractall(extract_path)

                # Coletar os nomes dos arquivos extraídos
                return zip_ref.namelist()
        else:
            return None
            # return HttpResponse("O arquivo enviado não é um arquivo ZIP.")
    except KeyError:
        return None
        # return HttpResponse("Nenhum arquivo foi enviado.")
    except zipfile.BadZipFile:
        return None
        # return HttpResponse("O arquivo ZIP está corrompido.")
    except Exception:
        logger.exception("ERRO")
        return None
        # return HttpResponse(f"Erro ao extrair o arquivo: {str(e)}")


class FinanceiroListView(LoginRequiredMixin, ExportMixin, SingleTableMixin, FilterView):
    model = Financeiro
    table_class = FinanceiroTable
    template_name = "financeiro/financeiro_list.html"
    filterset_class = filters.FinanceiroFilter
    paginate_by = 20

    def get_export_table(self):
        return FinanceiroTableExport

    def get_export_columns(self):
        if self.request.GET.get("_export"):
            # Retorna as colunas da tabela de exportação
            return FinanceiroTableExport.Meta.fields
        # Caso contrário, retorna as colunas da tabela normal
        return super().get_export_columns()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtém o queryset filtrado
        qs_filtrado = self.filterset_class(
            self.request.GET,
            queryset=self.get_queryset(),
        ).qs

        # Anotação para calcular as somas de diferentes tipos de transações em uma única consulta
        financeiros = Financeiro.calcular_somas(qs_filtrado)

        # Adicionar ao contexto
        context["receitas"] = financeiros["receitas"] or 0
        context["despesas"] = financeiros["despesas"] or 0
        context["saidas"] = financeiros["saidas"] or 0
        context["devolucoes"] = financeiros["devolucoes"] or 0

        return context


@login_required
def event_colaborador_list_view(request):
    try:
        # Aplicando o filtro
        f = EventColaboradorFilter(request.GET, queryset=Event.objects.all())

        # Configurando a tabela
        table = EventColaboradorTable(f.qs)
        RequestConfig(request, paginate={"per_page": 10}).configure(table)

        # Paginação manual (alternativa ao RequestConfig se necessário)
        paginator = Paginator(f.qs, 10)
        page = request.GET.get("page", 1)

        try:
            events = paginator.page(page)
        except PageNotAnInteger:
            logger.warning("Página não é um inteiro, retornando a primeira página.")
            events = paginator.page(1)
        except EmptyPage:
            logger.warning("Página vazia, retornando a última página.")
            events = paginator.page(paginator.num_pages)

        context = {
            "filter": f,
            "table": table,
            "events": events,
        }

        return render(request, "eventos/evento_colaborador_list.html", context)

    except Exception as e:
        logger.exception(
            f"Ocorreu um erro ao processar a lista de eventos: {e!s}",
        )
        return HttpResponseServerError(
            "Ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde.",
        )


@login_required
def financeiro_colaborador_list(request):
    try:
        # Filtrando os dados com base nos parâmetros GET
        filterset = filters.FinanceiroColaboradorFilter(
            request.GET,
            queryset=Financeiro.objects.all(),
        )

        # Aplicando a tabela aos dados filtrados
        table = FinanceiroColaboradorTable(filterset.qs)

        # Configurando a tabela para permitir a exportação e a paginação
        RequestConfig(request, paginate={"per_page": 20}).configure(table)

        context = {"filter": filterset, "table": table}
        template_name = "financeiro/financeiro_colaborador_list.html"

        # Renderizando a página com a tabela e o filtro
        return render(request, template_name, context)

    except SuspiciousOperation as e:
        # Log de operações suspeitas
        logger.warning(f"Operação suspeita detectada: {e}")
        return render(request, "errors/400.html", status=400)

    except Exception as e:
        # Log de qualquer outro erro
        logger.exception(
            f"Erro inesperado ao listar financeiro colaborador: {e}",
        )
        return render(request, "errors/500.html", status=500)


@login_required
def financeiro_transacao_detalhes(request, pk: int) -> HttpResponse:
    try:
        # Obter o objeto Financeiro com o ID (pk) especificado ou retornar 404 se não existir
        financeiro = get_object_or_404(Financeiro, pk=pk)

        # Obter o tempo atual
        agora = timezone.now()

        # Criar o contexto com os dados necessários
        context = {
            "financeiro": financeiro,
            "agora": agora,
            "pedido": financeiro.pedido,
            "titulo": "Recibo de Pagamento",
        }

        # Log de sucesso ao acessar os detalhes da transação
        logger.info(
            f"Usuário {request.user.username} acessou os detalhes da transação {pk} com sucesso.",
        )

        # Renderizar o template com o contexto fornecido
        return render(request, "financeiro/financeiro_detail.html", context)

    except Financeiro.DoesNotExist:
        # Log do erro de objeto não encontrado
        logger.exception(
            f"Transação {pk} não encontrada pelo usuário {request.user.username}.",
        )

        # Mensagem de erro para o usuário
        messages.error(
            request,
            "Transação não encontrada. Por favor, verifique o ID e tente novamente.",
        )
        return render(request, "financeiro/erro.html")

    except Exception as e:
        # Log de erro geral
        logger.exception(
            f"Erro ao acessar os detalhes da transação {pk} para o usuário {request.user.username}: {e!s}",
        )

        # Mensagem de erro genérico para o usuário
        messages.error(
            request,
            "Ocorreu um erro inesperado ao tentar acessar a transação. Tente novamente mais tarde.",
        )
        return render(request, "financeiro/erro.html")


@login_required
def financeiro_recibo_print(request, pk):
    try:
        # Tenta obter o objeto Financeiro correspondente ao PK (Primary Key)
        financeiro = get_object_or_404(Financeiro, pk=pk)

        # Cria o contexto que será passado para o template
        context = {
            "financeiro": financeiro,
            "agora": timezone.now(),
            "pedido": financeiro.pedido,
            "titulo": "Recibo de Pagamento",
        }

        # Renderiza o template com o contexto
        return render(request, "financeiro/financeiro_recibo_print.html", context)

    except Financeiro.DoesNotExist:
        # Se o objeto não for encontrado, redireciona o usuário e exibe uma mensagem de erro
        messages.error(
            request,
            "Recibo não encontrado. Por favor, verifique o número e tente novamente.",
        )
        return redirect(
            "financeiro_list",
        )  # Substitua 'financeiro_list' pela URL de listagem apropriada

    except Exception as e:
        # Trata qualquer outro erro inesperado
        messages.error(request, f"Ocorreu um erro ao gerar o recibo: {e!s}")
        return redirect(
            "financeiro_list",
        )  # Substitua 'financeiro_list' pela URL de listagem apropriada


# Baixar EXCELL dados
def download_excel_protocolo_onr(
    request,
    origem,
    data_inicio=None,
    data_fim=None,
):
    data_inicio = data_inicio or timezone.now().date()
    data_fim = data_fim or timezone.now().date() + timedelta(1)

    # FORMATAR ORIGEM
    origem = int(origem)

    # PEDIDOS DE CERTIDÃO DE MATRÍCULA VISUALIZADA NO DIA ATUAL
    if origem == 7:
        protocolo = Livro01Protocolo.onr_e_protocolo(
            request,
            data_inicio,
            data_fim,
        )
    else:
        protocolo = Livro01Protocolo.onr_e_protocolo(
            request,
            data_inicio,
            data_fim,
        )

    # content-type of response
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename= "Relatório.xls"'
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Relatório ONR")
    row_num = 0
    xlwt.XFStyle()

    columns = [
        "Número Protocolo",
        "Origem ONR",
        "Apresentante",
        "Entrada",
        "Data Selo",
        "Valor",
    ]

    col_widths = [256 * 15, 256 * 20, 256 * 60, 256 * 12, 256 * 12, 256 * 15]

    # Styles for headers
    header_style = xlwt.XFStyle()
    header_style.font = xlwt.Font()
    header_style.font.bold = True
    header_style.font.colour_index = xlwt.Style.colour_map["white"]
    header_style.alignment = xlwt.Alignment()
    header_style.alignment.horz = xlwt.Alignment.HORZ_CENTER
    header_style.pattern = xlwt.Pattern()
    header_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    header_style.pattern.pattern_fore_colour = xlwt.Style.colour_map[
        "dark_blue"
    ]  # Example color

    # Styles
    alignment_center = xlwt.Alignment()
    alignment_center.horz = xlwt.Alignment.HORZ_CENTER
    font_style_center = xlwt.XFStyle()
    font_style_center.alignment = alignment_center

    alignment_right = xlwt.Alignment()
    alignment_right.horz = xlwt.Alignment.HORZ_RIGHT
    font_style_right = xlwt.XFStyle()
    font_style_right.alignment = alignment_right

    # Currency format
    currency_style = xlwt.XFStyle()
    currency_style.alignment = alignment_right
    currency_style.num_format_str = '"R$" #,##0.00'  # Brazilian Real currency format

    # Create a combined style for sum cell
    sum_style = xlwt.XFStyle()

    # Font
    sum_style.font = xlwt.Font()
    sum_style.font.bold = True
    sum_style.font.colour_index = xlwt.Style.colour_map["white"]

    # Alignment
    sum_style.alignment = xlwt.Alignment()
    sum_style.alignment.horz = xlwt.Alignment.HORZ_RIGHT

    # Background
    sum_style.pattern = xlwt.Pattern()
    sum_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    sum_style.pattern.pattern_fore_colour = xlwt.Style.colour_map["dark_blue"]

    # Currency format
    sum_style.num_format_str = '"R$" #,##0.00'

    font_style_default = xlwt.XFStyle()

    for col_num in range(len(columns)):
        ws.col(col_num).width = col_widths[col_num]
        ws.write(row_num, col_num, columns[col_num], header_style)

    for my_row in protocolo:
        row_num = row_num + 1
        ws.write(row_num, 0, my_row.numero_protocolo, font_style_center)
        ws.write(row_num, 1, my_row.origem_formatada, font_style_center)
        ws.write(row_num, 2, my_row.nome_apresentante, font_style_default)
        ws.write(
            row_num,
            3,
            my_row.data_protocolo.strftime(settings.DATE_FORMAT_STR),
            font_style_center,
        )

        if my_row.data_protocolo is None:
            ws.write(row_num, 4, "", font_style_center)
        else:
            ws.write(
                row_num,
                4,
                my_row.data_protocolo.strftime(settings.DATE_FORMAT_STR),
                font_style_center,
            )
        ws.write(
            row_num,
            5,
            my_row.valor_prenotacao_mg,
            currency_style,
        )

    # Sum formula for the last column
    if row_num > 0:
        ws.write(row_num + 1, 5, xlwt.Formula(f"SUM(F2:F{row_num + 1})"), sum_style)

    wb.save(response)

    return response


class ImpressaoRecibosView(LoginRequiredMixin, TemplateView):
    template_name = "relatorios/protocolos_registrados/multiplos_protocolos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        numero_protocolos = self.request.GET.getlist("numero_protocolo")
        protocolos = Livro01Protocolo.objects.filter(
            numero_protocolo__in=numero_protocolos,
        )

        recibos_data = []
        for pedido in protocolos:
            pedido_data = {
                "pedido": pedido,
                "itens_agrupados": pedido.get_itens_agrupados(),
                "agora": timezone.now(),
                "titulo": Configuracao.obter(
                    "titulo_recibo_protocolo",
                    "COMPROVANTE DE PROTOCOLO",
                ),
            }
            pedido.registrar_impressao_recibo(usuario=self.request.user)
            recibos_data.append(pedido_data)

        context["recibos_data"] = recibos_data
        return context


# RETORNAR DATA COM HORA
def converter_data_com_hora(start_date_str, end_date_str):
    # Converter as strings para objetos datetime.date
    if start_date_str:
        start_date_str = start_date_str.replace("T00:00", "")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        start_date = start_date.replace(hour=0, minute=0, second=0)
    else:
        start_date = timezone.now()
        start_date = start_date.replace(hour=0, minute=0, second=0)

    if end_date_str:
        end_date_str = end_date_str.replace("T00:00", "")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        end_date = end_date.replace(hour=23, minute=59, second=59)
    else:
        end_date = timezone.now()
        end_date = end_date.replace(hour=23, minute=59, second=59)

    # Verificação para garantir que a data de início não seja maior que a data de fim
    if start_date > end_date:
        end_date = start_date.replace(hour=23, minute=59, second=59)

    return start_date, end_date


class ImpressaoRecibosCaixaView(LoginRequiredMixin, TemplateView):
    template_name = "financeiro/relatorio_caixa_diario.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obter as datas como strings
        start_date_str = self.request.GET.get("data_transacao_inicio")
        end_date_str = self.request.GET.get("data_transacao_fim")
        colaborador_id = self.request.GET.get("colaborador")
        tipo_categoria_financeira = self.request.GET.get("tipo_categoria_financeira")

        # RETORNAR DATA COM HORA
        start_date, end_date = converter_data_com_hora(start_date_str, end_date_str)

        # PESQUISAR PELO COLABORADOR - VALOR DIARIO
        financeiro_diario = Financeiro.get_financeiro_diario(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR DESPESAS
        financeiro_total_despesa = Financeiro.get_financeiro_total_despesa(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR DESPESAS
        financeiro_total_receita = Financeiro.get_financeiro_total_receita(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR SAIDAS
        financeiro_total_saidas = Financeiro.get_financeiro_total_saidas(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR TOTAL CAIXA
        financeiro_total_caixa = Financeiro.get_financeiro_total_caixa(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- ABERTURA CAIXA
        financeiro_total_abertura_caixa = (
            Financeiro.get_financeiro_total_abertura_caixa(
                colaborador_id,
                start_date,
                end_date,
                tipo_categoria_financeira,
            )
        )

        # Filtrar os registros - TOTAL AGRUPADO
        (
            financeiro_total_agrupado,
            financeiro_total_agrupado_despesa_saida_grupo1,
            financeiro_total_agrupado_despesa_saida_grupo2,
            financeiro_total_agrupado_despesa_saida_grupo3,
        ) = Financeiro.get_financeiro_total_agrupado(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Defina os tipos de operação financeira que você deseja filtrar
        tipos_operacao_financeira, total_dinheiro_liquido = (
            Financeiro.get_total_dinheiro_liquido(
                financeiro_total_agrupado,
            )
        )

        # Filtrar os registros- VALOR SAIDAS
        financeiro_total_devolucoes_dinheiro = (
            Financeiro.get_financeiro_total_devolucoes_dinheiro(
                colaborador_id,
                start_date,
                end_date,
                tipo_categoria_financeira,
            )
        )

        # Obter o valor da soma
        total_devolucoes_dinheiro = (
            financeiro_total_devolucoes_dinheiro["total_devolucoes_dinheiro"] or 0
        )
        total_saidas = financeiro_total_saidas["total_saidas"] or 0
        total_despesa = financeiro_total_despesa["total_despesa"] or 0
        total_receita = financeiro_total_receita["total_receita"] or 0
        total_caixa = financeiro_total_caixa["total_caixa"] or 0
        total_abertura_caixa = (
            financeiro_total_abertura_caixa["total_abertura_caixa"] or 0
        )

        # Depois, calcule a soma de todos os itens do total_caixa
        total_soma_entrada = financeiro_total_agrupado.aggregate(
            soma_total=Sum("total_caixa"),
        )

        if financeiro_total_agrupado_despesa_saida_grupo1:
            total_soma_saida = financeiro_total_agrupado_despesa_saida_grupo1.aggregate(
                soma_total=Sum("total_caixa"),
            )
            total_saida_grupo1 = total_soma_saida["soma_total"]
        else:
            financeiro_total_agrupado_despesa_saida_grupo1 = []
            total_saida_grupo1 = 0

        if financeiro_total_agrupado_despesa_saida_grupo2:
            total_soma_saida = financeiro_total_agrupado_despesa_saida_grupo2.aggregate(
                soma_total=Sum("total_caixa"),
            )
            total_saida_grupo2 = total_soma_saida["soma_total"]
        else:
            financeiro_total_agrupado_despesa_saida_grupo2 = []
            total_saida_grupo2 = 0

        if financeiro_total_agrupado_despesa_saida_grupo3:
            total_soma_saida = financeiro_total_agrupado_despesa_saida_grupo3.aggregate(
                soma_total=Sum("total_caixa"),
            )
            total_saida_grupo3 = total_soma_saida["soma_total"]
        else:
            financeiro_total_agrupado_despesa_saida_grupo3 = []
            total_saida_grupo3 = 0

        # total_caixa_saida1 = total_soma_entrada["soma_total"] or 0 + total_saida_grupo1
        valor = total_soma_entrada["soma_total"] or 0
        total_caixa_saida1 = valor + total_saida_grupo1

        total_caixa_saida2 = total_saida_grupo2
        total_caixa_saida3 = total_saida_grupo3

        total_receita = total_receita - total_abertura_caixa

        total_caixa = total_caixa - total_abertura_caixa

        # TOTAL DO DINHEIRO
        total_dinheiro_menos_saida = (
            (total_dinheiro_liquido) - (total_despesa) + (total_devolucoes_dinheiro)
        )

        # LISTA DE PEDIDOS DE CERTIDAO NAO CONFIRMADOS NO CAIXA
        lista_pedidos_certidao_nao_confirmados_caixa = (
            Financeiro.get_pedidos_certidao_nao_confirmados_caixa(
                start_date,
                end_date,
            )
        )

        # LISTA DE PEDIDOS DE PROTOCOLO NAO CONFIRMADOS NO CAIXA
        lista_pedidos_protocolo_nao_confirmados_caixa = (
            Financeiro.get_pedidos_protocolo_nao_confirmados_caixa(
                start_date,
                end_date,
            )
        )

        context["lista_pedidos_protocolo_nao_confirmados_caixa"] = (
            lista_pedidos_protocolo_nao_confirmados_caixa
        )
        context["lista_pedidos_certidao_nao_confirmados_caixa"] = (
            lista_pedidos_certidao_nao_confirmados_caixa
        )
        context["total_dinheiro_menos_saida"] = total_dinheiro_menos_saida
        context["tipos_operacao_financeira"] = tipos_operacao_financeira
        context["total_dinheiro_liquido"] = total_dinheiro_liquido
        context["financeiro_diario"] = financeiro_diario
        context["total_abertura_caixa"] = total_abertura_caixa
        context["total_abertura_caixa_total_caixa"] = total_caixa

        context["total_despesa"] = total_despesa
        context["total_saidas"] = total_saidas
        context["total_receita"] = total_receita
        context["total_caixa"] = total_caixa

        context["receitas"] = total_receita
        context["despesas"] = total_despesa
        context["saidas"] = total_saidas
        context["devolucoes"] = total_caixa_saida3

        context["financeiro_total_agrupado"] = financeiro_total_agrupado
        context["financeiro_total_agrupado_despesa_saida_grupo1"] = (
            financeiro_total_agrupado_despesa_saida_grupo1
        )
        context["financeiro_total_agrupado_despesa_saida_grupo2"] = (
            financeiro_total_agrupado_despesa_saida_grupo2
        )
        context["financeiro_total_agrupado_despesa_saida_grupo3"] = (
            financeiro_total_agrupado_despesa_saida_grupo3
        )
        context["soma_total_entrada"] = total_soma_entrada["soma_total"]
        context["soma_total_despesa_saida_grupo1"] = total_saida_grupo1
        context["soma_total_despesa_saida_grupo2"] = total_saida_grupo2
        context["soma_total_despesa_saida_grupo3"] = total_saida_grupo3
        context["total_caixa_saida1"] = total_caixa_saida1
        context["total_caixa_saida2"] = total_caixa_saida2
        context["total_caixa_saida3"] = total_caixa_saida3
        context["start_date"] = start_date
        context["end_date"] = end_date
        context["hoje"] = timezone.now().date()

        return context


class ImpressaoRecibosCaixaColaboradorView(LoginRequiredMixin, TemplateView):
    template_name = "financeiro/relatorio_caixa_diario_colaborador.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obter as datas como strings
        start_date_str = self.request.GET.get("start_date")
        end_date_str = self.request.GET.get("end_date")
        colaborador_id = self.request.user.id
        tipo_categoria_financeira = self.request.GET.get("tipo_categoria_financeira")

        # RETORNAR DATA COM HORA
        start_date, end_date = converter_data_com_hora(start_date_str, end_date_str)

        # PESQUISAR PELO COLABORADOR - VALOR DIARIO
        financeiro_diario = Financeiro.get_financeiro_diario(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR DESPESAS
        financeiro_total_despesa = Financeiro.get_financeiro_total_despesa(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR DESPESAS
        financeiro_total_receita = Financeiro.get_financeiro_total_receita(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR SAIDAS
        financeiro_total_saidas = Financeiro.get_financeiro_total_saidas(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- VALOR TOTAL CAIXA
        financeiro_total_caixa = Financeiro.get_financeiro_total_caixa(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Filtrar os registros- ABERTURA CAIXA
        financeiro_total_abertura_caixa = (
            Financeiro.get_financeiro_total_abertura_caixa(
                colaborador_id,
                start_date,
                end_date,
                tipo_categoria_financeira,
            )
        )

        # Filtrar os registros - TOTAL AGRUPADO
        (
            financeiro_total_agrupado,
            financeiro_total_agrupado_despesa_saida_grupo1,
            financeiro_total_agrupado_despesa_saida_grupo2,
            financeiro_total_agrupado_despesa_saida_grupo3,
        ) = Financeiro.get_financeiro_total_agrupado(
            colaborador_id,
            start_date,
            end_date,
            tipo_categoria_financeira,
        )

        # Defina os tipos de operação financeira que você deseja filtrar
        tipos_operacao_financeira, total_dinheiro_liquido = (
            Financeiro.get_total_dinheiro_liquido(
                financeiro_total_agrupado,
            )
        )

        # Obter o valor da soma
        total_saidas = financeiro_total_saidas["total_saidas"] or 0
        total_despesa = financeiro_total_despesa["total_despesa"] or 0
        total_receita = financeiro_total_receita["total_receita"] or 0
        total_caixa = financeiro_total_caixa["total_caixa"] or 0
        total_abertura_caixa = (
            financeiro_total_abertura_caixa["total_abertura_caixa"] or 0
        )

        context["tipos_operacao_financeira"] = tipos_operacao_financeira
        context["total_dinheiro_liquido"] = total_dinheiro_liquido
        context["financeiro_diario"] = financeiro_diario
        context["total_abertura_caixa"] = total_abertura_caixa
        context["total_abertura_caixa_total_caixa"] = total_caixa
        context["total_despesa"] = total_despesa
        context["total_receita"] = total_receita - total_abertura_caixa
        context["total_saidas"] = total_saidas
        context["total_caixa"] = total_caixa - total_abertura_caixa
        context["financeiro_total_agrupado"] = financeiro_total_agrupado
        context["hoje"] = timezone.now().date()
        context["start_date"] = start_date
        context["end_date"] = end_date

        return context


class ImpressaoProtocolosRegistradosView(LoginRequiredMixin, TemplateView):
    template_name = "relatorios/protocolos_registrados/multiplos_protocolos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        protocolos_ids = self.request.GET.getlist("protocolo_id")
        protocolos = Livro01Protocolo.objects.filter(id__in=protocolos_ids)
        titulo = Configuracao.obter(
            "titulo_relatorios_registrados",
            "RELATORIO DE PROTOCOLOS REGISTRADOS",
        )
        agora = timezone.now()
        relatorios_data = []

        for protocolo in protocolos:
            itens_agrupados = protocolo.get_itens_separados()

            dados = {
                "protocolo": protocolo,
                "itens_agrupados": itens_agrupados,
            }
            protocolo.registrar_impressao_recibo(usuario=self.request.user)
            relatorios_data.append(dados)

        context["relatorios_data"] = relatorios_data
        context["titulo"] = titulo
        context["agora"] = agora

        return context


class ImpressaoReciboProtocoloView(LoginRequiredMixin, TemplateView):
    template_name = "relatorios/protocolos_registrados/recibo_protocolo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        protocolos_ids = self.request.GET.getlist("protocolo_id")
        protocolos = Livro01Protocolo.objects.filter(id__in=protocolos_ids)
        titulo = Configuracao.obter(
            "comprovante_de_protocolo",
            "COMPROVANTE DE PROTOCOLO",
        )
        agora = timezone.now()
        relatorios_data = []

        for protocolo in protocolos:
            itens_agrupados = protocolo.get_itens_separados()

            dados = {
                "protocolo": protocolo,
                "itens_agrupados": itens_agrupados,
            }
            protocolo.registrar_impressao_recibo(usuario=self.request.user)
            relatorios_data.append(dados)

        context["relatorios_data"] = relatorios_data
        context["titulo"] = titulo
        context["agora"] = agora

        return context


class ImpressaoProtocolosPrenotadosView(LoginRequiredMixin, TemplateView):
    template_name = "relatorios/protocolos_registrados/multiplos_protocolos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        protocolos_ids = self.request.GET.getlist("protocolo_id")
        protocolos = Livro01Protocolo.objects.filter(id__in=protocolos_ids)
        titulo = Configuracao.obter(
            "titulo_relatorios_prenotados",
            "RELATORIO DE PROTOCOLOS PRENOTADOS",
        )
        agora = timezone.now()
        relatorios_data = []

        for protocolo in protocolos:
            itens_agrupados = protocolo.get_itens_separados()

            dados = {
                "protocolo": protocolo,
                "itens_agrupados": itens_agrupados,
            }
            protocolo.registrar_impressao_recibo(usuario=self.request.user)
            relatorios_data.append(dados)

        context["relatorios_data"] = relatorios_data
        context["titulo"] = titulo
        context["agora"] = agora

        return context


class ExportarSelosTJMGView(LoginRequiredMixin, View):
    model = SeloEletronico


class SelosListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = SeloEletronico
    table_class = SeloTable
    template_name = "selos/selos_list.html"
    filterset_class = filters.SeloFilter
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-utilizado_em")
        self.filter = filters.SeloFilter(self.request.GET, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filter
        return context

    def get(self, request, *args, **kwargs):
        if "export_xml" in request.GET:
            selos = self.get_queryset()
            codigo_serventia_tjmg = Configuracao.obter("codigo_serventia_tjmg")
            if not codigo_serventia_tjmg:
                messages.error(request, "Código da serventia não configurado.")
                return redirect("home:selos_listar")

            xml_content = SeloEletronico.gerar_xml_tjmg(selos, codigo_serventia_tjmg)
            response = HttpResponse(xml_content, content_type="application/xml")
            response["Content-Disposition"] = 'attachment; filename="selos.xml"'
            return response

        return super().get(request, *args, **kwargs)


@login_required
def abrir_caixa(request):
    if request.method == "POST":
        saldo_inicial = request.POST.get("saldo_inicial")
        if saldo_inicial:
            Caixa.objects.create(
                usuario=request.user,
                saldo_inicial=saldo_inicial,
                saldo_atual=saldo_inicial,
            )
            return redirect(
                "alguma_url_para_redirect",
            )  # Redirecione conforme necessário
    return render(request, "caixa/abrir_caixa.html")  # Nome do template a ser criado


@login_required
def fechar_caixa(request):
    caixa_atual = Caixa.objects.filter(
        usuario=request.user,
        data_fechamento__isnull=True,
    ).first()
    if caixa_atual and request.method == "POST":
        caixa_atual.data_fechamento = now()
        caixa_atual.save()
        return redirect("alguma_url_para_redirect")  # Redirecione conforme necessário
    return render(request, "caixa/fechar_caixa.html")  # Nome do template a ser criado


@login_required
def registrar_transacao(request):
    caixa_atual = Caixa.objects.filter(
        usuario=request.user,
        data_fechamento__isnull=True,
    ).first()
    if caixa_atual and request.method == "POST":
        valor = request.POST.get("valor")
        descricao = request.POST.get("descricao")
        tipo = request.POST.get("tipo")
        if valor and descricao and tipo:
            Transacao.objects.create(
                caixa=caixa_atual,
                valor=valor,
                descricao=descricao,
                tipo=tipo,
            )
            # Atualize o saldo atual do caixa
            if tipo == "entrada":
                caixa_atual.saldo_atual += Decimal(valor)
            else:
                caixa_atual.saldo_atual -= Decimal(valor)
            caixa_atual.save()
            return redirect(
                "alguma_url_para_redirect",
            )  # Redirecione conforme necessário
    return render(
        request,
        "caixa/registrar_transacao.html",
    )  # Nome do template a ser criado


# Listar para enviar
@login_required
def caixa_despesa(request):
    template_name = "form-caixa-despesa.html"

    # Verificar a opção de reentrada - Exibir o caption
    caption = "Lançamento de Despesa"

    if request.method == "POST":
        tipocategoria_id = request.POST.get("tipocategoria_id")
        tipooperacaofinanceira_id = request.POST.get("tipooperacaofinanceira_id")
        colaborador_encaminhado_id = request.POST.get("colaborador_id")
        data_transacao = request.POST.get("data_lancamento")
        request.POST.get("data_original_transacao")
        valor_lancado = request.POST.get("valor_lancado", "0.0")
        dadp_id = request.POST.get("dadp_id")
        imposto_renda_id = request.POST.get("imposto_renda_id")
        descricao = request.POST.get("descricao_id")
        # tipo_transacao_financeira_id = request.POST.get("tipo_transacao_financeira_id")
        quantidade_parcelas = request.POST.get("quantidade_id")
        recorrencia_id = request.POST.get("recorrencia_id")

        valor_lancado = Decimal(valor_lancado.replace(",", ".")) * -1

        # TIPO DE OPERACAO DESPESA
        # tipooperacaofinanceira_id = 102
        tipooperacaofinanceira_id = TipoOperacaoFinanceira.despesa_id()

        # JA ESTA CONFIRMADO
        colaborador_encaminhado_id = (
            request.user.id if str(colaborador_encaminhado_id) == "S" else None
        )

        # GRAVAR CAIXA DESPESA
        financeiro = Financeiro.criar_financeiro_despesa_receita(
            pedido_id=None,
            pedido_certidao_id=None,
            tipo_transacao_id=2,
            tipo_categoria_financeira_id=tipocategoria_id,
            tipo_operacao_financeira_id=tipooperacaofinanceira_id,
            colaborador_id=request.user.id,
            colaborador_confirmado_id=colaborador_encaminhado_id,
            data_transacao=data_transacao,
            data_original_transacao=data_transacao,
            valor_transacao=valor_lancado,
            dadp=dadp_id,
            imposto_renda=imposto_renda_id,
            descricao=descricao,
            quantidade_parcelas=quantidade_parcelas,
            recorrencia_id=recorrencia_id,
            user_id=request.user.id,
        )

        return redirect(financeiro.get_absolute_url())

    # EXIBIR APENAS OS VALORES PARA LANCAR
    if request.method == "GET":
        colaboradores = (
            Colaborador.objects.filtrar_por_pode_receber_protocolos_do_balcao()
        )
        tipo_transacao_financeira = TipoTransacaoFinanceira.objects.all().order_by(
            "descricao",
        )
        tipocategorias = TipoCategoriaFinanceira.objects.all().order_by("descricao")
        tipooperacaofinanceiras = TipoOperacaoFinanceira.objects.all().order_by(
            "descricao",
        )
        financeiro_repetir_lancamentos = FinanceiroPeriodicidade.objects.all().order_by(
            "descricao",
        )

        context = {
            "colaboradores": colaboradores,
            "tipo_transacao_financeira": tipo_transacao_financeira,
            "tipocategorias": tipocategorias,
            "tipooperacaofinanceiras": tipooperacaofinanceiras,
            "financeiro_repetir_lancamentos": financeiro_repetir_lancamentos,
            "data_lancamento": timezone.now().strftime("%Y-%m-%d"),
            "data_original_transacao": timezone.now().strftime("%Y-%m-%d"),
            "caption": caption,
            "valor": 0,
        }

        return render(request, template_name, context)
    return None


@login_required
def caixa_receita(request):
    template_name = "form-caixa-receita.html"

    # Verificar a opção de reentrada - Exibir o caption
    caption = "Lançamento de Receita"

    if request.method == "POST":
        tipocategoria_id = request.POST.get("tipocategoria_id")
        tipooperacaofinanceira_id = request.POST.get("tipooperacaofinanceira_id")
        colaborador_encaminhado_id = request.POST.get("colaborador_id")
        data_transacao = request.POST.get("data_lancamento")
        request.POST.get("data_original_transacao")
        valor_lancado = request.POST.get("valor_lancado", "0.0")
        dadp_id = request.POST.get("dadp_id")
        imposto_renda_id = request.POST.get("imposto_renda_id")
        descricao = request.POST.get("descricao_id")
        protocolo_id = request.POST.get("protocolo_id")
        quantidade_parcelas = request.POST.get("quantidade_id")
        recorrencia_id = request.POST.get("recorrencia_id")

        # Substituir vírgula por ponto
        valor_lancado = valor_lancado.replace(".", "")
        valor_lancado = valor_lancado.replace(",", ".")

        # # Remover pontos de milhar
        # valor_lancado = re.sub(r"\.(?=\d{3}(?:,|$))", "", valor_lancado)

        try:
            valor_lancado = Decimal(valor_lancado)
        except InvalidOperation:
            return HttpResponse("Valor monetário inválido", status=400)

        # JA ESTA CONFIRMADO
        colaborador_encaminhado_id = (
            request.user.id if str(colaborador_encaminhado_id) == "S" else None
        )

        # PROTOCOLO DE ENTRADA = 2          PEDIDO DE CERTIDAO = 3
        pedido_id, pedido_certidao_id = None, None
        if str(tipocategoria_id) == "2":
            protocolo = Livro01Protocolo.objects.filter(
                numero_protocolo=protocolo_id,
            ).first()
            pedido_id = protocolo.pedido_id if protocolo else None
        elif str(tipocategoria_id) == "3":
            pedido_certidao_id = protocolo_id

        # GRAVAR CAIXA RECEITA
        financeiro = Financeiro.criar_financeiro_despesa_receita(
            pedido_id=pedido_id if pedido_id else None,
            pedido_certidao_id=pedido_certidao_id,
            tipo_transacao_id=1,
            tipo_categoria_financeira_id=tipocategoria_id,
            tipo_operacao_financeira_id=tipooperacaofinanceira_id,
            colaborador_id=request.user.id,
            colaborador_confirmado_id=colaborador_encaminhado_id,
            data_transacao=data_transacao,
            data_original_transacao=data_transacao,
            valor_transacao=valor_lancado,
            dadp=dadp_id,
            imposto_renda=imposto_renda_id,
            descricao=descricao,
            quantidade_parcelas=quantidade_parcelas,
            recorrencia_id=recorrencia_id,
            user_id=request.user.id,
        )

        return redirect(financeiro.get_absolute_url())

    # EXIBIR APENAS OS VALORES PARA LANCAR
    if request.method == "GET":
        colaboradores = (
            Colaborador.objects.filtrar_por_pode_receber_protocolos_do_balcao()
        )
        tipo_transacao_financeira = TipoTransacaoFinanceira.objects.all().order_by(
            "descricao",
        )
        tipocategorias = TipoCategoriaFinanceira.objects.all().order_by("descricao")
        tipooperacaofinanceiras = TipoOperacaoFinanceira.objects.all().order_by(
            "descricao",
        )
        financeiro_repetir_lancamentos = FinanceiroPeriodicidade.objects.all().order_by(
            "descricao",
        )

        context = {
            "colaboradores": colaboradores,
            "tipo_transacao_financeira": tipo_transacao_financeira,
            "tipocategorias": tipocategorias,
            "tipooperacaofinanceiras": tipooperacaofinanceiras,
            "financeiro_repetir_lancamentos": financeiro_repetir_lancamentos,
            "data_lancamento": timezone.now().strftime("%Y-%m-%d"),
            "data_original_transacao": timezone.now().strftime("%Y-%m-%d"),
            "caption": caption,
            "valor": 0,
        }

        return render(request, template_name, context)
    return None


@login_required
def caixa_saida(request):
    template_name = "form-caixa-saida.html"

    # Verificar a opção de reentrada - Exibir o caption
    caption = "Lançamento de Saida"

    if request.method == "POST":
        tipocategoria_id = request.POST.get("tipocategoria_id")
        # tipooperacaofinanceira_id = request.POST.get("tipooperacaofinanceira_id")
        colaborador_encaminhado_id = request.POST.get("colaborador_id")
        data_transacao = request.POST.get("data_lancamento")
        data_original_transacao = request.POST.get("data_original_transacao")
        valor_lancado = request.POST.get("valor_lancado", "0.0")
        # request.POST.get("dadp_id")
        # request.POST.get("imposto_renda_id")
        descricao = request.POST.get("descricao_id")
        protocolo_id = request.POST.get("protocolo_id")
        quantidade_parcelas = request.POST.get("quantidade_id")
        recorrencia_id = request.POST.get("recorrencia_id")

        valor_lancado = Decimal(valor_lancado.replace(",", ".")) * -1

        # JA ESTA CONFIRMADO
        colaborador_encaminhado_id = (
            request.user.id if str(colaborador_encaminhado_id) == "S" else None
        )

        # TIPO DE OPERACAO SAIDA
        # tipooperacaofinanceira_id = 101
        tipooperacaofinanceira_id = TipoOperacaoFinanceira.saida_id()

        # PROTOCOLO DE ENTRADA = 2          PEDIDO DE CERTIDAO = 3
        pedido_id, pedido_certidao_id = None, None
        if str(tipocategoria_id) == "2":
            pedido_id = Livro01Protocolo.objects.get(
                numero_protocolo=protocolo_id,
            ).pedido_id
        elif str(tipocategoria_id) == "3":
            pedido_certidao_id = protocolo_id

        # GRAVAR CAIXA RECEITA
        financeiro = Financeiro.criar_financeiro_despesa_receita(
            pedido_id=pedido_id,
            pedido_certidao_id=pedido_certidao_id,
            tipo_transacao_id=4,
            tipo_categoria_financeira_id=tipocategoria_id,
            tipo_operacao_financeira_id=tipooperacaofinanceira_id,
            colaborador_id=request.user.id,
            colaborador_confirmado_id=colaborador_encaminhado_id,
            data_transacao=data_transacao,
            data_original_transacao=data_original_transacao,
            valor_transacao=valor_lancado,
            dadp="N",
            imposto_renda="N",
            descricao=descricao,
            quantidade_parcelas=quantidade_parcelas,
            recorrencia_id=recorrencia_id,
            user_id=request.user.id,
        )

        return redirect(financeiro.get_absolute_url())

    # EXIBIR APENAS OS VALORES PARA LANCAR
    if request.method == "GET":
        colaboradores = (
            Colaborador.objects.filtrar_por_pode_receber_protocolos_do_balcao()
        )
        tipo_transacao_financeira = TipoTransacaoFinanceira.objects.all().order_by(
            "descricao",
        )
        tipocategorias = TipoCategoriaFinanceira.objects.all().order_by("descricao")
        tipooperacaofinanceiras = TipoOperacaoFinanceira.objects.all().order_by(
            "descricao",
        )
        financeiro_repetir_lancamentos = FinanceiroPeriodicidade.objects.all().order_by(
            "descricao",
        )

        context = {
            "colaboradores": colaboradores,
            "tipo_transacao_financeira": tipo_transacao_financeira,
            "tipocategorias": tipocategorias,
            "tipooperacaofinanceiras": tipooperacaofinanceiras,
            "financeiro_repetir_lancamentos": financeiro_repetir_lancamentos,
            "data_lancamento": timezone.now().strftime("%Y-%m-%d"),
            "data_original_transacao": timezone.now().strftime("%Y-%m-%d"),
            "caption": caption,
            "valor": 0,
        }

        return render(request, template_name, context)
    return None


class CaixaUpdate(UpdateView):
    model = Financeiro

    tipo_operacao_financeira = TipoOperacaoFinanceira.objects.all().order_by(
        "descricao",
    )

    fields = [
        "id",
        "descricao",
        "tipo_operacao_financeira",
        "tipo_transacao",
        "tipo_categoria_financeira",
        "data_original_transacao",
        "nome_interessado",
    ]

    template_name = "form-caixa-editar.html"


# def caixa_grafico_view(request):
#     data_inicio = request.GET["data_inicio"]
#     data_fim = request.GET["data_fim"]
#     caixa = Caixa.objects.filter(data_transacao__range=[data_inicio, data_fim])

#     data = {
#         "labels": ["Receitas", "Despesas"],
#         "datasets": [
#             {
#                 "data": [5000, 3000],  # Substitua com os dados reais
#                 "backgroundColor": ["#36A2EB", "#FF6384"],
#             },
#         ],
#     }
#     return JsonResponse(data)


def exportar_xml_selo_digital_mg(request):
    # Obtenha os selos e o código da serventia conforme necessário
    selos = SeloEletronico.objects.get_selo_usados_e_nao_enviado()
    codigo_serventia = Configuracao.obter("codigo_serventia")

    if not selos:
        messages.error(request, "Nenhum selo disponível para exportação.")

    if not codigo_serventia:
        messages.error(request, "Código da serventia não configurado.")

    # Gere o XML
    xml_data = SeloEletronico.gerar_xml_tjmg(selos, codigo_serventia)

    # Crie uma resposta HTTP com o XML
    response = HttpResponse(xml_data, content_type="application/xml")
    response["Content-Disposition"] = "attachment; filename=selos.xml"

    return response


@login_required
def caixa_cancelar(request, pk):
    template_name = "form-caixa-cancelar.html"

    # Verificar a opção de reentrada - Exibir o caption
    caption = "Cancelar o Lançamento no CAIXA:"
    # tipooperacaofinanceiras = TipoOperacaoFinanceira.objects.all().order_by("descricao")

    if request.method == "POST":
        descricao_cancelamento = request.POST.get("descricao_cancelamento_id")
        item = Financeiro.objects.get(pk=pk)

        # ATUALIZAR CAIXA
        financeiro, created = Financeiro.objects.update_or_create(
            pk=item.pk,
            defaults={
                "descricao_cancelado": descricao_cancelamento,
                "data_transacao_cancelado": timezone.now().date(),
                "valor_transacao_cancelado": item.valor_transacao,
                "valor_transacao": 0,
                "ativo": TipoAtivoCancelado.CANCELADO,
                "colaborador_transacao_cancelado_id": request.user.id,
            },
        )

        return redirect(financeiro.get_absolute_url())

    # EXIBIR APENAS OS VALORES PARA LANCAR
    if request.method == "GET":
        # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
        try:
            item = Financeiro.objects.get(pk=pk)

            caption = item.descricao
            valor_transacao = item.valor_transacao
            data_transacao = item.data_transacao
        except Financeiro.DoesNotExist:
            # Handle the case where the object does not exist
            caption = None
            valor_transacao = None
            data_transacao = None

        context = {
            "caption": caption,
            "valor_transacao": valor_transacao,
            "data_transacao": data_transacao,
        }

        return render(request, template_name, context)
    return None


@login_required
def caixa_fechar(request):
    template_name = "form-caixa-fechar.html"

    # Verificar a opção de reentrada - Exibir o caption
    caption = "Fechar o CAIXA:"

    # if request.method == "POST":
    #     context = {
    #         "data_transacao": timezone.now(),
    #     }

    #     return reverse("home:confirmar_fechamento_caixa", kwargs={})

    # EXIBIR APENAS OS VALORES PARA LANCAR
    if request.method == "GET":
        # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
        try:
            data_transacao = timezone.now()

        except Financeiro.DoesNotExist:
            # Handle the case where the object does not exist
            caption = None
            data_transacao = None

        context = {
            "caption": caption,
            "data_transacao": data_transacao,
        }

        return render(request, template_name, context)
    return None


@login_required
def certidao_create_imovel_view(request, imovel_id):
    # Inicializa os kwargs do formulário com o filtro adequado
    form_kwargs = {"tipo_item_certidao_nome_list": ["Ambos", "Imóvel"]}

    if request.method == "POST":
        form = forms.PedidoCertidaoCertidaoForm(request.POST, **form_kwargs)
        if form.is_valid():
            imovel = PedidoCertidaoImovel.objects.get(pk=imovel_id)
            criar_certidoes(form, imovel=imovel)
            return redirect(
                reverse("home:pedido_certidao_update_imovel", args=[imovel_id]),
            )
    else:
        form = forms.PedidoCertidaoCertidaoForm(**form_kwargs)

    return render(request, "certidoes/certidao_form.html", {"form": form})


@login_required
def certidao_create_pessoa_view(request, pessoa_id):
    # Inicializa os kwargs do formulário com o filtro adequado
    form_kwargs = {"tipo_item_certidao_nome_list": ["Ambos", "Pessoa"]}

    if request.method == "POST":
        form = forms.PedidoCertidaoCertidaoForm(request.POST, **form_kwargs)
        if form.is_valid():
            pessoa = PedidoCertidaoPessoa.objects.get(pk=pessoa_id)
            criar_certidoes(form, pessoa=pessoa)
            return redirect(
                reverse("home:pedido_certidao_pessoa_update", args=[pessoa_id]),
            )
    else:
        form = forms.PedidoCertidaoCertidaoForm(**form_kwargs)

    return render(request, "certidoes/certidao_form.html", {"form": form})


def criar_certidoes(form, imovel=None, pessoa=None):
    quantidades = form.cleaned_data["quantidades"]
    for tipo_certidao_id, quantidade in quantidades.items():
        tipo_certidao_instance = TipoCertidao.objects.get(id=tipo_certidao_id)
        for _ in range(quantidade):
            Certidao.objects.create(
                tipo_certidao=tipo_certidao_instance,
                imovel=imovel,
                pessoa=pessoa,
                tipo_tributacao=form.cleaned_data["tipo_tributacao"],
            )


# def listar_certidoes(request, **kwargs):
#     if "imovel_id" in kwargs:
#         return listar_certidoes_imovel(request, kwargs["imovel_id"])
#     elif "pessoa_id" in kwargs:
#         return listar_certidoes_pessoa(request, kwargs["pessoa_id"])


class CertidoesPessoaListView(SingleTableMixin, ListView):
    model = Certidao
    template_name = "certidoes/pedido_certidao_list.html"
    table_class = CertidaoTable
    table_pagination = {"per_page": 10}

    def get_queryset(self):
        pessoa_id = self.kwargs["pessoa_id"]
        pessoas = PedidoCertidaoPessoa.objects.filter(pk=pessoa_id)
        return Certidao.objects.filter(pessoa__in=pessoas)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent"] = "Certidões"
        context["segment"] = "pedidos"
        context["title"] = "Certidões da Pessoa"

        pessoa_id = self.kwargs["pessoa_id"]
        pessoa = PedidoCertidaoPessoa.objects.filter(pk=pessoa_id).first()

        url_retorno = self.request.GET.get(
            "next",
            reverse("home:pedido_certidao_detalhes", args=[pessoa.pedido_id]),
        )

        botoes = {
            "adicionar": {
                "url": reverse(
                    "home:pedido_certidao_adicionar_certidao_pessoa",
                    args=[pessoa_id],
                ),
                "label": "Adicionar",
                "class": "btn-primary",
            },
            "voltar": {
                "url": url_retorno,
                "label": "Ver Pedido de Certidão",
                "class": "btn-outline-secondary",
            },
            "andamento": {
                "url": reverse(
                    "home:pedido_certidao_andamentos",
                    args=[pessoa.pedido_id],
                ),
                "label": "Andamentos",
                "class": "btn-outline-secondary",
            },
        }

        context.update(
            {
                "parent": "certidoes",
                "segment": "pedidos",
                "title": "Partes do Pedido de Certidão",
                "botoes": botoes,
            },
        )

        return context


class PedidoCertidaoCertidoesImovelListView(SingleTableMixin, ListView):
    model = Certidao
    template_name = "certidoes/pedido_certidao_list.html"
    table_class = CertidaoTable
    table_pagination = {"per_page": 10}

    def get_queryset(self):
        imovel_id = self.kwargs["imovel_id"]
        imovel = PedidoCertidaoImovel.objects.filter(pk=imovel_id).first()
        return Certidao.objects.filter(imovel=imovel)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent"] = "Certidões"
        context["segment"] = "pedidos"
        context["title"] = "Certidões do Imovel"

        imovel_id = self.kwargs["imovel_id"]
        imovel = PedidoCertidaoImovel.objects.filter(pk=imovel_id).first()

        url_retorno = self.request.GET.get(
            "next",
            reverse("home:pedido_certidao_detalhes", args=[imovel.pedido_id]),
        )

        botoes = {
            "adicionar": {
                "url": reverse(
                    "home:pedido_certidao_adicionar_certidao_imovel",
                    args=[imovel_id],
                ),
                "label": "Adicionar",
                "class": "btn-primary",
            },
            "voltar": {
                "url": url_retorno,
                "label": "Ver Pedido de Certidão",
                "class": "btn-outline-secondary",
            },
        }

        context.update(
            {
                "parent": "certidoes",
                "segment": "pedidos",
                "title": "Certidões do Pedido de Certidão",
                "botoes": botoes,
            },
        )

        return context


class ProjetoDeleteView(DeleteView):
    model = Projeto
    template_name = "confirmar_exclusao_projeto.html"


class HidrogenioDeleteView(DeleteView):
    model = Hidrogenio
    template_name = "confirmar_exclusao_hidrogenio.html"


class InversorDeleteView(DeleteView):
    model = Inversor
    template_name = "confirmar_exclusao_inversor.html"


class PainelDeleteView(DeleteView):
    model = PainelSolar
    template_name = "confirmar_exclusao_painel.html"

    def get_success_url(self):
        # pedido_id = self.object.pedido_id
        return reverse("home:criar_painel_solar", args=[])


# class ProjetoUpdateView(LoginRequiredMixin, UpdateView):
#     model = Projeto
#     fields = [
#         "nome_projeto",
#         "localidade",
#         "data_inicio_projeto",
#         "data_fim_projeto",
#         "latitude",
#         "longitude",
#         "fotovoltaico",
#         "biogas",
#         "hidrogenio",
#         "baterias",
#         "observacoes",
#     ]

#     template_name = "certidoes/projeto_update_form.html"

#     def get_form(self, form_class=None):
#         return super().get_form(form_class)

#     def form_valid(self, form):
#         # Modifique os valores dos campos aqui antes de salvar
#         projeto = form.save(commit=False)  # Não salva ainda no banco

#         # Aqui você pode adicionar qualquer lógica de negócio antes de salvar
#         projeto.save()  # Agora salva as mudanças no banco de dados

#         return redirect(reverse("home:criar_projeto"))

class ProjetoUpdateView(LoginRequiredMixin, UpdateView):
    model = Projeto
    form_class = ProjetoForm  # <- use o formulário com layout de 2 colunas
    template_name = "certidoes/projeto_update_form.html"

    def form_valid(self, form):
        projeto = form.save(commit=False)
        projeto.save()
        return redirect(reverse("home:criar_projeto"))

class CertidaoUpdateView(LoginRequiredMixin, UpdateView):
    model = Certidao
    fields = [
        "tipo_certidao",
        "tipo_tributacao",
        # imovel
        # pessoa
    ]
    template_name = "certidoes/certidao_update_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Ordena o queryset dos campos em ordem alfabética e aplica filtros
        form.fields["tipo_certidao"].queryset = (
            form.fields["tipo_certidao"].queryset.filter(ativo=True).order_by("nome")
        )
        form.fields["tipo_tributacao"].queryset = (
            form.fields["tipo_tributacao"]
            .queryset.filter(utilizado="S")
            .order_by("descricao")
        )
        return form

    def form_valid(self, form):
        # Modifique os valores dos campos aqui antes de salvar
        certidao = form.save(commit=False)  # Não salva ainda no banco

        # Exemplo de alteração de valores
        certidao.tipo_certidao = (
            certidao.tipo_certidao
        )  # Acessa o valor do campo na instância
        certidao.tipo_tributacao = (
            certidao.tipo_tributacao
        )  # Acessa o valor do campo na instância

        # Aqui você pode adicionar qualquer lógica de negócio antes de salvar
        certidao.save()  # Agora salva as mudanças no banco de dados

        # PARA QUAL TELA VOLTAR
        if certidao.imovel:
            pedido_id = certidao.imovel.pedido_id

        if certidao.pessoa:
            pedido_id = certidao.pessoa.pedido_id

        url = reverse(
            "home:pedido_certidao_listar_certidoes_pedido",
            kwargs={"pedido_id": pedido_id},
        )

        return redirect(url)


# class CertidaoUpdateView(LoginRequiredMixin, UpdateView):

#     #model = Certidao
#     #form_class = forms.PedidoCertidaoCertidaoForm
#     template_name = "certidoes/certidao_update_form.html"

#     class Meta:
#         model = Certidao
#         fields = ["tipo_certidao", "tipo_tributacao"]

# def get_form_kwargs(self):
#     kwargs = super().get_form_kwargs()
#     kwargs["is_editing"] = True
#     certidao = self.get_object()
#     if certidao.imovel:
#         kwargs["tipo_item_certidao_nome_list"] = ["Ambos", "Imóvel"]
#     elif certidao.pessoa:
#         kwargs["tipo_item_certidao_nome_list"] = ["Ambos", "Pessoa"]
#     return kwargs

# def get_context_data(self, **kwargs):
#     context = super().get_context_data(**kwargs)
#     certidao = self.get_object()

#     entidade = certidao.imovel or certidao.pessoa
#     tipo = (
#         "imovel_id" if isinstance(entidade, PedidoCertidaoImovel) else "pessoa_id"
#     )
#     context[tipo] = entidade.pk

#     certidoes = (
#         Certidao.objects.filter(imovel=entidade)
#         if certidao.imovel
#         else Certidao.objects.filter(pessoa=entidade)
#     )

#     certidoes_table = CertidaoTable(certidoes)

#     context["certidoes_table"] = certidoes_table
#     # context["pedido_id"] = self.kwargs["pedido_id"]

#     return context

# def get_success_url(self):
#     certidao = self.get_object()
#     if certidao.imovel:
#         return reverse(
#             "home:pedido_certidao_update_imovel",
#             args=[certidao.imovel_id],
#         )
#     else:
#         return reverse(
#             "home:pedido_certidao_pessoa_update",
#             args=[certidao.pessoa_id],
#         )


class CertidaoListView(SingleTableMixin, LoginRequiredMixin, ListView):
    model = Certidao
    table_class = CertidaoTable
    template_name = "certidoes/pedido_certidao_list.html"
    table_pagination = {"per_page": 10}
    context_object_name = "certidoes"  # nome da variável no template

    def get_queryset(self):
        return Certidao.objects.filter(pedido_id=self.kwargs["pedido_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        RequestConfig(self.request).configure(self.table)
        context["parent"] = "Certidões"
        context["segment"] = "pedidos"

        return context


class CertidaoDeleteView(LoginRequiredMixin, DeleteView):
    model = Certidao
    template_name = "certidoes/certidao_confirm_delete.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Certidao, pk=self.kwargs.get("pk"))

    def get_success_url(self):
        # Redirecione com base em se a certidão estava associada a um Imovel ou Pessoa
        certidao = self.get_object()
        if certidao.imovel:
            return reverse(
                "home:pedido_certidao_update_imovel",
                args=[certidao.imovel.pk],
            )
        elif certidao.pessoa:
            return reverse(
                "home:pedido_certidao_pessoa_update",
                args=[certidao.pessoa.pk],
            )
        else:
            # URL de fallback, por exemplo, uma lista de certidões ou página inicial
            return reverse("home:pedido_certidao_index")


class CertidaoPrintView(LoginRequiredMixin, TemplateView):
    template_name = "impressao/certidao_print.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certidao = get_object_or_404(Certidao, pk=self.kwargs.get("pk"))
        context["certidao"] = certidao
        return context


# class ProtocoloAndamentoListView(LoginRequiredMixin, SingleTableMixin, ListView):
#     model = Livro01Andamento
#     table_class = Livro01AndamentoTable
#     template_name = "protocolo/listar.html"
#     paginate_by = 10

#     def get_queryset(self):
#         protocolo_id = self.kwargs.get("protocolo_id")
#         return Livro01Andamento.objects.filter(protocolo_id=protocolo_id).order_by(
#             "-id",
#         )

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         protocolo_id = self.kwargs.get("protocolo_id")

#         url_retorno = self.request.GET.get(
#             "next",
#             reverse("home:protocolo_detalhes", args=[protocolo_id]),
#         )

#         protocolo = PedidoCertidao.objects.get(id=protocolo_id)

#         botoes = {
#             "adicionar": {
#                 "url": Livro01Andamento.get_adicionar_ao_pedido_url(protocolo_id),
#                 "label": "Adicionar",
#                 "class": "btn-primary",
#             },
#             "voltar": {
#                 "url": url_retorno,
#                 "label": "Voltar ao Protocolo",
#                 "class": "btn-outline-secondary",
#             },
#             # "pessoa": {
#             #     "url": reverse("home:pedido_certidao_pessoas_list", args=[pedido_id]),
#             #     "label": "Pessoas",
#             #     "class": "btn-outline-secondary",
#             # },
#             # "imovel": {
#             #     "url": reverse("home:pedido_certidao_imoveis_listar", args=[pedido_id]),
#             #     "label": "Imóveis",
#             #     "class": "btn-outline-secondary",
#             # },
#         }

#         title = "Andamentos do Protocolo: " + str(
#             helpers.formatar_inteiro_como_string(protocolo.numero_protocolo, 6),
#         )

#         context.update(
#             {
#                 "protocolo_id": protocolo_id,
#                 "parent": "livro01",
#                 "segment": "protocolo",
#                 "title": title,
#                 "botoes": botoes,
#             },
#         )

#         return context


class PedidoCertidaoAndamentoListView(LoginRequiredMixin, SingleTableMixin, ListView):
    model = PedidoCertidaoAndamento
    table_class = AndamentoTable
    template_name = "certidoes/pedido_certidao_list.html"
    paginate_by = 10

    def get_queryset(self):
        pedido_id = self.kwargs.get("pedido_id")
        return PedidoCertidaoAndamento.objects.filter(pedido_id=pedido_id).order_by(
            "-id",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_id = self.kwargs.get("pedido_id")

        url_retorno = self.request.GET.get(
            "next",
            reverse("home:pedido_certidao_detalhes", args=[pedido_id]),
        )

        pedido_certidao = PedidoCertidao.objects.get(id=pedido_id)

        botoes = {
            "adicionar": {
                "url": PedidoCertidaoAndamento.get_adicionar_ao_pedido_url(pedido_id),
                "label": "Adicionar",
                "class": "btn-primary",
            },
            "voltar": {
                "url": url_retorno,
                "label": "Ver Pedido de Certidão",
                "class": "btn-outline-secondary",
            },
            "pessoa": {
                "url": reverse("home:pedido_certidao_pessoas_list", args=[pedido_id]),
                "label": "Pessoas",
                "class": "btn-outline-secondary",
            },
            "imovel": {
                "url": reverse("home:pedido_certidao_imoveis_listar", args=[pedido_id]),
                "label": "Imóveis",
                "class": "btn-outline-secondary",
            },
        }

        title = "Andamentos do Pedido de Certidão: " + str(
            helpers.formatar_inteiro_como_string(pedido_certidao.numero_pedido, 6),
        )

        context.update(
            {
                "pedido_id": pedido_id,
                "parent": "certidoes",
                "segment": "pedidos",
                "title": title,
                "botoes": botoes,
            },
        )

        return context


# GERAR TODOS OS SELOS DE CERTIDÃO POR PEDIDO - DATA ATUAL
@login_required
def pedido_certidao_andamento_adicionar_mesmo_colaborador(
    request,
    pedido_id,
    tipo_andamento_id,
):
    tipo_andamento = TipoAndamentoCertidao.objects.get(pk=tipo_andamento_id)

    pedido = PedidoCertidao.objects.get(pk=pedido_id)
    pedido.registrar_andamento(
        tipo_andamento=tipo_andamento,
        descricao=tipo_andamento.descricao,
        usuario=request.user,
    )

    url = reverse("home:pedido_certidao_detalhes", kwargs={"pk": pedido_id})
    return redirect(url)


# GERAR TODOS OS SELOS DE CERTIDÃO POR PEDIDO - SELECIONADOS NA LISTA- DATA ATUAL
@login_required
def pedido_certidao_andamento_adicionar_mesmo_colaborador_lista(request):
    pedidos_ids = request.GET.get("numeros_pedidos", "")
    tipo_andamento_id = request.GET.get("tipo_andamento_id")

    # Convertendo a string de IDs para uma lista de inteiros
    pedidos_ids = [int(pk) for pk in pedidos_ids.split(",") if pk.isdigit()]

    tipo_andamento = get_object_or_404(TipoAndamentoCertidao, pk=tipo_andamento_id)

    # Filtrando os pedidos pelo IDs
    pedidos = PedidoCertidao.objects.filter(numero_pedido__in=pedidos_ids)

    # Registrando o andamento para cada pedido
    for pedido in pedidos:
        pedido.registrar_andamento(
            tipo_andamento=tipo_andamento,
            descricao=tipo_andamento.descricao,
            usuario=request.user,
        )

    # Redirecionando para a página de detalhes do primeiro pedido
    if pedidos:
        url = reverse("home:pedido_certidao_detalhes", kwargs={"pk": pedidos[0].pk})
        return redirect(url)
    else:
        return redirect("home:pedido_certidao_list")


class PedidoCertidaoAndamentoCreateView(LoginRequiredMixin, CreateView):
    model = PedidoCertidaoAndamento
    form_class = forms.PedidoCertidaoAndamentoForm
    template_name = "certidoes/andamento_form.html"

    def get_success_url(self):
        pedido_id = self.kwargs["pedido_id"]
        return reverse("home:pedido_certidao_detalhes", args=[pedido_id])

    def form_valid(self, form):
        user_id = self.request.user.id

        pedido_id = self.kwargs["pedido_id"]
        pedido = get_object_or_404(PedidoCertidao, id=pedido_id)
        andamento = form.save(commit=False)
        andamento.criado_por_id = user_id  # Defina o usuário aqui
        andamento.pedido = pedido
        resultado = andamento.save()

        # VERIFICAR SE O ANDAMENTO EXISTE ESTAR SELADO
        if resultado == "SELO_OBRIGATORIO":
            messages.error(
                self.request,
                "Inclusão de andamento cancelada: Selo obrigatório não informado ainda.",
            )

            url = reverse("home:pedido_certidao_andamentos", args=[andamento.pedido_id])
            return redirect(url)  # Redireciona para a página desejada

        try:
            PedidoCertidaoAndamento.exportar_para_firebird(self, user_id)
        except Exception as e:
            logger.info(f"Erro ao exportar para Firebird: {e}")

        # Acessar o campo grupo_gerar_andamento_agenda corretamente - VERIFICAR SE E PARA GERAR AGENDA PARA OUTRAS COLABORADORES
        tipo_andamento = TipoAndamentoCertidao.objects.get(
            codigo=andamento.tipo_andamento_id,
        )
        if tipo_andamento.grupo_gerar_andamento_agenda:
            # Execute comandos adicionais aqui - GERAR O USUARIO PARA O GRUPO
            pedido.gerar_agenda_certidao_grupo_colaboradores(andamento)
            # print("Comandos adicionais após confirmação da inclusão.")

        return super().form_valid(form)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_certidao = get_object_or_404(PedidoCertidao, id=self.kwargs["pedido_id"])
        context["pedido_certidao"] = str(pedido_certidao)
        return context


def pedido_certidao_andamento_desativar(request, pk):
    """DESATIVAR ANDAMENTO DO PEDIDO DE CERTIDAO."""
    pedido_andamento = PedidoCertidaoAndamento.objects.get(pk=pk)
    pedido_andamento.ativo = False
    pedido_andamento.save()

    url = reverse("home:pedido_certidao_andamentos", args=[pedido_andamento.pedido_id])
    return redirect(url)


def pedido_certidao_andamento_ativar(request, pk):
    """ATIVAR ANDAMENTO DO PEDIDO DE CERTIDAO."""
    pedido_andamento = PedidoCertidaoAndamento.objects.get(pk=pk)
    pedido_andamento.ativo = True
    pedido_andamento.save()

    url = reverse("home:pedido_certidao_andamentos", args=[pedido_andamento.pedido_id])
    return redirect(url)


@login_required
def pedido_certidao_andamento_update(request, pk):
    andamento = get_object_or_404(PedidoCertidaoAndamento, pk=pk)

    if request.method == "POST":
        form = forms.PedidoCertidaoAndamentoForm(request.POST, instance=andamento)
        form.request = request  # Passa a request para o formulário

        if form.is_valid():
            form.save()
            return redirect(
                reverse(
                    "home:pedido_certidao_andamentos",
                    args=[andamento.pedido_id],
                ),
            )
    else:
        form = forms.PedidoCertidaoAndamentoForm(instance=andamento)

    context = {
        "form": form,
        "object": andamento,
    }

    return render(request, "certidoes/andamento_form.html", context)


@login_required
def pedido_certidao_imovel_create(request, pedido_id):
    pedido = get_object_or_404(PedidoCertidao, id=pedido_id)

    if request.method == "POST":
        form = forms.ImovelForm(request.POST)
        form.request = request  # Passa a request para o formulário

        if form.is_valid():
            imovel = form.save(commit=False)
            imovel.pedido = pedido
            imovel.save()

            if "save_and_add_another" in request.POST:
                return redirect(
                    reverse("home:pedido_certidao_adicionar_imovel", args=[pedido_id]),
                )
            else:
                return redirect(
                    reverse("home:pedido_certidao_update_imovel", args=[imovel.id]),
                )
    else:
        form = forms.ImovelForm()

    context = {
        "form": form,
        "titulo_principal": "Adicionar Imóvel",
        "parent": "Certidões",
        "segment": f"PedidoCertidao {pedido.numero_pedido} | {pedido.nome_apresentante}",
        "botoes": {
            "cancelar": {
                "url": pedido.get_absolute_url(),
                "label": "Ver Pedido de Certidão",
                "class": "btn-outline-secondary",
            },
        },
    }

    return render(request, "certidoes/item_form.html", context)


@login_required
def pedido_certidao_imovel_update(request, pk):
    imovel = get_object_or_404(PedidoCertidaoImovel, pk=pk)

    if request.method == "POST":
        imovel_form = forms.ImovelForm(request.POST, instance=imovel)
        imovel_form.request = request  # Passa o request para o form

        if imovel_form.is_valid():
            imovel = imovel_form.save()

            if "save_and_add_another" in request.POST:
                return redirect(
                    reverse(
                        "home:pedido_certidao_adicionar_imovel",
                        args=[imovel.pedido_id],
                    ),
                )
            else:
                return redirect(
                    reverse("home:pedido_certidao_update_imovel", args=[imovel.id]),
                )
    else:
        imovel_form = forms.ImovelForm(instance=imovel)
        imovel_form.request = request  # Passa o request para o form

    # Calculando as certidões agrupadas e total
    certidoes_agrupadas = (
        Certidao.objects.filter(imovel=imovel)
        .values("tipo_certidao__nome")
        .annotate(quantidade=Count("id"))
    )

    for certidao_group in certidoes_agrupadas:
        certidoes = Certidao.objects.filter(
            imovel=imovel,
            tipo_certidao__nome=certidao_group["tipo_certidao__nome"],
        )
        certidao_group["total"] = sum(c.total for c in certidoes)

    certidoes_agrupadas_table = CertidaoAgrupadaTable(certidoes_agrupadas)

    context = {
        "object": imovel,
        "certidoes_table": certidoes_agrupadas_table,
        "parent": "Certidões",
        "segment": f"PedidoCertidao Nº {imovel.pedido.numero_pedido} | {imovel.pedido.nome_apresentante}",
        "title": "Editar Registro do Pedido de Certidões",
        "titulo_card": "Dados do Registro ou Registro Auxiliar",
        "url_de_exclusao": "home:excluir_imovel",
        "form": imovel_form,
    }

    return render(request, "certidoes/item_form.html", context)


class PedidoCertidaoImovelListView(SingleTableMixin, ListView):
    model = PedidoCertidaoImovel
    table_class = ImovelTable
    template_name = "certidoes/pedido_certidao_list.html"
    context_table_name = "table"
    paginate_by = 10

    def get_queryset(self):
        pedido_id = self.kwargs["pedido_id"]
        return PedidoCertidaoImovel.objects.filter(pedido_id=pedido_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pedido_id = self.kwargs["pedido_id"]
        pedido_certidao = get_object_or_404(PedidoCertidao, id=pedido_id)

        url_retorno = self.request.GET.get(
            "next",
            reverse("home:pedido_certidao_detalhes", args=[pedido_id]),
        )

        botoes = {
            "adicionar": {
                "url": reverse(
                    "home:pedido_certidao_adicionar_imovel",
                    args=[pedido_id],
                ),
                "label": "Adicionar",
                "class": "btn-primary",
            },
            "voltar": {
                "url": url_retorno,
                "label": "Ver Pedido de Certidão",
                "class": "btn-outline-secondary",
            },
            "pessoa": {
                "url": reverse("home:pedido_certidao_pessoas_list", args=[pedido_id]),
                "label": "Pessoas",
                "class": "btn-outline-secondary",
            },
            "andamento": {
                "url": reverse("home:pedido_certidao_andamentos", args=[pedido_id]),
                "label": "Andamentos",
                "class": "btn-outline-secondary",
            },
        }

        context.update(
            {
                "form_id": str(pedido_certidao.numero_pedido),
                "parent": "certidoes",
                "segment": "pedidos",
                "title": (
                    "Imóveis do Pedido de Certidão: "
                    + str(pedido_certidao.numero_pedido)
                ),
                "botoes": botoes,
            },
        )

        return context


def pedido_certidao_imovel_detail(request, pk):
    try:
        # Tenta obter o objeto com base na chave primária (pk)
        pedido_certidao_imovel = get_object_or_404(PedidoCertidaoImovel, pk=pk)

        # Contexto a ser passado para o template
        context = {
            "pedido_certidao_imovel": pedido_certidao_imovel,
            "url_de_exclusao": "home:excluir_imovel",  # ou qualquer lógica dinâmica aqui
            # 'url_de_voltar_item_imovel': 'home:pedido_certidao_imoveis_listar',
        }

        # Renderiza o template com o contexto fornecido
        return render(request, "certidoes/detail_view.html", context)

    except PedidoCertidaoImovel.DoesNotExist:
        # Retorna uma resposta 404 caso o objeto não seja encontrado
        return HttpResponseNotFound(
            "O pedido de certidão de imóvel solicitado não foi encontrado.",
        )

    except Exception as e:
        # Captura qualquer outra exceção e retorna um erro 500 com uma mensagem genérica
        logger.exception(
            f"Erro ao exibir detalhes do pedido de certidão de imóvel: {e!s}",
        )
        return HttpResponseServerError()(
            "Ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde.",
        )


class PedidoCertidaoImovelDeleteView(DeleteView):
    model = PedidoCertidaoImovel
    template_name = "certidoes/pessoa_confirm_delete.html"

    def get_success_url(self):
        pedido_id = self.object.pedido_id
        return reverse("home:pedido_certidao_detalhes", args=[pedido_id])


class Dashboard(LoginRequiredMixin, TemplateView):
    template_name = "certidoes/PedidoCertidoesIndex.html"


@login_required
def criar_pedido_certidao(request):
    if request.method == "POST":
        form = CriarPedidoCertidaoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    logger.debug(f"{request.user} criando pedido de certidão...")

                    # Criando o pedido sem salvar
                    pedido: PedidoCertidao = form.save(commit=False)
                    pedido.criado_por = request.user

                    # Criando o apresentante com o pedido ainda não salvo
                    apresentante = criar_apresentante(form, request.user)

                    # Associando o apresentante ao pedido
                    pedido.apresentante = apresentante

                    # Salvando o pedido com o apresentante vinculado
                    pedido.save()

                    # Associando o pedido ao apresentante e salvando o apresentante
                    apresentante.pedido = pedido
                    apresentante.save()

                    logger.debug(f"Pedido de certidão criado com sucesso: {pedido}")
                    messages.success(request, "Pedido de certidão criado com sucesso!")

                    return redirect(
                        reverse("home:pedido_certidao_detalhes", args=[pedido.id]),
                    )
            except Exception as e:
                logger.exception(f"Erro ao criar pedido de certidão: {e!s}")
                messages.error(
                    request,
                    "Ocorreu um erro ao criar o pedido de certidão.",
                )
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarPedidoCertidaoForm()

    context = {
        "form": form,
        "title": "Novo Pedido de Certidão",
        "segment": "criar_pedido_certidao",
        "parent": "certidoes",
    }

    return render(request, "certidoes/pedido_create_form.html", context)


def criar_apresentante(form, user):
    logger.debug(f"{user} criando apresentante...")

    apresentante = Apresentante.objects.create(
        nome=form.cleaned_data["nome_apresentante"],
        tipo_documento=form.cleaned_data["tipo_documento"],
        documento=form.cleaned_data["documento"],
        telefone=form.cleaned_data["telefone"],
        observacao=form.cleaned_data["observacoes"],
        email=form.cleaned_data["email"],
        interessado_nome=form.cleaned_data["interessado_nome"],
        interessado_tipo_documento=form.cleaned_data["interessado_tipo_documento"],
        interessado_documento=form.cleaned_data["interessado_documento"],
    )
    logger.debug(f"Apresentante {apresentante.nome} criado com sucesso.")
    return apresentante


class PedidoCertidaoAnexosListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model: type = PedidoCertidaoAnexo
    template_name: str = "certidoes/anexos/pedido_create_anexo_list.html"
    context_table_name: str = "table"
    table_class = PedidoCertidaoAnexoTable
    filterset_class = filters.PedidoCertidaoAnexoFilter
    table_pagination = {"per_page": 10}
    paginate_by: int = 10

    def get_queryset(self):
        pedido_certidao_id = self.kwargs["pedido_certidao_id"]
        return PedidoCertidaoAnexo.objects.filter(pedido_certidao_id=pedido_certidao_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_certidao_id = self.kwargs["pedido_certidao_id"]
        context["pedido_certidao"] = get_object_or_404(
            PedidoCertidao,
            id=pedido_certidao_id,
        )
        return context


class PedidoCertidaoAnexoCreateView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        pedido_certidao_id = self.kwargs["pedido_certidao_id"]
        pedido_certidao = get_object_or_404(PedidoCertidao, id=pedido_certidao_id)
        form = PedidoCertidaoAnexoForm()
        template_name = "certidoes/anexos/pedido_certidao_anexo_form.html"
        context = {
            "form": form,
            "pedido_certidao": pedido_certidao,
        }

        return render(request, template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        pedido_certidao_id = self.kwargs["pedido_certidao_id"]
        pedido_certidao = get_object_or_404(PedidoCertidao, id=pedido_certidao_id)
        files = request.FILES.getlist("arquivo")

        if not files:
            return self.form_invalid("No files uploaded.")

        files_valid = False

        for file in files:
            anexo_form = forms.PedidoCertidaoAnexoForm(request.POST, {"arquivo": file})
            if anexo_form.is_valid():
                PedidoCertidaoAnexo.objects.create(
                    pedido_certidao=pedido_certidao,
                    arquivo=file,
                )
                files_valid = True
            else:
                return self.form_invalid(anexo_form)

        if files_valid:
            return redirect(self.get_success_url(pedido_certidao_id))
        else:
            return self.form_invalid("No valid files uploaded.")

    def form_invalid(self, form) -> HttpResponse:
        pedido_certidao_id = self.kwargs["pedido_certidao_id"]
        pedido_certidao = get_object_or_404(PedidoCertidao, id=pedido_certidao_id)
        template_name = "certidoes/anexos/pedido_certidao_anexo_form.html"
        context = {
            "form": form,
            "pedido_certidao": pedido_certidao,
        }

        return render(self.request, template_name, context)

    def get_success_url(self, pedido_certidao_id: int) -> str:
        return reverse_lazy(
            "home:pedido_certidao_anexos_list",
            kwargs={"pedido_certidao_id": pedido_certidao_id},
        )


class Delete(LoginRequiredMixin, UpdateView):
    model = PedidoCertidao
    form_class = forms.PedidoCertidaoPedidoForm
    template_name = "certidoes/delete_pedido.html"
    success_url = "/list_pedidos/"


@login_required
def pedido_certidao_list_view(request):
    """Exibe uma lista de pedidos de certidão."""
    # Filtrando pedidos por numero_pedido se presente na requisição GET
    numero_pedidos_str = request.GET.get("numero_pedido", "").replace(".", "")
    if numero_pedidos_str:
        pedidos_selecionados = numero_pedidos_str.split(",")
        queryset = PedidoCertidao.objects.filter(
            numero_pedido__in=pedidos_selecionados,
        )
    else:
        queryset = PedidoCertidao.objects.all()

    filtro = PedidoCertidaoFilter(request.GET, queryset)

    # Adicionando ao contexto o número de pedidos filtrados
    numeros_dos_pedidos_no_filtro = list(
        filtro.qs.values_list("numero_pedido", flat=True),
    )

    # Obtendo as opções de andamento
    opcoes_andamento = TipoAndamentoCertidao.obter_exibir_botao_opcoes()

    # Construindo a URL de impressão
    base_url = reverse("home:pedido_certidao_impressao_recibos")
    query_string = urlencode(
        {"numero_pedido": numeros_dos_pedidos_no_filtro},
        doseq=True,
    )
    impressao_url = f"{base_url}?{query_string}"

    # Configurando a tabela com ou sem paginação
    tabela = PedidoCertidaoTable(filtro.qs)
    exibir_todos = request.GET.get("show_all") == "true"
    paginate_by = (
        999
        if exibir_todos
        else request.user.paginate_by
        if request.user.is_authenticated
        else 5
    )

    if "exportar_excel" in request.GET:
        return exportar_table(tabela, "pedidos_de_certidao.xlsx")

    RequestConfig(request=request, paginate={"per_page": paginate_by}).configure(tabela)

    context = {
        "title": "Pedidos de Certidão",
        "segment": "buscar_pedidos",
        "parent": "certidoes",
        "filter": filtro,
        "table": tabela,
        "impressao_url": impressao_url,
        "opcoes_andamento": opcoes_andamento,
        "filtered_numero_pedidos": numeros_dos_pedidos_no_filtro,
    }

    # Renderizando o template com o contexto
    return render(request, "certidoes/pedido_certidao_list.html", context)


# FILTRAR PELO NUMERO DO PEDIDO DE CERTIDAO
def pedido_certidao_numero_certidao_view(request, numero_pedido_certidao):
    pedido_certidao = PedidoCertidao.objects.filter(
        numero_pedido=numero_pedido_certidao,
    ).first()

    if pedido_certidao:
        return redirect(pedido_certidao.get_absolute_url())
    else:
        hoje = datetime.now().strftime("%Y-%m-%d")

        query_params = urllib.parse.urlencode(
            {
                "data_transacao_inicio": hoje,
                "data_transacao_fim": hoje,
            },
        )

        url = f"{reverse('home:financeiro_listar')}?{query_params}"
        return redirect(url)


@login_required
def pedido_certidao_detail_view(request, pk):
    pedido_certidao: PedidoCertidao = get_object_or_404(PedidoCertidao, pk=pk)
    opcoes_andamento = TipoAndamentoCertidao.obter_exibir_botao_opcoes()
    certidao = pedido_certidao.certidoes_relacionadas.first()

    selos_do_pedido_certidao = (
        pedido_certidao.listar_selo_sqlserver
        if request.user.cartorio.usar_selo_sql_server == "S"
        else []
    )

    if selos_do_pedido_certidao:
        selos_no_sqlserver = len(selos_do_pedido_certidao)
        (
            certidao.get_selos_sql_server(selos_do_pedido_certidao)
            if certidao and selos_no_sqlserver > 0
            else {}
        )
    else:
        selos_no_sqlserver = 0

    with FbConnection() as db:
        firebird.get_selos_pedido_certidao(
            pedido_certidao.numero_pedido,
            db,
        )

    # quantidade_selos = (
    #     len(pedido_certidao.selos) or selos_no_sqlserver or len(selos_no_firebird)
    # )

    # certidao = pedido_certidao.certidoes_relacionadas.first()

    # selos_do_pedido_certidao = (
    #     pedido_certidao.listar_selo_sqlserver
    #     if request.user.cartorio.usar_selo_sql_server == "S"
    #     else []
    # )

    # if selos_do_pedido_certidao:
    #     selos_no_sqlserver = len(selos_do_pedido_certidao)
    #     (
    #         certidao.get_selos_sql_server(selos_do_pedido_certidao)
    #         if certidao and selos_no_sqlserver > 0
    #         else {}
    #     )
    # else:
    #     selos_no_sqlserver = 0

    # with FbConnection() as db:
    #     firebird.get_selos_pedido_certidao(
    #         pedido_certidao.numero_pedido,
    #         db,
    #     )

    # DETALHES.
    context = {
        "pedido_certidao": pedido_certidao,
        "quantidade_selos": pedido_certidao.quantidade_selos,
        "opcoes_andamento": opcoes_andamento,
        # "pedido_certidao_seguinte": pedido_certidao.seguinte,
        # "pedido_certidao_anterior": pedido_certidao.anterior,
        # "pedido_certidao_primeiro": pedido_certidao.primeiro,
        # "pedido_certidao_ultimo": pedido_certidao.ultimo,
        "title": "Pedido de Certidão",
        "segment": "pedido_certidao_detail",
        "parent": "certidoes",
    }

    return render(request, "certidoes/pedido_certidao_detail.html", context)


def certidoes_listar_selo(request, numero_pedido):
    numero_pedido = str(numero_pedido).replace(".", "")
    # Cria a URL com os parâmetros de data
    url = f"{reverse('home:selos_listar')}?numero_pedido={numero_pedido}"
    return redirect(url)


class PedidoCertidaoCertidoesListView(SingleTableMixin, ListView):
    """Lista as certidões associadas a um PedidoCertidao."""

    model = Certidao
    template_name = "certidoes/pedido_certidao_list.html"
    table_class = CertidaoTable
    table_pagination = {"per_page": 10}

    def get_queryset(self):
        pedido_id = self.kwargs["pedido_id"]
        # PedidoCertidaoImovel.objects.filter(pedido_id=pedido_id)
        # PedidoCertidaoPessoa.objects.filter(pedido_id=pedido_id)

        return Certidao.objects.filter(
            Q(imovel__pedido_id=pedido_id) | Q(pessoa__pedido_id=pedido_id),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_certidao = PedidoCertidao.objects.get(id=self.kwargs["pedido_id"])

        context["parent"] = "certidoes"
        context["segment"] = "pedidos"
        context["title"] = "Certidões do Pedido Certidão"
        context["pedido_id"] = self.kwargs["pedido_id"]
        context["pedido_certidao"] = pedido_certidao

        url_retorno = reverse(
            "home:pedido_certidao_detalhes",
            args=[self.kwargs["pedido_id"]],
        )
        context["botoes"] = {
            "voltar": {
                "url": url_retorno,
                "label": "Ver Pedido de Certidão",
                "class": "btn-outline-secondary",
            },
            "andamento": {
                "url": reverse(
                    "home:pedido_certidao_andamentos",
                    args=[self.kwargs["pedido_id"]],
                ),
                "label": "Andamentos",
                "class": "btn-outline-secondary",
            },
        }

        return context


class PedidoCertidaoApresentanteUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "certidoes/item_form_apresentante.html"
    model = Apresentante
    form_class = forms.ApresentanteForm

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related("dados_bancarios")

    def get_success_url(self):
        return reverse("home:pedido_certidao_detalhes", args=[self.object.pedido_id])


def confirmar_recebimento_certidao_view(request, pk):
    pedido = get_object_or_404(PedidoCertidao, pk=pk)

    try:
        msg = pedido.registrar_andamento_pedido_recebido(usuario=request.user)

        messages.success(request, msg)
    except Exception as e:
        messages.error(request, f"Erro ao enviar pedido para a Caixa: {e}")
        logger.exception("Erro ao enviar pedido para a Caixa")

    # RETORNAR PARA O VER PEDIDO CERTIDAO
    url = reverse("home:pedido_certidao_listar_pedidos")
    return redirect(url)


def pedido_certidao_caixa_view(request, pk):
    pedido = get_object_or_404(PedidoCertidao, pk=pk)

    try:
        msg = pedido.enviar_para_caixa(
            usuario=request.user,
            valor_transacao=pedido.total_pedido,
        )
        messages.success(request, msg)
    except Exception as e:
        messages.error(request, f"Erro ao enviar pedido para a Caixa: {e}")
        logger.exception("Erro ao enviar pedido para a Caixa")

    return redirect(pedido.get_absolute_url())


def pedido_de_protocolo_enviar_ao_caixa_no_firebird(
    request,
    numero_protocolo,
    valor_transacao,
):
    pedido = get_object_or_404(Livro01Protocolo, numero_protocolo=numero_protocolo)

    try:
        _, msg = pedido.enviar_para_caixa_firebird(
            usuario=request.user,
            valor_transacao=valor_transacao,
        )
        messages.success(request, msg)
    except Exception as e:
        messages.error(request, f"Erro ao enviar pedido para a Caixa no Firebird: {e}")
        logger.exception("Erro ao enviar pedido para o Caixa no Firebird")

    return redirect(pedido.get_absolute_url())


class PedidoCertidaoEmitirEtiquetaView(LoginRequiredMixin, TemplateView):
    template_name = "etiquetas/etiqueta-selo-certidao.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)
        # numero_pedidos = self.request.GET.getlist("numero_pedido")
        # pedidos = PedidoCertidao.objects.filter(numero_pedido__in=numero_pedidos)

        # recibos_data = []
        # for pedido in pedidos:
        #     pedido_data = {
        #         "pedido": pedido,
        #         "certidoes_agrupadas": pedido.get_certidoes_agrupadas(),
        #         "agora": timezone.now(),
        #         "titulo": Configuracao.obter(
        #             "titulo_recibo_certidao",
        #             "COMPROVANTE DE PEDIDO DE CERTIDÃO",
        #         ),
        #     }
        #     #pedido.registrar_impressao_recibo(usuario=self.request.user)
        #     # pedido.enviar_para_pagamento()
        #     #recibos_data.append(pedido_data)

        # context["recibos_data"] = recibos_data


def pedido_certidao_confirmar_entrega_view(request, pk):
    pedido = get_object_or_404(PedidoCertidao, pk=pk)

    try:
        msg = pedido.registrar_andamento_certidao_entregue(usuario=request.user)
        messages.success(request, msg)
    except Exception as e:
        messages.error(request, f"Confirmado Entrega do Pedido: {e}")
        logger.exception("Erro ao Entregar o Pedido")

    return redirect(pedido.get_absolute_url())


class PedidoCertidaoExportarView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            pedido_certidao = PedidoCertidao.objects.get(pk=pk)
        except PedidoCertidao.DoesNotExist:
            messages.error(request, "PedidoCertidao não encontrado!")
            return redirect(reverse("home:pedido_certidao_pedidos"))

        with firebird.FbConnection() as db:
            db.begin_transaction()
            try:
                (resultado, mensagem) = (
                    pedido_certidao.exportar_pedido_certidao_para_fb(
                        descricao_observacao="",
                        origem_id=1,
                        valor_transacao=0,
                        db=db,
                    )
                )
                db.commit()
            except Exception as e:
                db.rollback()
                logger.exception("Erro ao exportar pedido de certidão")
                resultado = False
                mensagem = str(e)

        if pedido_certidao.exportado > 0 or resultado is True:
            messages.success(request, "Exportado! " + mensagem)
        else:
            messages.error(
                request,
                "ERRO: PedidoCertidao NÃO foi exportado! " + mensagem,
            )

        return redirect(pedido_certidao.get_absolute_url())


def pedido_certidao_exportar_caixa_view(request, pk: int) -> bool:
    """Exporta um pedido de certidão para o sistema do caixa via Firebird."""
    logger.debug("Iniciando a exportação do pedido de certidão com ID %d", pk)

    try:
        pedido_certidao = PedidoCertidao.objects.get(pk=pk)
        logger.debug("PedidoCertidao encontrado: %s", pedido_certidao)
    except PedidoCertidao.DoesNotExist:
        logger.exception("PedidoCertidao com ID %d não encontrado", pk)
        messages.error(request, "PedidoCertidao não encontrado!")
        return False
    except DatabaseError as e:
        logger.exception("Erro de banco de dados ao buscar PedidoCertidao: %s", str(e))
        messages.error(
            request,
            "Erro de banco de dados ao buscar PedidoCertidao. Tente novamente mais tarde.",
        )
        return False

    try:
        with firebird.FbConnection() as db:
            db.begin_transaction()
            logger.debug("Conexão com o Firebird estabelecida e transação iniciada")

            try:
                resultado, mensagem = pedido_certidao.exportar_pedido_certidao_para_fb(
                    descricao_observacao="",
                    origem_id=1,
                    valor_transacao=0,
                    db=db,
                )
                logger.debug(
                    "Resultado da exportação: %s, Mensagem: %s",
                    resultado,
                    mensagem,
                )
                db.commit()
                logger.debug("Transação no Firebird cometida com sucesso")
            except DatabaseError as e:
                db.rollback()
                logger.exception(
                    "Erro no banco de dados Firebird durante a exportação: %s",
                    str(e),
                )
                messages.error(
                    request,
                    "Erro de banco de dados durante a exportação. Tente novamente mais tarde.",
                )
                return False
            except OperationalError as e:
                db.rollback()
                logger.exception(
                    "Erro operacional no Firebird durante a exportação: %s",
                    str(e),
                )
                messages.error(
                    request,
                    "Erro operacional durante a exportação. Tente novamente mais tarde.",
                )
                return False
            except Exception as e:
                db.rollback()
                logger.exception("Erro inesperado durante a exportação: %s", str(e))
                messages.error(
                    request,
                    f"Erro inesperado: {e!s}. Tente novamente mais tarde.",
                )
                return False
            finally:
                db.close()
                logger.debug("Conexão com o Firebird fechada")

        if pedido_certidao.exportado or resultado is True:
            messages.success(
                request,
                "Pedido de Certidão enviado ao CAIXA com sucesso!",
            )
            logger.debug("Pedido de Certidão exportado com sucesso")
        else:
            messages.error(
                request,
                f"ERRO: PedidoCertidao NÃO foi exportado! {mensagem}",
            )
            logger.error("Falha na exportação do PedidoCertidao: %s", mensagem)
            return False

        return True

    except InterfaceError as e:
        logger.exception("Erro de interface com o Firebird: %s", str(e))
        messages.error(
            request,
            "Erro de interface com o banco de dados. Tente novamente mais tarde.",
        )
        return False
    except InternalError as e:
        logger.exception("Erro interno no Firebird: %s", str(e))
        messages.error(
            request,
            "Erro interno do banco de dados. Tente novamente mais tarde.",
        )
        return False
    except ProgrammingError as e:
        logger.exception("Erro de programação no Firebird: %s", str(e))
        messages.error(
            request,
            "Erro de programação durante a exportação. Contate o suporte.",
        )
        return False
    except Error as e:
        logger.exception("Erro geral no Firebird: %s", str(e))
        messages.error(request, "Erro no banco de dados. Tente novamente mais tarde.")
        return False
    except Exception as e:
        logger.exception("Erro inesperado na conexão com o Firebird: %s", str(e))
        messages.error(
            request,
            f"Erro inesperado: {e!s}. Tente novamente mais tarde.",
        )
        return False


class PedidoCertidaoRelatorioView(LoginRequiredMixin, SingleTableMixin, TemplateView):
    table_class = PedidoCertidaoTable
    template_name = "certidoes/relatorios/relatorio_pedidos.html"

    def get_table_data(self):
        return PedidoCertidao.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["today"] = timezone.now().date()
        context["total_items"] = PedidoCertidao.objects.count()

        return context


class PedidoCertidaoReciboView(LoginRequiredMixin, DetailView):
    model = PedidoCertidao
    template_name = "certidoes/recibos/recibo_pedido_certidao.html"
    context_object_name = "pedido"

    def dispatch(self, request, *args, **kwargs):
        # Armazenando o usuário logado na instância da view
        self.current_user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Registrar a impressão do recibo com o usuário logado
        self.object.registrar_impressao_recibo(usuario=self.current_user)
        self.object.enviar_para_pagamento()
        # context["pedido"] = self.object
        context["certidoes_agrupadas"] = self.object.get_certidoes_agrupadas()
        context["agora"] = timezone.now()
        context["titulo"] = Configuracao.obter(
            "titulo_recibo_certidao",
            "COMPROVANTE DE PEDIDO DE CERTIDÃO",
        )
        logger.info(
            f"Pedido de Certidão {self.object.numero_pedido} enviado para pagamento. por {self.request.user}",
        )
        return context


class PedidoCertidaoReciboDoCaixaView(LoginRequiredMixin, DetailView):
    model = PedidoCertidao
    template_name = "certidoes/recibos/recibo_pedido_certidao.html"
    context_object_name = "pedido"

    def dispatch(self, request, *args, **kwargs):
        # Armazenando o usuário logado na instância da view
        self.current_user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Registrar a impressão do recibo com o usuário logado
        self.object.registrar_impressao_recibo(usuario=self.current_user)
        context["certidoes_agrupadas"] = self.object.get_certidoes_agrupadas()
        context["agora"] = timezone.now()
        context["titulo"] = Configuracao.obter(
            "titulo_recibo_certidao",
            "COMPROVANTE DE PEDIDO DE CERTIDÃO",
        )
        context["titulo_sem_pagamento"] = Configuracao.obter(
            "titulo_recibo_certidao_sem_pagamento",
            "COMPROVANTE DE PEDIDO DE CERTIDÃO",
        )
        # context["mensagem_finalizacao_html"] = Configuracao.obter(
        #     "mensagem_finalizacao_html",
        #     "A retirada do(s) documento(s) deve ocorrer entre 9h00 ás 12:00 e 13:00 ás 17h00,"
        #     "com a apresentação do comprovante original. É obrigatório retirar os documentos em "
        #     "até 90 dias da data de disponibilidade, sob pena de incineração."
        #     "A retirada do(s) documento(s) deve ocorrer entre 9h00 ás 12:00 e 13:00 ás 17h00, "
        #     "com a apresentação do comprovante original."
        #     "É obrigatório retirar os documentos em até 90 dias da data de disponibilidade, "
        #     "sob pena de incineração. <strong>Declaro que solicitei e li integralmente este pedido,"
        #     "concordando com seus termos.</strong>",
        # )

        return context


class PedidoCertidaoImpressaoRecibosView(LoginRequiredMixin, TemplateView):
    template_name = "certidoes/recibos/multiplos_recibos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        numero_pedidos = self.request.GET.getlist("numero_pedido")
        pedidos = PedidoCertidao.objects.filter(numero_pedido__in=numero_pedidos)

        recibos_data = []
        for pedido in pedidos:
            pedido_data = {
                "pedido": pedido,
                "certidoes_agrupadas": pedido.get_certidoes_agrupadas(),
                "agora": timezone.now(),
                "titulo": Configuracao.obter(
                    "titulo_recibo_certidao",
                    "COMPROVANTE DE PEDIDO DE CERTIDÃO",
                ),
            }
            pedido.registrar_impressao_recibo(usuario=self.request.user)
            # pedido.enviar_para_pagamento()
            recibos_data.append(pedido_data)

        context["recibos_data"] = recibos_data
        return context


class CertidoesListView(LoginRequiredMixin, ListView):
    model = Certidao
    template_name = "certidoes/pedido_certidao_list.html"


class PessoasListView(LoginRequiredMixin, ListView):
    template_name = "certidoes/pedido_certidao_list.html"
    context_object_name = "table"
    paginate_by = 10

    def get_queryset(self):
        pedido_id = self.kwargs["pedido_id"]
        pessoas = PedidoCertidaoPessoa.objects.filter(pedido_id=pedido_id)
        table = PedidoCertidaoPessoasTable(pessoas)
        RequestConfig(self.request).configure(table)
        return table

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent"] = "pedidos"
        context["segment"] = "pessoas"
        return context


def pedido_certidao_pessoas_list_view(request, pedido_id):
    url_retorno = request.GET.get(
        "next",
        reverse("home:pedido_certidao_detalhes", args=[pedido_id]),
    )
    numero_pedido = ""
    pessoas_do_pedido_certidao = PedidoCertidaoPessoa.objects.filter(
        pedido_id=pedido_id,
    ).select_related("pedido")
    for item in pessoas_do_pedido_certidao:
        numero_pedido = item.pedido.numero_pedido

    table = PedidoCertidaoPessoasTable(pessoas_do_pedido_certidao)
    RequestConfig(request, paginate={"per_page": 10}).configure(table)

    botoes = {
        "adicionar": {
            "url": reverse("home:pedido_certidao_pessoa_create", args=[pedido_id]),
            "label": "Adicionar",
            "class": "btn-primary",
        },
        "voltar": {
            "url": url_retorno,
            "label": "Ver Pedido de Certidão",
            "class": "btn-outline-secondary",
        },
        "imovel": {
            "url": reverse("home:pedido_certidao_imoveis_listar", args=[pedido_id]),
            "label": "Imóveis",
            "class": "btn-outline-secondary",
        },
        "andamento": {
            "url": reverse("home:pedido_certidao_andamentos", args=[pedido_id]),
            "label": "Andamentos",
            "class": "btn-outline-secondary",
        },
    }

    # Verifica se o numero_pedido é uma string vazia
    if str(numero_pedido) == "":
        numero_pedido = (
            PedidoCertidao.objects.filter(id=pedido_id)
            .values_list("numero_pedido", flat=True)
            .first()
        )

    return render(
        request=request,
        template_name="certidoes/pedido_certidao_list.html",
        context={
            "table": table,
            "parent": "certidoes",
            "segment": "pedidos",
            "title": "Partes do Pedido de Certidão: " + (str(numero_pedido) or ""),
            "botoes": botoes,
        },
    )


@login_required
def pedido_certidao_pessoa_update(request, pk):
    try:
        pedido_certidao_pessoa = get_object_or_404(PedidoCertidaoPessoa, pk=pk)
    except Http404:
        messages.error(request, _("Registro não encontrado."))
        return redirect(reverse("home:pedido_certidao_list"))

    if request.method == "POST":
        form = forms.PessoaForm(request.POST, instance=pedido_certidao_pessoa)

        if form.is_valid():
            try:
                pessoa = form.save()
                action = request.POST.get("action")

                if action == "save_and_add_another":
                    messages.success(
                        request,
                        _("Pessoa salva com sucesso! Adicione outra pessoa."),
                    )
                    return redirect(
                        reverse(
                            "home:pedido_certidao_pessoa_create",
                            args=[pessoa.pedido_id],
                        ),
                    )
                else:
                    messages.success(request, _("Pessoa atualizada com sucesso!"))
                    return redirect(
                        reverse("home:pedido_certidao_pessoa_update", args=[pessoa.id]),
                    )
            except Exception as e:
                messages.error(request, _("Erro ao salvar a pessoa: ") + str(e))
        else:
            messages.error(request, _("Por favor, corrija os erros abaixo."))
    else:
        form = forms.PessoaForm(instance=pedido_certidao_pessoa)

    pessoa = pedido_certidao_pessoa

    try:
        certidoes_agrupadas = Certidao.objects.get_agrupadas_por_tipo(pessoa)

        for certidao_group in certidoes_agrupadas:
            tipo_certidao_nome = certidao_group["tipo_certidao__nome"]
            tipo_certidao = (
                TipoCertidao.objects.filter(nome=tipo_certidao_nome)
                .order_by("id")
                .last()
            )

            if tipo_certidao:
                certidoes = Certidao.objects.filter(
                    pessoa=pessoa,
                    tipo_certidao=tipo_certidao,
                )
                total_certidoes = sum(c.total for c in certidoes)
                certidao_group["total"] = total_certidoes
            else:
                certidao_group["total"] = 0
    except Exception as e:
        messages.error(request, _("Erro ao agrupar as certidões: ") + str(e))
        certidoes_agrupadas = []

    certidoes_agrupadas_table = CertidaoAgrupadaTable(certidoes_agrupadas)

    context = {
        "object": pessoa,
        "form": form,
        "certidoes_table": certidoes_agrupadas_table,
        "parent": _("Certidões"),
        "segment": _("Pessoas"),
        "title": _("Editar Pessoa do PedidoCertidao"),
        "pedido_id": str(pessoa.id),
        "url_para_voltar": reverse(
            "home:pedido_certidao_detalhes",
            args=[pessoa.pedido_id],
        ),
        "url_de_exclusao": reverse("home:excluir_pessoa", args=[pessoa.id]),
    }

    return render(request, "certidoes/item_form_pessoa.html", context)


@login_required
def pedido_certidao_pessoa_create(request, pedido_id):
    try:
        # Recupera o pedido associado
        pedido = get_object_or_404(PedidoCertidao, id=pedido_id)
    except Exception as e:
        messages.error(
            request,
            "Erro ao tentar recuperar o pedido de certidão. Por favor, tente novamente.",
        )
        logger.exception(f"Erro ao recuperar PedidoCertidao com id {pedido_id}: {e!s}")
        return redirect(
            "home:pedido_certidao_list",
        )  # Redireciona para a lista de pedidos

    if request.method == "POST":
        form = forms.PessoaForm(request.POST)
        if form.is_valid():
            try:
                pessoa = form.save(commit=False)
                pessoa.pedido = pedido
                pessoa.save()

                # Verifica se o usuário clicou em "save_and_add_another"
                if request.POST.get("action") == "save_and_add_another":
                    messages.success(
                        request,
                        "Pessoa adicionada com sucesso. Adicione outra pessoa se desejar.",
                    )
                    return redirect(
                        "home:pedido_certidao_pessoa_create",
                        pedido_id=pedido_id,
                    )

                messages.success(request, "Pessoa adicionada com sucesso.")
                return redirect(
                    reverse("home:pedido_certidao_pessoa_update", args=[pessoa.id]),
                )
            except Exception as e:
                messages.error(
                    request,
                    "Erro ao salvar os dados da pessoa. Por favor, tente novamente.",
                )
                logger.exception(
                    f"Erro ao salvar Pessoa relacionada ao PedidoCertidao {pedido_id}: {e!s}",
                )
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")

    else:
        form = forms.PessoaForm()

    # Renderiza o template com o formulário vazio ou com erros
    return render(
        request,
        "certidoes/item_form_pessoa.html",
        {
            "form": form,
            "parent": "Certidões",
            "title": "Adicionar Pessoa ao Pedido de Certidão",
            "titulo_card": "Dados da Pessoa ou Empresa",
            "segment": f"PedidoCertidao {pedido.numero_pedido} - {pedido.nome_apresentante}",
            "form_id": str(pedido.numero_pedido),
            "pedido_id": str(pedido.id),
            "botoes": {
                "cancelar": {
                    "url": pedido.get_absolute_url(),
                    "label": "Ver Pedido de Certidão",
                    "class": "btn btn-sm btn-secondary",
                },
                "all": {
                    "url": pedido.get_url_pessoas_list(),
                    "label": "Ver Pessoas",
                    "class": "btn btn-sm btn-secondary",
                },
            },
        },
    )


class PedidoCertidaoPessoaDetailView(DetailView):
    model = PedidoCertidaoPessoa
    template_name = "certidoes/detail_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["url_de_exclusao"] = (
            "nome_da_url_de_exclusao"  # ou qualquer lógica dinâmica aqui
        )
        return context


class PedidoCertidaoPessoaDeleteView(DeleteView):
    model = PedidoCertidaoPessoa
    template_name = "certidoes/pessoa_confirm_delete.html"

    def get_success_url(self):
        pedido_id = self.object.pedido_id
        return reverse("home:pedido_certidao_detalhes", args=[pedido_id])


# Selar PARA O PEDIDO DE CERTIDÃO - ESPECIFICIO
@login_required
def pedido_certidao_onr_gerar_selo_view(request):
    print("Selar para os itens do pedido: matricula_visualizada")

    pedidos_ids = request.GET.getlist("pedido_id")
    pedidos = PedidoCertidao.objects.filter(id__in=pedidos_ids)

    if pedidos:
        for pedido_certidao in pedidos:
            try:
                pedido_certidao.selar_certidoes_do_pedido(request.user)
                messages.success(
                    request,
                    f"Selo gerado com sucesso para o pedido de certidão {pedido_certidao.numero_pedido}",
                )
            except Exception as e:
                logger.exception(
                    f"{pedido_certidao.numero_pedido}: {e!s}",
                )
                messages.error(
                    request,
                    f"{pedido_certidao.numero_pedido}: {e!s}",
                )

    # Renderiza a view atual novamente para manter o usuário na mesma página
    return redirect(request.headers.get("referer", "fallback_view"))


# GERAR TODOS OS SELOS DE CERTIDÃO POR PEDIDO - DATA ATUAL
@login_required
def pedido_certidao_gerar_selo_onr_todo_dia_atual(request, origem_id):
    print("Selar para os itens: ONR que não tenham sido selados ainda")

    start_date = timezone.now().date() - timedelta(0)
    end_date = timezone.now().date() + timedelta(1)

    pedidos = PedidoCertidao.objects.filter(
        origem_id=origem_id,
        data_entrada__range=[start_date, end_date],
    )
    print("Pedidos de certidão encontrados para selar: ", pedidos.count())
    for pedido in pedidos:
        try:
            pedido.selar_certidoes_do_pedido(request.user)
        except Exception as e:
            logger.exception(
                f" {pedido.numero_pedido} {e!s}",
            )
            messages.error(
                request,
                f": {pedido.numero_pedido} {e!s}",
            )

    return integracoes_onr_view(request, origem_id=origem_id)


@login_required
def pedido_certidao_gerar_selo_pedido_certidao(request, origem_id):
    print("Selar para os itens: ONR que não tenham sido selados ainda")

    start_date = timezone.now().date() - timedelta(0)
    end_date = timezone.now().date() + timedelta(1)

    pedidos = PedidoCertidao.objects.filter(
        origem_id=origem_id,
        data_entrada__range=[start_date, end_date],
    )

    print("Pedidos de certidão encontrados para selar: ", pedidos.count())

    for pedido in pedidos:
        try:
            pedido.selar_certidoes_do_pedido(request.user)
        except Exception as e:
            logger.exception(
                f" {pedido.numero_pedido} {e!s}",
            )
            messages.error(
                request,
                f": {pedido.numero_pedido} {e!s}",
            )

    return integracoes_onr_view(request, origem_id=origem_id)


def gerar_selo_protocolos_onr_view(request):
    # Recupera os ids de protocolos a serem selados
    ids = request.GET.getlist("ids")

    if not ids:
        messages.error(request, "Nenhum protocolo informado.")
        return redirect(request.headers.get("referer", "fallback_view"))

    # Recupera os protocolos
    protocolos = Livro01Protocolo.objects.filter(id__in=ids)

    for protocolo in protocolos:
        try:
            protocolo.selar(request.user)
        except Exception as e:
            logger.exception(
                f"Erro ao gerar selo para o protocolo {protocolo.numero_protocolo}: {e!s}",
            )
            messages.error(
                request,
                f"Erro ao gerar selo para o protocolo {protocolo.numero_protocolo}: {e!s}",
            )

    return redirect(request.headers.get("referer", "fallback_view"))


@login_required
def listar_andamento_view(request, pedido_id):
    andamentos = PedidoCertidaoAndamento.objects.filter(pedido_id=pedido_id)

    table = PedidoCertidaoAndamentoTable(andamentos)
    RequestConfig(request, paginate={"per_page": 10}).configure(table)

    # Adcionando botões
    url_retorno = request.GET.get(
        "next",
        reverse("home:pedido_certidao_detalhes", args=[pedido_id]),
    )
    botoes = {
        "adicionar": {
            "url": reverse(
                "home:pedido_certidao_andamento_adicionar",
                args=[pedido_id],
            ),
            "label": "Adicionar",
            "class": "btn-primary",
        },
        "voltar": {
            "url": url_retorno,
            "label": "Ver Pedido de Certidão",
            "class": "btn-outline-secondary",
        },
    }

    return render(
        request,
        "listar_andamento_view.html",
        {
            "table": table,
            "parent": "certidoes",
            "segment": "pedidos",
            "title": "Pessoas do Pedido de Certidão",
            "botoes": botoes,
        },
    )


# Baixar EXCELL dados
def download_excel_certidao_onr(
    request,
    origem_id: int,
    data_inicio=None,
    data_fim=None,
):
    from apps.home.models import PedidoCertidao

    data_inicio = data_inicio or timezone.now().date()
    data_fim = data_fim or timezone.now().date() + timedelta(1)

    # FORMATAR ORIGEM
    origem_id = int(origem_id)

    # PEDIDOS DE CERTIDÃO DE MATRÍCULA VISUALIZADA NO DIA ATUAL
    if origem_id == 2:
        pedido_certidao = PedidoCertidao.onr_matricula_visualizada(
            request,
            data_inicio,
            data_fim,
        )
    elif origem_id == 3:
        pedido_certidao = PedidoCertidao.onr_oficio(request, data_inicio, data_fim)
    else:
        pedido_certidao = PedidoCertidao.onr_matricula_visualizada(
            request,
            data_inicio,
            data_fim,
        )

    # content-type of response
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename= "Relatório.xls"'
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Relatório ONR")
    row_num = 0
    xlwt.XFStyle()

    columns = [
        "Número PedidoCertidao",
        "Origem ONR",
        "Apresentante",
        "Entrada",
        "Data Selo",
        "Valor",
    ]

    col_widths = [256 * 15, 256 * 20, 256 * 60, 256 * 12, 256 * 12, 256 * 15]

    # Styles for headers
    header_style = xlwt.XFStyle()
    header_style.font = xlwt.Font()
    header_style.font.bold = True
    header_style.font.colour_index = xlwt.Style.colour_map["white"]
    header_style.alignment = xlwt.Alignment()
    header_style.alignment.horz = xlwt.Alignment.HORZ_CENTER
    header_style.pattern = xlwt.Pattern()
    header_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    header_style.pattern.pattern_fore_colour = xlwt.Style.colour_map[
        "dark_blue"
    ]  # Example color

    # Styles
    alignment_center = xlwt.Alignment()
    alignment_center.horz = xlwt.Alignment.HORZ_CENTER
    font_style_center = xlwt.XFStyle()
    font_style_center.alignment = alignment_center

    alignment_right = xlwt.Alignment()
    alignment_right.horz = xlwt.Alignment.HORZ_RIGHT
    font_style_right = xlwt.XFStyle()
    font_style_right.alignment = alignment_right

    # Currency format
    currency_style = xlwt.XFStyle()
    currency_style.alignment = alignment_right
    currency_style.num_format_str = '"R$" #,##0.00'  # Brazilian Real currency format

    # Create a combined style for sum cell
    sum_style = xlwt.XFStyle()

    # Font
    sum_style.font = xlwt.Font()
    sum_style.font.bold = True
    sum_style.font.colour_index = xlwt.Style.colour_map["white"]

    # Alignment
    sum_style.alignment = xlwt.Alignment()
    sum_style.alignment.horz = xlwt.Alignment.HORZ_RIGHT

    # Background
    sum_style.pattern = xlwt.Pattern()
    sum_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    sum_style.pattern.pattern_fore_colour = xlwt.Style.colour_map["dark_blue"]

    # Currency format
    sum_style.num_format_str = '"R$" #,##0.00'

    font_style_default = xlwt.XFStyle()

    for col_num in range(len(columns)):
        ws.col(col_num).width = col_widths[col_num]
        ws.write(row_num, col_num, columns[col_num], header_style)

    for my_row in pedido_certidao:
        row_num = row_num + 1
        ws.write(row_num, 0, my_row.numero_pedido, font_style_center)
        ws.write(row_num, 1, my_row.origem_formatada, font_style_center)
        ws.write(row_num, 2, my_row.nome_apresentante, font_style_default)
        ws.write(
            row_num,
            3,
            my_row.data_entrada.strftime(settings.DATE_FORMAT_STR),
            font_style_center,
        )

        if my_row.data_selado is None:
            ws.write(row_num, 4, "", font_style_center)
        else:
            ws.write(
                row_num,
                4,
                my_row.data_selado.strftime(settings.DATE_FORMAT_STR),
                font_style_center,
            )
        ws.write(row_num, 5, my_row.total_pedido, currency_style)

    # Sum formula for the last column
    if row_num > 0:
        ws.write(row_num + 1, 5, xlwt.Formula(f"SUM(F2:F{row_num + 1})"), sum_style)

    wb.save(response)

    return response


def certidoes_onr_relatorio_excel_por_ids(request):
    from apps.home.models import PedidoCertidao

    # Capturar os IDs dos pedidos da URL
    pedidos_ids = request.GET.get("pedido_ids")

    if not pedidos_ids:
        return HttpResponseBadRequest("Nenhum ID de pedido fornecido.")

    # Dividir a string de IDs em uma lista de inteiros
    try:
        pedidos_ids = [int(pid) for pid in pedidos_ids.split(",")]
    except ValueError:
        return HttpResponseBadRequest("Formato inválido de ID de pedido fornecido.")

    # Filtrar os pedidos com base nos IDs fornecidos
    pedidos_de_certidao = PedidoCertidao.objects.filter(id__in=pedidos_ids)

    # # Filtrar pedidos conforme a origem
    # if origem_id == 2:
    #     pedido_certidao = pedido_certidao.filter(
    #         origem=PedidoCertidao.ORIGEM_MATRICULA_VISUALIZADA,
    #     )
    # elif origem_id == 3:
    #     pedido_certidao = pedido_certidao.filter(origem=PedidoCertidao.ORIGEM_OFICIO)
    # else:
    #     pedido_certidao = pedido_certidao.filter(
    #         origem=PedidoCertidao.ORIGEM_MATRICULA_VISUALIZADA,
    #     )

    # content-type of response
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename= "Relatório.xls"'
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Relatório ONR")
    row_num = 0
    xlwt.XFStyle()

    columns = [
        "Número PedidoCertidao",
        "Origem ONR",
        "Apresentante",
        "Entrada",
        "Data Selo",
        "Valor",
    ]

    col_widths = [256 * 15, 256 * 20, 256 * 60, 256 * 12, 256 * 12, 256 * 15]

    # Styles for headers
    header_style = xlwt.XFStyle()
    header_style.font = xlwt.Font()
    header_style.font.bold = True
    header_style.font.colour_index = xlwt.Style.colour_map["white"]
    header_style.alignment = xlwt.Alignment()
    header_style.alignment.horz = xlwt.Alignment.HORZ_CENTER
    header_style.pattern = xlwt.Pattern()
    header_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    header_style.pattern.pattern_fore_colour = xlwt.Style.colour_map["dark_blue"]

    # Styles
    alignment_center = xlwt.Alignment()
    alignment_center.horz = xlwt.Alignment.HORZ_CENTER
    font_style_center = xlwt.XFStyle()
    font_style_center.alignment = alignment_center

    alignment_right = xlwt.Alignment()
    alignment_right.horz = xlwt.Alignment.HORZ_RIGHT
    font_style_right = xlwt.XFStyle()
    font_style_right.alignment = alignment_right

    # Currency format
    currency_style = xlwt.XFStyle()
    currency_style.alignment = alignment_right
    currency_style.num_format_str = '"R$" #,##0.00'  # Brazilian Real currency format

    # Create a combined style for sum cell
    sum_style = xlwt.XFStyle()

    # Font
    sum_style.font = xlwt.Font()
    sum_style.font.bold = True
    sum_style.font.colour_index = xlwt.Style.colour_map["white"]

    # Alignment
    sum_style.alignment = xlwt.Alignment()
    sum_style.alignment.horz = xlwt.Alignment.HORZ_RIGHT

    # Background
    sum_style.pattern = xlwt.Pattern()
    sum_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    sum_style.pattern.pattern_fore_colour = xlwt.Style.colour_map["dark_blue"]

    # Currency format
    sum_style.num_format_str = '"R$" #,##0.00'

    font_style_default = xlwt.XFStyle()

    for col_num in range(len(columns)):
        ws.col(col_num).width = col_widths[col_num]
        ws.write(row_num, col_num, columns[col_num], header_style)

    for my_row in pedidos_de_certidao:
        row_num = row_num + 1
        ws.write(row_num, 0, my_row.numero_pedido, font_style_center)
        ws.write(row_num, 1, my_row.origem_formatada, font_style_center)
        ws.write(row_num, 2, my_row.nome_apresentante, font_style_default)
        ws.write(
            row_num,
            3,
            my_row.data_entrada.strftime(settings.DATE_FORMAT_STR),
            font_style_center,
        )

        if my_row.data_selado is None:
            ws.write(row_num, 4, "", font_style_center)
        else:
            ws.write(
                row_num,
                4,
                my_row.data_selado.strftime(settings.DATE_FORMAT_STR),
                font_style_center,
            )
        ws.write(row_num, 5, my_row.total_pedido, currency_style)

    # Sum formula for the last column
    if row_num > 0:
        ws.write(row_num + 1, 5, xlwt.Formula(f"SUM(F2:F{row_num + 1})"), sum_style)

    wb.save(response)

    return response


def protocolos_onr_relatorio_excel_por_ids(request):
    from apps.home.models import Livro01Protocolo

    # Capturar os IDs da URL
    ids = request.GET.get("ids")

    if not ids:
        return HttpResponseBadRequest("Nenhum ID de pedido fornecido.")

    # Dividir a string de IDs em uma lista de inteiros
    try:
        ids = [int(pid) for pid in ids.split(",")]
    except ValueError:
        return HttpResponseBadRequest("Formato inválido de ID de pedido fornecido.")

    # Filtrar os pedidos com base nos IDs fornecidos
    protocolos = Livro01Protocolo.objects.filter(id__in=ids)

    # Content-type of response
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename= "Relatório.xls"'
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Relatório ONR")
    row_num = 0
    xlwt.XFStyle()

    columns = [
        "Protocolo Cartório",
        "Protocolo ONR",
        "Apresentante",
        "Entrada",
        "Data Selo",
        "Valor",
    ]

    col_widths = [256 * 15, 256 * 20, 256 * 60, 256 * 12, 256 * 12, 256 * 15]

    # Styles for headers
    header_style = xlwt.XFStyle()
    header_style.font = xlwt.Font()
    header_style.font.bold = True
    header_style.font.colour_index = xlwt.Style.colour_map["white"]
    header_style.alignment = xlwt.Alignment()
    header_style.alignment.horz = xlwt.Alignment.HORZ_CENTER
    header_style.pattern = xlwt.Pattern()
    header_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    header_style.pattern.pattern_fore_colour = xlwt.Style.colour_map["dark_blue"]

    # Styles
    alignment_center = xlwt.Alignment()
    alignment_center.horz = xlwt.Alignment.HORZ_CENTER
    font_style_center = xlwt.XFStyle()
    font_style_center.alignment = alignment_center

    alignment_right = xlwt.Alignment()
    alignment_right.horz = xlwt.Alignment.HORZ_RIGHT
    font_style_right = xlwt.XFStyle()
    font_style_right.alignment = alignment_right

    # Currency format
    currency_style = xlwt.XFStyle()
    currency_style.alignment = alignment_right
    currency_style.num_format_str = '"R$" #,##0.00'  # Brazilian Real currency format

    # Create a combined style for sum cell
    sum_style = xlwt.XFStyle()

    # Font
    sum_style.font = xlwt.Font()
    sum_style.font.bold = True
    sum_style.font.colour_index = xlwt.Style.colour_map["white"]

    # Alignment
    sum_style.alignment = xlwt.Alignment()
    sum_style.alignment.horz = xlwt.Alignment.HORZ_RIGHT

    # Background
    sum_style.pattern = xlwt.Pattern()
    sum_style.pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    sum_style.pattern.pattern_fore_colour = xlwt.Style.colour_map["dark_blue"]

    # Currency format
    sum_style.num_format_str = '"R$" #,##0.00'

    font_style_default = xlwt.XFStyle()

    for col_num in range(len(columns)):
        ws.col(col_num).width = col_widths[col_num]
        ws.write(row_num, col_num, columns[col_num], header_style)

    for my_row in protocolos:
        row_num = row_num + 1
        ws.write(row_num, 0, my_row.numero_pedido, font_style_center)
        ws.write(row_num, 1, my_row.origem_formatada, font_style_center)
        ws.write(row_num, 2, my_row.nome_apresentante, font_style_default)
        ws.write(
            row_num,
            3,
            my_row.data_entrada.strftime(settings.DATE_FORMAT_STR),
            font_style_center,
        )

        if my_row.data_selado is None:
            ws.write(row_num, 4, "", font_style_center)
        else:
            ws.write(
                row_num,
                4,
                my_row.data_selado.strftime(settings.DATE_FORMAT_STR),
                font_style_center,
            )
        ws.write(row_num, 5, my_row.total_pedido, currency_style)

    # Sum formula for the last column
    if row_num > 0:
        ws.write(row_num + 1, 5, xlwt.Formula(f"SUM(F2:F{row_num + 1})"), sum_style)

    wb.save(response)

    return response


# PEDIDO DE CERTIDAO CAIXA
def enviar_pedido_de_protocolo_ao_caixa_view(
    request,
    numero_protocolo,
    valor_total_protocolo,
    mensagem="0",
):
    template_name = "form-pagamento-protocolo.html"

    logger.debug("Iniciando função enviar_pedido_de_protocolo_ao_caixa_view")
    logger.debug(
        f"Parâmetros recebidos - numero_protocolo: {numero_protocolo}, valor_total_protocolo: {valor_total_protocolo}, mensagem: {mensagem}",
    )

    try:
        valor_total_protocolo = Decimal(valor_total_protocolo)
    except ValueError as e:
        logger.exception(f"Erro ao converter valor_total_protocolo para Decimal: {e}")
        valor_total_protocolo = Decimal(0)

    logger.debug(f"Valor total do protocolo convertido: {valor_total_protocolo}")

    if request.method == "POST":
        referer = request.headers.get("referer")
        logger.debug(f"Referer: {referer}")

        # REGISTRAR ENVIO PARA CAIXA NO POSTGRESQL
        valor_transacao = helpers.retirar_dados_valor_monetario(
            request.POST.get("valor_diferenca_receber"),
        )
        data_original = request.POST.get("data_original")
        data_agendamento = request.POST.get("data_agendamento")
        tipo_operacao_financeira_id = request.POST.get("operacao_financeira_id")
        descricao = request.POST.get("descricao")
        nome_pagador = request.POST.get("nome_pagador")

        logger.debug(
            f"Valores do POST recebidos - valor_transacao: {valor_transacao}, data_original: {data_original}, data_agendamento: {data_agendamento}, tipo_operacao_financeira_id: {tipo_operacao_financeira_id}, descricao: {descricao}, nome_pagador: {nome_pagador}",
        )

        if Decimal(valor_transacao) < 0:
            tipo_transacao_id = TipoTransacaoFinanceira.get_devolucao().id
        else:
            tipo_transacao_id = TipoTransacaoFinanceira.get_receita().id

        logger.debug(f"Tipo de transação determinado: {tipo_transacao_id}")

        colaborador_financeiro_id = request.user.id
        logger.debug(f"ID do colaborador financeiro: {colaborador_financeiro_id}")

        try:
            protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)
        except Livro01Protocolo.DoesNotExist:
            logger.exception(f"Protocolo não encontrado: {numero_protocolo}")
            return redirect(referer)

        logger.debug(f"Protocolo encontrado: {protocolo}")

        protocolo.enviar_para_pagamento_caixa(
            valor_transacao=valor_transacao,
            tipo_operacao_financeira_id=tipo_operacao_financeira_id,
            tipo_transacao_id=tipo_transacao_id,
            descricao=descricao,
            nome_pagador=nome_pagador,
            data_original=data_original,
            colaborador_financeiro_id=colaborador_financeiro_id,
        )

        logger.debug("Envio para pagamento no caixa registrado")

        # Exportar para o Firebird
        pedido_de_protocolo_enviar_ao_caixa_no_firebird(
            request=request,
            numero_protocolo=protocolo.numero_protocolo,
            valor_transacao=valor_transacao,
        )

        logger.debug("Pedido de protocolo exportado para Firebird")

        if data_agendamento:
            protocolo.data_agendamento = data_agendamento
            protocolo.save()
            logger.debug(f"Agendamento salvo: {data_agendamento}")

        # DUPLICIDADE DE LANCAR NO CAIXA
        # with firebird.FbConnection() as db:
        #     firebird.acertar_valor_pago_firebird(
        #         numero_protocolo=protocolo.numero_protocolo,
        #         valor_transacao=valor_transacao,
        #         db=db,
        #     )

        logger.debug("Valor pago acertado no Firebird")

        return redirect(referer)

    if request.method == "GET":
        try:
            protocolo = Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)
        except Livro01Protocolo.DoesNotExist:
            logger.exception(f"Protocolo não encontrado: {numero_protocolo}")
            return redirect(
                "error_page",
            )  # Substitua "error_page" pela página de erro adequada

        nome_requerente = protocolo.nome_apresentante
        operacao_financeira = TipoOperacaoFinanceira.objects.filter(
            grupo_entradas="S",
        ).order_by("descricao")

        data_original = helpers.get_data_util_em_x_dias(timezone.now().date(), 0)
        data_original = data_original.strftime("%Y-%m-%d")

        caption = f"Pagamento do Protocolo nº: {numero_protocolo}"

        valor_atual_protocolo = protocolo.valor_total_caixa
        valor_diferenca = valor_total_protocolo - valor_atual_protocolo

        logger.debug(
            f"Dados para o template - data_original: {data_original}, caption: {caption}, valor_atual_protocolo: {valor_atual_protocolo}, valor_total_protocolo: {valor_total_protocolo}, valor_diferenca: {valor_diferenca}, nome_requerente: {nome_requerente}",
        )

        context = {
            "protocolo": protocolo,
            "operacao_financeira": operacao_financeira,
            "data_original": data_original,
            "caption": caption,
            "valor_atual_protocolo": valor_atual_protocolo,
            "valor_total_pago_protocolo": valor_total_protocolo,
            "valor_diferenca": Decimal(valor_diferenca),
            "nome_requerente": nome_requerente,
            "nome_interessado": "",
            "mensagem": "",
        }

        return render(request, template_name, context)

    return None


# PEDIDO DE CERTIDAO CAIXA
def pedido_certidao_caixa(request, pk):
    template_name = "form-pagamento-pedido_certidao.html"

    if request.method == "POST":
        referer = request.headers.get("referer")

        # REGISTRAR ENVIO PARA CAIXA NO POSTGRESQL
        valor_transacao = helpers.retirar_dados_valor_monetario(
            request.POST.get("valor_diferenca_receber"),
        )
        data_original = request.POST.get("data_original")
        tipo_operacao_financeira_id = request.POST.get("operacao_financeira_id")
        descricao = request.POST.get("descricao")
        nome_pagador = request.POST.get("nome_pagador")

        if Decimal(valor_transacao) < 0:
            tipo_transacao_id = TipoTransacaoFinanceira.get_devolucao().id
        else:
            tipo_transacao_id = TipoTransacaoFinanceira.get_receita().id

        # COLABORADOR FINANCEIRO
        colaborador_financeiro_id = request.user.id

        # FILTRANDO PEDIDO DE CERTIDAO
        pedido_certidao = PedidoCertidao.objects.get(pk=pk)

        pedido_certidao.enviar_para_pagamento_caixa(
            valor_transacao=valor_transacao,
            tipo_operacao_financeira_id=tipo_operacao_financeira_id,
            tipo_transacao_id=tipo_transacao_id,
            descricao=descricao,
            nome_pagador=nome_pagador,
            data_original=data_original,
            colaborador_financeiro_id=colaborador_financeiro_id,
        )

        # exportar para o firebird
        try:
            pedido_certidao_exportar_caixa_view(request, pedido_certidao.pk)
        except Exception as e:
            messages.error(request, f"Erro ao exportar para o Firebird: {e}")
            logger.exception(f"Erro ao exportar para o Firebird: {e}")

        # ATUALIZAR O PEDIDO DE CERTIDAO
        # pedido_certidao.numero_pedido_firebird = pedido_certidao.numero_pedido
        # pedido_certidao.save()

        messages.success(request, "Pedido de certidão enviado para o caixa.")

        return redirect(referer)

    if request.method == "GET":
        pedido_certidao = PedidoCertidao.objects.get(pk=pk)
        nome_requerente = Apresentante.objects.get(pedido_id=pk)
        operacao_financeira = TipoOperacaoFinanceira.objects.filter(
            grupo_entradas="S",
        ).order_by("descricao")

        # Formatando a data para distribuir
        data_original = helpers.get_data_util_em_x_dias(timezone.now().date(), 0)
        data_original = data_original.strftime("%Y-%m-%d")

        # Verificar a opção de reentrada - Exibir o caption
        caption = "Pagamento do Pedido de Certidão nº: " + str(
            pedido_certidao.numero_pedido,
        )

        # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
        valor_atual_pedido_certidao = pedido_certidao.valor_total_caixa
        valor_total_pago_pedido_certidao = pedido_certidao.total_pedido
        valor_diferenca = pedido_certidao.valor_diferenca

        context = {
            "pedido_certidao": pedido_certidao,
            "operacao_financeira": operacao_financeira,
            "data_original": data_original,
            "caption": caption,
            "valor_atual_pedido_certidao": valor_atual_pedido_certidao,
            "valor_total_pago_pedido_certidao": valor_total_pago_pedido_certidao,
            "valor_diferenca": Decimal(valor_diferenca),
            "nome_requerente": nome_requerente,
            "nome_interessado": "",
        }

        return render(request, template_name, context)
    return None


@login_required
def pedido_certidao_atualizar_sistema_anterior_view(request, pk):
    import apps.home.services.firebird as firebird
    from apps.home.services.firebird import update_firebird_temporario_sql_server

    try:
        # Tenta buscar o pedido de certidão pelo PK
        pedido_certidao = PedidoCertidao.objects.get(pk=pk)

        # Atualiza o pedido de certidão no sistema anterior
        try:
            # firebird.deletar_pedido_certidao_fb(pedido_certidao.numero_pedido)
            pedido_certidao_exportar_caixa_view(request, pedido_certidao.pk)
            messages.info(request, "Pedido de certidão atualizado no sistema anterior.")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar o sistema anterior: {e}")
            logger.exception(f"Erro ao atualizar o sistema anterior: {e}")

        # Verifica a quantidade de selos - SQL Server
        selos_do_pedido_certidao = (
            pedido_certidao.quantidade_selo_sqlserver
            if request.user.cartorio.usar_selo_sql_server == "S"
            else []
        )

        # Verifica se o selo principal está definido
        if (
            request.user.cartorio.usar_selo_sql_server == "S"
            and selos_do_pedido_certidao
        ):
            try:
                # pedido_certidao.atualizar_selo_principal_sqlserver()
                messages.info(request, "Selo principal atualizado no SQL Server.")
            except Exception as e:
                messages.error(request, f"Erro ao atualizar o selo principal: {e}")
                return redirect(pedido_certidao.get_absolute_url())

        # Gera o andamento de selo de certidão - GERAR SELO
        if selos_do_pedido_certidao:
            try:
                db = FbConnection()
                db.begin_transaction()
                firebird.gravar_andamentos_pedido_certidao(
                    pedido_id=pedido_certidao.numero_pedido,
                    data=timezone.now(),
                    funcionario_id=request.user.id,
                    tipo_andamento_id=4,  # GERAR SELO
                    db=db,
                )
                db.commit()
                db.close()
                messages.info(request, "Andamento de selo gerado com sucesso.")
            except DatabaseError as db_error:
                if db:
                    db.rollback()
                messages.error(
                    request,
                    f"Erro ao gravar o andamento do pedido: {db_error}",
                )
                return redirect(pedido_certidao.get_absolute_url())
            except Exception as e:
                messages.error(request, f"Erro desconhecido ao gerar o selo: {e}")
                return redirect(pedido_certidao.get_absolute_url())

            # ATUALIZAR OS SELOS ENCONTRADOS - SQL SERVER
            if request.user.cartorio.usar_selo_sql_server == "S":
                selo_encontrados = (
                    pedido_certidao.get_selos_do_pedido_certidao_sqlserver()
                )

                # CRIAR SELO NO SELOS_SQL_SERVER
                try:
                    if selo_encontrados:
                        update_firebird_temporario_sql_server(selo_encontrados)
                except Exception as e:
                    print("CRIAR SELO NO SELOS_SQL_SERVER")
                    print(e)

            # Verifica se existe selo principal
            # sum(
            #     1
            #     for item in selos_do_pedido_certidao
            #     if item.get("EH_SELO_PRINCIPAL") == "S"
            # )

            # print(contagem)
            # contagem = 0

            # if contagem == 0:
            #     try:
            #         # Acessa o valor da primeira identificação
            #         primeira_identificacao = selos_do_pedido_certidao[0].get(
            #             "IDENTIFICACAO",
            #         )
            #         print(primeira_identificacao)

            #         if primeira_identificacao:
            #             Certidao.atualizar_eh_principal_selo_sqlserver(
            #                 pedido_certidao.numero_pedido,
            #             )
            #             messages.info(
            #                 request,
            #                 "Selo principal atualizado no sistema SQL Server.",
            #             )
            #     except Exception as e:
            #         messages.error(request, f"Erro ao atualizar o selo principal: {e}")
            #         return redirect(pedido_certidao.get_absolute_url())

    except ObjectDoesNotExist:
        messages.error(request, "Pedido de Certidão não encontrado!")
        return redirect(reverse("home:pedido_certidao_listar_pedidos"))
    except ValidationError as e:
        messages.error(request, f"Erro de validação: {e}")
        return redirect(reverse("home:pedido_certidao_listar_pedidos"))
    except Exception as e:
        messages.error(request, f"Erro desconhecido: {e}")
        return redirect(reverse("home:pedido_certidao_listar_pedidos"))

    messages.success(request, "Certidões atualizadas com sucesso!")
    return redirect(pedido_certidao.get_absolute_url())


@login_required
def pedido_certidao_selar_certidoes_view(request, pk):
    logger.debug(f"Iniciando pedido_certidao_selar_certidoes_view com pk={pk}")
    try:
        try:
            pedido_certidao = PedidoCertidao.objects.get(pk=pk)
            logger.debug(f"PedidoCertidao encontrado: {pedido_certidao}")
        except ObjectDoesNotExist:
            messages.error(
                request,
                "Não foi possível encontrar o pedido de certidão com o ID fornecido.",
            )
            logger.exception("Pedido de Certidão não encontrado!")
            return redirect(reverse("home:pedido_certidao_listar_pedidos"))

        try:
            pedido_certidao.selar_certidoes_do_pedido(request.user)
            logger.debug(f"Pedido de Certidão selado pelo usuário: {request.user}")
        except ValidationError as ve:
            messages.error(
                request,
                f"Erro de validação ao tentar selar a certidão: {ve.message}. Por favor, verifique os dados e tente novamente.",
            )
            logger.exception(f"Erro de validação ao selar certidão {pk}: {ve}")
            return redirect(pedido_certidao.get_absolute_url())
        except DatabaseError as db_err:
            messages.error(
                request,
                "Ocorreu um problema ao acessar o banco de dados ao tentar selar a certidão. Por favor, tente novamente mais tarde.",
            )
            logger.exception(f"Erro no banco de dados ao selar certidão {pk}: {db_err}")
            return redirect(pedido_certidao.get_absolute_url())

    except Exception as e:
        messages.error(
            request,
            f"Ocorreu um erro inesperado ao tentar selar a certidão: {e}. Por favor, tente novamente mais tarde.",
        )
        logger.exception(f"Erro inesperado ao selar certidão para pk={pk}: {e}")

        if "pedido_certidao" in locals():
            return redirect(pedido_certidao.get_absolute_url())

        return redirect(reverse("home:pedido_certidao_listar_pedidos"))

    messages.success(request, "Certidões seladas com sucesso!")
    logger.debug("Certidões seladas com sucesso!")
    return redirect(pedido_certidao.get_absolute_url())


@login_required
def pedido_certidao_cancelar(request, pk):
    template_name = "form-pedido-certidao-cancelar.html"

    # Verificar a opção de reentrada - Exibir o caption
    caption = "Cancelar todos os itens do PEDIDO DE CERTIDÃO: "

    if request.method == "POST":
        item = PedidoCertidao.objects.get(pk=pk)

        descricao_cancelamento = request.POST.get("descricao_cancelamento_id")
        valor_devolver = request.POST.get("input_valor_devolver")
        tipooperacaofinanceira_id = request.POST.get("input_tipooperacaofinanceira_id")
        data_transacao = helpers.get_data_e_hora_por_opcao(3)

        # FORMATAR VALOR
        valor_devolver = (
            Decimal(str(valor_devolver).replace(".", "").replace(",", ".")) * -1
        )

        # PEDIDO DE CERTIDAO
        tipocategoria_id = 3

        # DEVOLUCAO
        tipo_transacao_id = 3

        # GRAVAR CAIXA DEVOLUCAO
        financeiro = Financeiro.criar_financeiro_despesa_receita(
            pedido_id=None,
            pedido_certidao_id=pk,
            tipo_transacao_id=tipo_transacao_id,
            tipo_categoria_financeira_id=tipocategoria_id,
            tipo_operacao_financeira_id=tipooperacaofinanceira_id,
            colaborador_id=request.user.id,
            colaborador_confirmado_id=None,
            data_transacao=data_transacao,
            data_original_transacao=data_transacao,
            valor_transacao=valor_devolver,
            dadp="N",
            imposto_renda="N",
            descricao=descricao_cancelamento,
            quantidade_parcelas=1,
            recorrencia_id=1,
            user_id=request.user.id,
        )

        # GERAR O CANCELAMENTO e DEVOLUCAO
        item.registrar_cancelar_devolucao(request.user)

        return redirect(financeiro.get_absolute_url())

    # EXIBIR APENAS OS VALORES PARA LANCAR
    if request.method == "GET":
        # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
        try:
            item = PedidoCertidao.objects.get(pk=pk)
            tipooperacaofinanceiras = TipoOperacaoFinanceira.objects.all().order_by(
                "descricao",
            )

            numero_pedido = item.numero_pedido
            observacao = item.observacao
            data_entrada = item.data_entrada
            nome_apresentante = item.nome_apresentante

            # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
            valor_atual_pedido_certidao = item.valor_total_caixa
            valor_total_pago_pedido_certidao = item.total_pedido
            valor_diferenca = item.valor_diferenca

            # VALOR A DEVOLVER
            valor_devolver = valor_atual_pedido_certidao

        except PedidoCertidao.DoesNotExist:
            # Handle the case where the object does not exist
            numero_pedido = None
            observacao = None
            data_entrada = None
            nome_apresentante = None
            valor_atual_pedido_certidao = None
            valor_total_pago_pedido_certidao = None
            valor_diferenca = None
            valor_devolver = None

        context = {
            "caption": caption,
            "numero_pedido": numero_pedido,
            "observacao": observacao,
            "data_entrada": data_entrada,
            "nome_apresentante": nome_apresentante,
            "valor_atual_pedido_certidao": valor_atual_pedido_certidao,
            "valor_total_pago_pedido_certidao": valor_total_pago_pedido_certidao,
            "valor_diferenca": valor_diferenca,
            "valor_devolver": valor_devolver,
            "tipooperacaofinanceiras": tipooperacaofinanceiras,
        }

        return render(request, template_name, context)
    return None


def selos_sqlserver_view(request):
    from apps.home.services.sqlserver import listar_selos_disponiveis_por_quantidade

    listar_selos_disponiveis_por_quantidade(10)
    return redirect("home:calender")


# LIMPAR O SELO DO PROTOCOLO
def limpar_selo(request, numero_selo):
    try:
        user = User.get_usuario_sistema()
        limpar = False

        if user.cartorio.usar_selo_sql_server == "S":
            limpar = limpar_selo_sqlServer(numero_selo)
        else:
            limpar = True

        if limpar:
            limpar_selo_sistema(numero_selo)

    except Exception as e:
        logger.exception(f"Erro ao limpar o selo {numero_selo}: {e}")
        return redirect("home:calender", error="Erro ao limpar o selo.")

    # Redireciona para a página anterior
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@csrf_exempt
def get_ai_suggestion(request):
    if request.method == "POST":
        data = json.loads(request.body)
        text = data.get("text", "")
        from openai import OpenAI

        client = OpenAI(
            # This is the default and can be omitted
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """Você é um assistente que ajuda na escrita de textos para o Cartório de Projeto CEHTES.
                                Reescreva para melhorar o texto e torna-lo mais claro, simples de entender e objetivo para o cliente do cartório. Torne o texto mais pessoal e educado e instrutivo. Na sua resposta não deve haver mais nada além do trecho rescrito.""",
                },
                {"role": "user", "content": text},
            ],
        )

        suggestion = completion.choices[0].message.content.strip()
        return JsonResponse({"suggestion": suggestion})

    return JsonResponse({"error": "Invalid request method"}, status=400)


# ENVIAR ARQUIVOS PARA AS ROTINAS DE IMPORTACAO
def gerar_certidao_webservice_onr(request, origem_id, file_location, filename):
    print("ENVIAR ARQUIVOS PARA AS ROTINAS DE IMPORTACAO: ", origem_id, filename)

    # PEGAR O usuario ADMIN
    if request is None:
        # PEGAR OS DADOS DO USUARIO
        usuario_model = apps.get_model("cartorios", "Usuario")

        # Obtendo o primeiro item da lista retornada
        user = usuario_model.objects.get(id=1)
    else:
        user = request.user

    # if origem_id not in [3, 4, 6]: IMPORTAR DA ONR
    if origem_id not in [3, 4, 5, 6]:
        return ""

    # 3:  # ONR - OFICIO
    elif origem_id == TipoIntegracao.get_onr_oficio().id:
        try:
            processar_xml_oficio_onr(file_location, filename, user)
        except:
            pass
    # 4:  # ONR - Consulta Eletronica
    elif origem_id == TipoIntegracao.get_tipo_integracao_onr_consulta_eletronica().id:
        try:
            processar_xml_consulta_eletronica_onr(
                file_location=file_location,
                uploaded_file=filename,
                user=user,
                origem_id=4,
            )
        except:
            pass
    # 5:  # ONR - Penhora Online SPH
    elif origem_id == TipoIntegracao.get_onr_penhora_online_sph().id:
        try:
            processar_xml_penhora_online_sph_onr(file_location, filename, user)
        except:
            pass
    # # 6:  # ONR - Certidões a Emitir
    # elif origem_id == TipoIntegracao.get_certidoes_a_emitir().id:
    #     try:
    #         processar_certidoes_emitir_onr(file_location, filename, user)
    #     except:
    #         pass
    else:
        print(" Origem não encontrada: ", origem_id)

    # GRAVAR NO AUDITOR ULTIMA LEITURA DE ARQUIVO
    try:
        AuditorIntegracao.objects.create(tipo_integracao_id=origem_id)
    except:
        pass

    return None


# VERIFICAR WEBSERVICE
def verificar_webservice_onr_robo(request):
    # CONSULTA ELETRONICA
    from apps.home.managers import descriptografar_lista

    nomes_criptografados = ["293C3536132C", "273B272100203B23"]
    nomes_descriptografados = descriptografar_lista(nomes_criptografados)
    print(nomes_descriptografados)


# VERIFICAR WEBSERVICE
def verificar_webservice_onr(request):
    import platform

    """DIRETORIO ONDE A WEBSERVICE EXTERNA VAI BAIXAR OS ARQUIVOS DO SITE DA ONR - SISTEMA EXTERNO C#."""
    ip_diretorio_xml_orn = Configuracao.obter("ip_diretorio_xml_orn")
    ip_diretorio_xml_orn_destino = Configuracao.obter("ip_diretorio_xml_orn_destino")
    dominio_usuario_senha_local = Configuracao.obter("dominio_usuario_senha_local")

    if not ip_diretorio_xml_orn:
        logger.error("IP do diretório XML da ONR não configurado.")
        return redirect("home:pedido_certidao_listar_pedidos")

    print("Plataforma: ", platform.system())

    # DIRETORIOS A BAIXAR - EM CADA ID TEM A SUB PASTA DEFAULT - ARQUIVOS DO SITE DA ONR
    tipo_integracao = TipoIntegracao.objects.all()

    # percorrer e baixar todas as pastas
    for integracao in tipo_integracao:
        pk = integracao.pk
        subpasta = integracao.sub_pasta

        if subpasta:
            if platform.system() == "Linux":
                print("Sistema operacional é Linux.")
                command = (
                    "smbclient "
                    + str(ip_diretorio_xml_orn)
                    + ' -U "'
                    + str(dominio_usuario_senha_local)
                    + '" -c "prompt; lcd '
                    + str(ip_diretorio_xml_orn_destino)
                    + "; cd "
                    + str(subpasta)
                    + '; mget *.xml"'
                )
                print("Comando linux:", command)

            # Executar o comando usando subprocess
            try:
                if platform.system() == "Linux":
                    result = subprocess.run(
                        command,
                        shell=True,
                        check=True,
                        capture_output=True,
                        text=True,
                    )

                arquivo_baixado = (
                    str(ip_diretorio_xml_orn_destino) + str(subpasta) + ".xml"
                )

                print("Comando executado com sucesso: Baixado: ", arquivo_baixado)

                # Verificar se houve erro na execução do comando
                if platform.system() == "Linux" and result.returncode != 0:
                    print("Nao baixado o comando: ", str(subpasta))

                # GERAR CERTIDAO e GRAVAR NO BANCO DE DADOS
                try:
                    gerar_certidao_webservice_onr(
                        request,
                        pk,
                        str(ip_diretorio_xml_orn_destino),
                        str(subpasta + ".xml"),
                    )
                except:
                    print("Erro no: ", pk, arquivo_baixado)

            except subprocess.CalledProcessError as e:
                gerar_certidao_webservice_onr(
                    request,
                    pk,
                    str(ip_diretorio_xml_orn_destino),
                    str(subpasta + ".xml"),
                )

                logger.info(f"Erro ao executar o comando: {e}")
                print("Saída de erro: ", str(subpasta))
                print(e.stderr)

    # RETORNAR PARA O VER PEDIDO CERTIDAO
    # url = reverse("home:pedido_certidao_listar_pedidos")
    # return redirect(url)
    return redirect(
        request.headers.get("referer", "home:pedido_certidao_listar_pedidos"),
    )


@api_view(["GET"])
def verificar_webservice_onr_api(request):
    """API para verificar e baixar arquivos do webservice da ONR."""
    # Variáveis de configuração
    ip_diretorio_xml_orn = Configuracao.obter("ip_diretorio_xml_orn")
    ip_diretorio_xml_orn_destino = Configuracao.obter("ip_diretorio_xml_orn_destino")
    dominio_usuario_senha_local = Configuracao.obter("dominio_usuario_senha_local")

    # Verificação da plataforma
    sistema_operacional = platform.system()
    logger.info(f"Plataforma: {sistema_operacional}")

    # Obtenção de tipos de integração
    tipo_integracao = TipoIntegracao.objects.all()

    # Processamento dos tipos de integração
    for integracao in tipo_integracao:
        pk = integracao.pk
        subpasta = integracao.sub_pasta

        if subpasta and sistema_operacional == "Linux":
            command = (
                f'smbclient {ip_diretorio_xml_orn} -U "{dominio_usuario_senha_local}" '
                f'-c "prompt; lcd {ip_diretorio_xml_orn_destino}; cd {subpasta}; mget *.xml"'
            )
            logger.info(f"Comando Linux: {command}")

            # Execução do comando
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                arquivo_baixado = f"{ip_diretorio_xml_orn_destino}{subpasta}.xml"
                logger.info(
                    f"Comando executado com sucesso: Baixado: {arquivo_baixado}",
                )

                # Verificação de erro na execução do comando
                if result.returncode != 0:
                    logger.error(f"Nao baixado o comando: {subpasta}")

                # Chamada para gerar a certidão
                try:
                    gerar_certidao_webservice_onr(
                        request,
                        pk,
                        ip_diretorio_xml_orn_destino,
                        f"{subpasta}.xml",
                    )
                except Exception as e:
                    logger.exception(f"Erro ao gerar certidão para {pk}: {e!s}")

            except subprocess.CalledProcessError as e:
                gerar_certidao_webservice_onr(
                    request,
                    pk,
                    ip_diretorio_xml_orn_destino,
                    f"{subpasta}.xml",
                )
                logger.exception(f"Erro ao executar o comando: {e}")
                logger.exception(f"Saída de erro: {subpasta}")
                logger.exception(f"Erro: {e.stderr}")

    return Response({"message": "Processamento concluído"}, status=status.HTTP_200_OK)


def assinar_xml(request, selo_xml_id):
    documento = get_object_or_404(SeloXML, pk=selo_xml_id)
    xml_path = documento.arquivo_xml.path
    key_path = "path/to/private_key.pem"
    cert_path = "path/to/certificate.pem"
    output_path = f"{os.path.splitext(xml_path)[0]}_signed.xml"

    assinar_xml(xml_path, key_path, cert_path, output_path)

    documento.arquivo_assinado = output_path
    documento.save()

    return HttpResponse("Documento assinado com sucesso.")


class Livro01ProtocoloViewSet(viewsets.ModelViewSet):
    queryset = Livro01Protocolo.objects.all()
    serializer_class = ProtocoloSerializer


import django_filters


class PedidoCertidaoImovelViewSetFilter(django_filters.FilterSet):
    class Meta:
        model = PedidoCertidaoImovel
        fields = ["numero_registro", "tipo_registro"]


class PedidoCertidaoImovelViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoCertidaoImovelSerializer
    filter_backends = [
        DjangoFilterBackend,
        rest_filters.OrderingFilter,
    ]
    filterset_class = PedidoCertidaoImovelViewSetFilter
    ordering_fields = ["pedido_id"]

    def get_queryset(self):
        queryset = PedidoCertidaoImovel.objects.all()
        pk = self.kwargs.get("pk")
        if pk:
            queryset = queryset.filter(pk=pk)
        return queryset


def protocolo_confirmar_entrega_view(request, pk):
    """REGISTRAR A ENTREGA PARA O CLIENTE."""
    protocolo = get_object_or_404(Livro01Protocolo, pk=pk)

    try:
        msg = protocolo.registrar_andamento_protocolo_entregue(usuario=request.user)
        messages.success(request, msg)
    except Exception as e:
        messages.error(request, f"Confirmado Entrega do Protocolo: {e}")
        logger.exception("Erro ao Entregar o Protocolo")

    return redirect(protocolo.get_absolute_url())


@login_required
def caixa_verificar_diferenca_direto_sistema_antigo(
    request,
    numero_protocolo=0,
    mensagem="0",
):
    # Receber o número de protocolo informado
    with transaction.atomic(), firebird.FbConnection():
        try:
            # # FILTRAR PEDIDO - ORIGINAL - CALCULAR DIFERENCA
            # protocolo = Livro01Protocolo.objects.filter(
            #     numero_protocolo=numero_protocolo,
            # ).first()

            # # DATA FICTICIA PARA NAO ATRAPALHAR OS RELATORIOS
            # data_pagamento = "2000-01-01"

            # # FINALIZAR NO PRIME PARA NAO TER PROBLEMAS ENQUANTO SINCRONIZA O SISTEMA ANTIGO
            # Financeiro.criar_financeiro_despesa_receita(
            #     pedido_id=protocolo.pedido.id,
            #     pedido_certidao_id=None,
            #     tipo_transacao_id=1,
            #     tipo_categoria_financeira_id=1,
            #     tipo_operacao_financeira_id=1,
            #     colaborador_id=1,
            #     colaborador_confirmado_id=None,
            #     data_transacao=data_pagamento,
            #     data_original_transacao=None,
            #     valor_transacao=protocolo.valor_diferenca,
            #     dadp="N",
            #     imposto_renda="N",
            #     descricao="FINALIZACAO INTERNA",
            #     user_id=1,
            #     quantidade_parcelas=1,
            #     recorrencia_id=1,
            # )

            url = reverse(
                "home:pedido_protocolo_caixa_view_sistema_antigo",
                args=[numero_protocolo],
            )
            return redirect(url)

        except Exception:
            msg = "Não foi possível importar o protocolo informado"
            logger.exception(msg)


def recolhido_sistema_antigo_protocolo(request, numero_protocolo):
    """DAR BAIXAR SISTEMA ANTIGO OS VALORES DE PROTOCOLO QUE ESTIVEREM EM ABERTO."""
    print("Dar baixa sistema antigo. Protocolo:", numero_protocolo)

    db = firebird.FbConnection()
    db.begin_transaction()

    # OBTER DADOS DO PROTOCOLO
    protocolo_fb = firebird.get_protocolo_fb(numero_protocolo, db) or None

    """ DAR BAIXA NO PROTOCOLO FIREBIRD. """
    if protocolo_fb:
        firebird.baixar_valor_acerto_final_no_fb(protocolo_fb["CHAVE_PEDIDOS"], db)

    db.commit()

    " VOLTAR OU FICAR NA MESMA PAGINA"
    return redirect(request.META.get("HTTP_REFERER", "/"))


def pedido_protocolo_caixa_sistema_antigo(request, numero_protocolo):
    template_name = "form-pagamento-protocolo.html"
    logger.debug(
        "Iniciando processo de pedido de protocolo caixa para o número de protocolo: %s",
        numero_protocolo,
    )

    try:
        with firebird.FbConnection() as db:
            caixa_id = db.sequence("CAIXA_SEQ").proximo
            logger.debug("Caixa ID obtido: %s", caixa_id)
    except Exception as e:
        logger.exception("Erro ao obter caixa ID: %s", e)
        return render(
            request,
            "error.html",
            {"message": "Erro ao conectar ao sistema de caixa"},
        )

    try:
        protocolo: Livro01Protocolo = Livro01Protocolo.objects.get(
            numero_protocolo=numero_protocolo,
        )
        logger.debug("Protocolo encontrado: %s", protocolo)
    except Livro01Protocolo.DoesNotExist:
        logger.exception("Protocolo com número %s não encontrado.", numero_protocolo)
        return render(request, "error.html", {"message": "Protocolo não encontrado"})
    except Exception as e:
        logger.exception("Erro ao obter protocolo: %s", e)
        return render(
            request,
            "error.html",
            {"message": "Erro ao acessar dados do protocolo"},
        )

    try:
        valor_atual_protocolo = protocolo.get_valor_final_sistema_antigo(db) or 0
        valor_total_pago_protocolo = protocolo.get_valor_acerto_sistema_antigo(db) or 0
        valor_transacao = valor_atual_protocolo - valor_total_pago_protocolo
        valor_transacao = Decimal(valor_transacao)
    except InvalidOperation as e:
        logger.exception("Erro ao converter valor da transação para Decimal: %s", e)
        valor_transacao = Decimal(0)
    except Exception as e:
        logger.exception("Erro ao calcular valores do protocolo: %s", e)
        messages.error(request, f"Erro ao calcular valores do protocolo: {e}")
        return render(
            request,
            "error.html",
            {"message": "Erro ao calcular valores do protocolo"},
        )

    if request.method == "POST":
        try:
            referer = request.headers.get("referer")
            logger.debug("Referer: %s", referer)

            valor_transacao = helpers.retirar_dados_valor_monetario(
                request.POST.get("valor_diferenca_receber"),
            )
            data_original = request.POST.get("data_original")
            data_agendamento = request.POST.get("data_agendamento")
            tipo_operacao_financeira_id = request.POST.get("operacao_financeira_id")
            descricao = request.POST.get("descricao")
            nome_pagador = request.POST.get("nome_pagador")

            logger.debug(
                "Dados do POST recebidos: valor_transacao=%s, data_original=%s, data_agendamento=%s, tipo_operacao_financeira_id=%s, descricao=%s, nome_pagador=%s",
                valor_transacao,
                data_original,
                data_agendamento,
                tipo_operacao_financeira_id,
                descricao,
                nome_pagador,
            )

            if Decimal(valor_transacao) < 0:
                tipo_transacao_id = TipoTransacaoFinanceira.get_devolucao().id
            else:
                tipo_transacao_id = TipoTransacaoFinanceira.get_receita().id

            colaborador_financeiro_id = request.user.id

            protocolo.enviar_para_pagamento_caixa(
                valor_transacao=valor_transacao,
                tipo_operacao_financeira_id=tipo_operacao_financeira_id,
                tipo_transacao_id=tipo_transacao_id,
                descricao=descricao,
                nome_pagador=nome_pagador,
                data_original=data_original,
                colaborador_financeiro_id=colaborador_financeiro_id,
            )

            logger.debug(
                "Enviado para pagamento no caixa do FB: valor_transacao=%s, tipo_operacao_financeira_id=%s, tipo_transacao_id=%s, descricao=%s, nome_pagador=%s, data_original=%s, colaborador_financeiro_id=%s",
                valor_transacao,
                tipo_operacao_financeira_id,
                tipo_transacao_id,
                descricao,
                nome_pagador,
                data_original,
                colaborador_financeiro_id,
            )

            pedido_de_protocolo_enviar_ao_caixa_no_firebird(
                request=request,
                numero_protocolo=protocolo.numero_protocolo,
                valor_transacao=valor_transacao,
            )

            if data_agendamento:
                protocolo.data_agendamento = data_agendamento
                protocolo.save()

            logger.debug(
                "Protocolo atualizado com data de agendamento: %s",
                data_agendamento,
            )

            """ DAR BAIXA NO PROTOCOLO FIREBIRD. """
            firebird.acertar_valor_pago_firebird(
                protocolo.numero_protocolo,
                valor_transacao,
                db,
            )

            return redirect(referer)
        except Exception as e:
            logger.exception("Erro ao processar POST: %s", e)
            return render(
                request,
                "error.html",
                {"message": "Erro ao processar a transação"},
            )

    if request.method == "GET":
        try:
            nome_requerente = protocolo.nome_apresentante
            operacao_financeira = TipoOperacaoFinanceira.objects.filter(
                grupo_entradas="S",
            ).order_by("descricao")

            data_original = helpers.get_data_util_em_x_dias(timezone.now().date(), 0)
            data_original = data_original.strftime("%Y-%m-%d")

            caption = "Pagamento do Protocolo nº: " + str(numero_protocolo)

            context = {
                "protocolo": protocolo,
                "operacao_financeira": operacao_financeira,
                "data_original": data_original,
                "caption": caption,
                "valor_atual_protocolo": valor_atual_protocolo,
                "valor_total_pago_protocolo": valor_total_pago_protocolo,
                "valor_diferenca": valor_transacao,
                "nome_requerente": nome_requerente,
                "nome_interessado": "",
                "mensagem": "",
            }

            logger.debug("Contexto para renderização do template GET: %s", context)

            return render(request, template_name, context)
        except Exception as e:
            logger.exception("Erro ao processar GET: %s", e)
            return render(
                request,
                "error.html",
                {"message": "Erro ao carregar a página de pagamento"},
            )

    return None


# Atualizar no prime os protocolos ANTERIOR E POSTERIOR
#     print("Protocolo anterior e posterior atualizados com sucesso.")
def atualizar_protocolo_anterior(numero_protocolo_anterior, numero_protocolo_posterior):
    def get_or_import_protocolo(numero_protocolo):
        try:
            return Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)
        except Livro01Protocolo.DoesNotExist:
            print(f"Protocolo {numero_protocolo} não encontrado. Importando...")
            db = firebird.FbConnection()
            db.begin_transaction()
            firebird.importar_protocolo_por_numero_fb(
                numero_protocolo=numero_protocolo,
                tipo_importacao="P",
                db=db,
            )
            db.commit()
            return Livro01Protocolo.objects.get(numero_protocolo=numero_protocolo)

    anterior = get_or_import_protocolo(numero_protocolo_anterior)
    posterior = get_or_import_protocolo(numero_protocolo_posterior)

    anterior.numero_protocolo_posterior = posterior
    anterior.save()

    posterior.numero_protocolo_anterior = anterior
    posterior.save()

    print("Protocolo anterior e posterior atualizados com sucesso.")


# ADEQUACOES PARA PROTOCOLO ANTIGO E NOVO
def adqueacoes_reprotocolo(protocolo_anterior, protocolo_posterior):
    # POSTGRESQL - ATUALIZAR NOVO E ANTERIOR
    atualizar_protocolo_anterior(protocolo_anterior, protocolo_posterior)

    # FIREBIRD - ATUALIZAR EMAIL DO FIREBIRD
    texto_protocolo_posterior = str(protocolo_posterior)
    texto_protocolo_posterior = (
        "'Protocolo Posterior: " + texto_protocolo_posterior + "'"
    )

    # CORRECOES NO FIREBIRD
    command = """
        UPDATE PEDIDOS
        SET EMAIL = :texto_protocolo_posterior
        WHERE CHAVE_PEDIDOS = (SELECT CHAVE_PEDIDOS FROM PROTOCOLOS WHERE NROORDEM = :protocolo_anterior)
    """

    command = str(command).replace(
        ":texto_protocolo_posterior",
        texto_protocolo_posterior,
    )

    command = str(command).replace(":protocolo_anterior", str(protocolo_anterior))

    try:
        firebird.atualizar_dados_firebird(command)
    except:
        pass


# LIMPAR SELO DO SQLSERVER
def limpar_selo_sqlServer(numero_selo):
    from apps.home.services import sqlserver

    with transaction.atomic():
        try:
            return sqlserver.limpar_selo(numero_selo)

        except Exception as e:
            logger.exception(f"Erro ao limpar selos no sql_server: {e}")
            raise

            return False


# LIMPAR SELO DO SISTEMA
def limpar_selo_sistema(numero_selo):
    # Atualizando os selos diretamente no banco de dados
    SeloEletronico.objects.filter(
        codigo_sequencial_unico=numero_selo,
        # certidao_id=certidao_id,
        # enviado_tribunal=False,
    ).update(
        pedido_item_id=None,
        certidao_id=None,
        utilizado_em=None,
        selo_de_consulta="N",
    )


@login_required
def criar_projeto(request):
    if request.method == "POST":
        form = CriarProjetoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    logger.debug(f"{request.user} criando projeto ...")

                    # Criando o pedido sem salvar
                    projeto: Projeto = form.save(commit=False)
                    # projeto.criado_por = request.user

                    # Salvando o pedido com o apresentante vinculado
                    projeto.save()

                    logger.debug("Projeto salvo com sucesso....")
                    messages.success(
                        request,
                        "Projeto criado com sucesso!",
                    )

                    " VOLTAR OU FICAR NA MESMA PAGINA"
                    return redirect(request.META.get("HTTP_REFERER", "/"))

            except Exception as e:
                logger.exception(f"Erro ao criar projeto: {e!s}")
                messages.error(
                    request,
                    "Ocorreu um erro ao criar o projeto.",
                )
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarProjetoForm()

    projetos = Projeto.objects.all()

    context = {
        "form": form,
        "title": "Novo Projeto",
        "segment": "criar_projeto",
        "parent": "projeto",
        "projetos": projetos,
        "total_projetos": projetos.count(),
    }

    return render(request, "certidoes/projeto_create_form.html", context)


@login_required
def criar_bateria(request):
    if request.method == "POST":
        form = CriarBateriaForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    logger.debug(f"{request.user} criando bateria ...")

                    # Criando o pedido sem salvar
                    bateria: Bateria = form.save(commit=False)
                    # projeto.criado_por = request.user

                    # Salvando o pedido com o apresentante vinculado
                    bateria.save()

                    logger.debug("Bateria salvo com sucesso....")
                    messages.success(
                        request,
                        "Bateria criado com sucesso!",
                    )

                    " VOLTAR OU FICAR NA MESMA PAGINA"
                    return redirect(request.META.get("HTTP_REFERER", "/"))

            except Exception as e:
                logger.exception(f"Erro ao criar bateria: {e!s}")
                messages.error(
                    request,
                    "Ocorreu um erro ao criar o bateria.",
                )
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarBateriaForm()

    baterias = Bateria.objects.all()

    context = {
        "form": form,
        "title": "Nova Bateria",
        "segment": "criar_bateria",
        "parent": "bateria",
        "baterias": baterias,
        "total_baterias": baterias.count(),
    }

    return render(request, "certidoes/bateria_create_form.html", context)


@login_required
def criar_hidrogenio(request):
    if request.method == "POST":
        form = CriarHidrogenioForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    logger.debug(f"{request.user} criando hidrogenio ...")

                    # Criando o pedido sem salvar
                    hidrogenio: Hidrogenio = form.save(commit=False)
                    # projeto.criado_por = request.user

                    # Salvando o pedido com o apresentante vinculado
                    hidrogenio.save()

                    logger.debug("hidrogenio salvo com sucesso....")
                    messages.success(
                        request,
                        "Hidrogenio criado com sucesso!",
                    )

                    " VOLTAR OU FICAR NA MESMA PAGINA"
                    return redirect(request.META.get("HTTP_REFERER", "/"))

            except Exception as e:
                logger.exception(f"Erro ao criar hidrogenio: {e!s}")
                messages.error(
                    request,
                    "Ocorreu um erro ao criar o hidrogenio.",
                )
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarHidrogenioForm()

    hidrogenios = Hidrogenio.objects.all()

    context = {
        "form": form,
        "title": "Novo Hidrogênio",
        "segment": "criar_hidrogenio",
        "parent": "hidrogenio",
        "hidrogenios": hidrogenios,
        "total_hidrogenios": hidrogenios.count(),
    }

    return render(request, "certidoes/hidrogenio_create_form.html", context)


@login_required
def criar_inversor(request):
    if request.method == "POST":
        form = CriarInversorForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    logger.debug(f"{request.user} criando inversor ...")

                    # Criando o pedido sem salvar
                    hidrogenio: Inversor = form.save(commit=False)
                    # projeto.criado_por = request.user

                    # Salvando o pedido com o apresentante vinculado
                    hidrogenio.save()

                    logger.debug("inversor salvo com sucesso....")
                    messages.success(
                        request,
                        "Inversor criado com sucesso!",
                    )

                    " VOLTAR OU FICAR NA MESMA PAGINA"
                    return redirect(request.META.get("HTTP_REFERER", "/"))

            except Exception as e:
                logger.exception(f"Erro ao criar inversor: {e!s}")
                messages.error(
                    request,
                    "Ocorreu um erro ao criar o inversor.",
                )
        else:
            logger.error(f"Erros no formulário: {form.errors.as_json()}")
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarInversorForm()

    hidrogenios = Inversor.objects.all()

    context = {
        "form": form,
        "title": "Novo Inversor",
        "segment": "criar_inversor",
        "parent": "inversor",
        "hidrogenios": hidrogenios,
        "total_hidrogenios": hidrogenios.count(),
    }

    return render(
        request,
        "certidoes/inversor_create_form.html",
        context,
    )


@login_required
def criar_painel_solar(request):
    if request.method == "POST":
        form = CriarPainelForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    logger.debug(f"{request.user} criando painel solar ...")

                    # Criando o pedido sem salvar
                    hidrogenio: PainelSolar = form.save(commit=False)
                    # projeto.criado_por = request.user

                    # Salvando o pedido com o apresentante vinculado
                    hidrogenio.save()

                    logger.debug("painel solar salvo com sucesso....")
                    messages.success(
                        request,
                        "Painel solar criado com sucesso!",
                    )

                    " VOLTAR OU FICAR NA MESMA PAGINA"
                    return redirect(request.META.get("HTTP_REFERER", "/"))

            except Exception as e:
                logger.exception(f"Erro ao criar painel solar: {e!s}")
                messages.error(
                    request,
                    "Ocorreu um erro ao criar o painel solar.",
                )
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarPainelForm()

    hidrogenios = PainelSolar.objects.all()

    context = {
        "form": form,
        "title": "Novo Painel Solar",
        "segment": "criar_painel_solar",
        "parent": "painel_solar",
        "hidrogenios": hidrogenios,
        "total_hidrogenios": hidrogenios.count(),
    }

    return render(
        request,
        "certidoes/painel_solar_create_form.html",
        context,
    )


@login_required
def criar_controlador_carga(request):
    if request.method == "POST":
        form = CriarHidrogenioForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    logger.debug(f"{request.user} criando controlador de carga ...")

                    # Criando o pedido sem salvar
                    hidrogenio: Hidrogenio = form.save(commit=False)
                    # projeto.criado_por = request.user

                    # Salvando o pedido com o apresentante vinculado
                    hidrogenio.save()

                    logger.debug("Controlador carga salvo com sucesso....")
                    messages.success(
                        request,
                        "Controlador de carga criado com sucesso!",
                    )

                    " VOLTAR OU FICAR NA MESMA PAGINA"
                    return redirect(request.META.get("HTTP_REFERER", "/"))

            except Exception as e:
                logger.exception(f"Erro ao criar controlador de carga: {e!s}")
                messages.error(
                    request,
                    "Ocorreu um erro ao criar o controlador carga.",
                )
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarHidrogenioForm()

    hidrogenios = Hidrogenio.objects.all()

    context = {
        "form": form,
        "title": "Novo Controlador de Carga ",
        "segment": "criar_controlador_carga",
        "parent": "controlador_carga",
        "hidrogenios": hidrogenios,
        "total_hidrogenios": hidrogenios.count(),
    }

    return render(
        request,
        "certidoes/controlador_carga_create_form.html",
        context,
    )


class HidrogenioUpdateView(LoginRequiredMixin, UpdateView):
    model = Hidrogenio
    fields = [
        "numero_hidrogenio",
        "marca",
    ]

    template_name = "certidoes/hidrogenio_update_form.html"

    def get_form(self, form_class=None):
        return super().get_form(form_class)

    def form_valid(self, form):
        # Modifique os valores dos campos aqui antes de salvar
        projeto = form.save(commit=False)  # Não salva ainda no banco

        # Aqui você pode adicionar qualquer lógica de negócio antes de salvar
        projeto.save()  # Agora salva as mudanças no banco de dados

        return redirect(reverse("home:criar_hidrogenio"))


class InversorUpdateView(LoginRequiredMixin, UpdateView):
    model = Inversor
    fields = [
        "numero_hidrogenio",
        "marca",
        "modelo",
        "tipo_de_celula",
        "pot_max_entrada",
        "n_mppta",
        "corr_dc_maxa",
        "corrente_dc_max_totala",
        "intervalo_tensao_dc_inicial",
        "intervalo_tensao_dc_final",
        "tensao_dc_nominal",
        "intervalo_tensao_mppt_inicial",
        "intervalo_tensao_mppt_final",
        "pot_ac_maxa",
        "corrente_falha_maxima",
        "duracao_maxima_falha",
        "corrente_ac_maxa",
        "eficiencia_maxa",
        "intervalo_tensao_ac_inicial",
        "intervalo_tensao_ac_final",
        "frequencia",
        "distorcoes_harmonicas_totais",
        "fator_de_potencia_fpa",
    ]

    template_name = "certidoes/inversor_update_form.html"

    def get_form(self, form_class=None):
        return super().get_form(form_class)

    def form_valid(self, form):
        # Modifique os valores dos campos aqui antes de salvar
        projeto = form.save(commit=False)  # Não salva ainda no banco

        # Aqui você pode adicionar qualquer lógica de negócio antes de salvar
        projeto.save()  # Agora salva as mudanças no banco de dados

        return redirect(reverse("home:criar_inversor"))


class PainelUpdateView(LoginRequiredMixin, UpdateView):
    model = PainelSolar
    fields = [
        "numero_hidrogenio",
        "marca",
        "modelo",
        "tipo_de_celula",
        "numero_celulas",
        "isc",
        "pontencial_nominal",
        "tensao_maxima_saida",
        "tensao_nomimal_saida",
        "corrente_nominal_saida",
        "corrente_maxima_potencia",
        "eficiencia",
        "isc",
        "vmp",
        "mp",
        "coef_temp_pot_max_upmax",
        "coef_temp_voc_uvoc",
        "coef_temp_isc_uisc",
    ]

    template_name = "certidoes/painel_update_form.html"

    def get_form(self, form_class=None):
        return super().get_form(form_class)

    def form_valid(self, form):
        # Modifique os valores dos campos aqui antes de salvar
        projeto = form.save(commit=False)  # Não salva ainda no banco

        # Aqui você pode adicionar qualquer lógica de negócio antes de salvar
        projeto.save()  # Agora salva as mudanças no banco de dados

        return redirect(reverse("home:criar_painel_solar"))

# class ProjetoVisualizarView(LoginRequiredMixin, UpdateView):
#     model = Projeto

#     fields = [
#         "nome_projeto",
#         "localidade",
#         "data_inicio_projeto",
#         "data_fim_projeto",
#         "latitude",
#         "longitude",
#         # "fotovoltaico",
#         # "biogas",
#         # "hidrogenio",
#         # "baterias",
#         "observacoes",
#     ]

#     template_name = "certidoes/projeto_visualizar_form.html"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # filtra todos os ProjetosPainelSolar deste projeto
#         context["painel_solar_list"] = ProjetoPainelSolar.objects.filter(
#             projeto=self.object,
#         ).select_related("painelsolar")

#         context["inversor_list"] = ProjetoInversor.objects.filter(
#             projeto=self.object,
#         ).select_related("inversor")

#         return context

#     def get_form(self, form_class=None):
#         return super().get_form(form_class)

#     def form_valid(self, form):
#         # Modifique os valores dos campos aqui antes de salvar
#         projeto = form.save(commit=False)  # Não salva ainda no banco

#         # Aqui você pode adicionar qualquer lógica de negócio antes de salvar
#         projeto.save()  # Agora salva as mudanças no banco de dados

#         return redirect(reverse("home:criar_projeto"))
class ProjetoVisualizarView(LoginRequiredMixin, UpdateView):
    model = Projeto
    form_class = ProjetoForm  # <-- alterado aqui
    template_name = "certidoes/projeto_visualizar_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["painel_solar_list"] = ProjetoPainelSolar.objects.filter(
            projeto=self.object,
        ).select_related("painelsolar")
        context["inversor_list"] = ProjetoInversor.objects.filter(
            projeto=self.object,
        ).select_related("inversor")
        return context

    def form_valid(self, form):
        projeto = form.save(commit=False)

        projeto.save()
        return redirect(reverse("home:criar_projeto"))


@login_required
def painel_importar_excell_view(request):
    from apps.home.models.models_certidoes import CecModule

    numero_hidrogenio = 2

    # Pegando todos os paineis novos
    paineis_novos = CecModule.objects.filter(stc__isnull=False)
    for painel in paineis_novos:
        print(painel.name)

        # em qualquer lugar do seu código Django
        painel = PainelSolar.objects.create(
            numero_hidrogenio=numero_hidrogenio,
            marca=painel.manufacturer,
            modelo=painel.name,
            tipo_de_celula=painel.technology,
            numero_celulas=painel.n_s,
            pontencial_nominal=painel.stc,
            eficiencia="16.63",
            mp=painel.i_mp_ref,
            isc=painel.i_sc_ref,
            vmp=painel.v_mp_ref,
            coef_temp_isc_uisc=painel.alpha_sc,
            coef_temp_pot_max_upmax="-1.220",
            coef_temp_voc_uvoc=painel.beta_oc,
        )
        numero_hidrogenio = numero_hidrogenio + 1

        # print(painel.manufacturer)

        # print(painel.bifacial)
        # print(painel.stc)
        # print(painel.ptc)
        # print(painel.a_c)
        # print(painel.length)
        # print(painel.width)
        # print(painel.n_s)
        # print(painel.i_sc_ref)
        # print(painel.v_oc_ref)
        # print(painel.i_mp_ref)
        # print(painel.v_mp_ref)
        # print(painel.alpha_sc)
        # print(painel.beta_oc)
        # print(painel.t_noct)
        # print(painel.a_ref)
        # print(painel.i_l_ref)
        # print(painel.i_o_ref)
        # print(painel.r_s)
        # print(painel.r_sh_ref)
        # print(painel.adjust)
        # print(painel.gamma_pmp)
        # print(painel.bipv)
        # print(painel.version)
        # print(painel.date)



    " VOLTAR OU FICAR NA MESMA PAGINA"
    return redirect(request.META.get("HTTP_REFERER", "/"))

def download_excel_relatorio(request):
    df = gerar_relatorio_projetos()
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = "attachment; filename=relatorio_fotovoltaico.xlsx"
    df.to_excel(response, index=False)
    return response


def parse_float(val):
    try:
        return float(str(val).replace(",", "."))
    except:
        return 0.0

def horas_sol(inicio, fim):
    try:
        h1 = int(inicio.split(":")[0])
        h2 = int(fim.split(":")[0])
        return max(1, h2 - h1)
    except:
        return 5

def gerar_relatorio_projetos():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, nome_projeto, area_disponível_instalacao, horario_inicio_sol_pleno, horario_fim_sol_pleno
            FROM home_projeto
            WHERE fotovoltaico = TRUE AND area_disponível_instalacao IS NOT NULL
        """)
        projetos = dictfetchall(cursor)

        cursor.execute("""
            SELECT id, modelo, pontencial_nominal, eficiencia
            FROM home_painelsolar
            WHERE is_active = TRUE
        """)
        paineis = dictfetchall(cursor)

    resultados = []

    for projeto in projetos:
        area_m2 = parse_float(projeto["area_disponível_instalacao"])
        horas = horas_sol(str(projeto["horario_inicio_sol_pleno"]), str(projeto["horario_fim_sol_pleno"]))
        max_paineis = int(area_m2 // AREA_POR_PAINEL)

        for painel in paineis:
            potencia = parse_float(painel["pontencial_nominal"])
            eficiencia = parse_float(painel["eficiencia"]) or 18
            if potencia <= 0:
                continue

            potencia_kw = potencia / 1000
            producao = potencia_kw * horas * 30 * (eficiencia / 100)
            if producao == 0:
                continue

            qtde = math.ceil(DEFAULT_GASTO_KWH / producao)
            if qtde > max_paineis:
                continue

            custo_unit = potencia_kw * PRECO_KW
            custo_total = custo_unit * qtde
            producao_total = producao * qtde * 12 * 25
            custo_por_kwh = custo_total / producao_total

            resultados.append({
                "Projeto": projeto["nome_projeto"],
                "Painel": painel["modelo"],
                "Potência (W)": potencia,
                "Eficiência (%)": eficiencia,
                "Qtd Painéis": qtde,
                "Produção Mensal (kWh)": round(producao * qtde, 2),
                "Custo Total (R$)": round(custo_total, 2),
                "Custo por kWh (R$)": round(custo_por_kwh, 4),
            })

    return pd.DataFrame(resultados)

def dictfetchall(cursor):
    """Converte resultado em lista de dicionários"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

def sugerir_equipamento_fotovoltaico(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)

    # Coleta os dados do banco
    queryset = PainelSolar.objects.all().values(
        "marca", "modelo", "mp", "eficiencia", "valor_total_onr",
    )
    df = pd.DataFrame(list(queryset))

    # Conversões
    df["mp"] = pd.to_numeric(df["mp"], errors="coerce")
    df["valor_total_onr"] = pd.to_numeric(df["valor_total_onr"], errors="coerce").fillna(0)
    df = df[df["mp"].notnull() & (df["mp"] > 0)]

    # Conversão dos parâmetros do projeto (todos como float ou int para compatibilidade com Pandas)
    consumo_mensal_kwh = float(projeto.consumo_mensal_kwh or 500)
    HORAS_SOL = float(projeto.horas_sol_dia or 4.5)
    FATOR_PERDA = float(projeto.fator_perda or 0.8)
    DIAS = int(projeto.dias_mes or 30)
    VIDA = int(projeto.vida_util_anos or 25)

    # Cálculos usando somente float
    demanda_diaria_kwh = consumo_mensal_kwh / DIAS
    potencia_necessaria = demanda_diaria_kwh / (HORAS_SOL * FATOR_PERDA)

    # Evita TypeError aqui
    df["qtd_paineis"] = (potencia_necessaria * 1000 / df["mp"]).apply(lambda x: int(x) + 1)
    df["geracao_total_kwh"] = df["mp"] * HORAS_SOL * DIAS * 12 * VIDA * FATOR_PERDA / 1000
    df["custo_total"] = df["valor_total_onr"] * df["qtd_paineis"]
    df["custo_kwh"] = df["custo_total"] / (df["geracao_total_kwh"] * df["qtd_paineis"])

    # Verifica se os valores de preço foram preenchidos
    if df["valor_total_onr"].max() == 0:
        sugestoes = df.sort_values("mp", ascending=False).head(10)
        sem_precos = True
    else:
        sugestoes = df[df["valor_total_onr"] > 0].sort_values("custo_kwh").head(10)
        sem_precos = False

    return render(request, "certidoes/sugestoes_ia.html", {
        "sugestoes": sugestoes,
        "projeto": projeto,
        "sem_precos": sem_precos,
    })

def exportar_sugestoes(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)

    # Repetimos a lógica de sugestão
    queryset = PainelSolar.objects.all().values("marca", "modelo", "mp", "eficiencia", "valor_total_onr")
    df = pd.DataFrame(list(queryset))

    df["mp"] = pd.to_numeric(df["mp"], errors="coerce")
    df["valor_total_onr"] = pd.to_numeric(df["valor_total_onr"], errors="coerce").fillna(0)
    df = df[df["mp"].notnull() & (df["mp"] > 0)]

    consumo_mensal_kwh = float(projeto.consumo_mensal_kwh or 500)
    HORAS_SOL = float(projeto.horas_sol_dia or 4.5)
    FATOR_PERDA = float(projeto.fator_perda or 0.8)
    DIAS = int(projeto.dias_mes or 30)
    VIDA = int(projeto.vida_util_anos or 25)

    demanda_diaria_kwh = consumo_mensal_kwh / DIAS
    potencia_necessaria = demanda_diaria_kwh / (HORAS_SOL * FATOR_PERDA)

    df["qtd_paineis"] = (potencia_necessaria * 1000 / df["mp"]).apply(lambda x: int(x) + 1)
    df["geracao_total_kwh"] = df["mp"] * HORAS_SOL * DIAS * 12 * VIDA * FATOR_PERDA / 1000
    df["custo_total"] = df["valor_total_onr"] * df["qtd_paineis"]
    df["custo_kwh"] = df["custo_total"] / (df["geracao_total_kwh"] * df["qtd_paineis"])

    if df["valor_total_onr"].max() == 0:
        sugestoes = df.sort_values("mp", ascending=False).head(10)
    else:
        sugestoes = df[df["valor_total_onr"] > 0].sort_values("custo_kwh").head(10)

    formato = request.GET.get("formato", "xlsx")

    if formato == "xlsx":
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="sugestoes_{projeto_id}.xlsx"'
        sugestoes.to_excel(response, index=False)
        return response

    return HttpResponse("Formato não suportado", status=400)



# def exportar_sugestoes_pdf(request, projeto_id):
#     projeto = get_object_or_404(Projeto, id=projeto_id)

#     # Lógica da IA (idêntica ao que já usamos)
#     queryset = PainelSolar.objects.all().values("marca", "modelo", "mp", "eficiencia", "valor_total_onr")
#     df = pd.DataFrame(list(queryset))
#     df["mp"] = pd.to_numeric(df["mp"], errors="coerce")
#     df["valor_total_onr"] = pd.to_numeric(df["valor_total_onr"], errors="coerce").fillna(0)
#     df = df[df["mp"].notnull() & (df["mp"] > 0)]

#     consumo_mensal_kwh = float(projeto.consumo_mensal_kwh or 500)
#     HORAS_SOL = float(projeto.horas_sol_dia or 4.5)
#     FATOR_PERDA = float(projeto.fator_perda or 0.8)
#     DIAS = int(projeto.dias_mes or 30)
#     VIDA = int(projeto.vida_util_anos or 25)

#     demanda_diaria_kwh = consumo_mensal_kwh / DIAS
#     potencia_necessaria = demanda_diaria_kwh / (HORAS_SOL * FATOR_PERDA)

#     df["qtd_paineis"] = (potencia_necessaria * 1000 / df["mp"]).apply(lambda x: int(x) + 1)
#     df["geracao_total_kwh"] = df["mp"] * HORAS_SOL * DIAS * 12 * VIDA * FATOR_PERDA / 1000
#     df["custo_total"] = df["valor_total_onr"] * df["qtd_paineis"]
#     df["custo_kwh"] = df["custo_total"] / (df["geracao_total_kwh"] * df["qtd_paineis"])

#     if df["valor_total_onr"].max() == 0:
#         sugestoes = df.sort_values("mp", ascending=False).head(10)
#         sem_precos = True
#     else:
#         sugestoes = df[df["valor_total_onr"] > 0].sort_values("custo_kwh").head(10)
#         sem_precos = False

#     formato = request.GET.get("formato", "xlsx")

#     if formato == "xlsx":
#         response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
#         response["Content-Disposition"] = f'attachment; filename="sugestoes_{projeto_id}.xlsx"'
#         sugestoes.to_excel(response, index=False)
#         return response

#     elif formato == "pdf":
#         html_string = render_to_string("certidoes/sugestoes_pdf.html", {
#             "sugestoes": sugestoes,
#             "projeto": projeto,
#             "sem_precos": sem_precos,
#         })

#         response = HttpResponse(content_type='application/pdf')
#         response['Content-Disposition'] = f'attachment; filename="sugestoes_{projeto_id}.pdf"'

#         with tempfile.NamedTemporaryFile(delete=True) as temp_pdf:
#             HTML(string=html_string).write_pdf(target=response)

#         return response

#     return HttpResponse("Formato não suportado", status=400)


def buscar_preco_mercado_livre(modelo: str) -> float | None:
    query = modelo.replace(" ", "+")
    url = f"https://lista.mercadolivre.com.br/{query}"

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        preco_element = soup.select_one(".ui-search-price__second-line .price-tag-fraction")

        if preco_element:
            preco_str = preco_element.text.replace(".", "").replace(",", ".")
            return float(preco_str)
    except Exception as e:
        print(f"Erro ao buscar preço (scraping) para '{modelo}': {e}")

    return None

def atualizar_precos_view(request):
    """Atualiza preços de painéis solares via Mercado Livre."""
    paineis = PainelSolar.objects.all()
    #paineis = PainelSolar.objects.filter(id=1)
    atualizados = 0

    for painel in paineis:
        preco = buscar_preco_mercado_livre(painel.modelo or "")
        if preco:
            painel.valor_total_onr = preco
            painel.save()
            atualizados += 1
        time.sleep(1.5)  # respeita limites da API

    messages.success(request, f"{atualizados} painéis atualizados com sucesso!")
    return redirect("home:projeto_listar")  # redirecione conforme sua estrutura

def grafico_custo_geracao(request):
    # Carrega e prepara os dados
    queryset = PainelSolar.objects.all().values("modelo", "mp", "valor_total_onr")
    df = pd.DataFrame(list(queryset))
    df["mp"] = pd.to_numeric(df["mp"], errors="coerce")
    df["valor_total_onr"] = pd.to_numeric(df["valor_total_onr"], errors="coerce").fillna(0)
    df = df[df["mp"].notnull() & (df["mp"] > 0)]

    # Parâmetros fixos
    HORAS_SOL = 4.5
    DIAS = 30
    VIDA = 25
    FATOR_PERDA = 0.8
    consumo_kwh_mes = 533
    potencia_total_watts_necessaria = consumo_kwh_mes / DIAS / (HORAS_SOL * FATOR_PERDA)

    df["qtd_paineis"] = (potencia_total_watts_necessaria * 1000 / df["mp"]).apply(lambda x: int(x) + 1)
    df["geracao_total_kwh"] = df["mp"] * HORAS_SOL * DIAS * 12 * VIDA * FATOR_PERDA / 1000
    df["custo_total"] = df["valor_total_onr"] * df["qtd_paineis"]

    # Filtra válidos
    df_plot = df[(df["custo_total"] > 0) & (df["geracao_total_kwh"] > 0)].copy()
    df_plot = df_plot.sort_values("geracao_total_kwh", ascending=True).head(20)

    # Gera o gráfico com Matplotlib
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(df_plot["geracao_total_kwh"], df_plot["custo_total"])

    for _, row in df_plot.iterrows():
        ax.text(row["geracao_total_kwh"], row["custo_total"], row["modelo"], fontsize=7)

    ax.set_xlabel("Geração Total (kWh)")
    ax.set_ylabel("Custo Total (R$)")
    ax.set_title("Custo Total vs Geração Total")
    ax.grid(True, linestyle="--", alpha=0.5)

    # Salva a imagem em memória
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)

    # Codifica imagem como base64 para HTML
    imagem_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return render(request, "certidoes/grafico_geracao.html", {
        "grafico_base64": imagem_base64,
    })


def grafico_comparar_marcas(request):
    marcas_desejadas = ["Ablytek", "Trina", "Canadian Solar"]  # ou pegue do `GET` para ser dinâmico

    queryset = PainelSolar.objects.filter(marca__in=marcas_desejadas).values(
        "marca", "modelo", "mp", "valor_total_onr",
    )
    df = pd.DataFrame(list(queryset))
    df["mp"] = pd.to_numeric(df["mp"], errors="coerce")
    df["valor_total_onr"] = pd.to_numeric(df["valor_total_onr"], errors="coerce").fillna(0)
    df = df[df["mp"].notnull() & (df["mp"] > -1)]

    # Parâmetros do projeto (poderiam vir do banco)
    HORAS_SOL = 4.5
    DIAS = 30
    VIDA = 25
    FATOR_PERDA = 0.8
    consumo_kwh_mes = 533
    potencia_total_watts_necessaria = consumo_kwh_mes / DIAS / (HORAS_SOL * FATOR_PERDA)

    df["qtd_paineis"] = (potencia_total_watts_necessaria * 1000 / df["mp"]).apply(lambda x: int(x) + 1)
    df["geracao_total_kwh"] = df["mp"] * HORAS_SOL * DIAS * 12 * VIDA * FATOR_PERDA / 1000
    df["custo_total"] = df["valor_total_onr"] * df["qtd_paineis"]
    df["custo_kwh"] = df["custo_total"] / (df["geracao_total_kwh"] * df["qtd_paineis"])

    df = df[(df["custo_total"] > 0) & (df["geracao_total_kwh"] > 0)].copy()

    fig = px.scatter(
        df,
        x="geracao_total_kwh",
        y="custo_total",
        color="marca",
        hover_data=["modelo", "qtd_paineis", "custo_kwh"],
        title="Comparação entre Marcas de Painéis",
        labels={"geracao_total_kwh": "Geração Total (kWh)", "custo_total": "Custo Total (R$)"},
    )

    fig.update_traces(marker=dict(size=12), selector=dict(mode="markers"))
    fig.update_layout(height=600)

    grafico_html = fig.to_html(full_html=False)

    return render(request, "certidoes/grafico_comparar_marcas.html", {
        "grafico_html": grafico_html,
        "marcas_desejadas": marcas_desejadas,
    })


def grafico_interativo_geracao(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)

    # Marcas selecionadas via GET
    marcas_filtradas = request.GET.getlist("marcas")

    queryset = PainelSolar.objects.all().values("modelo", "marca", "mp", "valor_total_onr")

    # Se marcas forem filtradas, aplica no queryset
    if marcas_filtradas:
        queryset = queryset.filter(marca__in=marcas_filtradas)

    df = pd.DataFrame(list(queryset))
    df["mp"] = pd.to_numeric(df["mp"], errors="coerce")
    df["valor_total_onr"] = pd.to_numeric(df["valor_total_onr"], errors="coerce").fillna(0)
    df = df[df["mp"].notnull() & (df["mp"] > 0)]

    # Parâmetros do projeto
    consumo_mensal_kwh = float(projeto.consumo_mensal_kwh or 500)
    HORAS_SOL = float(projeto.horas_sol_dia or 4.5)
    FATOR_PERDA = float(projeto.fator_perda or 0.8)
    DIAS = int(projeto.dias_mes or 30)
    VIDA = int(projeto.vida_util_anos or 25)

    demanda_diaria_kwh = consumo_mensal_kwh / DIAS
    potencia_necessaria = demanda_diaria_kwh / (HORAS_SOL * FATOR_PERDA)

    df["qtd_paineis"] = (potencia_necessaria * 1000 / df["mp"]).apply(lambda x: int(x) + 1)
    df["geracao_total_kwh"] = df["mp"] * HORAS_SOL * DIAS * 12 * VIDA * FATOR_PERDA / 1000

    sem_precos = df["valor_total_onr"].max() == 0

    if sem_precos:
        df["valor_total_onr"] = 1000
        df["custo_total"] = df["valor_total_onr"] * df["qtd_paineis"]
        df = df.sort_values("mp", ascending=False).head(10)
    else:
        df = df[df["valor_total_onr"] > 0]
        df["custo_total"] = df["valor_total_onr"] * df["qtd_paineis"]
        df = df[(df["custo_total"] > 0) & (df["geracao_total_kwh"] > 0)]
        df["custo_kwh"] = df["custo_total"] / (df["geracao_total_kwh"] * df["qtd_paineis"])
        df = df.sort_values("custo_kwh").head(10)

    # ✅ Agora extraímos apenas as marcas dos itens exibidos no gráfico
    marcas_no_grafico = sorted(df["marca"].dropna().unique().tolist())

    fig = px.scatter(
        df,
        x="geracao_total_kwh",
        y="custo_total",
        text="modelo",
        color="marca" if not df.empty else None,
        title=f"Custo Total vs Geração Total - Projeto {projeto.nome_projeto}",
        labels={
            "geracao_total_kwh": "Geração Total (kWh)",
            "custo_total": "Custo Total (R$)",
        },
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(height=550, dragmode="zoom")
    grafico_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return render(request, "certidoes/grafico_interativo.html", {
        "grafico_html": grafico_html,
        "projeto": projeto,
        "sem_precos": sem_precos,
        "marcas_unicas": marcas_no_grafico,
        "marcas_selecionadas": marcas_filtradas,
    })

import html

from django.conf import settings
from django.views import View

from .forms import PerguntaCustomForm, QuantasPlacasForm, RankingEmpresasForm
from .helpers import (
    ranquear_empresas,
)
from .models import PerguntaCustom


class IndexView(View):
    template_name = "fotovoltaico/index.html"

    def get(self, request):
        return render(request, self.template_name)


class QuantasPlacasView(View):
    template_name = "fotovoltaico/quantas_placas.html"

    def get(self, request, pk):
        form = QuantasPlacasForm()
        projeto = Projeto.objects.get(id=pk)

        return render(request,
                      self.template_name,
                      {"form": form, "projeto": projeto},
                      )

    def post(self, request, pk):
        form = QuantasPlacasForm(request.POST)
        contexto = {"form": form}
        projeto = Projeto.objects.get(id=pk)

        if form.is_valid():
            meta = form.cleaned_data["meta_kwh_mes"]
            hsp = form.cleaned_data["hsp"]
            eff = form.cleaned_data["system_eff"]
            panel = form.cleaned_data["panel_watts"]
            margem = form.cleaned_data["margem"]

            meta_ajustada = meta * (1 + margem/100)
            qnt, producao, sobra = helpers.placas_necessarias(meta_ajustada, panel, hsp, eff)
            prod_por_placa = helpers.kwh_mes_por_placa(panel, hsp, eff)

            contexto.update({
                "meta": meta,
                "meta_ajustada": meta_ajustada,
                "qnt": qnt,
                "producao": producao,
                "sobra": sobra,
                "panel": panel,
                "hsp": hsp,
                "eff": eff,
                "prod_por_placa": prod_por_placa,
                "projeto": projeto,
            })

        return render(request, self.template_name, contexto)


class RankingEmpresasView(View):
    template_name = "fotovoltaico/ranking_empresas.html"

    def get(self, request, pk):
        form = RankingEmpresasForm()
        projeto = Projeto.objects.get(id=pk)

        return render(request,
                      self.template_name,
                      {"form": form, "projeto": projeto},
                      )

    def post(self, request, pk):
        form = RankingEmpresasForm(request.POST)
        projeto = Projeto.objects.get(id=pk)

        contexto = {
            "form": form,
            "projeto": projeto,
            }

        if form.is_valid():
            qs = PainelSolar.objects.values(
                "id",
                "marca",
                "vmp",
                "numero_celulas",
                "eficiencia",
                potencia_nominal=F("pontencial_nominal"),  # kwargs NO FIM
            )

            # Converte para float com a chave CERTA (potencia_nominal)
            qs_float = [
                {
                    "id": row["id"],
                    "marca": row["marca"],
                    "potencia_nominal": float(row["potencia_nominal"] or 0),
                    "vmp": float(row["vmp"] or 0),
                    "numero_celulas": float(row["numero_celulas"] or 0),
                    "eficiencia": float(row["eficiencia"] or 0),
                }
                for row in qs
            ]

            # Ajuste os nomes também em filtros/pesos:
            filtros = {
                "potencia_nominal": ("<=", 2700.64),
                "vmp": (">=", 8.8),
                "numero_celulas": (">=", 60),
                "eficiencia": (">=", 16.63),
            }

            pesos = {
                "potencia_nominal": 270.64,
                "vmp": 8.8,
                "numero_celulas": 60,
                "eficiencia": 16.63,
            }

            #df = pd.DataFrame(list(qs))
            df = pd.DataFrame(list(qs_float))

            #ranked = ranquear_empresas(df, pesos=pesos, filtros=filtros) if not df.empty else pd.DataFrame()
            #top = ranked.iloc[0].to_dict() if not ranked.empty else None
            #contexto.update({"ranked": ranked.to_dict("records"), "top": top})

            ranked = ranquear_empresas(df, pesos=pesos, filtros=filtros) if not df.empty else pd.DataFrame()

            # 🔧 Garante que 'marca' volte para o resultado final
            if not ranked.empty and "marca" not in ranked.columns and "id" in ranked.columns:
                ranked = ranked.merge(df[["id", "marca"]], on="id", how="left")

            # (Opcional) ordenar colunas para o template
            ordem = ["id", "marca", "potencia_nominal", "vmp", "numero_celulas", "eficiencia", "score"]
            ranked = ranked[[c for c in ordem if c in ranked.columns]]

            top = ranked.iloc[0].to_dict() if not ranked.empty else None
            contexto.update({"ranked": ranked.to_dict("records"), "top": top})

        return render(request, self.template_name, contexto)


class PerguntasListView(View):
    template_name = "fotovoltaico/perguntas_list.html"

    def get(self, request, pk):
        perguntas = PerguntaCustom.objects.all().order_by("titulo")
        projeto = Projeto.objects.get(id=pk)

        return render(request,
                      self.template_name,
                      {
                          "perguntas": perguntas,
                          "projeto": projeto,
                          },
                      )


class PerguntaCustomCreateView(View):
    template_name = "fotovoltaico/pergunta_custom_form.html"

    def get(self, request, pk):
        form = PerguntaCustomForm()
        projeto = Projeto.objects.get(id=pk)

        return render(request,
                      self.template_name,
                      {
                          "form": form,
                          "projeto": projeto,
                          },
                      )

    def post(self, request, pk):
        form = PerguntaCustomForm(request.POST)
        projeto = Projeto.objects.get(id=pk)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.criado_por = request.user if request.user.is_authenticated else None
            obj.save()
            messages.success(request, "Pergunta criada.")

            return redirect(reverse("home:perguntas_list", kwargs={"pk": projeto.id}))

        return render(request, self.template_name,
                      {
                          "form": form, "projeto": projeto},
                      )


class PerguntaCustomDetailView(View):
    template_name = "fotovoltaico/pergunta_custom_detail.html"

    def get(self, request, pk, projeto_id):
        pergunta = get_object_or_404(PerguntaCustom, pk=pk)
        projeto = Projeto.objects.get(id=projeto_id)

        # Texto da pergunta que vai para o modelo:
        user_question = getattr(pergunta, "enunciado", None) or getattr(pergunta, "titulo", "") or "Sem conteúdo"
        # Trate 'codigo_handler' como instruções opcionais (system prompt), não como código:
        system_instructions = getattr(pergunta, "codigo_handler", "") or ""

        qs = PainelSolar.objects.values_list(
            "marca",
            "modelo",
            "tipo_de_celula",
            "numero_celulas",
            "pontencial_nominal",
            "eficiencia",
            "mp",
            "isc",
            "vmp",
            "coef_temp_isc_uisc",
            "coef_temp_pot_max_upmax",
            "coef_temp_voc_uvoc",
        )

        # converte para dicionário {campo: [valores...]}
        campos = ["marca",
                  "modelo",
                  "tipo_de_celula",
                  "numero_celulas",
                  "pontencial_nominal",
                  "eficiencia",
                  "mp",
                  "isc",
                  "vmp",
                  "coef_temp_isc_uisc",
                  "coef_temp_pot_max_upmax",
                  "coef_temp_voc_uvoc"]

        # quais campos devem ser inteiros ou float
        CAMPOS_INT = {"numero_celulas"}
        CAMPOS_FLOAT = {
            "pontencial_nominal",
            "eficiencia",
            "mp",
            "isc",
            "vmp",
            "coef_temp_isc_uisc",
            "coef_temp_pot_max_upmax",
            "coef_temp_voc_uvoc",
        }

        dados = {
            campo: [
                int(linha[i]) if campo in CAMPOS_INT
                else round(float(linha[i]), 2) if campo in CAMPOS_FLOAT
                else linha[i]
                for linha in qs
            ]
            for i, campo in enumerate(campos)
        }

        try:
           answer = ask_llm(user_question, system_instructions=system_instructions, data=dados)
           rendered = answer  # pode já vir em HTML; se preferir, sanitize ou confiar no modelo para HTML básico
        except Exception as e:
            rendered = f"<pre>Erro ao consultar o modelo:\n{html.escape(str(e))}</pre>"

        return render(request, self.template_name,
                      {
                          "pergunta": pergunta,
                          "rendered": rendered,
                          "projeto": projeto,
                          },
                      )

class PerguntaCustomLivreDetailView(View):
    template_name = "fotovoltaico/pergunta_custom_livre_detail.html"

    def get(self, request, projeto_id):
        pergunta = request.GET.get("texto")  # aqui vem a pergunta digitada
        projeto = Projeto.objects.get(id=projeto_id)

        # Trate 'codigo_handler' como instruções opcionais (system prompt), não como código:
        system_instructions = PerguntaCustom.objects.values_list("codigo_handler", flat=True).first()

        qs = PainelSolar.objects.values_list(
            "marca",
            "modelo",
            "tipo_de_celula",
            "numero_celulas",
            "pontencial_nominal",
            "eficiencia",
            "mp",
            "isc",
            "vmp",
            "coef_temp_isc_uisc",
            "coef_temp_pot_max_upmax",
            "coef_temp_voc_uvoc",
        )

        # converte para dicionário {campo: [valores...]}
        campos = ["marca",
                  "modelo",
                  "tipo_de_celula",
                  "numero_celulas",
                  "pontencial_nominal",
                  "eficiencia",
                  "mp",
                  "isc",
                  "vmp",
                  "coef_temp_isc_uisc",
                  "coef_temp_pot_max_upmax",
                  "coef_temp_voc_uvoc"]

        # quais campos devem ser inteiros ou float
        CAMPOS_INT = {"numero_celulas"}
        CAMPOS_FLOAT = {
            "pontencial_nominal",
            "eficiencia",
            "mp",
            "isc",
            "vmp",
            "coef_temp_isc_uisc",
            "coef_temp_pot_max_upmax",
            "coef_temp_voc_uvoc",
        }

        dados = {
            campo: [
                int(linha[i]) if campo in CAMPOS_INT
                else round(float(linha[i]), 2) if campo in CAMPOS_FLOAT
                else linha[i]
                for linha in qs
            ]
            for i, campo in enumerate(campos)
        }

        try:
           answer = ask_llm(pergunta, system_instructions=system_instructions, data=dados)
           rendered = answer  # pode já vir em HTML; se preferir, sanitize ou confiar no modelo para HTML básico
        except Exception as e:
            rendered = f"<pre>Erro ao consultar o modelo:\n{html.escape(str(e))}</pre>"

        # REGISTRAR PERGUNTA PARA ENVIO
        registrar_pergunta_feita(request=request, pergunta=pergunta)

        return render(request, self.template_name,
                      {
                          "pergunta": pergunta,
                          "rendered": rendered,
                          "projeto": projeto,
                          },
                      )

class PerguntaCustomUpdateView(UpdateView):
    template_name = "fotovoltaico/pergunta_custom_update.html"
    model = PerguntaCustom
    fields = ["titulo", "descricao", "codigo_handler"]

    def get_success_url(self):
        projeto_id = self.kwargs["projeto_id"]
        return reverse_lazy("home:perguntas_list", kwargs={"pk": projeto_id})

class PerguntaCustomDeleteView(DeleteView):
    model = PerguntaCustom
    template_name = "fotovoltaico/confirmar_exclusao_pergunta.html"

    def get_success_url(self):
        projeto_id = self.kwargs["projeto_id"]
        return reverse_lazy("home:perguntas_list", kwargs={"pk": projeto_id})

def registrar_pergunta_feita(request, pergunta):
    msg = "REGISTRAR A PERGUNTA PARA SER ENVIADA VIA EMAIL"
    logger.info(msg)

    # GRAVAR NO PERGUNTAS PARA ENVIAR POR EMAIL
    obj, criado = PerguntasIA.objects.get_or_create(pergunta=pergunta)
    if criado:
        print("Nova pergunta adicionada:", obj.pergunta)
        enviar_email_pergunta(obj)
    else:
        print("Pergunta já existia:", obj.pergunta)

    return redirect(request.META.get("HTTP_REFERER", "/"))

def enviar_email_pergunta(obj):
    # Enviar email somente se for nova
    try:
        send_mail(
            subject=f"Nova Pergunta Recebida: {obj.pergunta[:50]}",
            message=(
                f"Uma nova pergunta foi registrada no sistema.\n\n"
                f"Pergunta: {obj.pergunta}\n"
                f"Data/Hora: {obj.created_at.strftime('%d/%m/%Y %H:%M')}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["bierley@gmail.com", "cehtesavisoscehtes@gmail.com"],
            fail_silently=False,
        )
        obj.enviado_email = True
        obj.save(update_fields=["enviado_email"])
        logger.info("E-mail enviado com sucesso para nova pergunta.")
    except Exception as e:
        logger.error(f"Erro ao enviar email da pergunta: {e}")


@login_required
def auditar_perguntas_ia_view(request):
    perguntas = PerguntasIA.objects.all().order_by("-created_at")

    context = {
        "title": "Perguntas para IA",
        "segment": "pergunta_IA",
        "parent": "pergunta",
        "perguntas": perguntas,
        "total_perguntas": perguntas.count(),
    }

    return render(request, "certidoes/auditar_perguntas_ia_form.html", context)

@login_required
def analisar_perguntas_ia_view(request, pergunta):
    template_name = "fotovoltaico/pergunta_custom_detail.html"

    system_instructions = "Comporte-se como um gestor de equipamentos fotovoltaicos mais de 20 anos de experiencia. Analisar a intenção da pergunta !!!"
    dados = []

    projeto = Projeto.objects.all().first()

    answer = ask_llm(pergunta, system_instructions=system_instructions, data=dados)
    rendered = answer  # pode já vir em HTML; se preferir, sanitize ou confiar no modelo para HTML básico

    return render(
        request,
        template_name,
        {
            "pergunta": pergunta,
            "rendered": rendered,
            "projeto": projeto,
        },
    )
