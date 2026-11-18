import logging
import os

import django
from django.contrib.contenttypes.models import ContentType
from django.core.files import File

from apps.cartorios.models import Usuario as User
from apps.home.forms import AnexoForm
from apps.home.models import Livro01Protocolo

logger = logging.getLogger(__name__)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()


def adicionar_anexos_de_pastas(caminho_base) -> None:
    # Obtém o primeiro superusuário disponível para usar como usuário que fez o upload
    usuario_admin = User.objects.filter(is_superuser=True).first()
    if not usuario_admin:
        print("Nenhum usuário administrador encontrado.")
        return

    for nome_protocolo in os.listdir(caminho_base):
        caminho_protocolo = os.path.join(caminho_base, nome_protocolo)
        if not os.path.isdir(caminho_protocolo):
            continue

        try:
            protocolo = Livro01Protocolo.objects.get(numero_protocolo=nome_protocolo)
        except Livro01Protocolo.DoesNotExist:
            logger.info(f"Protocolo {nome_protocolo} não encontrado.")
            continue

        for nome_arquivo in os.listdir(caminho_protocolo):
            if nome_arquivo.lower().endswith(".pdf"):
                caminho_arquivo = os.path.join(caminho_protocolo, nome_arquivo)
                with open(caminho_arquivo, "rb") as arquivo_pdf:
                    arquivo_django = File(arquivo_pdf, name=nome_arquivo)
                    form = AnexoForm(
                        {"descricao": nome_arquivo},
                        {"arquivo": arquivo_django},
                    )
                    if form.is_valid():
                        anexo = form.save(commit=False)
                        anexo.content_type = ContentType.objects.get_for_model(
                            protocolo,
                        )
                        anexo.object_id = protocolo.pk
                        # Aqui você define o usuário administrador diretamente no modelo Anexo
                        anexo.uploaded_by = usuario_admin
                        anexo.save()
                        print(
                            f"Anexo {nome_arquivo} adicionado ao protocolo {nome_protocolo}.",
                        )
                    else:
                        logger.info(f"Erro ao adicionar {nome_arquivo}: {form.errors}")


# Caminho base para as pastas dos protocolos
caminho_base = "C:/Prime/static/assets/images/ged/protocolos"

# Chamada da função
adicionar_anexos_de_pastas(caminho_base)
