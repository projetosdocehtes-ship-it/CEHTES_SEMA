import logging
import uuid
from datetime import date, datetime, time, timedelta
from functools import cached_property
from typing import TYPE_CHECKING

from django.apps import apps
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import OperationalError, models, transaction
from django.db.models import QuerySet
from django.utils import timezone
from markdownx.models import MarkdownxField
from psycopg2 import IntegrityError

from apps.comum.managers import TipoRegistroImobiliarioManager
from apps.home.padroes import MATRICULA_VISUALIZADA_ORIGEM_ID
from core.middlewares import get_current_user

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

if TYPE_CHECKING:
    from apps.cartorios.models import Usuario


class DiaDaSemana:
    SEGUNDA = 1
    TERCA = 2
    QUARTA = 3
    QUINTA = 4
    SEXTA = 5
    # SÁBADO = 6
    # DOMINGO = 7


class UUIDPrimaryKeyField(models.UUIDField):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["primary_key"] = True
        kwargs["default"] = uuid.uuid4
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    @staticmethod
    def generate_uuid() -> uuid.UUID:
        return uuid.uuid4()


class BaseModel(models.Model):
    """Modelo base com campos e métodos úteis para todos os modelos do projeto."""

    criado_por: "Usuario" = models.ForeignKey(
        "cartorios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_criado_por",
        help_text="Usuário que criou o registro",
        verbose_name="Criado por",
    )
    modificado_por: "Usuario" = models.ForeignKey(
        "cartorios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_modificado_por",
        help_text="Usuário que atualizou o registro pela última vez",
        verbose_name="Atualizado por",
    )
    criado_em: datetime = models.DateTimeField(
        auto_now_add=True,
        help_text="Data e hora de criação do registro",
        verbose_name="Criado em",
    )
    modificado_em: datetime = models.DateTimeField(
        auto_now=True,
        help_text="Data e hora da última atualização do registro",
        verbose_name="Atualizado em",
    )

    is_active: bool = models.BooleanField(
        default=True,
        help_text="Indica se o registro está ativo",
        verbose_name="Ativo",
    )

    class Meta:
        abstract = True
        ordering = ["-criado_em"]
        get_latest_by = "criado_em"
        indexes = [
            models.Index(fields=["criado_em"]),
            models.Index(fields=["modificado_em"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):
        try:
            # Tenta obter o usuário atual
            user = get_current_user()
        except ObjectDoesNotExist:
            user = None

        if not user or not user.is_authenticated:
            # Se o usuário atual não for autenticado, busca o usuário com pk=1
            User = apps.get_model("cartorios", "Usuario")
            try:
                user = User.objects.get(pk=1)
            except User.DoesNotExist:
                # Você pode levantar uma exceção ou definir user como None dependendo do caso
                msg = "Usuário padrão não encontrado."
                raise ValueError(msg)

        if not self.pk and hasattr(self, "criado_por"):
            # Verifica se o campo 'criado_por' existe antes de atribuir
            self.criado_por = user

        # Verifica se o campo 'modificado_por' existe antes de atribuir
        if hasattr(self, "modificado_por"):
            self.modificado_por = user

        # Chama o método save da superclasse
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Adiciona lógica personalizada ao deletar o modelo, se necessário
        super().delete(*args, **kwargs)

    def soft_delete(self):
        """Marca o registro como inativo ao invés de deletá-lo do banco de dados."""
        self.is_active = False
        self.save()

    def restore(self):
        """Restaura um registro que foi marcado como inativo."""
        self.is_active = True
        self.save()

    def has_changed(self):
        """Verifica se algum campo do modelo foi alterado."""
        if not self.pk:
            return False
        old_values = self.__class__.objects.get(pk=self.pk)
        for field in self._meta.fields:
            if getattr(old_values, field.name) != getattr(self, field.name):
                return True
        return False

    @classmethod
    def get_recent(cls, days=7):
        """Retorna os registros criados nos últimos X dias."""
        return cls.objects.filter(
            criado_em__gte=timezone.now() - timezone.timedelta(days=days),
            is_active=True,
        )

    @classmethod
    def get_by_user(cls, user) -> QuerySet:
        """Retorna os registros criados por um usuário específico."""
        return cls.objects.filter(criado_por=user, is_active=True)

    @classmethod
    def get_last_updated(cls):
        """Retorna o registro mais recentemente atualizado."""
        return cls.objects.filter(is_active=True).latest("modificado_em")

    @classmethod
    def get_deleted(cls):
        """Retorna todos os registros marcados como inativos."""
        return cls.objects.filter(is_active=False)

    @classmethod
    def get_active(cls):
        """Retorna todos os registros marcados como ativos."""
        return cls.objects.filter(is_active=True)


class TipoCartorio(models.Model):
    nome: str = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = "Tipo de Cartório"
        verbose_name_plural = "Tipos de Cartórios"

    def __str__(self) -> str:
        return self.nome

    @staticmethod
    def get_cartorio_registro_imoveis_id() -> int:
        return TipoCartorio.objects.update_or_create(
            defaults={
                "nome": "Projeto CEHTES",
            },
        )[0].id

    @staticmethod
    def get_cartorio_registro_imoveis() -> "TipoCartorio":
        return TipoCartorio.objects.update_or_create(
            defaults={
                "nome": "Projeto CEHTES",
            },
        )


def get_um_ano_a_partir_de_agora():
    return timezone.now() + timedelta(days=365)


# class ModeloAuditavel(models.Model):
#     criado_em:datetime = models.DateTimeField(auto_now_add=True)
#     modificado_em:datetime = models.DateTimeField(auto_now=True)
#     criado_por = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         related_name="criado_%(class)s_set",
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#     )
#     modificado_por = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         related_name="modificado_%(class)s_set",
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#     )

#     class Meta:
#         abstract = True


class Pais(models.Model):
    nome: str = models.CharField(max_length=50, unique=True, db_index=True)
    sigla: str = models.CharField(max_length=3, unique=True, db_index=True)

    class Meta:
        verbose_name = "País"
        verbose_name_plural = "Países"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    @staticmethod
    def get_default_pais() -> int:
        return Pais.objects.get_or_create(
            nome="Brasil",
            defaults={
                "sigla": "BR",
            },
        )[0].id


class UnidadeFederativa(models.Model):
    sigla: str = models.CharField(max_length=2, unique=True, db_index=True)
    nome: str = models.CharField(
        max_length=50,
        db_index=True,
        unique=True,
    )
    pais = models.ForeignKey(
        Pais,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_related",
        null=True,
        blank=True,
        default=Pais.get_default_pais,
    )
    numero_interno = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name="Código Interno",
    )

    class Meta:
        verbose_name = "Unidade Federativa"
        verbose_name_plural = "Unidades Federativas"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    @staticmethod
    def get_default_uf() -> "UnidadeFederativa":  # MG
        uf, created = UnidadeFederativa.objects.update_or_create(
            sigla="MG",
            defaults={"numero_interno": 11},
        )
        return uf

    @staticmethod
    def get_default_uf_id() -> int:  # MG
        uf = UnidadeFederativa.get_default_uf()
        return uf.id

    @staticmethod
    def get_default_uf_numero() -> int:
        uf = UnidadeFederativa.get_default_uf()
        return uf.numero_interno or 11  # MG

    @classmethod
    def retornar_estado(cls, numero_estado: str) -> str:
        try:
            # Convertendo número para int e somando 1 para obter o índice correto no dicionário
            numero_estado = int(numero_estado) + 1
        except ValueError:
            logger.exception("ERRO")

        # Dicionário de estados do Brasil
        estados = {
            0: "",
            1: "AC",
            2: "AL",
            3: "AM",
            4: "AP",
            5: "BA",
            6: "CE",
            7: "DF",
            8: "ES",
            9: "GO",
            10: "MA",
            11: "MG",
            12: "MS",
            13: "MT",
            14: "PA",
            15: "PB",
            16: "PE",
            17: "PR",
            18: "RD",
            19: "RJ",
            20: "RN",
            21: "RO",
            22: "RR",
            23: "RS",
            24: "SC",
            25: "SE",
            26: "SP",
            27: "TO",
        }
        return estados.get(numero_estado, "MG")

    @classmethod
    def criar_unidades_federativas_padroes(cls) -> None:
        UnidadeFederativa = apps.get_model("comum", "UnidadeFederativa")

        ufs = [
            (31, "MG", "Minas Gerais"),
            (35, "SP", "São Paulo"),
            (41, "PR", "Paraná"),
            (42, "SC", "Santa Catarina"),
            (43, "RS", "Rio Grande do Sul"),
            (50, "MS", "Mato Grosso do Sul"),
            (11, "RO", "Rondônia"),
            (12, "AC", "Acre"),
            (13, "AM", "Amazonas"),
            (14, "RR", "Roraima"),
            (15, "PA", "Pará"),
            (16, "AP", "Amapá"),
            (17, "TO", "Tocantins"),
            (21, "MA", "Maranhão"),
            (24, "RN", "Rio Grande do Norte"),
            (25, "PB", "Paraíba"),
            (26, "PE", "Pernambuco"),
            (27, "AL", "Alagoas"),
            (28, "SE", "Sergipe"),
            (29, "BA", "Bahia"),
            (33, "RJ", "Rio de Janeiro"),
            (51, "MT", "Mato Grosso"),
            (52, "GO", "Goiás"),
            (53, "DF", "Distrito Federal"),
            (22, "PI", "Piauí"),
            (23, "CE", "Ceará"),
            (32, "ES", "Espírito Santo"),
        ]

        for pk, sigla, nome in ufs:
            try:
                with transaction.atomic():
                    if not UnidadeFederativa.objects.filter(sigla=sigla).exists():
                        unidade, created = UnidadeFederativa.objects.get_or_create(
                            sigla=sigla,
                            defaults={"id": pk, "nome": nome},
                        )
                        if not created:
                            unidade.id = pk
                            unidade.nome = nome
                            unidade.save()
            except IntegrityError:
                logger.info(
                    f"Erro ao criar ou atualizar a Unidade Federativa com sigla {sigla}.",
                )

        logger.info("Unidades Federativas criadas/atualizadas com sucesso!")


# def get_default_estado_civil():
#     return EstadoCivil.objects.get_or_create(nome="Solteiro(a)")[0].id


# default_estado_civil = get_default_estado_civil()


class Municipio(models.Model):
    nome: str = models.CharField(max_length=255, verbose_name="Nome")
    uf = models.ForeignKey(
        UnidadeFederativa,
        on_delete=models.PROTECT,  # Protege a exclusão se houver municípios relacionados
        # Permite acesso reverso: unidade_federativa.municipios
        related_name="%(app_label)s_%(class)s_related",
        verbose_name="Unidade Federativa",
        default=UnidadeFederativa.get_default_uf,
    )
    codigo_ibge: str = models.CharField(
        max_length=7,
        verbose_name="Código IBGE",
        unique=True,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["nome"]  # Ordena os municípios alfabeticamente por nome
        verbose_name = "Município"
        verbose_name_plural = "Municípios"

    def __str__(self) -> str:
        return f"{self.nome}"

    def get_taxa_issqn(
        self,
        atividade="Atividade notarial ou de registro",
        data_referencia=None,
    ) -> float:
        if data_referencia is None:
            data_referencia = timezone.now()
        try:
            taxa = self.taxas_issqn.filter(
                atividade=atividade,
                data_inicio_validade__lte=data_referencia,
                data_fim_validade__gte=data_referencia,
            ).first()
            if taxa is None:
                taxa = self.taxas_issqn.last()
            return taxa.taxa_percentual if taxa else 0.0
        except Issqn.DoesNotExist:
            return 0.0

    def qualificacao(self) -> str:
        if self.uf:
            return f"{self.nome}"
        else:
            return self.nome

    def get_codigo_ibge(self) -> int:
        if self.codigo_ibge:
            return self.codigo_ibge
        else:
            return 0

    def clean(self) -> None:
        super().clean()
        # Aqui você pode adicionar qualquer validação adicional necessária para o modelo de Município

    @staticmethod
    def get_default_municipio() -> int:
        return Municipio.objects.get_or_create(
            id=2310,
            defaults={
                "nome": "Belo Horizonte",
                "uf": UnidadeFederativa.get_default_uf(),
            },
        )[0].id

    @classmethod
    def criar_municipios_default(cls) -> None:
        mg, created = UnidadeFederativa.objects.update_or_create(sigla="MG")

        municipios = [
            ("Belo Horizonte", 3106200),
            ("Araxá", 3104007),
            ("Monte Carmelo", 3143104),
            ("Alfenas", 3101607),
            ("Uberlandia", 3170206),
            ("Ituiutaba", 3134202),
            ("Sacramento", 3156908),
            ("Uberaba", 3170107),
        ]
        logger.info("Populando Municípios")
        for nome, codigo_ibge in municipios:
            cls.objects.get_or_create(
                id=codigo_ibge,
                defaults={"codigo_ibge": codigo_ibge, "nome": nome, "uf": mg},
            )


class TaxaEstadual(models.Model):
    estado = models.ForeignKey(
        UnidadeFederativa,
        on_delete=models.CASCADE,
        related_name="taxas_estaduais",
        default=UnidadeFederativa.get_default_uf,
    )
    atividade: str = models.CharField(
        max_length=255,
        default="Atividade notarial ou de registro",
    )  # ou outra forma de identificar a atividade
    taxa_percentual = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=5,
    )  # taxa em percentual
    data_inicio_validade = models.DateField(null=True, blank=True)
    data_fim_validade = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ["estado", "atividade", "data_inicio_validade"]
        verbose_name = "Taxa Estadual"
        verbose_name_plural = "Taxas Estaduais"

    def __str__(self) -> str:
        return f"{self.estado} - {self.atividade}: {self.taxa_percentual}%"

    # metodo que devolve a taxa estadual em vigencia, ou seja, que está dentro da data de validade com base na data recebida e no estado ou a ultima cadastrada
    def get_taxa_em_vigencia(self: "TaxaEstadual", data_referencia=None, estado=None):
        try:
            taxa = self.taxas_estaduais.filter(
                estado=estado or UnidadeFederativa.get_default_uf(),
                data_inicio_validade__lte=data_referencia or timezone.now(),
                data_fim_validade__gte=data_referencia,
            ).first()
            if taxa is None:
                taxa = self.taxas_estaduais.last()
            return taxa
        except TaxaEstadual.DoesNotExist:
            return None


class Issqn(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        related_name="taxas_issqn",
        default=Municipio.get_default_municipio,
    )
    atividade: str = models.CharField(
        max_length=255,
        default="Atividade notarial ou de registro",
    )
    taxa_percentual = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=5,
    )  # taxa em percentual
    data_inicio_validade = models.DateField()
    data_fim_validade = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ["municipio", "atividade", "data_inicio_validade"]
        verbose_name = "Taxa ISSQN"
        verbose_name_plural = "Taxas ISSQN"

    def __str__(self) -> str:
        return f"{self.municipio} - {self.atividade}: {self.taxa_percentual}%"

    # metodo que devolve a taxa issqn em vigencia, ou seja, que está dentro da data de validade com base na data recebida e no municipio ou a ultima cadastrada
    def get_taxa_em_vigencia(self, data_referencia=None, municipio=None):
        data_referencia = data_referencia or timezone.now()

        if municipio is None:
            municipio = Municipio.get_default_municipio()
        try:
            taxa = self.taxas_issqn.filter(
                municipio=municipio,
                data_inicio_validade__lte=data_referencia,
                data_fim_validade__gte=data_referencia,
            ).first()
            if taxa is None:
                taxa = self.taxas_issqn.last()
            return taxa
        except Issqn.DoesNotExist:
            return None


