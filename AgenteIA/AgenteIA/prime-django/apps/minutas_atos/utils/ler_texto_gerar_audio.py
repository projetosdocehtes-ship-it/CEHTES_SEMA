# # FUNCAO PARA FALAR O TEXTO
# import uuid

# from django.core.files.storage import default_storage
# from gtts import gTTS


# def falar_texto(request, text):
#     # Gera um identificador único para o arquivo
#     unique_filename = f"audio_{uuid.uuid4()}.mp3"
#     file_path = default_storage.save(unique_filename, None)  # Reserva o nome no storage

#     try:
#         print("Iniciando geração de texto em áudio")
#         sound = gTTS(text, lang="pt", tld="com.br", slow=False)

#         # Salvando temporariamente em um buffer para não precisar de IO de disco duas vezes
#         from io import BytesIO

#         buffer = BytesIO()
#         sound.save(buffer)
#         buffer.seek(0)

#         # Salva o arquivo no sistema de armazenamento configurado
#         default_storage.save(file_path, buffer)
#         logger.info(f"Áudio salvo em {file_path}")
#     except Exception:
#         print("Erro ao gerar o arquivo de áudio: ")
#         # Apagar arquivo reservado em caso de falha
#         default_storage.delete(file_path)
#         raise

#     # Retorna o caminho completo para acesso ao arquivo
#     return default_storage.url(file_path)

import os
import time

from gtts import gTTS

from apps.home.views import limpar_texto_html


# FUNCAO PARA FALAR O TEXTO
def falar_texto(request, html):
    import uuid

    text = limpar_texto_html(html)  # Supondo a existência dessa função.

    # Define Django project base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    media_root = os.path.join(base_dir, "media")

    # Cria o diretório media_root se ele não existir
    if not os.path.exists(media_root):
        os.makedirs(media_root)

    # GERA UM NUMERO ALEATORIO PARA O ARQUIVO
    # numero_aleatorio = random.randrange(1, 999999)
    # Gera um identificador único para o arquivo
    numero_aleatorio = f"audio_{uuid.uuid4()}"

    print("Gerar texto", time.strftime("%H:%M:%S"))
    sound = gTTS(
        text[:],
        lang="pt",
        tld="com.br",
        slow=False,
    )  # pt-br = português do Brasil
    # sound = gTTS(text, lang="pt")

    # GERA O ARQUIVO ALEATORIO
    print("Criar pasta do audio: ", media_root)
    nome_arquivo = media_root + "/audio_" + str(numero_aleatorio) + ".mp3"
    print("Criar arquivo do audio: ", nome_arquivo)

    print("Salvar texto", time.strftime("%H:%M:%S"))
    sound.save(nome_arquivo)

    # RETORNA O NOME DO ARQUIVO A SER GERADO E BAIXADO
    return nome_arquivo
