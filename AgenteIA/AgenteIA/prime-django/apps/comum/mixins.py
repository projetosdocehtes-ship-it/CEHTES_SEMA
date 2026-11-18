import logging
from functools import cached_property

from django.db import models

from apps.comum.models import Municipio, TipoDocumento, TipoLogradouro
from apps.comum.utils import mascarar_documento

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class EnderecoMixin(models.Model):
    tipo_logradouro: TipoLogradouro = models.ForeignKey(
        TipoLogradouro,
        on_delete=models.SET_NULL,
        verbose_name="Tipo de Logradouro",
        # default=TipoLogradouro.get_default_tipo_logradouro,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_related",
        help_text="Ex: rua, avenida, praça, fazenda, etc.",
    )
    logradouro: str = models.CharField(
        "Logradouro/Fazenda",
        max_length=255,
        blank=True,
        null=True,
    )
    numero: str = models.CharField("Número", max_length=11, blank=True, null=True)
    quadra: str = models.CharField("Quadra", max_length=10, blank=True, null=True)
    lote: str = models.CharField("Lote", max_length=10, blank=True, null=True)
    complemento: str = models.CharField(
        "Complemento/Características",
        max_length=50,
        blank=True,
        null=True,
        default="",
    )
    bairro: str = models.CharField("Bairro", max_length=100, blank=True, null=True)
    municipio: Municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Município",
        related_name="%(app_label)s_%(class)s_related",
    )
    cep: str = models.CharField("CEP", max_length=10, blank=True, null=True)

    class Meta:
        abstract = True
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"

    def __str__(self) -> str:
        return str(self.endereco)

    @cached_property
    def get_municipio(self):
        return self.municipio if self.municipio else None

    # property estado para retornar a UF com base no municipio informado.
    @cached_property
    def estado(self):
        return self.municipio.uf if self.municipio else None

    @cached_property
    def endereco(self):
        parts = [
            self.logradouro or "",
            self.numero or "",
            self.bairro or "",
            self.cep or "",
            str(self.municipio) if self.municipio else "",
            self.uf.sigla if self.uf else "",
        ]
        # Filtra os valores vazios ou None
        parts_filtered = [part for part in parts if part]

        # Se todos os valores forem None ou vazios, retorna uma mensagem padrão
        if not parts_filtered:
            return "Endereço não disponível"

        return ", ".join(parts_filtered)

    def get_uf(self):
        return self.municipio.uf if self.municipio else None

    @cached_property
    def uf(self):
        return self.municipio.uf if self.municipio else None

    # Para obter a UF do endereço, você pode utilizar o relacionamento com Municipio
    @cached_property
    def pais(self):
        return self.uf.pais if self.uf else None


class DocumentoMixin(models.Model):
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.CASCADE,
        null=True,
        related_name="%(app_label)s_%(class)s_related",
    )

    documento: str = models.CharField(
        max_length=255,
        verbose_name="Número do Documento",
        null=True,
        blank=True,
    )
    data_emissao = models.DateField(
        verbose_name="Data de Emissão",
        null=True,
        blank=True,
    )
    orgao_emissor: str = models.CharField(
        max_length=255,
        verbose_name="Órgão Emissor",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True  # Isso torna o DocumentoMixin abstrato
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def sigla_tipo_documento(self):
        return self.tipo_documento.sigla if self.tipo_documento else None

    def get_documento_formatado(self):
        from apps.comum.models import TipoDocumento

        """
        Formata o documento com base no seu tipo.

        - Se o tipo do documento for CPF, formata como xxx.xxx.xxx-xx.
        - Se o tipo do documento for CNPJ, formata como xx.xxx.xxx/xxxx-xx.
        - Para outros tipos, divide o documento em três partes aproximadamente iguais e
        retorna a primeira e a última parte separadas por "...".

        Retorna:
            str: O documento formatado.
        """
        try:
            doc = self.documento
            if self.tipo_documento.sigla == "CPF" and len(doc) == 11:
                return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
            elif self.tipo_documento.sigla == "CNPJ" and len(doc) == 14:
                return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
            else:
                n = len(doc)
                divs = n // 3  # Encontra o número de divisões
                partes = [
                    doc[i * divs : (i + 1) * divs] for i in range(3)
                ]  # Divide o documento em 3 partes

                # Retorna a primeira e a última parte, unidas por "..."
                return f"{partes[0]}...{partes[-1]}"
        except TipoDocumento.DoesNotExist:
            return self.documento

    def get_documento_formatado_mascadado(self):
        doc_formatado = self.get_documento_formatado()
        return mascarar_documento(doc_formatado)




class ConfiguracaoMixin(models.Model):
    sessao: str = models.CharField(max_length=255, default="Geral")
    valor: str = models.CharField(max_length=100, blank=True, null=True)
    chave: str = models.CharField(max_length=255, null=True, blank=True)
    descricao = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"

    def __str__(self) -> str:
        return str(self.descricao)

    @classmethod
    def get_valor(cls, chave, valor_padrao=None) -> str:
        try:
            return cls.objects.get(chave=chave).valor
        except cls.DoesNotExist:
            return valor_padrao

    # Exemplo de como criar uma nova configuracao
    # Configuracao.objects.create(chave='MARGEM_SUPERIOR_IMAGEM', valor='20', descricao='Margem superior para imagens em mm')

    # Exemplo de como obter uma configuracao
    # margem_superior = Configuracao.get_valor("MARGEM_SUPERIOR_IMAGEM", "20")


# class AuditMixin(models.Model):
#     Usuario = get_user_model()

#     criado_por = models.ForeignKey(
#         Usuario,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="%(app_label)s_%(class)s_criado_por",
#         help_text="Usuário que criou o registro",
#         verbose_name="Criado por",
#     )
#     modificado_por = models.ForeignKey(
#         Usuario,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="%(app_label)s_%(class)s_modificado_por",
#         help_text="Usuário que atualizou o registro pela última vez",
#         verbose_name="Atualizado por",
#     )
#     criado_em:datetime = models.DateTimeField(
#         auto_now_add=True,
#         help_text="Data e hora de criação do registro",
#         verbose_name="Criado em",
#     )
#     modificado_em:datetime = models.DateTimeField(
#         auto_now=True,
#         help_text="Data e hora da última atualização do registro",
#         verbose_name="Atualizado em",
#     )

#     class Meta:
#         abstract = True

#     def save(self, *args, **kwargs):
#         user = get_current_user()
#         if not self.pk:
#             self.created_by = user
#         self.updated_by = user
#         super().save(*args, **kwargs)
