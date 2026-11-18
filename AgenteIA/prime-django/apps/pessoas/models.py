import datetime
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from apps.home.models import Livro05 as PessoaHome
from apps.home.tipos import TipoSexo
from apps.pessoas.managers import VersaoPessoaManager


class Pessoa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    documento: str = models.CharField(max_length=100)
    pessoa_home = models.ForeignKey(
        PessoaHome,
        on_delete=models.CASCADE,
        related_name="PessoaHomeId",
        null=True,
        blank=True,
    )

    objects = models.Manager()

    def __str__(self: "Pessoa") -> str:
        return self.pessoa_home.nome if self.pessoa_home else self.documento

    def ultima_versao(self):
        return self.versoes.last()

    def quantidade_versoes(self):
        return self.versoes.count()


class VersaoPessoa(models.Model):
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="versoes")
    nome: str = models.CharField(max_length=100, default="")
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True, default="")
    telefone: str = models.CharField(null=True, blank=True, max_length=20, default="")
    logradouro = models.TextField(default="")
    bairro: str = models.CharField(max_length=50, default="")
    cidade: str = models.CharField(max_length=50, default="")
    estado: str = models.CharField(max_length=2, default="")
    cep: str = models.CharField(max_length=10, default="")
    estado_civil: str = models.CharField(max_length=20, default="")
    sexo: str = models.CharField(max_length=1, choices=TipoSexo.CHOICES, default="")
    conjuge = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    observacoes = models.TextField(default="")
    criado_em: datetime = models.DateTimeField(auto_now_add=True)
    documento_apresentado: str = models.CharField(max_length=100, null=True, blank=True)

    objects: VersaoPessoaManager = VersaoPessoaManager()

    class Meta:
        verbose_name = "Pessoa"
        verbose_name_plural = "Pessoas"

    def __str__(self) -> str:
        vinculo = self.vinculos.first()
        return f"{self.nome} - {vinculo.tipo_vinculo}" if vinculo else self.nome

    def get_absolute_url(self):
        return reverse("pessoas:pessoa-detail", args=[str(self.id)])

    def get_conjuge(self):
        if self.conjuge:
            return self.conjuge

        # procura outro registro que tenha o meu id como conjuge
        return VersaoPessoa.objects.filter(conjuge=self.id).first()

    def documento(self):
        return self.pessoa.documento


class Anexo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="anexos")
    descricao: str = models.CharField(max_length=50)
    arquivo = models.FileField(upload_to="anexos-pessoas/")
    data_upload: datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"

    def __str__(self) -> str:
        return f"{self.descricao} - {self.pessoa.nome}"

    def get_absolute_url(self):
        return reverse("pessoas:anexo-detail", args=[str(self.id)])


class TipoVinculo(models.Model):
    nome: str = models.CharField(max_length=50)
    papel: str = models.CharField(max_length=1, null=True, blank=True, unique=True)

    objects = models.Manager()

    class Meta:
        verbose_name = "Tipo de Vínculo"
        verbose_name_plural = "Tipos de Vínculos"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


# class de vinculo generico com outros models e registros do sistema
class Vinculo(models.Model):
    versao_pessoa = models.ForeignKey(
        VersaoPessoa,
        on_delete=models.CASCADE,
        related_name="vinculos",
    )
    tipo_vinculo = models.ForeignKey(TipoVinculo, on_delete=models.CASCADE)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    objects = models.Manager()

    class Meta:
        verbose_name = "Vínculo"
        verbose_name_plural = "Vínculos"

    def __str__(self: "Vinculo") -> str:
        return f"{self.versao_pessoa.nome} - {self.tipo_vinculo}"