def get_default_issqn():
    return Issqn.objects.get_or_create(
        id=1,
        defaults={
            "municipio": Municipio.get_default_municipio,
            "atividade": "Atividade notarial ou de registro",
            "taxa_percentual": 2.0,
            "data_inicio_validade": timezone.now(),
        },
    )[0].id


default_issqn = get_default_issqn


class TipoRegistro(models.Model):
    MATRICULA = "M"
    AVERBACAO = "A"
    TRANSCRICAO = "T"
    INSCRICAO = "I"

    CHOICES = (
        (MATRICULA, "Matrícula"),
        (AVERBACAO, "Registro Auxiliar (L3)"),
        (TRANSCRICAO, "Transcrição"),
        (INSCRICAO, "Inscrição"),
    )

    _choice_dict = dict(CHOICES)

    nome: str = models.CharField(
        max_length=25,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Tipo de Registro"
        verbose_name_plural = "Tipos de Registro"

    def __str__(self) -> str:
        return self.nome or "Urbano"

    def get_default_tipo_imovel():
        return TipoRegistro.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Urbano",
            },
        )[0].id

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Matrícula")


# default_tipo_imovel = get_default_tipo_imovel()


class TipoRegistroImobiliario(models.Model):
    """
    Modelo para representar os diferentes Tipos de Registros Imobiliários que podem existir
    em um Cartório de Projeto CEHTES.

    Cada tipo de registro imobiliário, seja ele Matrícula, Transcrição ou Inscrição, terá uma
    entrada única nesta tabela.

    Fields:
        descricao (CharField): Descrição ou nome do tipo de registro imobiliário.
                               Pode ser, por exemplo, 'Matrícula', 'Transcrição', 'Inscrição', etc.

    """

    nome: str = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
    )

    objects: TipoRegistroImobiliarioManager = TipoRegistroImobiliarioManager()

    class Meta:
        verbose_name = "Tipo de Registro Imobiliário"
        verbose_name_plural = "Tipos de Registros Imobiliários"

    def __str__(self) -> str:
        return self.nome

    @cached_property
    def sigla(self):
        return self.nome[0].upper()

    @staticmethod
    def get_default_tipo_registro_imobiliario() -> "TipoRegistroImobiliario":
        return TipoRegistroImobiliario.get_matricula()

    @staticmethod
    def get_matricula() -> "TipoRegistroImobiliario":
        obj, created = TipoRegistroImobiliario.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Matrícula",
            },
        )

        return obj


