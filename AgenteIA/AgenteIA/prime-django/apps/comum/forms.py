# forms.py
import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms

from apps.comum.models import DadosBancarios

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class FormDuasColunas(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        self.show_save_and_add_another = kwargs.pop("show_save_and_add_another", True)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Adicionando a classe "form-control" para cada campo
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        # Configurando o layout de duas colunas usando FormHelper
        self.helper = FormHelper(self)
        self.helper.layout = layout_duas_colunas(self)

        # Adicionando os botões
        self.helper.add_input(
            Submit("salvar", "Salvar", css_class="btn btm-sm btn-primary"),
        )
        if self.show_save_and_add_another:
            self.helper.add_input(
                Submit(
                    "save_and_add_another",
                    "Salvar e Adicionar Outro",
                    css_class="btn btm-sm btn-outline-info",
                ),
            )


# class EnderecoForm(forms.ModelForm):
#     municipio = forms.ModelChoiceField(
#         queryset=Municipio.objects.all(),
#         widget=ModelSelect2Widget(
#             model=Municipio,
#             search_fields=["nome__icontains"],
#             dependent_fields={"uf": "uf"},
#         ),
#     )
#     uf = forms.ModelChoiceField(
#         queryset=UnidadeFederativa.objects.all(), required=False
#     )
#     pais = forms.ModelChoiceField(queryset=Pais.objects.all(), required=False)

#     class Meta:
#         model = EnderecoMixin
#         fields = [
#             "logradouro",
#             "numero",
#             "quadra",
#             "lote",
#             "complemento",
#             "bairro",
#             "municipio",
#             "cep",
#         ]

#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         uf = self.cleaned_data.get("uf")
#         pais = self.cleaned_data.get("pais")
#         if uf:
#             instance.municipio.uf = uf
#         if pais:
#             instance.municipio.uf.pais = pais
#         if commit:
#             instance.save()
#         return instance

#     def __init__(self, *args, **kwargs):
#         user = kwargs.pop("user", None)  # Obtém o usuário atual, se disponível
#         super(EnderecoForm, self).__init__(*args, **kwargs)

#         if user and user.cartorio:
#             self.fields["municipio"].initial = user.cartorio.municipio
#             self.fields["uf"].initial = (
#                 user.cartorio.municipio.uf if user.cartorio.municipio else None
#             )
#             self.fields["pais"].initial = (
#                 user.cartorio.municipio.uf.pais
#                 if user.cartorio.municipio and user.cartorio.municipio.uf
#                 else None
#             )


class DadosBancariosForm(FormDuasColunas):
    class Meta:
        model = DadosBancarios
        fields = [
            "titular",
            "nome_banco",
            "numero_agencia",
            "numero_conta",
            "tipo_conta",
        ]
        widgets = {
            "titular": forms.TextInput(attrs={"class": "form-control"}),
            "nome_banco": forms.TextInput(attrs={"class": "form-control"}),
            "numero_agencia": forms.NumberInput(attrs={"class": "form-control"}),
            "numero_conta": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_conta": forms.Select(
                choices=[
                    ("corrente", "Conta Corrente"),
                    ("poupanca", "Conta Poupança"),
                ],
                attrs={"class": "form-control"},
            ),
        }
        labels = {
            "titular": "Titular da Conta",
            "nome_banco": "Nome do Banco",
            "numero_agencia": "Número da Agência",
            "numero_conta": "Número da Conta",
            "tipo_conta": "Tipo de Conta",
        }


def layout_duas_colunas(form):
    rows = []
    fields = list(form.fields.keys())

    while fields:
        field1 = fields.pop(0)
        field2 = fields.pop(0) if fields else None

        if field2:
            row = Row(
                Column(field1, css_class="form-group col-md-6 mb-0"),
                Column(field2, css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            )
        else:
            row = Row(
                Column(field1, css_class="form-group col-md-12 mb-0"),
                css_class="form-row",
            )
        rows.append(row)

    return Layout(*rows)
