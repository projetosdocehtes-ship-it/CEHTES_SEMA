# pip install pdfrw
# https://stackoverflow.com/questions/28281108/reportlab-how-to-add-a-footer-to-a-pdf-file

import configparser
import os

from apps.home.utils import token

# Diretorio aplicacao
path_dir = os.path.split(os.path.abspath(__file__))[0]


def get_imagem_da_assinatura():
    config = configparser.ConfigParser()
    try:
        # Substitua 'diretorio_raiz' pela variável que contém o caminho do diretório raiz do seu projeto
        caminho_token_ini = os.path.join(path_dir, "Token.ini")
        config.read(caminho_token_ini, encoding="utf-8")
        return str(config["TOKEN"]["CAMINHO_IMAGEM_ASSINATURA"])
    except FileNotFoundError:
        # Trate o erro conforme necessário
        print("Arquivo Token.ini não encontrado.")
    except KeyError:
        # Trate o erro conforme necessário
        print("Configuração 'CAMINHO_IMAGEM_ASSINATURA' não encontrada.")


# Adicionar todos os dados do token
def add_token(src_pdf_path, dst_pdf_path) -> None:
    imagem_assinatura = get_imagem_da_assinatura()
    print("ADICIONAR TOKEN: ", src_pdf_path, dst_pdf_path)
    token.adicionar_imagem_e_assinar_pdf(src_pdf_path, dst_pdf_path, imagem_assinatura)

    print("Salvar como assinado em A1: ")
    # ERP.Gerar_Arquivo_Assinado_A1()