# default_tipo_registro_imobiliario = TipoRegistroImobiliario.get_default_tipo_registro_imobiliario()


class Instrucao(models.Model):
    card_id = models.IntegerField(unique=True)
    texto = MarkdownxField()

    class Meta:
        verbose_name = "Instruçao"
        verbose_name_plural = "Instruções"

    def __str__(self) -> str:
        return f"{self.card_id} - {self.texto}"


class Feriado(models.Model):
    TIPO_NACIONAL = "N"
    TIPO_ESTADUAL = "E"
    TIPO_MUNICIPAL = "M"

    TIPO_CHOICES = [
        (TIPO_NACIONAL, "Nacional"),
        (TIPO_ESTADUAL, "Estadual"),
        (TIPO_MUNICIPAL, "Municipal"),
    ]

    nome: str = models.CharField(max_length=255)
    data = models.DateField()
    tipo: str = models.CharField(
        max_length=1,
        choices=TIPO_CHOICES,
        default=TIPO_NACIONAL,
        verbose_name="Tipo de Feriado",
    )
    estado = models.ForeignKey(
        "UnidadeFederativa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Estado",
    )
    municipio = models.ForeignKey(
        "Municipio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Município",
    )

    class Meta:
        unique_together = (("data", "tipo", "estado", "municipio"),)
        verbose_name = "Feriado"
        verbose_name_plural = "Feriados"

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_tipo_display()})"

    def clean(self) -> None:
        super().clean()
        if self.tipo == self.TIPO_ESTADUAL and not self.estado:
            msg = "Feriados estaduais devem ter um estado associado."
            raise ValidationError(msg)
        if self.tipo == self.TIPO_MUNICIPAL and not self.municipio:
            msg = "Feriados municipais devem ter um município associado."
            raise ValidationError(msg)

    @staticmethod
    def get_default_feriado() -> int:
        return Feriado.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Natal",
                "data": date(2021, 12, 25),
                "tipo": "N",
            },
        )[0].id


class DadosBancarios(models.Model):
    titular: str = models.CharField("Titular da Conta", max_length=255)
    nome_banco: str = models.CharField("Nome do Banco", max_length=255)
    numero_agencia = models.PositiveIntegerField("Número da Agência")
    numero_conta: str = models.CharField("Número da Conta", max_length=20)
    tipo_conta: str = models.CharField(
        "Tipo de Conta",
        max_length=20,
        choices=[
            ("corrente", "Conta Corrente"),
            ("poupanca", "Conta Poupança"),
        ],
    )

    class Meta:
        verbose_name = "Dados Bancários"
        verbose_name_plural = "Dados Bancários"

    def __str__(self) -> str:
        return f"{self.titular} - {self.nome_banco} - {self.numero_conta} ({self.tipo_conta})"


