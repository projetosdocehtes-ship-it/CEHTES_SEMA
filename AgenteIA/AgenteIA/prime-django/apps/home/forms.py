import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    Button,
    ButtonHolder,
    Column,
    Div,
    Field,
    Layout,
    Row,
    Submit,
)
from django import forms
from django.db.models import Q

# from datetime import timezone
from django.utils import timezone
from django_ckeditor_5.widgets import CKEditor5Widget
from django_select2.forms import Select2Widget

from apps.cartorios.models import Usuario as User
from apps.comum.models import (
    Municipio,
    TipoDocumento,
    TipoRegistroImobiliario,
)
from apps.home.models.models_certidoes import (
    Apresentante,
    Bateria,
    Certidao,
    Finalidade,
    Hidrogenio,
    Inversor,
    PainelSolar,
    PedidoCertidao,
    PedidoCertidaoAndamento,
    PedidoCertidaoAnexo,
    PedidoCertidaoImovel,
    PedidoCertidaoPessoa,
    PerguntaCustom,
    Projeto,
    TipoApresentante,
    TipoCertidao,
)
from apps.home.models.models_home import (
    Anexo,
    CertificadoDigital,
    ChecklistBalcao,
    Colaborador,
    Documento,
    EstadoCivil,
    Event,
    EventMember,
    Funcionario,
    Livro01Andamento,
    Livro02,
    Livro05,
    MotivoAssinaturaDigital,
    PedidoItemImovel,
    PedidoParteAto,
    TipoRegimeCasamento,
)
from apps.minutas_atos.models import MinutaModeloAto

# from django import forms
from .helpers import DEFAULT_HSP, DEFAULT_PANEL_WATTS, DEFAULT_SYSTEM_EFF

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class IconSubmit(Submit):
    def __init__(self, *args, **kwargs) -> None:
        self.icon = kwargs.pop("icon", None)
        super().__init__(*args, **kwargs)


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
            Submit("salvar", "Salvar", css_class="btn btn-sm btn-primary"),
        )
        if self.show_save_and_add_another:
            self.helper.add_input(
                Submit(
                    "save_and_add_another",
                    "Salvar e Adicionar Outro",
                    css_class="btn btm-sm btn-outline-info",
                ),
            )


# class TodoForm(BootstrapHelperForm, forms.ModelForm):
#     class Meta:
#         model = Funcionario
#         fields = ("nome",)

#     def __init__(self, *args, **kwargs):
#         print(kwargs)

#         request = kwargs.pop("request")
#         super().__init__(*args, **kwargs)


class Livro05Form(forms.ModelForm):
    class Meta:
        model = Livro05
        fields = ("documento", "nacionalidade")

    widgets = {
        "documento": forms.TextInput(attrs={"class": "form-control"}),
        "nacionalidade": forms.TextInput(attrs={"class": "form-control"}),
    }


class Livro02Form(forms.ModelForm):
    class Meta:
        model = Livro02
        fields = ("id", "numero", "texto")


class MinutaModeloAtoTextoForm(forms.ModelForm):
    class Meta:
        model = MinutaModeloAto
        fields = ("observacao",)


class EstadoCivilForm(forms.ModelForm):
    class Meta:
        model = EstadoCivil
        fields = ("id", "descricao_estado_civil", "tipo")

    widgets = {
        "id": forms.TextInput(attrs={"class": "form-control"}),
        "descricao_estado_civil": forms.TextInput(attrs={"class": "form-control"}),
        "tipo": forms.TextInput(attrs={"class": "form-control"}),
    }


class AddMemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ["user"]


class InsereFuncionarioForm(forms.ModelForm):
    nome = forms.IntegerField(label="nome", required=False)
    sobrenome = forms.CharField(label="sobrenome", required=False)
    cpf = forms.CharField(label="cpf", required=False)
    tempo_de_servico = forms.CharField(label="tempo_de_servico", required=False)
    remuneracao = forms.CharField(label="remuneracao", required=False)

    class Meta:
        # Modelo base
        model = Funcionario

        # Campos que estarão no form
        fields = ["nome", "sobrenome", "cpf", "remuneracao", "tempo_de_servico"]

    # Campos que não estarão no form
    # exclude = ['tempo_de_servico']


class VinculaPessoaCheckListForm(forms.ModelForm):
    # VINCULAR PESSOA
    pedido_item_id = forms.CharField(label="pedido_item", required=False)
    pessoa = forms.CharField(label="pessoa", required=False)

    class Meta:
        # Modelo base
        model = PedidoParteAto

        # Campos que estarão no form
        fields = ["pedido_item_id", "pessoa"]


class InsereEnderecoCheckListForm(forms.ModelForm):
    # LOTE
    lote = forms.CharField(label="lote", required=False)
    quadra = forms.CharField(label="quadra", required=False)
    setor = forms.CharField(label="setor", required=False)
    area = forms.CharField(label="area", required=False)
    area_construida_residencial = forms.CharField(
        label="area_construida_residencial",
        required=False,
    )
    residencial = forms.CharField(label="residencial", required=False)
    comercial = forms.CharField(label="comercial", required=False)
    nome_rua = forms.CharField(label="nome_rua", required=False)
    numero_casa = forms.CharField(label="numero_casa", required=False)
    municipio = forms.CharField(label="municipio", required=False)

    # RURAL
    nome_fazenda = forms.CharField(label="nome_fazenda", required=False)
    caracteristica_fazenda = forms.CharField(
        label="caracteristica_fazenda",
        required=False,
    )
    reserva_legal = forms.CharField(label="reserva_legal", required=False)
    georefenciada = forms.CharField(label="georefenciada", required=False)
    numero_nirf = forms.CharField(label="numero_nirf", required=False)
    numero_ccirr = forms.CharField(label="numero_ccirr", required=False)
    numero_car = forms.CharField(label="numero_car", required=False)
    numero_incra = forms.CharField(label="numero_incra", required=False)
    area_fazenda = forms.CharField(label="area_fazenda", required=False)

    m_frente_metros = forms.CharField(label="m_frente_metros", required=False)
    p_frente_metros = forms.CharField(label="p_frente_metros", required=False)
    m_direito_metros = forms.CharField(label="m_direito_metros", required=False)
    p_direito_metros = forms.CharField(label="p_direito_metros", required=False)
    p_esquerdo_metros = forms.CharField(label="p_esquerdo_metros", required=False)
    m_esquerdo_metros = forms.CharField(label="m_esquerdo_metros", required=False)
    p_fundo_metros = forms.CharField(label="p_fundo_metros", required=False)
    m_fundo_metros = forms.CharField(label="m_fundo_metros", required=False)

    class Meta:
        # Modelo base
        model = PedidoItemImovel

        # Campos que estarão no form
        fields = [
            "lote",
            "quadra",
            "setor",
            "area",
            "residencial",
            "comercial",
            "nome_rua",
            "numero_casa",
            "municipio",
            "nome_fazenda",
            "caracteristica_fazenda",
            "reserva_legal",
            "georefenciada",
            "numero_nirf",
            "numero_ccirr",
            "numero_car",
            "numero_incra",
            "area_fazenda",
            "area_construida_residencial",
            "m_frente_metros",
            "p_frente_metros",
            "p_frente_metros",
            "m_direito_metros",
            "p_direito_metros",
            "p_esquerdo_metros",
            "m_esquerdo_metros",
            "p_fundo_metros",
            "m_fundo_metros",
        ]


class InserePessoaForm(forms.ModelForm):
    nome = forms.CharField(label="nome", required=False)
    cpf = forms.CharField(label="cpf", required=False)
    documento = forms.CharField(label="cpf", required=False)

    class Meta:
        # Modelo base
        model = Livro05

        # Campos que estarão no form
        fields = ["nome", "cpf", "documento"]


# class TodoForm(BootstrapHelperForm, forms.ModelForm):
#     class Meta:
#         model = Funcionario
#         fields = ("nome",)

#     def __init__(self, *args, **kwargs):
#         print(kwargs)

#         # request = kwargs.pop("request")
#         super().__init__(*args, **kwargs)


class EstilizadoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, CKEditor5Widget):
                field.widget.attrs.update({"class": "form-control"})


class PessoaUpdateForm(EstilizadoForm):
    data_nascimento = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        label="Dt Nascimento",
        required=False,
    )

    class Meta:
        model = Livro05
        fields = (
            "cpf",
            "nome",
            "documento",
            "sexo",
            "estado_civil",
            "tipo_regime_casamento",
            "nacionalidade",
            "profissao",
            "endereco",
            "data_nascimento",
            "email",
            "naturalidade",
            "telefone",
            # "conjuge",
        )
        labels = {
            "cpf": "CPF/CNPJ",
            "profissao": "Profissão",
            "estado_civil": "Estado Civil",
            # Adicione mais pessoalizações conforme necessário
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Aqui você modifica o queryset para o campo estado_civil
        self.fields["estado_civil"].queryset = EstadoCivil.objects.filter(
            exibir="S",
        ).order_by(
            "descricao_estado_civil",
        )
        self.fields[
            "tipo_regime_casamento"
        ].queryset = TipoRegimeCasamento.objects.filter(exibir="S").order_by(
            "descricao_regime",
        )
        if self.instance and self.instance.data_nascimento:
            self.fields["data_nascimento"].initial = self.instance.data_nascimento
        # self.fields["conjuge"].queryset = EstadoCivil.objects.filter(exibir="S").order_by("descricao_estado_civil")

        # Campos opcionais
        optional_fields = [
            "email",
            "profissao",
            # "nome_pai",
            # "nome_mae",
            # "email",
            # "cidade",
            # "uf",
            "telefone",
            # "conjuge",
        ]
        for field_name in optional_fields:
            self.fields[field_name].required = False

        required_fields = [
            "documento",
            "nacionalidade",
            "endereco",
            "data_nascimento",
            "naturalidade",
            "sexo",
        ]
        for field_name in required_fields:
            self.fields[field_name].required = True

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div(
                    Field("nome", readonly=True),
                    Field("documento"),
                    Field("sexo"),
                    Field("estado_civil"),
                    Field("naturalidade"),
                    Field("telefone"),
                    css_class="col-md-6",
                ),
                Div(
                    Field("cpf", readonly=True),
                    Field("data_nascimento"),
                    Field("nacionalidade"),
                    Field("tipo_regime_casamento"),
                    Field("profissao"),
                    Field("email"),
                    css_class="col-md-6",
                ),
                css_class="row",
            ),
            "endereco",
        )

        self.fields["documento"].widget.attrs["autofocus"] = "autofocus"
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Salvar e Voltar"))
        self.helper.add_input(
            Button(
                "cancel",
                "Cancelar",
                css_class="btn-secondary",
                onclick="window.history.back()",
            ),
        )

        self.fields["documento"].widget.attrs["autofocus"] = "autofocus"
        self.helper.form_method = "post"

        # self.helper.add_input(Submit("submit", "Salvar e Voltar ao Checklist"))
        # self.helper.add_input(
        #     Button(
        #         "cancel",
        #         "Cancelar",
        #         css_class="btn-secondary",
        #         onclick="window.history.back()",
        #     )
        # )


