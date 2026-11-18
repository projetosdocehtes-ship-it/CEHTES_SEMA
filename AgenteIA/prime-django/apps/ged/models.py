import datetime
import hashlib
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.cartorios.models import Usuario as CustomUser
from apps.ged.managers import ArquivoManager

# class Documento(models.Model):
#     titulo:str = models.CharField(max_length=255)
#     # arquivo = models.FileField(upload_to='documentos/')
#     models.FileField(storage=TenantFileSystemStorage())
#     data_upload:datetime = models.DateTimeField(auto_now_add=True)

# Opções para sistema de armazenamento
LOCAL = "local"
S3 = "s3"

STORAGE_CHOICES = [
    (LOCAL, "Local"),
    (S3, "Amazon S3"),
]


def get_file_path(instance, filename) -> str:
    # Gera um novo UUID
    uuid_name = uuid.uuid4()
    # Pega as primeiras 4 letras do UUID gerado
    subdir = str(uuid_name)[:4]
    # Retorna o caminho do arquivo incluindo a subpasta, mas sem a extensão
    return f"arquivos/{subdir}/{uuid_name}"


class Arquivo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    arquivo = models.FileField(upload_to=get_file_path, max_length=255)
    nome_original: str = models.CharField(max_length=255)
    extensao: str = models.CharField(max_length=10)
    storage: str = models.CharField(
        max_length=10,
        choices=STORAGE_CHOICES,
        default=LOCAL,
    )
    data_envio: datetime = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Usuário",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id: str = models.CharField(max_length=255)
    content_object = GenericForeignKey("content_type", "object_id")
    descricao = models.TextField(blank=True, null=True)
    tamanho = models.PositiveIntegerField()
    hash: str = models.CharField(max_length=64)

    objects: ArquivoManager = ArquivoManager()

    def __str__(self) -> str:
        return self.nome_completo

    def get_absolute_url(self):
        return reverse("ged:arquivo_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs) -> None:
        # Calcular e salvar o tamanho e o hash do arquivo
        if self.arquivo:
            self.arquivo.seek(0)
            self.tamanho = self.arquivo.size
            self.hash = hashlib.sha256(self.arquivo.read()).hexdigest()
        super().save(*args, **kwargs)

    @property
    def nome_completo(self) -> str:
        """Retorna o nome completo do arquivo (nome original + extensão)."""
        return f"{self.nome_original}{self.extensao}"

    @classmethod
    def criar_e_salvar(cls, arquivo, usuario, content_type, object_id, descricao=None):
        nome_original, extensao = os.path.splitext(arquivo.name)
        novo_arquivo = cls(
            arquivo=arquivo,
            nome_original=nome_original,
            extensao=extensao,
            usuario=usuario,
            descricao=descricao,
            content_type=content_type,
            object_id=object_id,
        )
        novo_arquivo.save()
        return novo_arquivo

    def get_download_url(self):
        if self.storage == "local":
            # Gera a URL completa para arquivos armazenados localmente
            return Path(settings.MEDIA_URL) / self.arquivo.name
        elif self.storage == "s3":
            # Para o S3, a URL é armazenada diretamente no campo 'arquivo'
            return self.arquivo.url
        else:
            # Trata outros tipos de armazenamento ou retorna None se desconhecido
            return None


class RegistroDownload(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    arquivo: str = models.CharField(max_length=255)
    data_hora: datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        hora_local = timezone.localtime(self.data_hora)
        return f"{self.usuario} baixou {self.arquivo} em {hora_local.strftime(settings.DATE_FORMAT_STR)}"