class TipoDocumento(models.Model):
    sigla: str = models.CharField(
        "Sigla",
        max_length=20,
        unique=True,
        null=True,
        blank=True,
    )
    nome: str = models.CharField(
        "nome",
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        default="",
        db_index=True,
    )

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = [
            "nome",
        ]  # Isso ordenará todas as consultas por 'nome' em ordem ascendente

    def __str__(self) -> str:
        logger.debug(f"TipoDocumento.__str__ - {self.nome}")
        return self.get_sigla_formatada

    @classmethod
    def get_por_sigla(cls, sigla) -> "TipoDocumento":
        try:
            return cls.objects.get(sigla=sigla)
        except cls.DoesNotExist:
            return None

    @property
    def get_sigla_formatada(self):
        if self.sigla:
            return self.sigla

        return self.nome[:3].upper()

    @staticmethod
    def get_default_tipo_documento_id() -> int:
        return TipoDocumento.objects.get_or_create(
            sigla="CPF",
            defaults={
                "nome": "Cadastro de Pessoas Físicas",
            },
        )[0]


class TipoTributacao(models.Model):
    """Modo como o emolumento será cobrado, se haverá desconto por politicas publicas, etc."""

    nome: str = models.CharField(max_length=100, unique=True, db_index=True)
    descricao: str = models.CharField(max_length=255, null=True, blank=True)
    percentual_desconto = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=5,
        default=0.0,
        verbose_name="Desconto (%)",
        help_text="Percentual de desconto a ser aplicado sobre os emolumento.",
    )
    ativo: bool = models.BooleanField(
        default=True,
        help_text="Se o tipo de tributação está ativo ou não.",
    )

    outros_codigo_trib_tj = models.BigIntegerField(
        blank=True,
        null=True,
        help_text="Ao utilizar o outros_codigo_trib_tj (28) para casos como erro do cartorio, que cobrar apenas a taxa judiciaria.",
    )
    sempre_cobrar_taxa_judiciaria: bool = models.BooleanField(
        default=False,
        help_text="Ao utilizar o outros_codigo_trib_tj, pode ser informado se a cobrança da taxa judiciária é sempre obrigatória.",
    )

    percentual_desconto_tfj = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=5,
        default=0.0,
        verbose_name="Desconto TFJ (%)",
        help_text="Percentual de desconto a ser aplicado sobre o TFJ.",
    )

    codigo = models.IntegerField(
        blank=False,
        null=True,
        verbose_name="Código de Tributação do Tribunal",
        help_text="Exibe o número do código de tributação fornecido pelo tribunal.",
    )

    class Meta:
        verbose_name = "Tributação"
        verbose_name_plural = "Tributações"

    def __str__(self) -> str:
        if self.percentual_desconto > 0:
            if self.codigo:
                return f"{self.codigo} - {self.nome} - {self.percentual_desconto}% desconto"
            else:
                return f"{self.nome} - {self.percentual_desconto}% desconto"
        else:
            if self.codigo:
                return f"{self.codigo} - {self.nome}"
            else:
                return f"{self.nome}"

    @staticmethod
    def get_default_tipo_tributacao() -> int:
        return TipoTributacao.get_normal()

    @staticmethod
    def get_normal() -> "TipoTributacao":
        return TipoTributacao.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Normal",
                "descricao": "Normal",
                "percentual_desconto": 0,
            },
        )[0]

    @classmethod
    def get_ativos(cls) -> QuerySet["TipoTributacao"]:
        return cls.objects.filter(ativo=True).order_by("nome")


class Fundo(models.Model):
    TIPO_VALOR = (
        ("PERCENTUAL", "Percentual"),
        ("FIXO", "Fixo"),
    )
    nome: str = models.CharField(max_length=100, unique=True, db_index=True)
    descricao: str = models.CharField(max_length=255, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo: str = models.CharField(max_length=10, choices=TIPO_VALOR)

    estado = models.ForeignKey(
        "UnidadeFederativa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Estado",
        default=UnidadeFederativa.get_default_uf,
    )
    # campos de data de inicio e fim da validade
    data_inicio_validade = models.DateField(auto_now_add=True)
    data_fim_validade = models.DateField(default=get_um_ano_a_partir_de_agora)

    class Meta:
        verbose_name = "Fundo"
        verbose_name_plural = "Fundos"

    def __str__(self) -> str:
        return self.nome

    # metodo obter fundo em vigencia, ou seja, que está dentro da data de validade com base na data recebida e no estado

    def get_fundo_em_vigencia(self, data_referencia=None, estado=None):
        data_referencia = (
            data_referencia if data_referencia is not None else timezone.now()
        )
        estado = estado if estado is not None else UnidadeFederativa.get_default_uf()

        fundo = self.fundos.filter(
            estado=estado,
            data_inicio_validade__lte=data_referencia,
            data_fim_validade__gte=data_referencia,
        ).first()

        return fundo if fundo is not None else self.fundos.last()

    @staticmethod
    def get_default_fundo() -> int:
        return Fundo.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Recompe",
                "descricao": "Recompe",
                "valor": "5,66",
                "tipo": "PERCENTUAL",
                "estado": UnidadeFederativa.get_default_uf(),
                "data_inicio_validade": timezone.now(),
                "data_fim_validade": get_um_ano_a_partir_de_agora,
            },
        )[0].id


class UnidadePrazo(models.Model):
    nome: str = models.CharField(
        max_length=50,
        help_text="Nome da unidade de tempo. Por exemplo: 'Dias', 'Horas', 'Minutos'.",
    )
    em_horas = models.FloatField(
        help_text="Conversão da unidade para horas. Por exemplo, para 'Dias' insira '24', para 'Minutos' insira '1/60'.",
    )
    horas_uteis_por_dia = models.FloatField(
        default=8,
        help_text="Número de horas úteis em um dia.",
    )

    class Meta:
        verbose_name = "Prazo"
        verbose_name_plural = "Prazos"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    def converter_para_horas(self, valor, eh_prazo_util=False):
        if self.nome.lower() == "dias" and eh_prazo_util:
            return valor * self.horas_uteis_por_dia
        return valor * self.em_horas

    def converter_de_horas(self, valor_em_horas):
        return valor_em_horas / self.em_horas

    @staticmethod
    # def get_default_unidade_prazo():
    #     return UnidadePrazo.objects.get_or_create(
    #         nome="Dias",
    #         em_horas=24,
    #     )[0]
    def get_default_unidade_prazo() -> "UnidadePrazo":
        # get_or_create retorna uma tupla (objeto, criado)
        unidade_prazo, criado = UnidadePrazo.objects.get_or_create(
            nome="Dias",
            defaults={"em_horas": 24},
        )
        return unidade_prazo


