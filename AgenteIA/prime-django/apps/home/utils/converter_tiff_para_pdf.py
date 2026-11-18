import glob
import logging
import os
from pathlib import Path
from textwrap import dedent

import img2pdf

from apps.home.models import Configuracao

logger = logging.getLogger(__name__)
# # Diretorio aplicacao
# path_dir = os.path.split(os.path.abspath(__file__))[0]

# config = configparser.ConfigParser()

# # Caminho para o arquivo Margens.ini
# path_margens_ini = os.path.join(path_dir, "Margens.ini")

# # Verifique se o arquivo existe
# if os.path.exists(path_margens_ini):
#     config.read(path_margens_ini, encoding="utf-8")

#     # Obtenha os valores com valores padrão caso as chaves não existam
#     MARGEM_SUPERIOR_IMAGEM = config.get(
#         "IMAGEM", "MARGEM_SUPERIOR_IMAGEM", fallback="20"
#     )
#     LARGURA_PAGINA = config.get("IMAGEM", "LARGURA_PAGINA", fallback="210")
#     ALTURA_PAGINA = config.get("IMAGEM", "ALTURA_PAGINA", fallback="297")
# else:
#     # Para uma página A4 em milímetros
#     MARGEM_SUPERIOR_IMAGEM = "20"  # Margem superior de 20 mm
#     LARGURA_PAGINA = "210"  # Largura de uma folha A4
#     ALTURA_PAGINA = "297"  # Altura de uma folha A4

Mensagem = ""


def verificar_status():
    global Mensagem
    #return Mensagem


# Listar os arquivos tif e salvar todos em unico PDF
def gerar_pdf(foldername_o, foldername_d, name_file):
    #global Mensagem

    print("foldername_o", foldername_o)
    print("foldername_d", foldername_d)
    print("name_file", name_file)

    # Criar a pasta se ela nao existir
    if not os.path.exists(os.path.dirname(foldername_d)):
        print("Vendo arquivo: ", foldername_d)
        os.makedirs(os.path.dirname(foldername_d))

    # Deletar o pdf se ele existir
    if os.path.exists(foldername_d):
        os.remove(foldername_d)

    # Arquivos a filtrar para gerar o pdf
    caminho_filtrar = foldername_o + "\\" + name_file + ".*"
    print("caminho_filtrar", caminho_filtrar)

    # multiple inputs (variant 1)
    try:
        print("Gerando:", foldername_d)
        "Sucesso ao gerar: \n" + foldername_d

        # margin   = 110

        # ALFENAS
        # margin   = 180
        # MARGEM SUPERIOR DE INICIO DA IMAGEM
        # margin = int(MARGEM_SUPERIOR_IMAGEM)

        a4_width = img2pdf.mm_to_pt(int(Configuracao.obter("LARGURA_PAGINA")))
        a4_height = img2pdf.mm_to_pt(int(Configuracao.obter("ALTURA_PAGINA")))
        page_size = (a4_width, a4_height)

        # Definindo as margens
        margem_topo = int(Configuracao.obter("MARGEM_SUPERIOR_IMAGEM"))
        margem_direita = 0
        margem_inferior = 0
        margem_esquerda = 0

        margem_topo_pt = img2pdf.mm_to_pt(margem_topo)
        margem_direita_pt = img2pdf.mm_to_pt(margem_direita)
        margem_inferior_pt = img2pdf.mm_to_pt(margem_inferior)
        margem_esquerda_pt = img2pdf.mm_to_pt(margem_esquerda)
        print("Lendo pagina A4: ", page_size, a4_width, page_size)

        image_width = a4_width - margem_direita_pt - margem_esquerda_pt
        image_height = a4_height - margem_topo_pt - margem_inferior_pt

        image_size = (
            (img2pdf.ImgSize.abs, image_width),
            (img2pdf.ImgSize.abs, image_height),
        )

        # image_size = ((img2pdf.ImgSize.abs, a4_height - 0), (img2pdf.ImgSize.abs, a4_width))

        print("Gerando a pagina A4: ", page_size, a4_width, page_size)

        layout_fun = img2pdf.get_layout_fun(
            page_size,
            image_size,
            border=(
                margem_topo_pt,
                margem_direita_pt,
                margem_inferior_pt,
                margem_esquerda_pt,
            ),
            fit=None,
            auto_orient=False,
        )

        print("Lendo pagina A4: ", page_size, a4_width, page_size)

        with open(foldername_d, "wb") as f:
            f.write(
                img2pdf.convert(
                    sorted(glob.glob(caminho_filtrar)),
                    layout_fun=layout_fun,
                ),
            )
            print("Salvado no arquivo: ", caminho_filtrar)

    except Exception as e:
        logger.exception(
            f"ERRO ao gerar: {caminho_filtrar} => Destino: {foldername_d}: {e}",
        )
        print("Detalhes do erro:", str(e))
        # sleep(100)
        dedent(
            """ERRO ao gerar:\n\n"""
            + caminho_filtrar
            + """\n\n=>\n\nDestino: """
            + foldername_d
            + """\n\nDetalhes do erro: """
            + str(e),
        )

        # Retonar o PDF padrao
        foldername_d = caminho_filtrar + "\\000000.pdf"

    # Retornar o arquivo Gerado
    return foldername_d


# Verificar a pasta se ela existe e formatar o diretorio inicial
def inicialiar_pdf(origem, destino, numero):
    # global Mensagem

    nro_temp = numero.zfill(6)
    origem_temp = origem + "\\" + nro_temp[0:3]
    destino_temp = str(destino + "\\" + nro_temp + ".pdf")

    if not os.path.exists(origem_temp):
        # criando subdiretório
        Path(origem_temp).mkdir(parents=True, exist_ok=True)

    # Retorna o arquivo gerado
    return gerar_pdf(origem_temp, destino_temp, nro_temp)


# Verificar a pasta se ela existe e formatar o diretorio inicial
def nome_localizar(origem, destino, numero):
    nro_temp = numero.zfill(6)
    origem_temp = origem + "\\" + nro_temp[0:3]
    destino_temp = str(destino + "\\" + nro_temp + ".pdf")

    print("Atualizando os dados", "Aguarde")

    if not os.path.exists(origem_temp):
        # criando subdiretório
        Path(origem_temp).mkdir(parents=True, exist_ok=True)

    # Retorna o arquivo gerado
    return destino_temp


# Como executar o procedimento
"""
Numero      = "1"
foldername_o = "D:\\---\\Ged\\Matriculas"
foldername_d = "D:\\Sistema_Geral\\PDF\\"
nome_localizar(foldername_o, foldername_d, Numero)
inicialiar_pdf(foldername_o, foldername_d, Numero)
"""
