from django.db import models
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field


class ModeloTexto(models.Model):
    titulo: str = models.CharField(max_length=255)
    conteudo = CKEditor5Field("conteudo", config_name="default")

    def __str__(self) -> str:
        return self.titulo

    def get_absolute_url(self):
        return reverse("modelos:modelo_detail", kwargs={"pk": self.pk})


# model de exemplo que preenche um documento.
class Cliente(models.Model):
    nome: str = models.CharField(max_length=100)
    email = models.EmailField()
    data_nascimento = models.DateField()
    endereco: str = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.nome