class Expediente(models.Model):
    DIA_DA_SEMANA_CHOICES = [
        (0, "Segunda"),
        (1, "Terça"),
        (2, "Quarta"),
        (3, "Quinta"),
        (4, "Sexta"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]
    dia_da_semana = models.IntegerField(
        choices=DIA_DA_SEMANA_CHOICES,
        help_text="0 = Segunda, 1 = Terça, etc.",
    )
    inicio = models.TimeField(default="09:00")
    fim = models.TimeField(default="17:00")

    class Meta:
        verbose_name = "Expediente"
        verbose_name_plural = "Expedientes"
        ordering = ["dia_da_semana"]

    def __str__(self) -> str:
        dia_nome = dict(self.DIA_DA_SEMANA_CHOICES).get(
            self.dia_da_semana,
            "Dia inválido",
        )
        return f"{dia_nome} - {self.inicio} às {self.fim}"

    def horas_uteis(self, data):
        if isinstance(data, datetime):
            data = data.date()  # Converter para datetime.date

        inicio_expediente = datetime.combine(data, self.inicio)
        fim_expediente = datetime.combine(data, self.fim)

        # Ajustar para a timezone correta, se necessário
        inicio_expediente = timezone.make_aware(
            inicio_expediente,
            timezone.get_default_timezone(),
        )
        fim_expediente = timezone.make_aware(
            fim_expediente,
            timezone.get_default_timezone(),
        )

        agora = timezone.now()
        # Se a data atual já passou do início do expediente, usar a data atual; senão, usar o início do expediente
        inicio_efetivo = (
            agora
            if agora.date() == data and agora > inicio_expediente
            else inicio_expediente
        )

        # Se a data atual já passou do fim do expediente, considerar o expediente como encerrado
        if agora >= fim_expediente:
            return 0

        # Calcula a diferença em horas
        return (fim_expediente - inicio_efetivo).seconds / 3600

    @staticmethod
    def get_default_expedientes() -> list["Expediente"]:
        dias_da_semana = range(5)  # De 0 (Segunda-feira) a 4 (Sexta-feira)

        # Buscar todos os Expedientes existentes para os dias da semana de interesse
        expedientes_existentes = Expediente.objects.filter(
            dia_da_semana__in=dias_da_semana,
        )

        # Criar um dicionário para mapear os dias da semana aos Expedientes existentes
        expedientes_map = {
            expediente.dia_da_semana: expediente
            for expediente in expedientes_existentes
        }

        expedientes = []
        for dia in dias_da_semana:
            # Verificar se já existe um Expediente para o dia da semana
            if dia not in expedientes_map:
                # Se não existir, criar um novo Expediente
                expediente, created = Expediente.objects.get_or_create(
                    dia_da_semana=dia,
                    defaults={
                        "inicio": time(9, 0),  # Cria um objeto time para as 9:00
                        "fim": time(17, 0),  # Cria um objeto time para as 17:00
                    },
                )
            else:
                # Se já existir, usar o Expediente existente
                expediente = expedientes_map[dia]

            expedientes.append(expediente)

        return expedientes


class PrazoLegal(models.Model):
    valor = models.IntegerField(
        help_text="Valor numérico do prazo legal na unidade especificada. Por exemplo, se a unidade for 'Dias', e o prazo for de 5 dias, insira '5'.",
    )
    unidade = models.ForeignKey(
        UnidadePrazo,
        on_delete=models.CASCADE,
        help_text="Selecione a unidade de tempo para o prazo legal. Por exemplo, 'Dias' ou 'Horas'.",
    )
    eh_prazo_util: bool = models.BooleanField(
        default=False,
        help_text="Marque esta opção se o prazo for contado em dias ou horas úteis.",
    )

    class Meta:
        verbose_name = "Prazo Legal"
        verbose_name_plural = "Prazos Legais"
        ordering = ["unidade", "valor"]

    def __str__(self) -> str:
        return f"{self.valor} {self.unidade.nome} ({self.tipo_prazo})"

    @cached_property
    def dias(self):
        if self.unidade.nome.lower() == "dias":
            return self.valor
        else:
            return self.unidade.converter_de_horas(self.em_horas)

    @cached_property
    def tipo_prazo(self) -> str:
        return "Útil" if self.eh_prazo_util else "Corrido"

    @cached_property
    def em_horas(self):
        return self.unidade.converter_para_horas(self.valor, self.eh_prazo_util)

    @staticmethod
    def get_default_prazo_legal() -> int:
        try:
            prazo_legal, criado = PrazoLegal.objects.get_or_create(
                unidade=UnidadePrazo.get_default_unidade_prazo(),
                eh_prazo_util=False,
                defaults={"valor": 5},
            )
        except MultipleObjectsReturned:
            prazo_legal = PrazoLegal.objects.filter(
                unidade=UnidadePrazo.get_default_unidade_prazo(),
                eh_prazo_util=False,
            ).first()
        return prazo_legal

    @classmethod
    def criar_padroes(cls) -> "PrazoLegal":
        return cls.get_default_prazo_legal()


# def get_default_prazo_legal():
#     return PrazoLegal.objects.get_or_create(
#         id=1,
#         defaults={
#             "valor": 10,
#             "unidade": UnidadePrazo.objects.get_or_create(
#                 id=1,
#                 defaults={
#                     "nome": "Dias",
#                     "em_horas": 24,
#                 },
#             )[0],
#             "eh_prazo_util": False,
#         },
#     )[0].id


# default_prazo_legal = get_default_prazo_legal()


class TipoPapelParte(models.Model):
    """Adquirente, Transmitente, Credor, Devedor, etc."""

    nome: str = models.CharField(max_length=255, null=True, blank=True)
    descricao: str = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Tipo de Papel da Parte"
        verbose_name_plural = "Tipos de Papéis das Partes"

    def __str__(self) -> str:
        return self.nome

    def get_default_tipo_papel_parte():
        return TipoPapelParte.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Adquirente",
                "descricao": "Adquirente",
            },
        )[0].id


class TipoOrigem(models.Model):
    nome: str = models.CharField(max_length=255, null=True, blank=True, unique=True)

    class Meta:
        verbose_name = "Origem"
        verbose_name_plural = "Origens"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome or "Balcão"

    @staticmethod
    def get_default_tipo_origem() -> "TipoOrigem":
        tipo_origem, created = TipoOrigem.objects.get_or_create(
            id=1,
            defaults={"nome": "Balcão"},
        )
        return tipo_origem  # Retorna o ID do Tipo de Origem

    @staticmethod
    def get_consulta_eletronica() -> "TipoOrigem":
        return TipoOrigem.objects.get_or_create(
            id=4,
            defaults={"nome": "Consulta Eletrônica"},
        )[0]

    #  (2,'ONR - Matrícula Visualizada'),
    @staticmethod
    def get_visualizacao_matricula() -> "TipoOrigem":
        return TipoOrigem.objects.get_or_create(
            id=2,
            defaults={"nome": "ONR - Matrícula Visualizada"},
        )[0]

    @staticmethod
    def criar_padroes() -> None:
        pass
        #  (2,'ONR - Matrícula Visualizada'),
        #  (3,'ONR - Ofício'),
        #  (4,'ONR - Consulta Eletrônica'),
        #  (5,'ONR - Penhora Online SPH'),
        #  (0,'Balcão Protocolo'),
        #  (6,'ONR - Certidões a Emitir'),
        #  (7,'ONR - e-Protocolo'),
        #  (8,'ONR - Intimação'),
        #  (9,'ONR - Penhora Online PH');


