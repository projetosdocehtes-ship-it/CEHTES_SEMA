import re

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django_filters.views import FilterView
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin
from formtools.wizard.views import SessionWizardView

from apps.home.models import Livro05, PedidoItem, PedidoParte, PedidoParteAto
from apps.pessoas.filters import PessoaFilter, VersaoPessoaFilter, VinculoFilter
from apps.pessoas.forms import PessoaForm, VersaoPessoaForm, VinculoForm
from apps.pessoas.models import Pessoa, VersaoPessoa, Vinculo
from apps.pessoas.tables import PessoaTable, VersaoPessoaTable, VinculoTable
from core.mixins import ExportMixin


# Views para Pessoa
def vincular_pessoa_ao_protocolo(vinculo, target_object, pessoa) -> None:
    PedidoParte.objects.update_or_create(
        papel=vinculo.tipo_vinculo.papel,
        pedido_id=target_object.pedido_id,
        pessoa_id=pessoa.pessoa_home_id,
        pessoa_vinculo_id=vinculo.id,
        defaults={
            "papel": vinculo.tipo_vinculo.papel,
            "pedido_id": target_object.pedido_id,
            "pessoa_id": pessoa.pessoa_home_id,
            "pessoa_vinculo_id": vinculo.id,
        },
    )


class PessoaListView(LoginRequiredMixin, ListView):
    model = Pessoa
    template_name = "pessoas/pessoas_list.html"
    paginate_by = 5

    def get_queryset(self):
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pessoa_filter = PessoaFilter(self.request.GET, queryset=self.get_queryset())
        pessoa_table = PessoaTable(pessoa_filter.qs)
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(
            pessoa_table,
        )

        context["filter"] = pessoa_filter
        context["table"] = pessoa_table

        return context


class VersaoPessoaListView(LoginRequiredMixin, ListView):
    model = VersaoPessoa
    template_name = "pessoas/pessoas_list.html"
    paginate_by = 5

    def get_queryset(self):
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        versao_pessoa_filter = VersaoPessoaFilter(
            self.request.GET,
            queryset=self.get_queryset(),
        )
        table = VersaoPessoaTable(versao_pessoa_filter.qs)
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(
            table,
        )

        context["filter"] = versao_pessoa_filter
        context["table"] = table

        return context


class PessoaDetailView(LoginRequiredMixin, DetailView):
    model = VersaoPessoa
    template_name = "pessoas/pessoa_detail.html"


class PessoaCreateView(LoginRequiredMixin, CreateView):
    model = VersaoPessoa
    form_class = PessoaForm
    template_name = "pessoas/pessoa_form.html"

    def get_success_url(self):
        return reverse("pessoas:versao-create", kwargs={"pk": self.object.pk})


class PessoaUpdateView(LoginRequiredMixin, UpdateView):
    model = Pessoa
    fields = "__all__"
    template_name = "pessoas/pessoa_form.html"
    success_url = ""


class VersaoPessoaCreateView(LoginRequiredMixin, CreateView):
    model = VersaoPessoa
    fields = "__all__"
    template_name = "pessoas/pessoa_form.html"


class VersaoPessoaUpdateView(LoginRequiredMixin, UpdateView):
    model = VersaoPessoa
    fields = "__all__"
    template_name = "pessoas/versao_form.html"


class VinculoCreateView(LoginRequiredMixin, CreateView):
    model = Vinculo
    fields = "__all__"
    template_name = "pessoas/vinculo_form.html"