# class EstadoCivilForm(forms.ModelForm):
#     class Meta:
#         model = EstadoCivil
#         fields = ("id", "descricao_estado_civil", "tipo")


#     widgets = {
#         "id": forms.TextInput(attrs={"class": "form-control"}),
#         "descricao_estado_civil": forms.TextInput(attrs={"class": "form-control"}),
#         "tipo": forms.TextInput(attrs={"class": "form-control"}),
#     }


class BaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Adicionando a classe "form-control" para cada campo
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        # Configurando o layout de duas colunas usando FormHelper
        self.helper = FormHelper(self)
        self.helper.add_input(Submit("salvar", "Salvar"))


class EventForm(BaseForm):
    auth_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        label="Colaborador",
        widget=forms.Select(attrs={"placeholder": "Selecione o colaborador"}),
    )

    STATUS_ORIGEM_CHOICES = (
        ("P", "Protocolo"),
        ("E", "Exame Cálculo"),
        ("C", "Pedido Certidão"),
        ("G", "Geral"),
    )

    origem = forms.TypedChoiceField(
        choices=STATUS_ORIGEM_CHOICES,
        coerce=lambda x: x,  # Não faz nada, mas garante que os valores sejam mantidos como estão
        label="Origem",
        widget=forms.Select(attrs={"placeholder": "Selecione a origem"}),
    )

    numero = forms.IntegerField(label="Número")

    class Meta:
        model = Event
        fields = [
            "title",
            "numero",
            "origem",
            "auth_user",
            "start_time",
            "end_time",
            "description",
            "url",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Insira o título do evento"},
            ),
            "description": forms.Textarea(
                attrs={"placeholder": "Digite a descrição do evento"},
            ),
            "numero": forms.TextInput(
                attrs={
                    "placeholder": "Insira o número do protocolo ou pedido certidão",
                },
            ),
            "origem": forms.TextInput(
                attrs={
                    "placeholder": "Insira a origem (Geral, Pedido de Certidão ou Protocolo)",
                },
            ),
            "start_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "url": forms.TextInput(attrs={"placeholder": "Insira o caminho da Ação"}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["start_time"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["end_time"].input_formats = ("%Y-%m-%dT%H:%M",)
        self._update_field_labels()

    def _update_field_labels(self) -> None:
        self.fields["title"].label = "Título do Evento"
        self.fields["description"].label = "Descrição"
        self.fields["start_time"].label = "Data e Hora de Início"
        self.fields["end_time"].label = "Data e Hora de Fim"
        self.fields["url"].label = "Caminho da Ação"
        self.fields["numero"].label = "Número"
        self.fields["origem"].label = "Origem"


# class AddMemberForm(forms.ModelForm):
#     class Meta:
#         model = EventMember
#         fields = ["user"]


# class InsereFuncionarioForm(forms.ModelForm):
#     nome = forms.CharField(label="nome", required=False)
#     sobrenome = forms.CharField(label="sobrenome", required=False)
#     cpf = forms.CharField(label="cpf", required=False)
#     tempo_de_servico = forms.CharField(label="tempo_de_servico", required=False)
#     remuneracao = forms.CharField(label="remuneracao", required=False)

#     class Meta:
#         # Modelo base
#         model = Funcionario

#         # Campos que estarão no form
#         fields = ["nome", "sobrenome", "cpf", "remuneracao", "tempo_de_servico"]

#     # Campos que não estarão no form
#     # exclude = ['tempo_de_servico']


# class VinculaPessoaCheckListForm(forms.ModelForm):
#     # VINCULAR PESSOA
#     pedido_item_id = forms.CharField(label="pedido_item", required=False)
#     pessoa = forms.CharField(label="pessoa", required=False)

#     class Meta:
#         # Modelo base
#         model = PedidoParteAto

#         # Campos que estarão no form
#         fields = ["pedido_item_id", "pessoa"]


# class InsereEnderecoCheckListForm(forms.ModelForm):
#     # LOTE
#     lote = forms.CharField(label="lote", required=False)
#     quadra = forms.CharField(label="quadra", required=False)
#     setor = forms.CharField(label="setor", required=False)
#     area = forms.CharField(label="area", required=False)
#     residencial = forms.CharField(label="residencial", required=False)
#     comercial = forms.CharField(label="comercial", required=False)
#     nome_rua = forms.CharField(label="nome_rua", required=False)
#     numero_casa = forms.CharField(label="numero_casa", required=False)
#     municipio = forms.CharField(label="municipio", required=False)
#     area_construida_residencial = forms.CharField(
#         label="area_construida_residencial", required=False
#     )

#     # RURAL
#     nome_fazenda = forms.CharField(label="nome_fazenda", required=False)
#     caracteristica_fazenda = forms.CharField(
#         label="caracteristica_fazenda", required=False
#     )
#     reserva_legal = forms.CharField(label="reserva_legal", required=False)
#     georefenciada = forms.CharField(label="georefenciada", required=False)
#     numero_nirf = forms.CharField(label="numero_nirf", required=False)
#     numero_ccirr = forms.CharField(label="numero_ccirr", required=False)
#     numero_car = forms.CharField(label="numero_car", required=False)
#     numero_incra = forms.CharField(label="numero_incra", required=False)
#     area_fazenda = forms.CharField(label="area_fazenda", required=False)

#     m_frente_metros = forms.CharField(label="m_frente_metros", required=False)
#     p_frente_metros = forms.CharField(label="p_frente_metros", required=False)
#     m_direito_metros = forms.CharField(label="m_direito_metros", required=False)
#     p_direito_metros = forms.CharField(label="p_direito_metros", required=False)
#     p_esquerdo_metros = forms.CharField(label="p_esquerdo_metros", required=False)
#     m_esquerdo_metros = forms.CharField(label="m_esquerdo_metros", required=False)
#     p_fundo_metros = forms.CharField(label="p_fundo_metros", required=False)
#     m_fundo_metros = forms.CharField(label="m_fundo_metros", required=False)

#     class Meta:
#         # Modelo base
#         model = PedidoItemImovel

#         # Campos que estarão no form
#         fields = [
#             "lote",
#             "quadra",
#             "setor",
#             "area",
#             "residencial",
#             "comercial",
#             "nome_rua",
#             "numero_casa",
#             "municipio",
#             "nome_fazenda",
#             "caracteristica_fazenda",
#             "reserva_legal",
#             "georefenciada",
#             "numero_nirf",
#             "numero_ccirr",
#             "numero_car",
#             "numero_incra",
#             "area_fazenda",
#             "area_construida_residencial",
#             "m_frente_metros",
#             "p_frente_metros",
#             "m_direito_metros",
#             "p_direito_metros",
#             "p_esquerdo_metros",
#             "m_esquerdo_metros",
#             "p_fundo_metros",
#             "m_fundo_metros",
#         ]


class BuscaProtocoloForm(forms.Form):
    OPCOES = (
        ("Exame", "Exame"),
        ("Protocolo", "Protocolo"),
    )

    select = forms.ChoiceField(
        choices=OPCOES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    numero = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "style": "padding-right: 60px",
                "aria-label": "Número do protocolo",
                "placeholder": "Placeholder Aqui",
            },
        ),
    )