class TipoLogradouro(models.Model):
    codigo: str = models.CharField(max_length=10, null=True, blank=True)
    nome: str = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Tipo de Logradouro"
        verbose_name_plural = "Tipos de Logradouros"

    def __str__(self) -> str:
        return str(self.nome)

    @staticmethod
    def get_default_tipo_logradouro() -> int:
        return TipoLogradouro.objects.get_or_create(
            id=1,
            defaults={
                "codigo": "R",
                "nome": "Rua",
            },
        )[0].id

    @classmethod
    def create_tipos_de_logradouro(cls) -> None:
        try:
            tipos_logradouro = [
                (1, "Acampamento", "Ac"),
                (2, "Acesso", "Acs"),
                (3, "Açude", "Aç"),
                (4, "Adro", "Adr"),
                (5, "Aeroporto", "Arp"),
                (6, "Afluente", "Af"),
                (7, "Aglomerado", "Ag"),
                (8, "Agrovila", "Agv"),
                (9, "Alagado", "Alg"),
                (10, "Alameda", "Al"),
                (11, "Aldeia", "Ad"),
                (12, "Aleia", "Al"),
                (13, "Alto", "At"),
                (14, "Anel", "An"),
                (15, "Antiga", "Ant"),
                (16, "Antigo", "Ant"),
                (17, "Área", "Ar"),
                (18, "Areal", "Arl"),
                (19, "Arraial", "Arl"),
                (20, "Arroio", "Ar"),
                (21, "Artéria", "Ar"),
                (22, "Assentamento", "As"),
                (23, "Atalho", "At"),
                (24, "Aterro", "Atr"),
                (25, "Autódromo", "Aut"),
                (26, "Avenida", "Av"),
                (27, "Baia", "Ba"),
                (28, "Bairro", "Ba"),
                (29, "Baixa", "Bx"),
                (30, "Baixada", "Bxd"),
                (31, "Baixadão", "Bxd"),
                (32, "Baixão", "Bxa"),
                (33, "Baixo", "Bx"),
                (34, "Balão", "Bl"),
                (35, "Balneário", "Bal"),
                (36, "Barra", "Ba"),
                (37, "Barragem", "Bgm"),
                (38, "Barranca", "Brc"),
                (39, "Barranco", "Brc"),
                (40, "Barreiro", "Br"),
                (41, "Barro", "Ba"),
                (42, "Beco", "Bc"),
                (43, "Beira", "Br"),
                (44, "Beirada", "Brd"),
                (45, "Belvedere", "Bel"),
                (46, "Bloco", "Blc"),
                (47, "Bocaina", "Bc"),
                (48, "Boqueirão", "Bq"),
                (49, "Bosque", "Bs"),
                (50, "Boulevard", "Blvd"),
                (51, "Brejo", "Brj"),
                (52, "Buraco", "Br"),
                (53, "Cabeceira", "Cb"),
                (54, "Cachoeira", "Cc"),
                (55, "Cachoeirinha", "Cch"),
                (56, "Cais", "Cs"),
                (57, "Calcada", "Cc"),
                (58, "Calçadão", "Ccd"),
                (59, "Caminho", "Cm"),
                (60, "Campo", "Cp"),
                (61, "Canal", "Cn"),
                (62, "Canteiro", "Ct"),
                (63, "Capão", "Cp"),
                (64, "Capoeira", "Cpr"),
                (65, "Cartódromo", "Ct"),
                (66, "Central", "Ct"),
                (67, "Centro", "Ct"),
                (68, "Cerca", "Cc"),
                (69, "Cerrado", "Crd"),
                (70, "Cerro", "Cr"),
                (71, "Chácara", "Ch"),
                (72, "Chapada", "Chp"),
                (73, "Chapadão", "Chp"),
                (74, "Charco", "Chc"),
                (75, "Cidade", "Cd"),
                (76, "Circular", "Cr"),
                (77, "Cohab", "Cb"),
                (78, "Colina", "Cl"),
                (79, "Colônia", "Cln"),
                (80, "Comunidade", "Cm"),
                (81, "Condomínio", "Cnd"),
                (82, "Conjunto", "Cjt"),
                (83, "Continuação", "Cnt"),
                (84, "Contorno", "Cnt"),
                (85, "Corredor", "Cr"),
                (86, "Córrego", "Crg"),
                (87, "Costa", "Cs"),
                (88, "Coxilha", "Cxl"),
                (89, "Cruzamento", "Cz"),
                (90, "Descida", "Dc"),
                (91, "Desvio", "Dsv"),
                (92, "Dique", "Dq"),
                (93, "Distrito", "Dt"),
                (94, "Divisa", "Dv"),
                (95, "Divisão", "Dv"),
                (96, "Divisor", "Dvr"),
                (97, "Edifício", "Ed"),
                (98, "Eixo", "Ex"),
                (99, "Elevado", "Elv"),
                (100, "Encosta", "Ec"),
                (101, "Engenho", "Eng"),
                (102, "Enseada", "Es"),
                (103, "Entrada", "Ed"),
                (104, "Entreposto", "Et"),
                (105, "Entroncamento", "Et"),
                (106, "Escada", "Esc"),
                (107, "Escadão", "Esc"),
                (108, "Escadaria", "Esc"),
                (109, "Escadinha", "Esc"),
                (110, "Espigão", "Ep"),
                (111, "Esplanada", "Es"),
                (112, "Esquina", "Esq"),
                (113, "Estação", "Est"),
                (114, "Estacionamento", "Est"),
                (115, "Estádio", "Est"),
                (116, "Estância", "Est"),
                (117, "Estrada", "Est"),
                (118, "Extensão", "Ex"),
                (119, "Faixa", "Fx"),
                (120, "Favela", "Fv"),
                (121, "Fazenda", "Fz"),
                (122, "Feira", "Fe"),
                (123, "Ferrovia", "Fv"),
                (124, "Final", "Fnl"),
                (125, "Floresta", "Fl"),
                (126, "Folha", "Fh"),
                (127, "Fonte", "Ft"),
                (128, "Fortaleza", "Fr"),
                (129, "Freguesia", "Fg"),
                (130, "Fundos", "Fd"),
                (131, "Furo", "Fr"),
                (132, "Galeria", "Gl"),
                (133, "Gameleira", "Gm"),
                (134, "Garimpo", "Gr"),
                (135, "Gleba", "Gl"),
                (136, "Granja", "Grj"),
                (137, "Grota", "Gr"),
                (138, "Habitacional", "Hb"),
                (139, "Haras", "Hs"),
                (140, "Hipódromo", "Hp"),
                (141, "Horto", "Ht"),
                (142, "Igarapé", "Ig"),
                (143, "Ilha", "Il"),
                (144, "Inaplicável", "In"),
                (145, "Invasão", "Iv"),
                (146, "Jardim", "Jd"),
                (147, "Jardinete", "Jdt"),
                (148, "Ladeira", "Ld"),
                (149, "Lado", "Ld"),
                (150, "Lago", "Lg"),
                (151, "Lagoa", "Lg"),
                (152, "Lagoinha", "Lg"),
                (153, "Largo", "Lg"),
                (154, "Lateral", "Lt"),
                (155, "Leito", "Lt"),
                (156, "Ligação", "Lg"),
                (157, "Limeira", "Lm"),
                (158, "Limite", "Lm"),
                (159, "Limites", "Lm"),
                (160, "Linha", "Ln"),
                (161, "Lote", "Lt"),
                (162, "Loteamento", "Lt"),
                (163, "Lugarejo", "Lg"),
                (164, "Maloca", "Ml"),
                (165, "Manancial", "Mn"),
                (166, "Mangue", "Mg"),
                (167, "Margem", "Mg"),
                (168, "Margens", "Mg"),
                (169, "Marginal", "Mg"),
                (170, "Marina", "Mn"),
                (171, "Mata", "Mt"),
                (172, "Mato", "Mt"),
                (173, "Módulo", "Md"),
                (174, "Monte", "Mt"),
                (175, "Morro", "Mr"),
                (176, "Muro", "Mr"),
                (177, "Não Especificado", "Ne"),
                (178, "Núcleo", "Nc"),
                (179, "Oca", "Oc"),
                (180, "Oleoduto", "Ol"),
                (181, "Olho", "Ol"),
                (182, "Olhos", "Ol"),
                (183, "Orla", "Or"),
                (184, "Outros", "Ot"),
                (185, "Paco", "Pc"),
                (186, "Palafita", "Pl"),
                (187, "Pântano", "Pt"),
                (188, "Parada", "Pd"),
                (189, "Paradouro", "Pd"),
                (190, "Paralela", "Pr"),
                (191, "Parque", "Pq"),
                (192, "Particular", "Pt"),
                (193, "Passagem", "Ps"),
                (194, "Passarela", "Ps"),
                (195, "Passeio", "Ps"),
                (196, "Passo", "Ps"),
                (197, "Pasto", "Pt"),
                (198, "Pátio", "Pt"),
                (199, "Pavilhão", "Pv"),
                (200, "Pedra", "Pd"),
                (201, "Pedras", "Pd"),
                (202, "Pedreira", "Pd"),
                (203, "Penhasco", "Pnh"),
                (204, "Perimetral", "Pm"),
                (205, "Perímetro", "Pm"),
                (206, "Perto", "Pr"),
                (207, "Planalto", "Pl"),
                (208, "Plataforma", "Pl"),
                (209, "Ponta", "Pn"),
                (210, "Ponte", "Pn"),
                (211, "Ponto", "Pt"),
                (212, "Porto", "Pr"),
                (213, "Posto", "Ps"),
                (214, "Povoado", "Pv"),
                (215, "Praça", "Pc"),
                (216, "Praia", "Pr"),
                (217, "Projeção", "Prj"),
                (218, "Projetada", "Prj"),
                (219, "Projeto", "Prj"),
                (220, "Prolongamento", "Pr"),
                (221, "Propriedade", "Pr"),
                (222, "Próximo", "Prx"),
                (223, "Quadra", "Qd"),
                (224, "Quarteirão", "Qr"),
                (225, "Quilombo", "Ql"),
                (226, "Quilometro", "Km"),
                (227, "Quinta", "Qn"),
                (228, "Quintas", "Qn"),
                (229, "Rachão", "Rch"),
                (230, "Ramal", "Rm"),
                (231, "Rampa", "Rp"),
                (232, "Rancho", "Rn"),
                (233, "Recanto", "Rc"),
                (234, "Região", "Rg"),
                (235, "Represa", "Rp"),
                (236, "Residencial", "Rs"),
                (237, "Reta", "Rt"),
                (238, "Retiro", "Rt"),
                (239, "Retorno", "Rtn"),
                (240, "Riacho", "Rc"),
                (241, "Ribanceira", "Rb"),
                (242, "Ribeirão", "Rb"),
                (243, "Rincão", "Rc"),
                (244, "Rio", "R"),
                (245, "Rocha", "Rc"),
                (246, "Rochedo", "Rc"),
                (247, "Rodovia", "Rv"),
                (248, "Rotatória", "Rt"),
                (249, "Rotula", "Rt"),
                (250, "Rua", "R"),
                (251, "Ruela", "Rl"),
                (252, "Saco", "Sc"),
                (253, "Saída", "Sd"),
                (254, "Sanga", "Sg"),
                (255, "Sede", "Sd"),
                (256, "Sem", "Sm"),
                (257, "Seringal", "Srg"),
                (258, "Serra", "Sr"),
                (259, "Sertão", "St"),
                (260, "Servidão", "Srv"),
                (261, "Seta", "St"),
                (262, "Setor", "St"),
                (263, "Sitio", "St"),
                (264, "Sopé", "Sp"),
                (265, "Subida", "Sb"),
                (266, "Superquadra", "Spq"),
                (267, "Tapera", "Tp"),
                (268, "Terminal", "Tm"),
                (269, "Terra", "Tr"),
                (270, "Terreno", "Tr"),
                (271, "Terrenos", "Tr"),
                (272, "Transversal", "Trv"),
                (273, "Travessa", "Tv"),
                (274, "Travessão", "Trv"),
                (275, "Travessia", "Trv"),
                (276, "Trecho", "Tr"),
                (277, "Trevo", "Trv"),
                (278, "Trilha", "Tr"),
                (279, "Trilho", "Tr"),
                (280, "Trilhos", "Tr"),
                (281, "Trincheira", "Tr"),
                (282, "Túnel", "Tn"),
                (283, "Unidade", "Un"),
                (284, "Usina", "Us"),
                (285, "Vala", "Vl"),
                (286, "Valão", "Vln"),
                (287, "Vale", "Vl"),
                (288, "Vargem", "Vg"),
                (289, "Variante", "Vr"),
                (290, "Várzea", "Vz"),
                (291, "Velódromo", "Vld"),
                (292, "Vereda", "Vr"),
                (293, "Vertente", "Vr"),
                (294, "Via", "V"),
                (295, "Viaduto", "Vd"),
                (296, "Vicinal", "Vc"),
                (297, "Viela", "Vl"),
                (298, "Vila", "Vl"),
                (299, "Vilarejo", "Vlj"),
                (300, "Volta", "Vt"),
                (301, "Zona", "Zn"),
                (302, "1a Travessa da Avenida", "1aTvAv"),
                (303, "1a Travessa da Rua", "1aTvR"),
                (304, "2a Travessa da Avenida", "2aTvAv"),
                (305, "2a Travessa da Rua", "2aTvR"),
                (306, "3a Travessa da Avenida", "3aTvAv"),
                (307, "3a Travessa da Rua", "3aTvR"),
                (308, "4a Travessa da Avenida", "4aTvAv"),
                (309, "4a Travessa da Rua", "4aTvR"),
                (310, "5a Travessa da Avenida", "5aTvAv"),
                (311, "5a Travessa da Rua", "5aTvR"),
            ]

            with transaction.atomic():
                for id_, nome, codigo in tipos_logradouro:
                    TipoLogradouro.objects.get_or_create(
                        id=id_,
                        defaults={
                            "nome": nome,
                            "codigo": codigo,
                        },
                    )

            logger.info("Tipos de logradouro criados/atualizados!")
        except OperationalError as e:
            logger.exception(
                f"Erro ao acessar a tabela TipoLogradouro no banco de dados: {e}",
            )


