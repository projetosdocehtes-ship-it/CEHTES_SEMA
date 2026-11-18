import datetime
import uuid

from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from apps.home.models import AtoPratica


class UUIDPrimaryKeyField(models.UUIDField):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["primary_key"] = True
        kwargs["default"] = uuid.uuid4
        kwargs["editable"] = False
        kwargs["verbose_name"] = "ID"
        super().__init__(*args, **kwargs)


# MINUTA DE EXIGENCIA
class MinutaModeloAto(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    titulo: str = models.CharField(
        max_length=500,
        blank=True,
        unique=True,
        verbose_name="Título",
        help_text="Descreva a minuta",
    )
    subtitulo: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Subtítulo",
    )
    observacao = CKEditor5Field(
        "Observacao",
        config_name="default",
        blank=True,
        null=True,
    )
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.titulo


# LIGACAO DOS TIPO DE ATO COM A MINUTA DE EXIGENCIA
class MinutaLigacaoAto(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    minuta = models.ForeignKey(MinutaModeloAto, on_delete=models.CASCADE, null=True)
    ato = models.ForeignKey(AtoPratica, on_delete=models.CASCADE, null=True)

    class Meta:
        unique_together = ("minuta", "ato")

    def __str__(self) -> str:
        return f"{self.minuta} - {self.ato}"


# MINUTA DE EXIGENCIA
class VariavelMinutaModeloAto(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    descricao: str = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        verbose_name="Descrição",
    )
    variavel: str = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        verbose_name="Variável",
    )
    descricao_masculino_simples: str = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Descrição masculino simples",
    )
    descricao_masculino_composto: str = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Descrição masculino composto",
    )
    descricao_feminino_simples: str = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Descrição feminino simples",
    )
    descricao_feminino_composto: str = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Descrição feminino composto",
    )
    created_at: datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )
    updated_at: datetime = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        verbose_name = "Variável"
        verbose_name_plural = "Variáveis"

    def __str__(self) -> str:
        return self.descricao
