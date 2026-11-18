# mapeamento/models.py


from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Mapeamento(models.Model):
    # Lado antigo
    content_type_antigo = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="mapeamento_antigo",
    )
    object_id_antigo = models.PositiveIntegerField()
    content_object_antigo = GenericForeignKey("content_type_antigo", "object_id_antigo")

    # Lado novo
    content_type_novo = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="mapeamento_novo",
    )
    object_id_novo: str = models.CharField(max_length=255)
    content_object_novo = GenericForeignKey("content_type_novo", "object_id_novo")

    def __str__(self) -> str:
        nome_antigo = (
            self.content_type_antigo.model_class()._meta.verbose_name
            if self.content_type_antigo
            else "Desconhecido"
        )
        nome_novo = (
            self.content_type_novo.model_class()._meta.verbose_name
            if self.content_type_novo
            else "Desconhecido"
        )
        return f"Mapeamento de {nome_antigo} para {nome_novo}"