class TipoCertidaoComum(models.Model):
    nome: str = models.CharField(max_length=255, null=True, blank=True, unique=True)
    descricao: str = models.CharField(max_length=255, null=True, blank=True)
    codigo: str = models.CharField(max_length=10, null=True, blank=True, unique=True)
    prazo_legal = models.ForeignKey(
        PrazoLegal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Prazo Legal",
        # default=PrazoLegal.get_default_prazo_legal,
    )
    tipo_cartorio = models.ForeignKey(
        TipoCartorio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Tipo de Certidão"
        verbose_name_plural = "Tipos de Certidões"

    def __str__(self) -> str:
        return self.nome

    @staticmethod
    def get_default_tipo_certidao_comum() -> int:
        return TipoCertidaoComum.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Certidão de Matrícula",
                "descricao": "Certidão de Matrícula",
                "codigo": "CM",
                "prazo_legal": PrazoLegal.get_default_prazo_legal(),
                "tipo_cartorio": TipoCartorio.get_cartorio_registro_imoveis(),
            },
        )[0].id


# Classe model para o determinar o papel das partes numa matricula de imóvel
class Papel(models.Model):
    nome: str = models.CharField(max_length=255, null=True, blank=True, unique=True)
    descricao: str = models.CharField(max_length=255, null=True, blank=True)
    codigo: str = models.CharField(max_length=10, null=True, blank=True, unique=True)

    class Meta:
        verbose_name = "Papel"
        verbose_name_plural = "Papéis"

    def __str__(self) -> str:
        return self.nome

    @staticmethod
    def get_default_papel() -> int:
        return Papel.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Proprietário",
                "descricao": "Proprietário",
                "codigo": "PRO",
            },
        )[0].id