class PessoaCreateWizardView(SessionWizardView):
    form_list = [
        PessoaForm,
        VersaoPessoaForm,
        VinculoForm,
    ]
    template_name = "pessoas/pessoa-create-wizard.html"

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == "1":
            kwargs["object_id"] = self.kwargs.get("object_id")
            kwargs["content_type_id"] = self.kwargs.get("content_type_id")
        return kwargs

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == "1":  # Assumindo que VersaoPessoaForm é o passo 1
            documento = self.get_cleaned_data_for_step("0")[
                "documento"
            ]  # Assumindo que PessoaForm é o passo 0

            # GARANTIR QUE SEJA APENAS NUMERO
            numeros = re.findall(r"\d+", documento)
            documento = "".join(numeros)

            pessoa_existente = Pessoa.objects.filter(documento=documento).first()

            if not pessoa_existente:
                registro_livro05 = Livro05.get_ultima_pessoa_pelo_cpf(cpf=documento)
                ultima_versao = (
                    VersaoPessoa.objects.criar_versao_pessoa_obtida_do_pessoas_em_home(
                        registro_livro05,
                    )
                )

                if ultima_versao:
                    pessoa_existente = ultima_versao.pessoa

            if pessoa_existente:
                ultima_versao = VersaoPessoa.objects.get_ultima_versao(
                    pessoa_existente.id,
                )

                # Utiliza a reflexão para obter todos os campos do modelo VersaoPessoa
                for field in VersaoPessoa._meta.fields:
                    field_name = field.name
                    field_value = getattr(ultima_versao, field_name, None)
                    if field_value is not None:
                        # Atualiza o dicionário de dados iniciais com o valor de cada campo
                        initial[field_name] = field_value

        return initial

    def done(self, form_list, **kwargs) -> redirect:
        try:
            with transaction.atomic():
                # Aqui você cria os objetos no banco de dados
                form_data = [form.cleaned_data for form in form_list]

                # Recupera os parâmetros passados
                object_id = self.kwargs.get("object_id")
                content_type_id = self.kwargs.get("content_type_id")
                content_type = ContentType.objects.get_for_id(content_type_id)

                # Tenta recuperar o ContentType usando o content_type_id
                try:
                    content_type = ContentType.objects.get_for_id(content_type_id)
                except ContentType.DoesNotExist as err:
                    msg = "O ContentType fornecido é inválido."
                    raise ValidationError(msg) from err

                # Verifica se o object_id corresponde a um objeto válido desse ContentType
                model_class = content_type.model_class()  # Obtém a classe do modelo
                if not model_class.objects.filter(pk=object_id).exists():
                    msg = "O object_id fornecido não corresponde a um objeto válido."
                    raise ValidationError(
                        msg,
                    )

                # Busca por uma pessoa existente com o mesmo documento
                documento = form_data[0]["documento"]
                pessoa_existente = Pessoa.objects.filter(documento=documento).first()

                pessoa = (
                    pessoa_existente
                    if pessoa_existente
                    else Pessoa.objects.create(**form_data[0])
                )

                versao_pessoa = VersaoPessoa.objects.create(
                    pessoa=pessoa,
                    **form_data[1],
                )

                vinculo = Vinculo.objects.create(
                    versao_pessoa=versao_pessoa,
                    content_type=content_type,
                    object_id=object_id,
                    tipo_vinculo=form_data[2]["tipo_vinculo"],
                )

                # Recupera o objeto alvo para o redirecionamento
                target_model = content_type.model_class()
                target_object = target_model.objects.get(pk=object_id)

                # VINCULAR A PESSOA AO OBJETO ALVO - PEDIDOPARTE
                vincular_pessoa_ao_protocolo(vinculo, target_object, pessoa)

                if hasattr(target_object, "get_partes_url"):
                    return redirect(target_object.get_partes_url())
                # Verifica se o objeto tem um método get_absolute_url
                if hasattr(target_object, "get_absolute_url"):
                    return redirect(target_object.get_absolute_url())

                # Se não tem, redireciona para uma URL padrão ou mostra um erro
                return redirect("home:protocolos_list")

        except ValidationError as e:
            print(e)
            return redirect("pagina_de_erro_url")


