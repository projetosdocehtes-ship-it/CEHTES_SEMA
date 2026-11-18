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
class MinutaExigencia(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    titulo: str = models.CharField(max_length=500, blank=True, unique=True)
    subtitulo: str = models.CharField(max_length=500, blank=True)
    observacao = CKEditor5Field(config_name="default")
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.titulo


# LIGACAO DOS TIPO DE ATO COM A MINUTA DE EXIGENCIA
class MinutaExigenciaAto(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    minuta = models.ForeignKey(MinutaExigencia, on_delete=models.CASCADE, null=True)
    ato = models.ForeignKey(AtoPratica, on_delete=models.CASCADE, null=True)

    class Meta:
        unique_together = (
            "minuta",
            "ato",
        )

    def __str__(self) -> str:
        return f"{self.minuta} - {self.ato}"
