from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from tinymce.models import HTMLField


class TipoMinuta(models.Model):
    nome: str = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = "Tipo de Minuta"
        verbose_name_plural = "Tipos de Minutas"

    def __str__(self) -> str:
        return self.nome


class Minuta(models.Model):
    nome: str = models.CharField(max_length=200)
    tipo_minuta = models.ForeignKey(
        TipoMinuta,
        related_name="minutas",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    content = HTMLField(null=True, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Minuta"
        verbose_name_plural = "Minutas"

    def __str__(self) -> str:
        return self.nome