class VinculoListView(LoginRequiredMixin, ExportMixin, SingleTableMixin, FilterView):
    model = Vinculo
    table_class = VinculoTable
    template_name = "pessoas/pessoas_list.html"  # Substitua pelo seu template real
    filterset_class = VinculoFilter

    def get_queryset(self):
        return super().get_queryset()

    def get_filterset_kwargs(self, *args, **kwargs):
        kwargs = super().get_filterset_kwargs(*args, **kwargs)
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset  # Adiciona o filtro ao contexto
        return context


# Atualizar o conjuge do Pedido Parte
def get_pedido_parte_ato(pedido_id, pessoa_id):
    # Busca os IDs dos PedidoItem relacionados ao pedido_id fornecido
    pedido_item_ids = PedidoItem.objects.filter(pedido_id=pedido_id).values_list(
        "id",
        flat=True,
    )

    # Usa os IDs obtidos diretamente na próxima consulta, sem necessidade de avaliar a query antecipadamente
    lista_id = PedidoParteAto.objects.filter(
        pedido_item_id__in=pedido_item_ids,
        pessoa_id=pessoa_id,
    ).values_list(
        "id",
        flat=True,
    )

    return list(lista_id)  # Converte QuerySet para lista, caso necessário


# Atualizar o conjuge do Pedido Parte
def atualizar_conjuge_pedido_parte(pedido_id, pessoa_id, pessoa_conjuge_id) -> None:
    PedidoParte.objects.update_or_create(
        pedido_id=pedido_id,
        pessoa_id=pessoa_id,
        defaults={
            "pessoa_conjuge_id": pessoa_conjuge_id,
        },
    )


# Atualizar o conjuge do Pedido Parte ATO
def atualizar_conjuge_pedido_parte_ato(lista_ids, pessoa_id, pessoa_conjuge_id) -> None:
    for pk in lista_ids:
        PedidoParteAto.objects.update_or_create(
            id=pk,
            pessoa_id=pessoa_id,
            pedido_item_id__isnull=False,
            defaults={
                "pessoa_conjuge_id": pessoa_conjuge_id,
            },
        )


# Alterar dados do ato da PARTE
def vincular_protocolo_parte_conjuge(request):
    if not request.POST:
        raise Http404

    # OBTER O ID PARA ATUALIZAR AS PESSOAS
    pessoa_conjuge_id = request.POST.get("conjuge_id")
    pessoa_id = request.POST.get("pessoa_id")
    pedido_id = request.POST.get("pedido_id")
    protocolo_id = request.POST.get("protocolo_id")

    # LISTA COM TODOS OS PEDIDOS DO ITEM
    lista_ids_pessoa = get_pedido_parte_ato(pedido_id, pessoa_id)
    lista_ids_pessoa_conjuge = get_pedido_parte_ato(pedido_id, pessoa_conjuge_id)

    # ATUALIZAR PEDIDO PARTE
    atualizar_conjuge_pedido_parte(pedido_id, pessoa_id, pessoa_conjuge_id)
    atualizar_conjuge_pedido_parte(pedido_id, pessoa_conjuge_id, pessoa_id)

    # ATUALIZAR PEDIDO PARTE ATO
    if lista_ids_pessoa:
        atualizar_conjuge_pedido_parte_ato(
            lista_ids_pessoa,
            pessoa_id,
            pessoa_conjuge_id,
        )
    # ATUALIZAR PEDIDO PARTE ATO
    if lista_ids_pessoa_conjuge:
        atualizar_conjuge_pedido_parte_ato(
            lista_ids_pessoa_conjuge,
            pessoa_conjuge_id,
            pessoa_id,
        )

    # ATUALIZAR PEDIDO PESSOA
    print("vincular_protocolo_parte_conjuge - ", pedido_id)

    # RETORNA PARA A PÁGINA DE DETALHE DO PROTOCOLO NAS PARTES DO PROTOCOLO
    url = reverse("home:protocolo_detail", args=[protocolo_id]) + "#itens_pedido_partes"
    return HttpResponseRedirect(url)
