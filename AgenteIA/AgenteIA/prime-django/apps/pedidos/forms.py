import logging

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms
from django.apps import apps
from django.utils import timezone
from django_select2.forms import ModelSelect2Widget

from apps.cartorios.models import Usuario
from apps.comum.forms import FormDuasColunas
from apps.comum.models import (
    TipoDocumento,
    TipoPapelParte,
    TipoRegistro,
    TipoRegistroImobiliario,
)
from apps.home.models import models_home

# from apps.selos.models import Selo
from apps.pedidos.form_helpers import AtoFormHelper
from apps.pedidos.models import (
    Apresentante,
    Ato,
    DocumentoParaRequerimento,
    Evento,
    Imovel,
    Parte,
    Participacao,
    Pedido,
    Requerimento,
    Tabela,
    TipoEmolumento,
    TipoTitulo,
    TipoTributacao,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class MunicipioSelect2Widget(ModelSelect2Widget):
    search_fields = ["nome__icontains"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.attrs["data-ajax--url"] = "/caminho/para/sua/view/ajax"


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


class PedidoForm(FormDuasColunas):
    class Meta:
        model = Pedido
        fields = [
            "observacao",
        ]  # e outros campos que você desejar
        observacao = forms.CharField(widget=forms.Textarea)


class ApresentanteLocatePorDocumentoForm(forms.ModelForm):
    documento = forms.CharField(
        label="Documento do Apresentante",
        max_length=20,
        help_text="Localize um Apresentante já cadastrado através do documento.",
    )

    class Meta:
        model = Apresentante
        fields = ["documento"]


class ApresentanteLocatePorNomeForm(forms.ModelForm):
    nome = forms.CharField(
        label="Nome do Apresentante",
        max_length=50,
        help_text="Localize um Apresentante já cadastrado  através do nome.",
    )

    class Meta:
        model = Apresentante
        fields = ["nome"]


class ApresentanteForm(forms.ModelForm):
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nome"),
        required=True,
    )
    documento = forms.CharField(max_length=100, required=False)

    class Meta:
        model = Apresentante
        fields = (
            "nome",
            "tipo_documento",
            "documento",
            "telefone",
            "email",
            "observacao",
            "nacionalidade",
            "profissao",
            "rg",
            "estado_civil",
            "endereco",
            # "filiacao",
            "nome_adquirente_parte",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar valor inicial para tipo_documento
        tipo_documento_inicial = TipoDocumento.objects.filter(sigla="CPF").first()
        self.fields["tipo_documento"].initial = tipo_documento_inicial

        # Configurar valor inicial para estadocivil
        estado_civil_inicial = models_home.EstadoCivil.objects.filter(
            descricao_estado_civil="Não Consta",
        ).first()
        self.fields["estado_civil"].initial = estado_civil_inicial

        # Configurar valor inicial para nacionalidade
        if "instance" not in kwargs or not kwargs["instance"]:
            self.fields["nacionalidade"].initial = "Brasileira"

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Column("nome", css_class="form-group col-md-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("tipo_documento", css_class="form-group col-md-4 mb-0"),
                Column("documento", css_class="form-group col-md-4 mb-0"),
                Column("rg", css_class="form-group col-md-4 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("telefone", css_class="form-group col-md-6 mb-0"),
                Column("email", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("nacionalidade", css_class="form-group col-md-4 mb-0"),
                Column("profissao", css_class="form-group col-md-4 mb-0"),
                Column("estado_civil", css_class="form-group col-md-4 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("endereco", css_class="form-group col-md-12 mb-0"),
                css_class="form-row",
            ),
            # Row(
            #     Column("filiacao", css_class="form-group col-md-12 mb-0"),
            #     css_class="form-row",
            # ),
            Row(
                Column("nome_adquirente_parte", css_class="form-group col-md-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("observacao", css_class="form-group col-md-12 mb-0"),
                css_class="form-row",
            ),
        )
        self.helper.add_input(Submit("action_save", "Salvar", css_class="btn-primary"))
        self.helper.add_input(
            Submit(
                "action_save_and_add_ato",
                "Salvar e Adicionar Ato",
                css_class="btn-info text-white",
            ),
        )


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
    # tipo_logradouro = forms.ModelChoiceField(
    #     queryset=TipoLogradouro.objects.all().order_by("nome"),
    #     label="Tipo de Logradouro",
    #     required=False,
    #     initial=TipoLogradouro.get_default_tipo_logradouro,
    # )
    tipo_registro = forms.ModelChoiceField(
        queryset=TipoRegistroImobiliario.objects.all().order_by("nome"),
        label="Tipo de Registro",
        required=False,
        initial=TipoRegistroImobiliario.get_default_tipo_registro_imobiliario,
    )
    # municipio = forms.ModelChoiceField(
    #     queryset=Municipio.objects.all(),
    #     label="Município",
    #     widget=ModelSelect2Widget(
    #         model=Municipio,
    #         search_fields=["nome__icontains"],
    #         dependent_fields={"uf": "uf"},
    #     ),
    # )
    # municipio = forms.ModelChoiceField(
    #     queryset=Municipio.objects.all(),
    #     label="Município",
    #     widget=MunicipioSelect2Widget,
    # )
    # uf = forms.ModelChoiceField(
    #     label="Estado", queryset=UnidadeFederativa.objects.all(), required=False
    # )
    # pais = forms.ModelChoiceField(queryset=Pais.objects.all(), required=False)

    # Campos do EnderecoMixin
    # logradouro = forms.CharField(
    #     label="Logradouro",
    #     max_length=255,
    #     required=False,
    #     help_text="Ex: Nome da rua, avenida, praça, fazenda, etc.",
    # )
    # numero = forms.CharField(label="Número", max_length=11, required=False)
    # quadra = forms.CharField(label="Quadra", max_length=10, required=False)
    # lote = forms.CharField(label="Lote", max_length=10, required=False)
    # complemento = forms.CharField(
    #     label="Complemento/Características", max_length=50, required=False
    # )
    # bairro = forms.CharField(label="Bairro", max_length=100, required=False)
    # municipio = forms.ModelChoiceField(
    #     queryset=Municipio.objects.all(), label="Município", required=False
    # )
    # cep = forms.CharField(label="CEP", max_length=10, required=False)

    class Meta:
        model = Imovel
        fields = [
            # "busca_numero_registro",
            "tipo_registro",
            "numero_registro",
            "cartorio",
            "tipo_imovel",
            # "tipo_logradouro",
            # "logradouro",
            # "numero",
            # "quadra",
            # "lote",
            # "complemento",
            # "bairro",
            # "cep",
            # "uf",
            # "municipio",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # self.helper = FormHelper(self)

        try:
            # usuario = Usuario.objects.get(pk=self.request.user.pk)
            tipo_imovel = TipoRegistro.get_default_tipo_imovel()
            self.fields["tipo_imovel"].initial = tipo_imovel
            # if usuario.cartorio:
            #     uf_inicial = usuario.cartorio.uf or None
            # else:
            #     uf_inicial = None
            # self.fields["uf"].initial = uf_inicial
            # self.fields["municipio"].initial = usuario.cartorio.municipio
        except Usuario.DoesNotExist:
            logger.exception("ERRO")

        # self.helper.layout = Layout(
        #     Row(
        #         Column("busca_numero_registro", css_class="form-group col-md-4 mb-0"),
        #         Column("numero_registro", css_class="form-group col-md-4 mb-0"),
        #         Column("tipo_registro", css_class="form-group col-md-2 mb-0"),
        #         Column("cartorio", css_class="form-group col-md-2 mb-0"),
        #         css_class="form-row",
        #     ),
        #     Row(
        #         Column("tipo_imovel", css_class="form-group col-md-6 mb-0"),
        #         Column("cep", css_class="form-group col-md-6 mb-0"),
        #         css_class="form-row",
        #     ),
        #     Row(
        #         Column("logradouro", css_class="form-group col-md-10 mb-0"),
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


class ParteForm(FormDuasColunas):
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nome"),
        required=False,
    )
    estado_civil = forms.ModelChoiceField(
        queryset=models_home.EstadoCivil.objects.all(),
        required=False,
    )

    class Meta:
        model = Parte
        fields = (
            "nome",
            "sexo",
            "tipo_documento",
            "documento",
            "documento_auxiliar",
            "profissao",
            "nacionalidade",
            "anotacoes",
            "endereco",
            "estado_civil",
            "tipo_regime_casamento",
            "data_casamento",
        )

    def clean(self):
        cleaned_data = super().clean()
        estado_civil = cleaned_data.get("estado_civil")
        tipo_regime_casamento = cleaned_data.get("tipo_regime_casamento")
        data_casamento = cleaned_data.get("data_casamento")
        cleaned_data.get("conjuge")

        # Verificar se o estado civil é "Casado" e o regime de casamento está vazio
        if (
            estado_civil
            and "casado" in estado_civil.descricao_estado_civil.lower()
            and not tipo_regime_casamento
        ):
            self.add_error(
                "tipo_regime_casamento",
                "Regime de Casamento é obrigatório quando Estado Civil contiver 'casado'.",
            )

        if tipo_regime_casamento and not data_casamento:
            self.add_error(
                "data_casamento",
                "Data de Casamento é obrigatória quando Regime de Casamento é informado.",
            )

        return cleaned_data

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Definir o valor inicial para 'papel' somente se for uma nova instância
        if (
            not self.instance.pk
        ):  # Verifica se não existe uma instância (ou seja, se é uma nova instância)
            self.fields["papel"].initial = TipoPapelParte.get_default_tipo_papel_parte()
            self.helper = FormHelper()
            self.helper.layout = Layout(
                Row(
                    Column("nome", css_class="form-group col-md-6 mb-0"),
                    Column("sexo", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                Row(
                    Column("tipo_documento", css_class="form-group col-md-6 mb-0"),
                    Column("documento", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                Row(
                    Column("documento_auxiliar", css_class="form-group col-md-6 mb-0"),
                    Column("profissao", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                Row(
                    Column("nacionalidade", css_class="form-group col-md-6 mb-0"),
                    Column("anotacoes", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                Row(
                    Column("endereco", css_class="form-group col-md-12 mb-0"),
                    css_class="form-row",
                ),
                Row(
                    Column("estado_civil", css_class="form-group col-md-6 mb-0"),
                    Column(
                        "tipo_regime_casamento",
                        css_class="form-group col-md-6 mb-0",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column("data_casamento", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                FormActions(forms.Submit("submit", "Salvar"), css_class="form-group"),
            )

    # def __init__(self, *args, **kwargs):
    #     # pedido_id = kwargs.pop("pedido_id", None)  # Obter o pedido_id e remover dos kwargs
    #     super(ParteForm, self).__init__(*args, **kwargs)

    #     # if pedido_id:
    #     #     # Filtrar a queryset de imovel com base no pedido_id
    #     #     self.fields["imovel"].queryset = Imovel.objects.filter(pedido=pedido_id)

    #     # self.helper.layout = Layout(
    #     #     Row(
    #     #         Column("busca_cpf", css_class="form-group col-md-6 mb-0"),
    #     #         Column("nome", css_class="form-group col-md-6 mb-0"),
    #     #         css_class="form-row",
    #     #     ),
    #     #     Row(
    #     #         Column("rg", css_class="form-group col-md-6 mb-0"),
    #     #         Column("estado_civil", css_class="form-group col-md-6 mb-0"),
    #     #         css_class="form-row",
    #     #     ),
    #     #     Row(
    #     #         Column("tipo_documento", css_class="form-group col-md-6 mb-0"),
    #     #         Column("documento", css_class="form-group col-md-6 mb-0"),
    #     #         css_class="form-row",
    #     #     ),
    #     #     Row(
    #     #         Column("anotacoes", css_class="form-group col-md-12 mb-0"),
    #     #         css_class="form-row",
    #     #     ),
    #     # )


class PedidoAlterarForm(forms.Form):
    numero_pedido = forms.CharField(label="Buscar Pedido", max_length=10)
    numero_pedido.widget.attrs.update({"class": "form-control"})
    numero_pedido.widget.attrs.update({"placeholder": "Qual pedido deseja alterar?"})

    class Meta:
        model = Pedido


class EventoForm(FormDuasColunas):
    class Meta:
        model = Evento
        fields = ("nome", "tipo_evento")


# class SeloForm(FormDuasColunas):
#     class Meta:
#         model = SeloEletronico
#         fields = (
#             "codigo",
#             "data_utilizacao",
#         )

#     # TODO: O selo é baseado no tipo de ato selecionada no item (parte ou imóvel)


class AtoForm(forms.ModelForm):
    tipo_tributacao = forms.ModelChoiceField(
        queryset=TipoTributacao.objects.none(),
        required=False,
    )
    quantidade = forms.IntegerField(
        help_text="Número de atos iguais a serem criados.",
        initial=1,
        min_value=1,
    )
    valor_titulo = forms.DecimalField(
        help_text="Valor do título em reais.",
        label="Valor do Título",
        initial=0,
        required=True,
        localize=True,
    )
    valor_avaliacao = forms.DecimalField(
        help_text="Valor da avaliação em reais.",
        label="Valor da Avaliação",
        initial=0,
        required=True,
        localize=True,
    )
    tipo_emolumento = forms.ModelChoiceField(
        queryset=TipoEmolumento.objects.none(),
        required=True,
    )

    class Meta:
        model = Ato
        fields = [
            "tipo_titulo",
            "ato_praticavel",
            "tipo_emolumento",
            "tipo_tributacao",
            "valor_titulo",
            "valor_avaliacao",
            "imovel_tipo_registro",
            "imovel_numero_registro",
            "imovel_cartorio",
            "tipo_ato",
            "numero_ato",
            "quantidade",
        ]

    def __init__(self, *args, **kwargs):
        self.pedido_id = kwargs.pop("pedido_id", None)
        super().__init__(*args, **kwargs)

        # Verificar se o formulário está em modo de edição
        if self.instance and self.instance.ato:
            self.fields["ato_praticavel"].widget.attrs["readonly"] = True
            self.fields["ato_praticavel"].disabled = True

        self.helper = AtoFormHelper()

        self.fields["tipo_titulo"].queryset = TipoTitulo.get_ativos()

        # Definir valores iniciais
        self.fields[
            "imovel_tipo_registro"
        ].initial = TipoRegistroImobiliario.get_matricula()

        self.fields["tipo_emolumento"].queryset = Tabela.get_tipos_de_emolumento_ativos(
            timezone.now().date(),
        )

        self.fields["tipo_tributacao"].initial = TipoTributacao.get_normal()

        self.fields["tipo_tributacao"].queryset = TipoTributacao.get_ativos()

        self.fields["tipo_ato"].initial = Ato.get_tipo_ato_registro()

        self.fields["imovel_numero_registro"] = forms.IntegerField(
            required=False,
            help_text="Número de registro do imóvel, apenas números inteiros positivos.",
            min_value=1,
        )
        self.fields["tipo_titulo"].required = False

        self.fields["valor_titulo"].localize = True
        self.fields["valor_titulo"].widget.is_localized = True
        self.fields["valor_avaliacao"].localize = True
        self.fields["valor_avaliacao"].widget.is_localized = True

    def save(self, commit=True):
        # Verifica se estamos atualizando um objeto existente
        if self.instance.pk and Ato.objects.filter(pk=self.instance.pk).exists():
            # Atualizar a instância existente
            for field in self.cleaned_data:
                setattr(self.instance, field, self.cleaned_data[field])
            if commit:
                self.instance.save()
            return self.instance  # Retorna a instância única atualizada
        else:
            # Criação: o comportamento original para criar múltiplas instâncias
            quantidade = self.cleaned_data.get("quantidade", 1)
            instancias = []

            # GRAVA APENAS UMA VEZ - QUANTIDADE CLIENTE DECIDIRÁ NA TELA
            quantidade = 1

            # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
            cartorio_model = apps.get_model("cartorios", "Cartorio")
            usar_selo_sql_server = cartorio_model.objects.all().values_list(
                "usar_selo_sql_server",
                flat=True,
            )[0]

            # SELAR NO SQL SERVER PROTOCOLO
            if usar_selo_sql_server == "S":
                nova_instancia = Ato()
                for field in self.cleaned_data:
                    setattr(nova_instancia, field, self.cleaned_data[field])
                if commit:
                    nova_instancia.save()
                instancias.append(nova_instancia)
            else:
                for _ in range(quantidade):
                    nova_instancia = Ato()
                    for field in self.cleaned_data:
                        setattr(nova_instancia, field, self.cleaned_data[field])
                    if commit:
                        nova_instancia.save()
                    instancias.append(nova_instancia)

            return instancias


class AtoComplementarForm(FormDuasColunas):
    # Adicionando o campo quantidade explicitamente
    quantidade = forms.IntegerField(
        help_text="Número de atos complementares iguais a serem criados.",
        initial=1,  # Valor inicial
        min_value=1,  # Valor mínimo
        # Outras opções necessárias
    )

    tipo_emolumento = forms.ModelChoiceField(
        queryset=TipoEmolumento.objects.none(),
        required=True,
    )

    class Meta:
        model = Ato
        fields = [
            "ato_praticavel",
            "tipo_emolumento",
            "tipo_tributacao",
            "quantidade",
            "valor_titulo",
            "valor_avaliacao",
        ]

    def __init__(self, *args, **kwargs) -> None:
        self.ato_id = kwargs.pop("ato_id", None)
        self.pedido_id = kwargs.pop("pedido_id", None)

        super().__init__(*args, **kwargs)

        self.pedido = Pedido.objects.get(pk=self.pedido_id)
        self.fields["tipo_emolumento"].queryset = Tabela.get_tipos_de_emolumento_ativos(
            timezone.now().date(),
        )

        # # Definir valor inicial para imovel_tipo_registro
        # tipo_registro_matricula_initial = (
        #     TipoRegistroImobiliario.get_default_tipo_registro_imobiliario()
        # )
        # self.fields["imovel_tipo_registro"].initial = tipo_registro_matricula_initial

        # Definir valor inicial para tipo_emolumento
        # tipo_emolumento_initial = TipoEmolumento.get_tipo_emolumento_provisorio()
        # self.fields["tipo_emolumento"].initial = tipo_emolumento_initial

        # Definir valor inicial para tipo_tributacao
        tipo_tributacao_initial = TipoTributacao.get_default_tipo_tributacao()
        self.fields["tipo_tributacao"].initial = tipo_tributacao_initial

    def save(self, commit=True):
        quantidade = self.cleaned_data.get("quantidade", 1)
        instancias = []

        # GRAVA APENAS UMA VEZ - QUANTIDADE CLIENTE DECIDIRÁ NA TELA
        quantidade = 1

        for _ in range(quantidade):
            # Criar uma nova instância do modelo Ato
            nova_instancia = Ato()

            # Copiar dados do formulário para a nova instância
            for field in self.cleaned_data:
                setattr(nova_instancia, field, self.cleaned_data[field])

            # Salvar a nova instância, se necessário
            if commit:
                nova_instancia.save()

            instancias.append(nova_instancia)

        return instancias


class ParticipacaoCreateForm(FormDuasColunas):
    documento_parte = forms.CharField(label="Documento da Parte", max_length=20)
    papel = forms.ModelChoiceField(
        queryset=TipoPapelParte.objects.none(),
        label="Papel",
    )
    conjuge = forms.ModelChoiceField(
        queryset=Participacao.objects.none(),
        label="Cônjuge",
        required=False,
    )

    class Meta:
        model = Participacao
        fields = ["documento_parte", "papel", "percentual_participacao", "conjuge"]

    def __init__(self, *args, ato=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Aplica o filtro baseado no 'ato' se ele for passado
        if ato:
            self.fields["conjuge"].queryset = Participacao.objects.filter(
                ato=ato,
                parte__estado_civil__descricao_estado_civil__icontains="casado",
            ).exclude(id=self.instance.id)
        else:
            # Caso 'ato' não seja fornecido, retornar queryset vazio ou conforme a necessidade
            self.fields["conjuge"].queryset = Parte.objects.none()

        self.fields["papel"].queryset = TipoPapelParte.objects.all()

    def save(self, commit=True):
        # Tenta encontrar o último Apresentante com o mesmo documento
        try:
            ultima_parte = Parte.objects.filter(
                documento=self.cleaned_data["documento_parte"],
            ).latest("criado_em")
        except Parte.DoesNotExist:
            ultima_parte = None

        participacao = super().save(commit=False)

        # Cria ou recupera a Parte
        parte, created = Parte.objects.get_or_create(
            documento=self.cleaned_data["documento_parte"],
        )

        # Se encontrou, copia os dados do último apresentante
        if ultima_parte:
            parte.nome = ultima_parte.nome
            parte.tipo_documento = ultima_parte.tipo_documento
            parte.estado_civil = ultima_parte.estado_civil
            # pass

        participacao.parte = parte

        if commit:
            participacao.save()

            if participacao.conjuge:
                conjuge = participacao.conjuge
                conjuge.conjuge = participacao
                conjuge.save()

        return participacao


class ParticipacaoForm(FormDuasColunas):
    papel = forms.ModelChoiceField(
        queryset=TipoPapelParte.objects.none(),
        label="Papel",
        required=True,
    )
    conjuge = forms.ModelChoiceField(
        queryset=Participacao.objects.none(),
        label="Cônjuge",
        required=False,
    )

    class Meta:
        model = Participacao
        fields = ["papel", "percentual_participacao", "conjuge"]

    def save(self, commit=True):
        participacao = super().save(commit=False)

        if commit:
            participacao.save()

            if participacao.conjuge:
                conjuge = participacao.conjuge
                conjuge.conjuge = participacao
                conjuge.save()

        return participacao

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.fields["conjuge"].queryset = Participacao.objects.filter(
            ato=self.instance.ato,
            parte__estado_civil__descricao_estado_civil__icontains="casado",
        ).exclude(id=self.instance.id)

        self.fields["papel"].queryset = TipoPapelParte.objects.all()


class RequerimentoForm(forms.ModelForm):
    class Meta:
        model = Requerimento
        fields = [
            "ato_praticavel",
            "observacao",
            "ativo",
            "obrigatorio",
            "ato_praticavel",
        ]


class DocumentoParaRequerimentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoParaRequerimento
        fields = ["nome", "requerimento", "observacao"]


class EntriesPerPageForm(forms.Form):
    entries_per_page = forms.ChoiceField(
        choices=[(5, "5"), (10, "10"), (20, "20"), (50, "50")],
        required=False,
        initial=10,
        widget=forms.Select(attrs={"onchange": "this.form.submit();"}),
    )