class TipoIntegracao(models.Model):
    ONR_MATRICULA_VISUALIZADA = 2
    ONR_OFICIO = 3
    ONR_CONSULTA_ELETRONICA = 4
    ONR_PENHORA_ONLINE_SPH = 5
    ONR_CERTIDOES_A_EMITIR = 6
    ONR_E_PROTOCOLO = 7
    ONR_INTIMACOES = 8

    CHOICES = [
        (ONR_MATRICULA_VISUALIZADA, "ONR - Matrícula Visualizada"),
        (ONR_OFICIO, "ONR - Ofício"),
        (ONR_CONSULTA_ELETRONICA, "ONR - Consulta Eletronica"),
        (ONR_PENHORA_ONLINE_SPH, "ONR - Penhora Online SPH"),
        (ONR_CERTIDOES_A_EMITIR, "ONR - Certidões a Emitir"),
        (ONR_E_PROTOCOLO, "ONR - E-Protocolo"),
        (ONR_INTIMACOES, "ONR - Intimações"),
    ]

    _choice_dict = dict(CHOICES)

    nome: str = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        choices=CHOICES,
    )

    sub_pasta: str = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Tipo de Integração"
        verbose_name_plural = "Tipos de Integrações"

    def __str__(self) -> str:
        return self.nome

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "")

    @classmethod
    def get_tipo_integracao_onr_matricula_visualizada(cls) -> "TipoIntegracao":
        if not cls.objects.filter(id=cls.ONR_MATRICULA_VISUALIZADA).exists():
            return cls.objects.create(
                id=cls.ONR_MATRICULA_VISUALIZADA,
                nome=cls.get_descricao(cls.ONR_MATRICULA_VISUALIZADA),
            )
        return cls.objects.get(id=cls.ONR_MATRICULA_VISUALIZADA)

    @classmethod
    def get_tipo_integracao_onr_matricula_visualizada_id(cls) -> int:
        resultado = cls.get_tipo_integracao_onr_matricula_visualizada()
        return resultado.id if resultado else None

    @classmethod
    def get_onr_oficio(cls) -> "TipoIntegracao":
        return cls.objects.get_or_create(
            id=cls.ONR_OFICIO,
            defaults={"nome": cls.get_descricao(cls.ONR_OFICIO)},
        )[0]

    @classmethod
    def get_tipo_integracao_onr_consulta_eletronica(cls) -> "TipoIntegracao":
        return cls.objects.get_or_create(
            id=cls.ONR_CONSULTA_ELETRONICA,
            defaults={"nome": cls.get_descricao(cls.ONR_CONSULTA_ELETRONICA)},
        )[0]

    @classmethod
    def get_onr_penhora_online_sph(cls) -> "TipoIntegracao":
        return cls.objects.get_or_create(
            id=cls.ONR_PENHORA_ONLINE_SPH,
            defaults={"nome": cls.get_descricao(cls.ONR_PENHORA_ONLINE_SPH)},
        )[0]

    @classmethod
    def get_certidoes_a_emitir(cls) -> "TipoIntegracao":
        return cls.objects.get_or_create(
            id=6,
            defaults={"nome": cls.get_descricao(cls.ONR_CERTIDOES_A_EMITIR)},
        )[0]

    @classmethod
    def get_tipo_integracao_intimacoes(cls) -> "TipoIntegracao":
        return cls.objects.get_or_create(
            id=8,
            defaults={"nome": cls.get_descricao(cls.ONR_INTIMACOES)},
        )[0]

    @classmethod
    def criar_tipo_integracao_padrao(cls) -> None:
        for value, descricao in cls.CHOICES:
            cls.objects.get_or_create(id=value, defaults={"nome": descricao})


class AuditorIntegracao(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    tipo_integracao = models.ForeignKey(
        "TipoIntegracao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Tipo de Integração",
    )
    created_at: datetime = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.tipo_integracao} - {self.created_at}"

    @classmethod
    def registrar(
        cls,
        tipo_integracao_id: int,
        tipo_integracao_nome: str = "",
    ) -> "AuditorIntegracao":
        obj, created = TipoIntegracao.objects.get_or_create(
            id=tipo_integracao_nome,
            defaults={"nome": tipo_integracao_nome},
        )
        return cls.objects.create(tipo_integracao=obj)

    @classmethod
    def get_data_ultima_importacao_matricula_visualizada(cls) -> datetime:
        registros_de_auditoria = cls.objects.filter(
            tipo_integracao_id=MATRICULA_VISUALIZADA_ORIGEM_ID,
        ).last()

        return (
            registros_de_auditoria.created_at
            if registros_de_auditoria
            else timezone.now()
        )

    @classmethod
    def get_data_ultima_importacao(cls, tipo_integracao_id) -> datetime:
        registros_de_auditoria = cls.objects.filter(
            tipo_integracao_id=tipo_integracao_id,
        ).last()

        return (
            registros_de_auditoria.created_at
            if registros_de_auditoria
            else timezone.now()
        )

    # def auditor_integracao_ultimo_andamento(self):
    #     # Se já temos um auditor, retornamos diretamente, economizando uma consulta ao banco.
    #     return self.objects.filter(tipo_integracao_id=self.tipo_integracao_id).last()["created_at"]