class QuestionForm(forms.ModelForm):
    class Meta:
        model = ChecklistBalcao
        fields = ["text"]
        widgets = {
            "text": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["options"] = forms.ModelMultipleChoiceField(
                queryset=self.instance.answeroption_set.all(),
                widget=forms.CheckboxSelectMultiple,
                required=False,
            )


class AnexoForm(forms.ModelForm):
    class Meta:
        model = Anexo
        fields = ["nome", "descricao"]
        widgets = {
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "nome": forms.FileInput(attrs={"class": "form-control-file"}),
        }
        labels = {
            "descricao": "Descrição",
            "nome": "Nome",
        }


class AnexoUpdateForm(forms.ModelForm):
    class Meta:
        model = Anexo
        fields = ["descricao", "nome"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "nome": "Nome",
            "descricao": "Descrição",
        }


class AndamentosForm(forms.ModelForm):
    class Meta:
        model = Livro01Andamento
        fields = []

        widgets = {
            "protocolo": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_andamento": forms.TextInput(attrs={"class": "form-control"}),
            "colaborador": forms.TextInput(attrs={"class": "form-control"}),
            "data": forms.DateInput(attrs={"class": "form-control"}),
            "colaborador_destino": forms.TextInput(attrs={"class": "form-control"}),
            # "data_reentrada": forms.DateInput(attrs={"class": "form-control"}),
        }
        labels = {
            "protocolo": "Protocolo",
            "tipo_andamento": "Evento",
            "colaborador": "Colaborador",
            "data": "Data",
            "colaborador_destino": "Destinatario",
            # "data_reentrada": "Data de Reentrada",
        }


class AssinarDocumentoForm(forms.Form):
    documento = forms.ModelChoiceField(
        queryset=Documento.objects.all(),
        label="Selecione o Documento",
    )
    certificado_digital = forms.ModelChoiceField(
        queryset=CertificadoDigital.objects.all(),
        label="Selecione o Certificado Digital",
    )
    senha = forms.CharField(
        widget=forms.PasswordInput(),
        label="Senha do Certificado Digital",
    )

    def __init__(self, *args, **kwargs) -> None:
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields[
                "certificado_digital"
            ].queryset = CertificadoDigital.objects.filter(
                usuario=user,
            )


class VerificarAssinaturaForm(forms.Form):
    documento = forms.ModelChoiceField(
        queryset=Documento.objects.all().order_by("-criado_em"),
        label="Selecione o Documento para Verificação",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Aqui você pode ajustar o queryset se necessário, dependendo da lógica de negócio.


class AndamentoCreateForm(forms.ModelForm):
    modelos_de_texto = forms.ModelChoiceField(queryset=None, required=False)

    class Meta:
        model = Livro01Andamento
        fields = [
            "data",
            "tipo_andamento",
            "colaborador_destino",
            "texto",
            "modelos_de_texto",
        ]
        widgets = {
            "data": forms.DateTimeInput(attrs={"readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        protocolo = kwargs.pop(
            "protocolo",
            None,
        )  # Remova o protocolo se não for usado nos campos
        logger.info(f"Protocolo: {protocolo}")
        super().__init__(*args, **kwargs)
        self.fields[
            "modelos_de_texto"
        ].queryset = Livro01Andamento.get_modelos_de_texto()
        self.fields["colaborador_destino"].initial = user.pk if user else None
        self.fields[
            "colaborador_destino"
        ].queryset = Colaborador.objects.filtrar_por_ativos()
        self.initial["data"] = timezone.now()


class AndamentoUpdateForm(forms.ModelForm):
    modelos_de_texto = forms.ModelChoiceField(
        queryset=Livro01Andamento.objects.none(),
        required=False,
        widget=Select2Widget,
    )

    class Meta:
        model = Livro01Andamento
        fields = [
            "modelos_de_texto",
            "texto",
        ]
        widgets = {
            "modelos_de_texto": Select2Widget,  # Substitua pelo campo real
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "modelos_de_texto"
        ].queryset = Livro01Andamento.get_modelos_de_texto()


class EscolherCertificadoForm(forms.Form):
    certificado = forms.ModelChoiceField(
        queryset=CertificadoDigital.objects.none(),
        required=True,
        help_text="Selecione o certificado digital para assinar o documento",
    )
    motivo = forms.ModelChoiceField(
        queryset=MotivoAssinaturaDigital.objects.all(),
        required=True,
        help_text="Selecione o motivo da assinatura digital",
    )

    def __init__(self, usuario, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["certificado"].queryset = CertificadoDigital.objects.filter(
            usuarios__id=usuario.id,
        )
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.layout = Layout(
            "certificado",
            "motivo",
            IconSubmit(
                "submit",
                "Assinar Documento",
                css_class="btn-primary",
                icon="fas fa-file-signature",
            ),
        )


class CertificadoDigitalForm(forms.ModelForm):
    senha = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
    )  # Campo adicional para a senha

    class Meta:
        model = CertificadoDigital
        fields = [
            "certificado",
            "imagem_assinatura",
            "texto_assinatura",
            "senha",
            "usuarios",
        ]
        widgets = {
            "usuarios": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.layout = Layout(
            "certificado",
            "imagem_assinatura",
            "texto_assinatura",
            "senha",
            "usuarios",
            IconSubmit("submit", "Salvar", css_class="btn-primary", icon="fas fa-save"),
        )


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


class AuditavelForm(forms.ModelForm):
    def __init__(self: "AuditavelForm", *args, **kwargs) -> None:
        self.request = kwargs.get("request", None)
        super().__init__(*args, **kwargs)
        self.is_new_instance = not bool(self.instance.pk)
        if (
            self.instance
            and hasattr(self.instance, "criado_por")
            and self.instance.criado_por
        ):
            self.initial["criado_por"] = self.instance.criado_por.username
        if (
            self.instance
            and hasattr(self.instance, "modificado_por")
            and self.instance.modificado_por
        ):
            self.initial["modificado_por"] = self.instance.modificado_por.username
            self.initial["modificado_em"] = self.instance.modificado_em

    def save(self, commit=True, *args, **kwargs):
        instance = super().save(commit=False)
        request = kwargs.get("request", self.request)
        if not instance.criado_por:  # Verifica se é uma nova instância
            instance.criado_por = request.user if request else None
        instance.modificado_por = request.user if request else None
        if commit:
            instance.save()
        return instance


class PedidoCertidaoPedidoForm(FormDuasColunas):
    class Meta:
        model = PedidoCertidao
        fields = [
            "finalidade",
            "observacao",
        ]  # e outros campos que você desejar
        observacao = forms.CharField(widget=forms.Textarea)


class CriarPedidoCertidaoForm(forms.ModelForm):
    nome_apresentante = forms.CharField(
        max_length=100,
        required=True,
        label="Nome do Apresentante",
    )

    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nome"),
        required=False,
        initial=TipoDocumento.get_default_tipo_documento_id,
        label="Tipo de Documento",
    )
    documento = forms.CharField(max_length=100, required=False, label="Documento")
    telefone = forms.CharField(max_length=100, required=False, label="Telefone")
    email = forms.EmailField(required=False, label="E-mail")
    observacoes = forms.CharField(max_length=100, required=False, label="Observações")

    finalidade = forms.ModelChoiceField(
        queryset=Finalidade.objects.all().order_by("nome"),
        required=False,
        initial=Finalidade.get_default_tipo_finalidade_id,
        label="Finalidade",
    )

    tipo_apresentante = forms.ModelChoiceField(
        queryset=TipoApresentante.objects.all().order_by("nome"),
        required=False,
        initial=TipoApresentante.get_default_tipo_apresentante_id,
        label="Tipo",
    )

    # interessado
    interessado_nome = forms.CharField(
        max_length=100,
        required=False,
        label="Nome do Interessado",
    )
    interessado_tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nome"),
        required=False,
        initial=TipoDocumento.get_default_tipo_documento_id,
        label="Tipo de Documento",
    )
    interessado_documento = forms.CharField(
        max_length=100,
        required=False,
        label="Documento",
    )

    interessado_tipo_apresentante = forms.ModelChoiceField(
        queryset=TipoApresentante.objects.all().order_by("nome"),
        required=False,
        initial=TipoApresentante.get_tipo_apresentante_interessado_id,
        label="Tipo",
    )

    class Meta:
        model = PedidoCertidao
        fields = [
            "finalidade",
            "nome_apresentante",
            "tipo_documento",
            "documento",
            "telefone",
            "email",
            "tipo_apresentante",
            "observacoes",
            "interessado_nome",
            "interessado_tipo_documento",
            "interessado_documento",
            "interessado_tipo_apresentante",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                HTML("<p>Informe os dados do apresentante e do interessado.</p>"),
            ),
            Row(
                Column("finalidade", css_class=" col-md-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                HTML("<hr>"),
            ),
            Row(
                Column("tipo_apresentante", css_class=" col-md-3 mb-0"),
                Column("nome_apresentante", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("tipo_documento", css_class=" col-md-3 mb-0"),
                Column("documento", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("telefone", css_class="col-md-6 mb-0"),
                Column("email", css_class="col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("observacoes", css_class=" col-md-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                HTML("<hr>"),
            ),
            # interessado
            Row(
                Column("interessado_tipo_apresentante", css_class=" col-md-3 mb-0"),
                Column("interessado_nome", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("interessado_tipo_documento", css_class=" col-md-3 mb-0"),
                Column("interessado_documento", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
        )
        self.helper.add_input(
            Submit("salvar", "Criar Pedido de Certidão", css_class="btn-primary"),
        )


class ApresentanteForm(FormDuasColunas):
    # busca_cpf = forms.ModelChoiceField(
    #     queryset=models.Livro05.objects.all(),
    #     widget=ModelSelect2Widget(
    #         model=models.Livro05,
    #         search_fields=["cpf__icontains"],
    #         attrs={
    #             "data-minimum-input-length": 11,  # O mínimo de caracteres para iniciar a busca
    #             "class": "form-control",
    #         },
    #     ),
    #     label="Buscar CPF no L2",
    #     required=False,  # Definindo o campo como não obrigatório
    # )

    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nome"),
        required=False,
    )
    documento = forms.CharField(max_length=100, required=False)

    tipo_apresentante = forms.ModelChoiceField(
        queryset=TipoApresentante.objects.all().order_by("nome"),
        required=False,
        initial=TipoApresentante.get_default_tipo_apresentante_id,
    )

    class Meta:
        model = Apresentante
        fields = (
            # "busca_cpf",
            "nome",
            "tipo_documento",
            "documento",
            "telefone",
            "email",
            "tipo_apresentante",
            "observacao",
        )

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["email"].required = False
    #     if self.instance:
    #         if (
    #             self.instance.cpf
    #         ):  # Verifica se a instância de Apresentante tem um documento setado
    #             busca_cpf = self.instance.cpf
    #             self.fields["nome"].initial = busca_cpf.nome

    # TODO: Na criação do pedido, pedir somente o nome do apresentante, e os demais dados podem ficar em tela dedicada ao formulario do apresentante.


class ImovelForm(FormDuasColunas):
    # busca_numero_registro = forms.ModelChoiceField(
    #     queryset=models.Livro02.objects.all(),
    #     widget=ModelSelect2Widget(
    #         model=models.Livro02,
    #         search_fields=["numero__icontains"],
    #         attrs={
    #             "data-minimum-input-length": 2,  # O mínimo de caracteres para iniciar a busca
    #             "class": "form-control",
    #         },
    #     ),
    #     label="Buscar Registro",
    #     required=False,  # Definindo o campo como não obrigatório
    # )
    tipo_registro = forms.ModelChoiceField(
        queryset=TipoRegistroImobiliario.objects.all().order_by("nome"),
        label="Tipo de Registro",
        required=False,
        initial=TipoRegistroImobiliario.get_default_tipo_registro_imobiliario,
    )
    # tipo_logradouro = forms.ModelChoiceField(
    #     queryset=TipoLogradouro.objects.all().order_by("nome"),
    #     label="Tipo de Logradouro",
    #     required=False,
    #     initial=TipoLogradouro.get_default_tipo_logradouro,
    # )
    # municipio = forms.ModelChoiceField(
    #     queryset=Municipio.objects.all(),
    #     label="Município",
    #     widget=ModelSelect2Widget(
    #         model=Municipio,
    #         search_fields=["nome__icontains"],
    #         dependent_fields={"uf": "uf"},
    #     ),
    # )
    # uf = forms.ModelChoiceField(
    #     label="Estado",
    #     queryset=UnidadeFederativa.objects.all(),
    #     required=False,
    # )
    # pais = forms.ModelChoiceField(
    #     queryset=Pais.objects.all(), required=False, initial=Pais.get_default_pais
    # )

    # Campos do EnderecoMixin

    logradouro = forms.CharField(
        label="Logradouro",
        max_length=255,
        required=False,
        help_text="Nome da rua, avenida, praça, etc.",
    )
    # numero = forms.CharField(label="Número", max_length=11, required=False)
    quadra = forms.CharField(label="Quadra", max_length=10, required=False)
    lote = forms.CharField(label="Lote", max_length=10, required=False)
    complemento = forms.CharField(
        label="Complemento/Características",
        max_length=50,
        required=False,
    )
    # bairro = forms.CharField(label="Bairro", max_length=100, required=False)
    # municipio = forms.ModelChoiceField(
    #     queryset=Municipio.objects.all(),
    #     label="Município",
    #     required=False,
    # )
    # cep = forms.CharField(label="CEP", max_length=10, required=False)
    numero_registro = forms.IntegerField(min_value=0, required=False)

    class Meta:
        model = PedidoCertidaoImovel
        fields = [
            # "busca_numero_registro",
            "tipo_registro",
            "numero_registro",
            "numero_registro_cnm",
            "livro",
            "cartorio",
            # "tipo_imovel",
            # "tipo_logradouro",
            # "numero",
            "quadra",
            "lote",
            "complemento",
            "logradouro",
            # "bairro",
            # "uf",
            # "municipio",
            # "cep",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # self.helper = FormHelper(self)

        # try:
        #     Usuario.objects.get(pk=self.request.user.pk)
        #     # tipo_imovel = TipoRegistro.get_default_tipo_imovel
        #     # self.fields["tipo_imovel"].initial = tipo_imovel
        #     # if usuario.cartorio:
        #     #     uf_inicial = usuario.cartorio.uf or None
        #     # else:
        #     #     uf_inicial = None
        #     # self.fields["uf"].initial = uf_inicial
        #     # self.fields["municipio"].initial = usuario.cartorio.municipio
        # except Usuario.DoesNotExist:
        #     logger.exception("ERRO")
        #     raise

        # self.helper.layout = Layout(
        #     Row(
        #         # Column("busca_numero_registro", css_class="form-group col-md-4 mb-0"),
        #         Column("tipo_registro", css_class="form-group col-md-4 mb-0"),
        #         Column("numero_registro", css_class="form-group col-md-4 mb-0"),
        #         Column("cartorio", css_class="form-group col-md-4 mb-0"),
        #         css_class="form-row",
        #     ),
        #     Row(
        #         Column("tipo_imovel", css_class="form-group col-md-3 mb-0"),
        #         Column("cep", css_class="form-group col-md-3 mb-0"),
        #         css_class="form-row",
        #     ),
        #     Row(
        #         Column("tipo_logradouro", css_class="form-group col-md-3 mb-0"),
        #         Column("logradouro", css_class="form-group col-md-7 mb-0"),
        #         Column("numero", css_class="form-group col-md-2 mb-0"),
        #         css_class="form-row",
        #     ),
        #     Row(
        #         Column("quadra", css_class="form-group col-md-6 mb-0"),
        #         Column("lote", css_class="form-group col-md-6 mb-0"),
        #         css_class="form-row",
        #     ),
        #     Row(
        #         Column("complemento", css_class="form-group col-md-6 mb-0"),
        #         Column("bairro", css_class="form-group col-md-6 mb-0"),
        #         css_class="form-row",
        #     ),
        #     Row(
        #         Column("uf", css_class="form-group col-md-6 mb-0"),
        #         Column("municipio", css_class="form-group col-md-6 mb-0"),
        #         css_class="form-row",
        #     ),
        # )

    # TODO: Campo para informar o tipo de certidão que será produzida para aquele imóvel.


class PessoaForm(FormDuasColunas):
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nome"),
        required=False,
        initial=TipoDocumento.get_default_tipo_documento_id,
    )

    estado_civil = forms.ModelChoiceField(
        # queryset=EstadoCivil.objects.all().order_by("nome"),
        queryset=EstadoCivil.objects.filter(exibir="S").order_by(
            "descricao_estado_civil",
        ),
        required=False,
    )

    anotacoes = forms.CharField(label="Endereço / Anotações", required=False)

    documento = forms.CharField(
        widget=forms.NumberInput(attrs={"class": "col-md-6"}),
        required=False,
    )

    tipo_documento_conjuge = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nome"),
        required=False,
        initial=TipoDocumento.get_default_tipo_documento_id,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].widget.attrs.update({"class": "col-md-12"})
        self.fields["tipo_documento"].widget.attrs.update({"class": "col-md-6"})
        self.fields["documento"].widget.attrs.update({"class": "col-md-6"})
        self.fields["rg"].widget.attrs.update({"class": "col-md-6"})
        self.fields["estado_civil"].widget.attrs.update({"class": "col-md-6"})
        self.fields["nacionalidade"].widget.attrs.update({"class": "col-md-6"})
        self.fields["profissao"].widget.attrs.update({"class": "col-md-6"})
        self.fields["anotacoes"].widget.attrs.update({"class": "col-md-6"})
        self.fields["endereco"].widget.attrs.update({"class": "col-md-6"})
        self.fields["nome_conjuge"].widget.attrs.update({"class": "col-md-12"})
        self.fields["tipo_documento_conjuge"].widget.attrs.update({"class": "col-md-6"})
        self.fields["documento_conjuge"].widget.attrs.update({"class": "col-md-6"})
        # Adicione classes CSS para os outros campos conforme necessário

    class Meta:
        model = PedidoCertidaoPessoa
        fields = (
            "nome",
            "tipo_documento",
            "documento",
            "rg",
            "estado_civil",
            "nacionalidade",
            "profissao",
            "anotacoes",
            "endereco",
            "nome_conjuge",
            "tipo_documento_conjuge",
            "documento_conjuge",
        )

    # TODO: Campo da colocar o tipo de certidão que será produzida.
    # TODO: Facilitar a inclusão de uma segunda pessoa que será o conjuge quando houver...
    # TODO: Considerar unificar o model pessoa do pedido de certidão a pessoa


class EditarPedidoForm(forms.Form):
    logradouro = forms.CharField(
        label="Logradouro/Fazenda",
        max_length=255,
        required=False,
    )
    numero = forms.CharField(label="Número", max_length=11, required=False)
    quadra = forms.CharField(label="Quadra", max_length=10, required=False)
    lote = forms.CharField(label="Lote", max_length=10, required=False)
    complemento = forms.CharField(
        label="Complemento/Características",
        max_length=50,
        required=False,
    )
    bairro = forms.CharField(label="Bairro", max_length=100, required=False)
    municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.all(),
        label="Município",
        required=False,
    )
    cep = forms.CharField(label="CEP", max_length=10, required=False)

    numero_pedido = forms.CharField(label="Buscar PedidoCertidao", max_length=10)
    numero_pedido.widget.attrs.update({"class": "form-control"})
    numero_pedido.widget.attrs.update({"placeholder": "Qual pedido deseja editar?"})


class PedidoCertidaoAndamentoForm(forms.ModelForm):
    modelos_de_texto = forms.ModelChoiceField(queryset=None, required=False)

    data_hora = forms.DateTimeField(
        disabled=True,
        required=False,
    )

    class Meta:
        model = PedidoCertidaoAndamento
        fields = (
            "data_hora",
            "tipo_andamento",
            "colaborador_destino",
            "modelos_de_texto",
            "descricao",
        )

    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["data_hora"].initial = instance.data_hora
            self.fields["tipo_andamento"].disabled = True
            self.fields["colaborador_destino"].initial = instance.colaborador_destino
        else:
            self.fields["colaborador_destino"].queryset = Colaborador.objects.filter(
                usuario__is_active=True,
            )
            self.fields["data_hora"].initial = timezone.now()
        self.fields[
            "modelos_de_texto"
        ].queryset = PedidoCertidaoAndamento.get_modelos_de_texto_certidao()

    def save(self, commit=True, *args, **kwargs):
        instance = super().save(commit=False)
        # kwargs.get("request", self.request)
        # if not instance.criado_por:  # Verifica se é uma nova instância
        #    instance.criado_por = request.user if request else None
        # if self.request:
        #     instance.criado_por = self.request.user

        if commit:
            instance.save()
        return instance


# class SeloForm(FormDuasColunas):
#     class Meta:
#         model = SeloEletronico
#         fields = (
#             "codigo",
#             "data_utilizacao",
#         )

#     # TODO: O selo é baseado no tipo de certidão selecionada no item (pessoa ou imóvel)


class PedidoCertidaoCertidaoForm(forms.ModelForm):
    class Meta:
        model = Certidao
        fields = ("tipo_tributacao",)

    def __init__(
        self,
        *args,
        tipo_item_certidao_nome_list=None,
        is_editing=False,
        **kwargs,
    ) -> None:
        try:
            if tipo_item_certidao_nome_list is None:
                tipo_item_certidao_nome_list = ["Ambos"]
            super().__init__(*args, **kwargs)

            self.helper = FormHelper()
            self.helper.form_tag = False
            self.helper.layout = Layout()

            self.setup_fields(tipo_item_certidao_nome_list)
            self.add_submit_button()
        except Exception as e:
            logger.exception(f"Erro na inicialização do formulário: {e}")
            raise

    def setup_fields(self, tipo_item_certidao_nome_list):
        """Configura os campos do formulário com base nos tipos de certidões fornecidos."""
        try:
            if tipo_item_certidao_nome_list:
                logger.debug(
                    f"Obtendo os tipos de certidão para {tipo_item_certidao_nome_list}",
                )

                tipos_certidoes = self.get_tipos_certidoes(tipo_item_certidao_nome_list)
                grid_layout = self.create_dynamic_fields(tipos_certidoes)
                self.helper.layout.append(Div(*grid_layout, css_class="row"))

                self.add_tipo_tributacao_field()
        except Exception as e:
            logger.exception(f"Erro ao configurar campos do formulário: {e}")
            raise

    def get_tipos_certidoes(self, tipo_item_certidao_nome_list):
        """Retorna a lista de tipos de certidões ativas com base nos nomes fornecidos."""
        try:
            return TipoCertidao.objects.filter(
                (
                    Q(tipo_item__nome__in=tipo_item_certidao_nome_list)
                    | Q(tipo_item__nome__isnull=True)
                )
                & Q(ativo=True),
            ).order_by("nome")
        except Exception as e:
            logger.exception(f"Erro ao obter tipos de certidões: {e}")
            raise

    def create_dynamic_fields(self, tipos_certidoes):
        """Cria campos dinâmicos para cada tipo de certidão."""
        try:
            grid_layout = []
            for _index, tipo in enumerate(tipos_certidoes):
                field_name = f"quantidade_{tipo.id}"
                self.fields[field_name] = forms.IntegerField(
                    label=tipo.nome,
                    min_value=0,
                    initial=0,
                    required=True,
                )
                grid_layout.append(
                    Div(
                        Field(field_name, css_class="form-control quantidade-field"),
                        css_class="col-md-2 mb-3",
                    ),
                )
            return grid_layout
        except Exception as e:
            logger.exception(f"Erro ao criar campos dinâmicos: {e}")
            raise

    def add_tipo_tributacao_field(self):
        """Adiciona o campo tipo_tributacao ao formulário."""
        try:
            self.helper.layout.append(
                Div(Field("tipo_tributacao"), css_class="form-group"),
            )
        except Exception as e:
            logger.exception(f"Erro ao adicionar campo tipo_tributacao: {e}")
            raise

    def add_submit_button(self):
        """Adiciona o botão de salvar ao formulário."""
        try:
            self.helper.layout.append(
                Div(
                    ButtonHolder(
                        Submit("submit", "Salvar", css_class="btn btn-primary"),
                    ),
                    css_class="form-group",
                ),
            )
        except Exception as e:
            logger.exception(f"Erro ao adicionar botão de submit: {e}")
            raise

    def clean(self):
        try:
            # Chama o método clean da superclasse para obter os dados limpos
            cleaned_data = super().clean()

            # Obtém todos os tipos de certidões ativas
            tipos_certidoes = TipoCertidao.objects.filter(ativo=True)

            # Cria um dicionário com as quantidades de cada tipo de certidão a partir dos dados limpos
            quantidades = {
                f"quantidade_{tipo.id}": cleaned_data.get(f"quantidade_{tipo.id}")
                for tipo in tipos_certidoes
            }

            # Verifica se pelo menos uma quantidade foi definida
            if not any(quantidades.values()):
                msg = "Você deve definir pelo menos uma quantidade para um tipo de certidão."
                logger.warning(
                    "Validação falhou: Nenhuma quantidade foi definida para os tipos de certidões.",
                )
                raise forms.ValidationError(msg)

            # Filtra as quantidades maiores que zero e adiciona ao cleaned_data
            cleaned_data["quantidades"] = {
                int(key.split("_")[1]): quantidade
                for key, quantidade in quantidades.items()
                if quantidade > 0
            }

            logger.debug("Dados limpos com sucesso: %s", cleaned_data["quantidades"])
            return cleaned_data

        except forms.ValidationError as e:
            # Log de aviso para validações que falham
            logger.warning("Erro de validação no método clean: %s", e)
            raise

        except Exception as e:
            # Log de erro para qualquer outra exceção
            logger.exception("Erro inesperado no método clean: %s", e)
            raise


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class PedidoCertidaoAnexoForm(forms.ModelForm):
    class Meta:
        model = PedidoCertidaoAnexo
        fields = ["arquivo"]

    arquivo = forms.FileField(widget=MultipleFileInput(attrs={"multiple": True}))


class CriarProjetoForm(forms.ModelForm):
    numero_projeto = forms.CharField(
        max_length=100,
        required=True,
        label="Número do projeto",
    )

    data_inicio_projeto = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        label="Data inicio do projeto",
        required=False,
    )

    data_fim_projeto = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        label="Data fim do projeto",
        required=False,
    )

    # latitude = forms.CharField(
    #     max_length=100,
    #     required=False,
    #     label="Latitude",
    # )

    # longitude = forms.CharField(
    #     max_length=100,
    #     required=False,
    #     label="Longitude",
    # )

    nome_projeto = forms.CharField(
        max_length=100,
        required=True,
        label="Nome do projeto",
    )

    observacoes = forms.CharField(
        max_length=100,
        required=True,
        label="Observações",
    )

    localidade = forms.CharField(
        max_length=100,
        required=True,
        label="Localidade do Projeto",
    )

    fotovoltaico = forms.BooleanField(
        required=False,
        label="Fotovoltaico",
        initial=False,  # Valor inicial (False por padrão)
        widget=forms.CheckboxInput(attrs={"style": "font-size: 1.5rem;"}),
    )

    biogas = forms.BooleanField(
        required=False,
        label="Biogás",
        initial=False,  # Valor inicial (False por padrão)
        widget=forms.CheckboxInput(attrs={"style": "font-size: 1.5rem;"}),
    )

    hidrogenio = forms.BooleanField(
        required=False,
        label="Hidrogênio",
        initial=False,  # Valor inicial (False por padrão)
        widget=forms.CheckboxInput(attrs={"style": "font-size: 1.5rem;"}),
    )

    baterias = forms.BooleanField(
        required=False,
        label="Baterias",
        initial=False,  # Valor inicial (False por padrão)
        widget=forms.CheckboxInput(attrs={"style": "font-size: 1.5rem;"}),
    )

    categoria_projeto = forms.ChoiceField(
        choices=[
            ("residencial", "Residencial"),
            ("comercial", "Comercial"),
            ("industrial", "Industrial"),
            ("outro", "Outro - Importar"),
        ],
        required=True,
        label="Curva de Consumo",
    )

    categoria_instalacao = forms.ChoiceField(
        choices=[
            ("solo", "Solo"),
            ("telhado", "Telhado"),
        ],
        required=True,
        label="Tipo de instalação",
    )

    area_disponível_instalacao = forms.CharField(
        max_length=100,
        required=True,
        label="Área disponível para instalação",
    )

    horario_inicio_sol_pleno = forms.TimeField(
        required=False,
        label="Horário Início Sol Pleno",
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )

    horario_fim_sol_pleno = forms.TimeField(
        required=False,
        label="Horário Fim Sol Pleno",
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )


    class Meta:
        model = Projeto
        fields = [
            "numero_projeto",
            "nome_projeto",
            "data_inicio_projeto",
            "data_fim_projeto",
            "observacoes",
            "localidade",
            #"latitude",
            #"longitude",
            "categoria_projeto",  # Adicionado ao formulário
            "categoria_instalacao",
            "area_disponível_instalacao",
            #"horario_inicio_sol_pleno",
            "horario_fim_sol_pleno",
            "fotovoltaico",
            "biogas",
            "hidrogenio",
            "baterias",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.fields["data_inicio_projeto"].initial = timezone.now().date()
        self.fields["data_fim_projeto"].initial = timezone.now().date()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                HTML("<p>Informe os dados do Novo Projeto.</p>"),
            ),
            # Row(
            #     Column("finalidade", css_class=" col-md-12 mb-0"),
            #     css_class="form-row",
            # ),
            # Row(
            #     HTML("<hr>"),
            # ),
            Row(
                Column("numero_projeto", css_class=" col-md-3 mb-0"),
                Column("nome_projeto", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("data_inicio_projeto", css_class=" col-md-6 mb-0"),
                Column("data_fim_projeto", css_class=" col-md-6 mb-0"),
                css_class="form-row",
            ),

            Row(
                Column("localidade", css_class=" col-md-3 mb-0"),
                Column("categoria_projeto", css_class="col-md-3 mb-0"),
                Column("categoria_instalacao", css_class="col-md-3 mb-0"),
                Column("area_disponível_instalacao", css_class="col-md-3 mb-0"),
                css_class="form-row",
            ),
            # Row(
            #     Column("horario_inicio_sol_pleno", css_class=" col-md-3 mb-0"),
            #     Column("horario_fim_sol_pleno", css_class=" col-md-3 mb-0"),
            #     Column("latitude", css_class=" col-md-3 mb-0"),
            #     Column("longitude", css_class=" col-md-3 mb-0"),
            #     css_class="form-row",
            # ),
            Row(
                Column("observacoes", css_class=" col-md-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column(
                    "fotovoltaico",
                    css_class="col-md-3 mb-0 center-checkbox",
                    style="display: flex; align-items: center; justify-content: center; font-size: 1.2rem;",
                ),
                Column(
                    "biogas",
                    css_class="col-md-3 mb-0 center-checkbox",
                    style="display: flex; align-items: center; justify-content: center; font-size: 1.2rem;",
                ),
                Column(
                    "hidrogenio",
                    css_class="col-md-3 mb-0 center-checkbox",
                    style="display: flex; align-items: center; justify-content: center; font-size: 1.2rem;",
                ),
                Column(
                    "baterias",
                    css_class="col-md-3 mb-0 center-checkbox",
                    style="display: flex; align-items: center; justify-content: center; font-size: 1.2rem;",
                ),
                css_class="form-row",
            ),
        )
        self.helper.add_input(
            Submit("salvar", "Criar Projeto", css_class="btn-primary"),
        )

        # self.helper.add_input(
        #     Button(
        #         "importar",
        #         "Importar dados meteorologicos",
        #         css_class="btn-success",
        #         onclick="window.history.back()",
        #     ),
        # )


class CriarBateriaForm(forms.ModelForm):
    numero_bateria = forms.CharField(
        max_length=100,
        required=True,
        label="Número da bateria",
    )

    marca = forms.CharField(
        max_length=100,
        required=True,
        label="Marca",
    )

    modelo = forms.CharField(
        max_length=100,
        required=True,
        label="Modelo",
    )

    tipo_de_bateria = forms.CharField(
        max_length=100,
        label="Tipo bateria",
    )

    tensao_celula = forms.CharField(
        max_length=100,
        label="Tensão",
    )

    capacidade = forms.CharField(
        max_length=100,
        label="Capacidade",
    )

    taxa_de_descarga = forms.CharField(
        max_length=100,
        required=True,
        label="Taxa de descarga",
    )

    eficiencia = forms.CharField(
        max_length=100,
        required=True,
        label="Eficiência",
    )

    estado_de_carga = forms.CharField(
        max_length=100,
        required=True,
        label="Estado de Carga",
    )

    profundidade_de_descarga = forms.CharField(
        max_length=100,
        required=True,
        label="Profundidade",
    )

    densidade_de_energia = forms.CharField(
        max_length=100,
        required=True,
        label="Densidade",
    )

    numero_maximo_ciclos = forms.CharField(
        max_length=100,
        required=True,
        label="Ciclos",
    )

    class Meta:
        model = Bateria
        fields = [
            "numero_bateria",
            "marca",
            "modelo",
            "tipo_de_bateria",
            "tensao_celula",
            "capacidade",
            "taxa_de_descarga",
            "eficiencia",
            "estado_de_carga",
            "profundidade_de_descarga",
            "densidade_de_energia",
            "numero_maximo_ciclos",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # self.fields["data_inicio_projeto"].initial = timezone.now().date()
        # self.fields["data_fim_projeto"].initial = timezone.now().date()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                HTML("<p>Informe os dados da Bateria.</p>"),
            ),
            Row(
                Column("numero_bateria", css_class=" col-md-3 mb-0"),
                Column("marca", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("modelo", css_class=" col-md-3 mb-0"),
                Column("tipo_de_bateria", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("tensao_celula", css_class=" col-md-3 mb-0"),
                Column("capacidade", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("taxa_de_descarga", css_class=" col-md-3 mb-0"),
                Column("eficiencia", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("estado_de_carga", css_class=" col-md-3 mb-0"),
                Column("profundidade_de_descarga", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("densidade_de_energia", css_class=" col-md-3 mb-0"),
                Column("numero_maximo_ciclos", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
        )
        self.helper.add_input(
            Submit("salvar", "Criar Bateria", css_class="btn-primary"),
        )


class CriarHidrogenioForm(forms.ModelForm):
    numero_hidrogenio = forms.CharField(
        max_length=100,
        required=True,
        label="Número Hidrogenio",
    )

    marca = forms.CharField(
        max_length=100,
        label="Marca",
    )

    modelo = forms.CharField(
        max_length=100,
        label="Modelo",
    )

    tipo_de_celula = forms.CharField(
        max_length=100,
        label="Tipo de célula",
        help_text="Informe o tipo de célula, por exemplo: Monocristalina, Policristalina, etc.",
    )

    numero_celulas = forms.CharField(
        max_length=100,
        label="Número de células",
        help_text="Informe o número de células do painel fotovoltaico.",
    )

    numero_celulas_stack = forms.CharField(
        max_length=100,
        label="Número de Célula Stack",
    )

    pontencial_nominal = forms.CharField(
        max_length=100,
        required=True,
        label="Potencia Nominal",
        help_text="Indique a potencia nominal do equipamento em watts (W), como especificado pelo fabricante. Exemplo: 12V, 24V, 48V.",
    )

    tensao_nomimal_saida = forms.CharField(
        max_length=100,
        required=True,
        label="tensao_nomimal_saida",
    )

    corrente_nominal_saida = forms.CharField(
        max_length=100,
        required=True,
        label="corrente_nominal_saida",
    )

    consumo_hidrogenio = forms.CharField(
        max_length=100,
        required=True,
        label="consumo_hidrogenio",
    )

    eficiencia = forms.CharField(
        max_length=100,
        required=True,
        label="eficiencia",
    )

    degracao_tempo = forms.CharField(
        max_length=100,
        required=True,
        label="degracao_tempo",
    )

    curva_eficiencia = forms.CharField(
        max_length=100,
        required=True,
        label="curva_eficiencia",
    )

    saida_agua = forms.CharField(
        max_length=100,
        required=True,
        label="saida_agua",
    )

    temperatura_maxima = forms.CharField(
        max_length=100,
        required=True,
        label="temperatura_maxima",
    )

    class Meta:
        model = Hidrogenio
        fields = [
            "numero_hidrogenio",
            "marca",
            "modelo",
            "tipo_de_celula",
            "numero_celulas",
            "numero_celulas_stack",
            "pontencial_nominal",
            "tensao_nomimal_saida",
            "corrente_nominal_saida",
            "consumo_hidrogenio",
            "eficiencia",
            "degracao_tempo",
            "curva_eficiencia",
            "saida_agua",
            "temperatura_maxima",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # self.fields["data_inicio_projeto"].initial = timezone.now().date()
        # self.fields["data_fim_projeto"].initial = timezone.now().date()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                HTML("<p>Informe os dados do Hidrogênio.</p>"),
            ),
            Row(
                Column("numero_hidrogenio", css_class=" col-md-3 mb-0"),
                Column("marca", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("modelo", css_class=" col-md-3 mb-0"),
                Column("tipo_de_celula", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("numero_celulas", css_class=" col-md-3 mb-0"),
                Column("numero_celulas_stack", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("pontencial_nominal", css_class=" col-md-3 mb-0"),
                Column("tensao_nomimal_saida", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("corrente_nominal_saida", css_class=" col-md-3 mb-0"),
                Column("consumo_hidrogenio", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("eficiencia", css_class=" col-md-3 mb-0"),
                Column("degracao_tempo", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("curva_eficiencia", css_class=" col-md-3 mb-0"),
                Column("saida_agua", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("temperatura_maxima", css_class=" col-md-3 mb-0"),
                # Column("saida_agua", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
        )
        self.helper.add_input(
            Submit("salvar", "Criar Hidrogeneo", css_class="btn-primary"),
        )

        self.helper.add_input(
            Button(
                "cancel",
                "Voltar ao Projeto",
                css_class="btn-secondary",
                onclick="window.history.back()",
            ),
        )


class CriarPainelForm(forms.ModelForm):
    numero_hidrogenio = forms.CharField(
        max_length=100,
        required=True,
        label="Número de Cadastro",
        help_text="Informe o número de identificação único do painel solar.",
    )

    marca = forms.CharField(
        max_length=100,
        required=True,
        label="Marca",
        help_text="Digite a marca do painel solar, por exemplo: Trina, Canadian Solar, Jinko.",
    )

    modelo = forms.CharField(
        max_length=100,
        required=False,
        label="Modelo",
        help_text="Informe o modelo específico do painel, conforme a especificação do fabricante.",
    )

    # tipo_de_celula = forms.CharField(
    #     max_length=100,
    #     required=False,
    #     label="Tipo de célula",
    #     help_text="Indique o Tipo de célula (Silicio, HIT).",
    # )
    tipo_de_celula = forms.ChoiceField(
        choices=[
            ("silicio", "Silício"),
            ("hit", "HIT"),
        ],
        required=False,
        label="Tipo de célula",
        help_text="Indique o Tipo de célula (Silício, HIT).",
        widget=forms.Select,  # Este widget cria o combobox
    )

    numero_celulas = forms.CharField(
        max_length=100,
        required=False,
        label="Número de células",
        help_text="Informe o número total de células no painel solar. Exemplo: 60, 72.",
    )

    numero_celulas_stack = forms.CharField(
        max_length=100,
        required=False,
        label="Número de células em série",
        help_text="Digite o número de células conectadas em série no painel.",
    )

    pontencial_nominal = forms.CharField(
        max_length=100,
        required=False,
        label="Potência Nominal (watts)",
        help_text="Informe a potência nominal do painel em watts (W). Exemplo: 500W, 550W, 600W.",
    )

    isc = forms.CharField(
        max_length=100,
        required=False,
        label="Corrente de Curto-Circuito - Isc  (A)",
        help_text="Informe a corrente de curto-circuito (Isc) do painel solar em amperes (A). Exemplo: 9.5A.",
    )

    tensao_nomimal_saida = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão de Cirtuito Aberto - Voc (V)",
        help_text="Digite a tensão de circuito aberto do painel em volts (V). Exemplo: 35V.",
    )

    tensao_maxima_saida = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão de Circuto Aberto VOC (V)",
        help_text="Informe a tensão na qual o painel solar gera sua máxima potência, medida em volts (V). Exemplo: 37.5V.",
    )

    corrente_nominal_saida = forms.CharField(
        max_length=100,
        required=False,
        label="Corrente Nominal de Saída",
        help_text="Informe a corrente nominal de saída em amperes (A). Exemplo: 10A.",
    )

    corrente_maxima_potencia = forms.CharField(
        max_length=100,
        required=False,
        label="Corrente máxima de potência - Imp (A)",
        help_text="Informe a corrente máxima de potência (Imp) do painel solar em amperes (A). Exemplo: 8.5A.",
    )

    consumo_hidrogenio = forms.CharField(
        max_length=100,
        required=False,
        label="Consumo de Hidrogênio",
        help_text="Informe o consumo de hidrogênio em litros por hora (L/h). Exemplo: 5 L/h.",
    )

    eficiencia = forms.CharField(
        max_length=100,
        required=False,
        label="Eficiência",
        help_text="Digite a eficiência do painel em percentual. Exemplo: 18%.",
    )

    degracao_tempo = forms.CharField(
        max_length=100,
        required=False,
        label="Degradação ao longo do tempo",
        help_text="Informe a taxa de degradação anual do painel em percentual. Exemplo: 0,5% ao ano.",
    )

    curva_eficiencia = forms.CharField(
        max_length=100,
        required=False,
        label="Eficiência do Painel",
        help_text="Descreva ou forneça um valor representando a curva de eficiência do painel ao longo do tempo.",
    )

    saida_agua = forms.CharField(
        max_length=100,
        required=False,
        label="Saída de Água",
        help_text="Informe a capacidade de saída de água em litros por hora (L/h).",
    )

    temperatura_maxima = forms.CharField(
        max_length=100,
        required=False,
        label="Temperatura Máxima",
        help_text="Digite a temperatura máxima suportada pelo painel em graus Celsius (°C). Exemplo: 85°C.",
    )

    coeficiente_temperatura_maxima = forms.CharField(
        max_length=100,
        required=False,
        label="Coeficiente de temperatura máxima (upmax)",
        help_text="Informe a variação da potência máxima em relação à temperatura, medida em %/°C. Exemplo: -0,4%/°C.",
    )

    coeficiente_temperatura = forms.CharField(
        max_length=100,
        required=False,
        label="Coeficiente de temperatura (tensão)",
        help_text="Digite o coeficiente de temperatura para a tensão do painel, que indica a variação da tensão em função da temperatura, medida em %/°C. Exemplo: -0,3%/°C.",
    )

    coeficiente_temperatura_corrrenta_curto = forms.CharField(
        max_length=100,
        required=False,
        label="Coeficiente de temperatura da corrente de curto (uisc)",
        help_text="Insira o coeficiente de temperatura para a corrente de curto-circuito (Isc), expresso em %/°C. Exemplo: 0,05%/°C.",
    )

    eficiencia_porcentagem = forms.CharField(
        max_length=100,
        required=False,
        label="Eficiência em porcentagem",
        help_text="Informe a eficiência do painel solar em porcentagem, que representa a taxa de conversão da luz solar em eletricidade. Exemplo: 18,5%.",
    )

    voc = forms.CharField(
        max_length=100,
        required=False,
        label="VOC",
        help_text="Tensão de circuito aberto (VOC) em volts.",
    )

    vmp = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão de máxima potência - VMP (V)",
        help_text="Tensão de máxima potência (VMP) em volts. Exemplo: 32V",
    )

    mp = forms.CharField(
        max_length=100,
        required=False,
        label="MP",
        help_text="Máxima potência (MP) em watts.",
    )

    coef_temp_pot_max_upmax = forms.CharField(
        max_length=100,
        required=False,
        label="Coef. Temp. Pot Max - UPmax",
        help_text="Informe o coeficiente de temperatura da potência máxima (UPmax), geralmente fornecido pelo fabricante do equipamento.",
    )

    coef_temp_voc_uvoc = forms.CharField(
        max_length=100,
        required=False,
        label="Coef. Temp. Voc - Uvoc",
        help_text="Digite o coeficiente de temperatura da tensão de circuito aberto (Voc), em unidades fornecidas na especificação.",
    )

    coef_temp_isc_uisc = forms.CharField(
        max_length=100,
        required=False,
        label="Coef. Temp. Isc - Uisc",
        help_text="Forneça o coeficiente de temperatura da corrente de curto-circuito (Isc), conforme indicado na ficha técnica do painel.",
    )

    class Meta:
        model = PainelSolar
        fields = [
            "numero_hidrogenio",
            "marca",
            "modelo",
            "tipo_de_celula",
            "numero_celulas",
            "isc",
            "pontencial_nominal",
            "tensao_maxima_saida",
            "tensao_nomimal_saida",
            "corrente_nominal_saida",
            "corrente_maxima_potencia",
            "eficiencia",
            "coeficiente_temperatura_maxima",
            "coeficiente_temperatura",
            "coeficiente_temperatura_corrrenta_curto",
            "eficiencia_porcentagem",
            "voc",
            "isc",
            "vmp",
            "mp",
            "coef_temp_pot_max_upmax",
            "coef_temp_voc_uvoc",
            "coef_temp_isc_uisc",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # self.fields["data_inicio_projeto"].initial = timezone.now().date()
        # self.fields["data_fim_projeto"].initial = timezone.now().date()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                HTML("<p>Informe os dados do Painel Solar.</p>"),
            ),
            Row(
                Column("numero_hidrogenio", css_class=" col-md-3 mb-0"),
                Column("marca", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("modelo", css_class=" col-md-3 mb-0"),
                Column("tipo_de_celula", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("numero_celulas", css_class=" col-md-3 mb-0"),
                Column("pontencial_nominal", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("tensao_nomimal_saida", css_class=" col-md-3 mb-0"),
                Column("isc", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("vmp", css_class=" col-md-3 mb-0"),
                Column(
                    "corrente_maxima_potencia",
                    css_class=" col-md-9 mb-0",
                ),
                css_class="form-row",
            ),
            Row(
                # Column("isc", css_class=" col-md-3 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("coef_temp_pot_max_upmax", css_class=" col-md-3 mb-0"),
                Column("coef_temp_voc_uvoc", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("coef_temp_isc_uisc", css_class=" col-md-3 mb-0"),
                Column("curva_eficiencia", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
        )
        self.helper.add_input(
            Submit("salvar", "Criar Painel", css_class="btn-primary"),
        )
        self.helper.add_input(
            Button(
                "cancel",
                "Voltar ao Projeto",
                css_class="btn-secondary",
                onclick="window.history.back()",
            ),
        )


class CriarInversorForm(forms.ModelForm):
    numero_hidrogenio = forms.CharField(
        max_length=100,
        required=True,
        label="Número",
        help_text="Insira o número de identificação do inversor, conforme especificado pelo fabricante.",
    )

    marca = forms.CharField(
        max_length=100,
        label="Marca",
        help_text="Digite a marca do equipamento, por exemplo, Siemens, ABB, etc.",
    )

    modelo = forms.CharField(
        max_length=100,
        label="Modelo",
        help_text="Informe o modelo específico do equipamento.",
    )

    tipo_de_celula = forms.ChoiceField(
        choices=[
            ("silicio", "Silício"),
            ("hit", "HIT"),
        ],
        required=False,
        label="Tipo de célula",
        help_text="Indique o Tipo de célula (Silício, HIT).",
        widget=forms.Select,  # Este widget cria o combobox
    )

    numero_celulas = forms.CharField(
        max_length=100,
        label="Número de Células",
        required=False,
        help_text="Informe a quantidade total de células no equipamento.",
    )

    numero_celulas_stack = forms.CharField(
        max_length=100,
        label="Número de Células Stack",
        required=False,
        help_text="Digite o número de células agrupadas em uma stack.",
    )

    pontencial_nominal = forms.CharField(
        max_length=100,
        required=False,
        label="Potência Nominal (watts)",
        help_text="Informe a potência nominal do painel em watts (W). Exemplo: 500W, 550W, 600W.",
    )

    tensao_nomimal_saida = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão de Cirtuito Aberto - Voc (V)",
        help_text="Digite a tensão de circuito aberto do painel em volts (V). Exemplo: 35V.",
    )

    corrente_nominal_saida = forms.CharField(
        max_length=100,
        required=False,
        label="Corrente Nominal de Saída",
        help_text="Informe a corrente nominal de saída em amperes (A). Exemplo: 10A.",
    )

    consumo_hidrogenio = forms.CharField(
        max_length=100,
        required=False,
        label="Consumo de Hidrogênio",
        help_text="Digite o consumo de hidrogênio em Nm³/h.",
    )

    eficiencia = forms.CharField(
        max_length=100,
        required=False,
        label="Eficiência",
        help_text="Informe a eficiência do equipamento em porcentagem (%).",
    )

    degracao_tempo = forms.CharField(
        max_length=100,
        required=False,
        label="Degradação ao longo do tempo",
        help_text="Especifique a taxa de degradação da eficiência ao longo do tempo, conforme os dados técnicos.",
    )

    curva_eficiencia = forms.CharField(
        max_length=100,
        required=False,
        label="Eficiência do Inversor",
        help_text="Descreva ou forneça valores para a curva de eficiência do equipamento.",
    )

    saida_agua = forms.CharField(
        max_length=100,
        required=False,
        label="Saída de Água",
        help_text="Informe a capacidade de saída de água em litros por hora (L/h).",
    )

    temperatura_maxima = forms.CharField(
        max_length=100,
        required=False,
        label="Temperatura Máxima",
        help_text="Digite a temperatura máxima suportada pelo painel em graus Celsius (°C). Exemplo: 85°C.",
    )

    pot_max_entrada = forms.CharField(
        max_length=100,
        required=False,
        label="Potência Máxima de Entrada (W)",
        help_text="Informe a potência máxima de entrada permitida em watts (W).",
    )

    n_mppt = forms.CharField(
        max_length=100,
        required=False,
        label="Nm MPPT",
        help_text="Especifique o número de rastreadores de ponto de máxima potência (MPPT).",
    )

    corr_dc_max = forms.CharField(
        max_length=100,
        required=False,
        label="Corrente Max por MPPT (A)",
        help_text="Informe a corrente contínua máxima suportada em amperes (A).",
    )

    corrente_dc_max_total = forms.CharField(
        max_length=100,
        required=False,
        label="Corrente DC Máxima Total",
        help_text="Digite a corrente máxima total em corrente contínua (DC) em amperes (A).",
    )

    intervalo_tensao_dc_inicial = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão Minima de Entrada (V)",
        help_text="Informe o valor mínimo da tensão DC operacional em volts (V).",
    )

    intervalo_tensao_dc_final = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão Maxima de Entrada (V)",
        help_text="Informe o valor máximo da tensão DC operacional em volts (V).",
    )

    tensao_dc_nominal = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão Nominal de Entrada (V)",
        help_text="Digite a tensão nominal de operação em corrente contínua (V).",
    )

    intervalo_tensao_mppt_inicial = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão Minima de ajuste MPPT (V)",
        help_text="Informe o valor mínimo da faixa de operação do MPPT (V).",
    )

    intervalo_tensao_mppt_final = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão Maxima de Ajuste MPPT (V)",
        help_text="Informe o valor máximo da faixa de operação do MPPT (V).",
    )

    pot_ac_max = forms.CharField(
        max_length=100,
        required=False,
        label="Potência Maxima de saida (W)",
        help_text="Indique a potência máxima de saída em corrente alternada (W).",
    )

    corrente_falha_maxima = forms.CharField(
        max_length=100,
        required=False,
        label="Corrente Maxima de saida (A)",
        help_text="Informe a corrente máxima em caso de falha (A).",
    )

    # duracao_maxima_falha = forms.CharField(
    #     max_length=100,
    #     required=False,
    #     label="Duração Máxima da Falha",
    #     help_text="Especifique a duração máxima permitida para falhas em segundos (s).",
    # )

    # corrente_ac_max = forms.CharField(
    #     max_length=100,
    #     required=False,
    #     label="Corrente AC Máxima",
    #     help_text="Digite a corrente máxima permitida em corrente alternada (A).",
    # )

    # eficiencia_max = forms.CharField(
    #     max_length=100,
    #     required=False,
    #     label="Eficiência do Inversor",
    #     help_text="Forneça a eficiência máxima do equipamento em porcentagem (%).",
    # )

    intervalo_tensao_ac_inicial = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão Máxima de Saída (V)",
        help_text="Informe a tensão máxima permitida em corrente alternada (V).",
    )

    intervalo_tensao_ac_final = forms.CharField(
        max_length=100,
        required=False,
        label="Tensão Nominal de Saída (V)",
        help_text="Informe a tensão nominal e saída permitida em corrente alternada (V).",
    )

    frequencia = forms.CharField(
        max_length=100,
        required=False,
        label="Frequência de saída (Hz)",
        help_text="Digite a frequência operacional em Hertz (Hz).",
    )

    distorcoes_harmonicas_totais = forms.CharField(
        max_length=100,
        required=False,
        label="Distorções Harmônicas Totais (THD)",
        help_text="Informe a taxa de distorção harmônica total em porcentagem (%).",
    )

    fator_de_potencia_fp = forms.CharField(
        max_length=100,
        required=False,
        label="Fator de Potência (FP)",
        help_text="Indique o fator de potência nominal do equipamento.",
    )

    class Meta:
        model = Inversor
        fields = [
            "numero_hidrogenio",
            "marca",
            "modelo",
            "tipo_de_celula",
            "pot_max_entrada",
            "n_mppt",
            "corr_dc_max",
            "corrente_dc_max_totala",
            "intervalo_tensao_dc_inicial",
            "intervalo_tensao_dc_final",
            "tensao_dc_nominal",
            "intervalo_tensao_mppt_inicial",
            "intervalo_tensao_mppt_final",
            "pot_ac_max",
            "corrente_falha_maxima",
            # "duracao_maxima_falha",
            # "corrente_ac_maxa",
            "curva_eficiencia",
            "intervalo_tensao_ac_inicial",
            "intervalo_tensao_ac_final",
            "frequencia",
            "distorcoes_harmonicas_totais",
            "fator_de_potencia_fpa",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # self.fields["data_inicio_projeto"].initial = timezone.now().date()
        # self.fields["data_fim_projeto"].initial = timezone.now().date()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                HTML("<p>Informe os dados do Inversor.</p>"),
            ),
            Row(
                Column("numero_hidrogenio", css_class=" col-md-3 mb-0"),
                Column("marca", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("modelo", css_class=" col-md-3 mb-0"),
                Column("pot_max_entrada", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("n_mppt", css_class=" col-md-3 mb-0"),
                Column("corr_dc_max", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("corrente_dc_max_total", css_class=" col-md-3 mb-0"),
                Column("intervalo_tensao_dc_inicial", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("intervalo_tensao_dc_final", css_class=" col-md-3 mb-0"),
                Column("tensao_dc_nominal", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("intervalo_tensao_mppt_inicial", css_class=" col-md-3 mb-0"),
                Column("intervalo_tensao_mppt_final", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("pot_ac_max", css_class=" col-md-3 mb-0"),
                Column("corrente_falha_maxima", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            # Row(
            #     # Column("duracao_maxima_falha", css_class=" col-md-3 mb-0"),
            #     Column("corrente_ac_maxa", css_class=" col-md-9 mb-0"),
            #     css_class="form-row",
            # ),
            Row(
                Column("curva_eficiencia", css_class=" col-md-3 mb-0"),
                Column("intervalo_tensao_ac_inicial", css_class=" col-md-3 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("intervalo_tensao_ac_final", css_class=" col-md-3 mb-0"),
                Column("frequencia", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("distorcoes_harmonicas_totais", css_class=" col-md-3 mb-0"),
                Column("fator_de_potencia_fpa", css_class=" col-md-9 mb-0"),
                css_class="form-row",
            ),
        )
        self.helper.add_input(
            Submit("salvar", "Criar Inversor", css_class="btn-primary"),
        )
        self.helper.add_input(
            Button(
                "cancel",
                "Voltar ao Projeto",
                css_class="btn-secondary",
                onclick="window.history.back()",
            ),
        )

class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = [
            "nome_projeto",
            "localidade",
            "data_inicio_projeto",
            "data_fim_projeto",
            "latitude",
            "longitude",
            "observacoes",
            "categoria_projeto",
            "categoria_instalacao",
            "area_disponível_instalacao",
            "horario_inicio_sol_pleno",
            "horario_fim_sol_pleno",
            "consumo_mensal_kwh",
            "horas_sol_dia",
            "fator_perda",
            "dias_mes",
            "vida_util_anos",
            "demanda_ponta",
            "demanda_fora_ponta",
            "demanda_contratada",
            "modalidade",
            "subgrupo_tarifario",
            "migracao_para_mercado_livre_energia",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("nome_projeto", css_class="form-group col-md-6 mb-0"),
                Column("localidade", css_class="form-group col-md-6 mb-0"),
            ),
            Row(
                Column("data_inicio_projeto", css_class="form-group col-md-6 mb-0"),
                Column("data_fim_projeto", css_class="form-group col-md-6 mb-0"),
            ),
            Row(
                Column("latitude", css_class="form-group col-md-6 mb-0"),
                Column("longitude", css_class="form-group col-md-6 mb-0"),
            ),
            Row(
                Column("observacoes", css_class="form-group col-md-6 mb-0"),
            ),
            Row(
                Column("categoria_projeto", css_class="form-group col-md-4 mb-0"),
                Column("categoria_instalacao", css_class="form-group col-md-4 mb-0"),
                Column("area_disponível_instalacao", css_class="form-group col-md-4 mb-0"),
            ),
            # Row(
            #     Column("horario_inicio_sol_pleno", css_class="form-group col-md-6 mb-0"),
            #     Column("horario_fim_sol_pleno", css_class="form-group col-md-6 mb-0"),
            # ),
            Row(
                Column("consumo_mensal_kwh", css_class="form-group col-md-6 mb-0"),
                Column("horas_sol_dia", css_class="form-group col-md-6 mb-0"),
            ),
            Row(
                Column("fator_perda", css_class="form-group col-md-6 mb-0"),
                Column("vida_util_anos", css_class="form-group col-md-6 mb-0"),
                Column("dias_mes", css_class="form-group col-md-6 mb-0"),
            ),
            HTML("<h5 class='mt-1 mb-1'><span class='badge bg-black text-white'>Dados do Consumidor</span></h5>"),
            Row(
                Column("demanda_ponta", css_class="form-group col-md-6 mb-0"),
                Column("demanda_fora_ponta", css_class="form-group col-md-6 mb-0"),
                Column("demanda_contratada", css_class="form-group col-md-6 mb-0"),
                Column("modalidade", css_class="form-group col-md-6 mb-0"),
                Column("subgrupo_tarifario", css_class="form-group col-md-6 mb-0"),
                Column("migracao_para_mercado_livre_energia", css_class="form-group col-md-6 mb-0"),
            ),
        )

class QuantasPlacasForm(forms.Form):
    meta_kwh_mes = forms.FloatField(label="Consumo/Meta mensal (kWh/mês)", min_value=0, initial=450)
    hsp = forms.FloatField(label="HSP (Horas de Sol Pleno / dia)", min_value=0.1, initial=DEFAULT_HSP)
    system_eff = forms.FloatField(label="Eficiência global (0.60–0.90)", min_value=0.5, max_value=0.95, initial=DEFAULT_SYSTEM_EFF)
    panel_watts = forms.IntegerField(label="Potência do módulo (Wp)", min_value=50, max_value=900, initial=DEFAULT_PANEL_WATTS)
    margem = forms.IntegerField(label="Margem de segurança (%)", min_value=0, max_value=50, initial=10)

class RankingEmpresasForm(forms.Form):
    # preco_max = forms.FloatField(label="Preço máximo (R$/Wp)", min_value=0, initial=5.0)
    # garantia_min = forms.IntegerField(label="Garantia mínima (anos)", min_value=0, initial=20)
    # nota_min = forms.FloatField(label="Nota de serviço mínima (0–5)", min_value=0, max_value=5, initial=4.0)
    # ef_min = forms.FloatField(label="Eficiência mínima (%)", min_value=0, initial=19.5)
    preco_max = forms.FloatField(label="Potencia nominal (W)", min_value=0, initial=2700)
    garantia_min = forms.IntegerField(label="VMP", min_value=0, initial=8)
    nota_min = forms.FloatField(label="Número de Células ()", min_value=0, max_value=5, initial=60)
    ef_min = forms.FloatField(label="Eficiência", min_value=0, initial=16)

    # peso_preco = forms.FloatField(label="Peso – Preço", min_value=0, max_value=1, initial=0.35)
    # peso_garantia = forms.FloatField(label="Peso – Garantia", min_value=0, max_value=1, initial=0.20)
    # peso_servico = forms.FloatField(label="Peso – Serviço", min_value=0, max_value=1, initial=0.25)
    # peso_ef = forms.FloatField(label="Peso – Eficiência", min_value=0, max_value=1, initial=0.20)

class PerguntaCustomForm(forms.ModelForm):
    class Meta:
        model = PerguntaCustom
        fields = ["titulo", "descricao", "codigo_handler"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "codigo_handler": forms.Textarea(attrs={"rows": 12, "spellcheck": "false", "class": "font-monospace"}),
        }
