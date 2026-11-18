from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Submit
from django import forms
from django.contrib.contenttypes.models import ContentType

from apps.comum.forms import layout_duas_colunas
from apps.home.tipos import TipoSexo
from apps.pessoas.models import Pessoa, TipoVinculo, VersaoPessoa, Vinculo


class VinculoForm(forms.ModelForm):
    tipo_vinculo = forms.ModelChoiceField(
        queryset=TipoVinculo.objects.all(),
        label="Tipo de Parte",
        required=True,
    )
    object_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    content_type = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(
            Submit("save", "Próximo", css_class="btn btn-sm btn-primary"),
        )

    class Meta:
        model = Vinculo
        fields = ("tipo_vinculo",)


class PessoaForm(forms.ModelForm):
    documento = forms.CharField(label="CPF ou CNPJ", required=True)

    def clean_documento(self) -> str:
        # Add type annotation for self parameter
        return self.cleaned_data.get("documento")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(
            Submit("save", "Próximo", css_class="btn btn-sm btn-primary"),
        )

    class Meta:
        model = Pessoa
        fields = ("documento",)


class VersaoPessoaForm(forms.ModelForm):
    nome = forms.CharField(label="Nome", required=True)
    # data_nascimento = forms.DateField(
    #     widget=forms.DateInput(attrs={"type": "date"}),
    #     label="Dt Nascimento",
    #     required=False,
    # )
    email = forms.EmailField(label="E-mail", required=False)
    telefone = forms.CharField(label="Telefone", required=False)
    logradouro = forms.CharField(label="Logradouro", required=False)
    bairro = forms.CharField(label="Bairro", required=False)
    cidade = forms.CharField(label="Cidade", required=False)
    estado = forms.CharField(label="Estado", required=False)
    cep = forms.CharField(label="CEP", required=False)
    estado_civil = forms.CharField(label="Estado Civil", required=False)
    sexo = forms.ChoiceField(
        choices=TipoSexo.CHOICES,
        label="Sexo",
        required=False,
    )
    conjuge = forms.ModelChoiceField(
        queryset=VersaoPessoa.objects.filter(),
        label="Cônjuge",
        required=False,
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Observações",
        required=False,
    )

    class Meta:
        model = VersaoPessoa
        fields = (
            "nome",
            "documento_apresentado",
            "sexo",
            "estado_civil",
            "conjuge",
            # "pessoa.documento",
            # "data_nascimento",
            "email",
            "telefone",
            "logradouro",
            "bairro",
            "cidade",
            "estado",
            "cep",
            "observacoes",
        )

    def __init__(self, *args, **kwargs) -> None:
        # Extrai os argumentos pessoalizados e remove-os de kwargs antes de chamar o super
        self.object_id = kwargs.pop("object_id", None)
        self.content_type_id = kwargs.pop("content_type_id", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = layout_duas_colunas(self)
        self.helper.layout.append(
            FormActions(
                HTML(
                    """
                {% if wizard.steps.prev %}
                <button class="btn btn-sm btn-primary"
                        name="wizard_goto_step"
                        type="submit"
                        value="{{ wizard.steps.first }}">Início</button>
                <button class="btn btn-sm btn-primary"
                        name="wizard_goto_step"
                        type="submit"
                        value="{{ wizard.steps.prev }}">Anterior</button>
                {% endif %}
                """,
                ),
                Submit("save", "Próximo", css_class="btn btn-sm btn-primary"),
            ),
        )

        if self.object_id and self.content_type_id:
            try:
                content_type = ContentType.objects.get_for_id(self.content_type_id)
                pessoa_ids = Vinculo.objects.filter(
                    content_type=content_type,
                    object_id=self.object_id,
                ).values_list("versao_pessoa_id", flat=True)

                # Use os IDs das pessoas para filtrar o queryset de 'conjuge'
                self.fields["conjuge"].queryset = VersaoPessoa.objects.filter(
                    id__in=pessoa_ids,
                )
            except ContentType.DoesNotExist:
                # Se o ContentType não existir, defina o queryset como none
                self.fields["conjuge"].queryset = VersaoPessoa.objects.none()
        else:
            self.fields["conjuge"].queryset = VersaoPessoa.objects.none()
