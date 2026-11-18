import typing

import django_tables2 as tables
from django.utils.html import format_html

from apps.pessoas.models import Pessoa, Vinculo


class PessoaTable(tables.Table):
    nome = tables.Column(accessor="ultima_versao__nome", verbose_name="Nome")
    email = tables.Column(accessor="ultima_versao__email", verbose_name="Email")
    telefone = tables.Column(
        accessor="ultima_versao__telefone",
        verbose_name="Telefone",
    )
    data_nascimento = tables.Column(
        accessor="ultima_versao__data_nascimento",
        verbose_name="Data de Nascimento",
    )
    sexo = tables.Column(accessor="ultima_versao__sexo", verbose_name="Sexo")
    observacoes = tables.Column(
        accessor="ultima_versao__observacoes",
        verbose_name="Observações",
    )

    class Meta:
        model = Pessoa
        attrs: typing.ClassVar[dict] = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "nome",
            "documento",
            "telefone",
            "data_nascimento",
            "sexo",
            "observacoes",
            "quantidade_versoes",
        )


class VersaoPessoaTable(tables.Table):
    nome = tables.Column(accessor="ultima_versao__nome", verbose_name="Nome")
    email = tables.Column(accessor="ultima_versao__email", verbose_name="Email")
    telefone = tables.Column(
        accessor="ultima_versao__telefone",
        verbose_name="Telefone",
    )
    data_nascimento = tables.Column(
        accessor="ultima_versao__data_nascimento",
        verbose_name="Data de Nascimento",
    )
    sexo = tables.Column(accessor="ultima_versao__sexo", verbose_name="Sexo")
    observacoes = tables.Column(
        accessor="ultima_versao__observacoes",
        verbose_name="Observações",
    )

    class Meta:
        model = Pessoa
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "nome",
            "documento",
            "telefone",
            "data_nascimento",
            "sexo",
            "observacoes",
            "quantidade_versoes",
        )


class VinculoTable(tables.Table):
    nome = tables.Column(accessor="versao_pessoa__nome", verbose_name="Nome")
    documento = tables.Column(
        accessor="versao_pessoa__documento",
        verbose_name="Documento",
    )
    tipo_vinculo = tables.Column(
        accessor="tipo_vinculo",
        verbose_name="Tipo de Vínculo",
    )
    conjuge = tables.Column(
        accessor="versao_pessoa__get_conjuge",
        verbose_name="Conjuge",
    )
    nome_objeto = tables.Column(empty_values=(), verbose_name="Nome do Objeto")

    def render_nome(self, value, record):
        if hasattr(record.versao_pessoa, "get_absolute_url"):
            url = record.versao_pessoa.get_absolute_url()
            return format_html('<a href="{}">{}</a>', url, value)
        return value

    def render_nome_objeto(self, record):
        if record.content_type:
            objeto_vinculado = record.content_type.get_object_for_this_type(
                pk=record.object_id,
            )
            if hasattr(objeto_vinculado, "get_absolute_url"):
                url = objeto_vinculado.get_absolute_url()
                return format_html(
                    '<a href="{}">{}</a>',
                    url,
                    str(objeto_vinculado.descricao),
                )

            return str(objeto_vinculado)
        return "Não definido"

    class Meta:
        model = Vinculo
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "tipo_vinculo",
            "nome",
            "documento",
            "conjuge",
            "nome_objeto",
        )
        exclude = ("content_type", "object_id")
