import logging
from decimal import Decimal
from typing import Any

from auditlog.models import LogEntry
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Count
from django.forms import model_to_dict
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View, generic
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_tables2 import RequestConfig, SingleTableMixin, SingleTableView

from apps.home import helpers
from apps.home.models import TipoOperacaoFinanceira
from apps.pedidos import models
from apps.pedidos.filters import PedidoFilter
from apps.pedidos.forms import (
    ApresentanteForm,
    ApresentanteLocatePorDocumentoForm,
    ApresentanteLocatePorNomeForm,
    AtoComplementarForm,
    AtoForm,
    EventoForm,
    ImovelForm,
    ParteForm,
    ParticipacaoCreateForm,
    ParticipacaoForm,
    PedidoForm,
    RequerimentoForm,
)
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
)
from apps.pedidos.services import get_cod_prenotacao, get_requeremento_inicial_id
from apps.pedidos.tables import (
    AtosComplementaresAgrupadosTable,
    AtosTable,
    DocumentoParaRequerimentoTable,
    EventoTable,
    ImovelTable,
    PartesTable,
    ParticipacaoTable,
    PedidoTable,
    ProtocoloTable,
    RequerimentoTable,
)

# from apps.selos.models import Selo

app_name = "pedidos"

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class EventoListView(LoginRequiredMixin, SingleTableMixin, generic.ListView):
    model = Evento
    table_class = EventoTable
    template_name = "pedidos/listar.html"
    paginate_by = 10


class EventoAddView(LoginRequiredMixin, View):
    def get(self, request, pedido_id):
        form = EventoForm()
        return render(request, "evento_form.html", {"form": form})

    def post(self, request, pedido_id):
        print(request.user)
        form = EventoForm(request.POST, request=request)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.pedido = get_object_or_404(Pedido, id=pedido_id)
            evento.save()
            return redirect("pedidos:pedido_detail", pedido_id)
        return render(request, "evento_form.html", {"form": form})


class EventoUpdateView(LoginRequiredMixin, View):
    def get(self, request, pedido_id, evento_id):
        evento = get_object_or_404(Evento, id=evento_id, pedido__id=pedido_id)
        form = EventoForm(instance=evento, request=request)
        return render(request, "pedidos/item_form.html", {"form": form})

    def post(self, request, pedido_id, evento_id):
        evento = get_object_or_404(Evento, id=evento_id, pedido__id=pedido_id)
        form = EventoForm(request.POST, instance=evento, request=request)
        if form.is_valid():
            form.save()
            return redirect("pedidos:pedido_detail", pedido_id)
        return render(request, "evento_form.html", {"form": form})


class ImovelCreateView(LoginRequiredMixin, generic.CreateView):
    model = Imovel
    form_class = ImovelForm
    template_name = "pedidos/item_form.html"
    extra_context = {
        "title": "Adicionar Imóvel ao Pedido",
        "parent": "Pedidos",
        "segment": "Adicionar Imóvel ao Pedido",
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.pedido = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        self.object.save()
        return redirect("pedidos:imovel_update", self.object.id)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", args=[self.kwargs["pedido_id"]])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        url_retorno = reverse("pedidos:pedido_detail", args=[self.kwargs["pedido_id"]])
        context["botoes"] = {
            "cancelar": {
                "url": url_retorno,
                "label": "Voltar ao Pedido",
                "class": "btn-secondary",
            },
        }

        return context


class ImovelUpdateView(LoginRequiredMixin, UpdateView):
    model = Imovel
    form_class = ImovelForm
    template_name = "pedidos/item_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        from apps.pedidos.tables import ProtocoloSomadaTable

        context = super().get_context_data(**kwargs)
        imovel = self.get_object()
        atos_agrupadas = (
            Ato.objects.filter(imovel=imovel)
            .values("ato_praticavel__nome")
            .annotate(quantidade=Count("id"))
        )
        atos_table = ProtocoloSomadaTable(atos_agrupadas)
        context["imovel"] = imovel
        context["atos_table"] = atos_table
        # context["pedido_id"] = self.kwargs["pedido_id"]
        context["parent"] = "Pedidos"
        context["url_de_exclusao"] = "pedidos:imovel_delete"
        return context

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", args=[self.kwargs["pedido_id"]])


class ImovelListView(SingleTableMixin, generic.ListView):
    model = Imovel
    table_class = ImovelTable
    template_name = "pedidos/listar.html"
    context_table_name = "table"
    paginate_by = 10

    def get_queryset(self):
        pedido_id = self.kwargs["pedido_id"]
        return Imovel.objects.filter(pedido_id=pedido_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pedido_id = self.kwargs["pedido_id"]

        url_retorno = self.request.GET.get(
            "next",
            reverse("pedidos:pedido_detail", args=[pedido_id]),
        )

        botoes = {
            "adicionar": {
                "url": reverse("pedidos:adicionar_imovel", args=[pedido_id]),
                "label": "Adicionar",
                "class": "btn-primary",
            },
            "voltar": {
                "url": url_retorno,
                "label": "Voltar ao Pedido",
                "class": "btn-secondary",
            },
        }

        context.update(
            {
                "parent": "atos",
                "segment": "pedidos",
                "title": "Imóveis do Pedido",
                "botoes": botoes,
            },
        )

        return context


class ImovelDetailView(generic.DetailView):
    model = Imovel
    template_name = "pedidos/detail_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["url_de_exclusao"] = (
            "pedidos:imovel_delete"  # ou qualquer lógica dinâmica aqui
        )
        return context


class ImovelDeleteView(generic.DeleteView):
    model = Imovel
    template_name = "pedidos/parte_confirm_delete.html"

    def get_success_url(self):
        pedido_id = self.object.pedido_id
        return reverse("pedidos:pedido_detail", kargs=[pedido_id])


class Dashboard(LoginRequiredMixin, generic.TemplateView):
    template_name = "pedidos/PedidosIndex.html"


class ApresentanteLocateView(LoginRequiredMixin, TemplateView):
    template_name = "pedidos/apresentante/apresentante_locate.html"
    success_url = reverse_lazy("pedidos:apresentante_create")

    def get(self, request, *args, **kwargs):
        documento_form = ApresentanteLocatePorDocumentoForm()
        nome_form = ApresentanteLocatePorNomeForm()
        return render(
            request,
            self.template_name,
            {
                "documento_form": documento_form,
                "nome_form": nome_form,
            },
        )

    def post(self, request, *args, **kwargs):
        # Inicializa os formulários no início para garantir que estejam sempre disponíveis
        documento_form = ApresentanteLocatePorDocumentoForm()
        nome_form = ApresentanteLocatePorNomeForm()

        if "search_by_documento" in request.POST:
            documento_form = ApresentanteLocatePorDocumentoForm(request.POST)
            if documento_form.is_valid():
                documento = documento_form.cleaned_data["documento"]
                apresentante = (
                    Apresentante.objects.filter(documento=documento)
                    .order_by("-criado_em")
                    .first()
                )
                if apresentante is not None:
                    request.session["apresentante_initial"] = model_to_dict(
                        apresentante,
                    )
                    request.session["apresentante_initial"]["observacao"] = ""
                    request.session.modified = True
                else:
                    request.session["apresentante_initial"] = {"documento": documento}
                return redirect(self.success_url)

        elif "search_by_nome" in request.POST:
            nome_form = ApresentanteLocatePorNomeForm(request.POST)
            if nome_form.is_valid():
                nome = nome_form.cleaned_data["nome"]
                apresentantes = Apresentante.objects.filter(nome__icontains=nome)
                if apresentantes.count() > 1:
                    request.session["nome_busca"] = nome
                    return redirect(reverse("pedidos:apresentante_list", args=[nome]))
                elif apresentantes.exists():
                    apresentante = apresentantes.first()
                    request.session["apresentante_selecionado"] = model_to_dict(
                        apresentante,
                    )
                    request.session["apresentante_selecionado"]["observacao"] = ""
                    request.session.modified = True
                    messages.success(request, "Apresentante localizado.")
                    return redirect(self.success_url)
                else:
                    request.session["apresentante_initial"] = {"nome": nome}
                return redirect(self.success_url)

        context = {
            "documento_form": documento_form,
            "nome_form": nome_form,
        }

        return render(request, self.template_name, context)


@login_required(login_url="/login")
def seleciona_apresentante(request, pk):
    """View para processar a seleção de um apresentante e armazenar na sessão."""
    apresentante = Apresentante.objects.get(pk=pk)
    request.session["apresentante_initial"] = model_to_dict(apresentante)

    # CAMPO OBSERVACAO INICIALIZADO VAZIO
    request.session["apresentante_initial"]["observacao"] = ""
    request.session["apresentante_initial"]["nacionalidade"] = "brasileira"

    # Redireciona para a página desejada após a seleção
    return redirect(reverse_lazy("pedidos:apresentante_create"))


@login_required(login_url="/login")
def desativar_apresentante(request, pk):
    """View para desativar a seleção de um apresentante."""
    apresentante = get_object_or_404(Apresentante, pk=pk)
    apresentante.ativo = False
    apresentante.save()

    # Redireciona para a página anterior
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


class ApresentanteListView(LoginRequiredMixin, ListView):
    model = Apresentante
    template_name = "pedidos/apresentante/apresentante_list.html"
    context_object_name = "apresentantes"

    def get_queryset(self):
        nome = self.kwargs.get("nome", "")
        return Apresentante.objects.filter(nome__icontains=nome, ativo=True)


class ApresentanteCreateView(LoginRequiredMixin, CreateView):
    model = Apresentante
    form_class = ApresentanteForm
    template_name = "pedidos/apresentante/apresentante_create.html"
    success_url = reverse_lazy("pedidos:apresentante_update")

    def get_initial(self):
        initial = super().get_initial()
        apresentante_initial = self.request.session.get("apresentante_initial", None)
        if apresentante_initial:
            initial.update(apresentante_initial)
        return initial

    def form_valid(self, form):
        # Isso salva o Apresentante e configura self.object
        response = super().form_valid(form)
        apresentante = self.object  # A instância de Apresentante recém-criada

        pedido = Pedido.criar(
            apresentante=apresentante,
            criado_por=self.request.user,
        )  # Cria o Pedido

        if "action_save" in self.request.POST:
            return redirect("pedidos:pedido_detail", pk=pedido.pk)
        elif "action_save_and_add_ato" in self.request.POST:
            return redirect("pedidos:ato_create", pedido_id=pedido.pk)

        # ou, por padrão, redireciona para a página de detalhes do pedido
        return response

    def get_success_url(self):
        return reverse("pedidos:apresentante_update", args=[self.object.pk])


class PedidosListView(LoginRequiredMixin, generic.ListView):
    model = Pedido
    template_name = "pedidos/pedidos_list.html"
    paginate_by = 10
    extra_context = {
        "title": model._meta.verbose_name_plural.title(),
        "parent": "Pedidos",
        "segment": "pedidos",
    }

    def get_queryset(self):
        try:
            queryset = super().get_queryset().order_by("-numero_pedido")
        except Pedido.DoesNotExist:
            messages.error(
                self.request,
                _(
                    "Erro ao recuperar os pedidos. Por favor, tente novamente mais tarde.",
                ),
            )
            queryset = Pedido.objects.none()
        except Exception as e:
            messages.error(
                self.request,
                _("Ocorreu um erro inesperado: {}").format(str(e)),
            )
            queryset = Pedido.objects.none()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            pedido_filter = PedidoFilter(self.request.GET, queryset=self.get_queryset())
            pedidos_table = PedidoTable(pedido_filter.qs)
            RequestConfig(
                self.request,
                paginate={"per_page": self.paginate_by},
            ).configure(pedidos_table)

            context["table"] = pedidos_table
            context["filter"] = pedido_filter
            context["botoes"] = {
                "criar_pedido": {
                    "url": reverse("pedidos:pedido_create"),
                    "class": "btn-success",
                    "label": "Criar Novo Pedido",
                },
            }
        except Exception as e:
            messages.error(
                self.request,
                _("Ocorreu um erro ao processar os dados da página: {}").format(str(e)),
            )
            raise Http404(_("Erro ao carregar os dados da página."))

        return context


@login_required
def pedido_detail(request: HttpRequest, pk: int) -> HttpResponse:
    # Recupera o objeto Pedido pelo ID (pk)
    pedido = get_object_or_404(Pedido, pk=pk)

    # Obter o ContentType do modelo Pedido
    pedido_content_type = ContentType.objects.get_for_model(pedido)

    # Filtra atos com número de registro de imóvel
    atos_com_imovel_numero_registro = (
        pedido.atos.all()
        .exclude(imovel_numero_registro__isnull=True)
        .exclude(imovel_numero_registro__exact="")
    )

    # Chama as funções para obter os contextos específicos
    tables_context = get_tables_context(request, pedido)
    navigation_context = get_navigation_context(pedido)

    # Atualiza o contexto com as informações adicionais
    context = {
        "pedido": pedido,
        "title": "Detalhes do Pedido",
        "parent": "Pedidos",
        "segment": "pedido_detail",
        "pedido_content_type_id": pedido_content_type.id,
        "atos_com_imovel_numero_registro": atos_com_imovel_numero_registro,
    }
    context.update(tables_context)
    context.update(navigation_context)

    return render(request, "pedidos/pedido_detail.html", context)


def get_tables_context(request: HttpRequest, pedido: Pedido) -> dict:
    atos_com_total = []
    valor_total_geral = sum(
        ato.total_valor for ato in atos_com_total if ato.total_valor
    )
    naturezas_dos_atos = pedido.atos.values_list("ato_praticavel", flat=True)

    requerimento_table = RequerimentoTable(
        Requerimento.objects.filter(ato_praticavel__in=naturezas_dos_atos),
    )

    # Configura a tabela com a request
    RequestConfig(request).configure(requerimento_table)
    requerimento_table.request = request

    # BUSCAR REQUERIMENTO INICIAL
    requerimento_inicial_id = get_requeremento_inicial_id()

    return {
        "valor_total_geral": valor_total_geral,
        "atos_com_total": atos_com_total,
        "requerimento_table": requerimento_table,
        "requerimento_inicial_id": requerimento_inicial_id,
    }


def get_navigation_context(pedido: Pedido) -> dict:
    current_pedido_num = pedido.numero_pedido
    next_pedido = (
        Pedido.objects.filter(numero_pedido__gt=current_pedido_num)
        .order_by("numero_pedido")
        .first()
    )
    previous_pedido = (
        Pedido.objects.filter(numero_pedido__lt=current_pedido_num)
        .order_by("-numero_pedido")
        .first()
    )
    first_pedido = Pedido.objects.all().order_by("numero_pedido").first()
    last_pedido = Pedido.objects.all().order_by("-numero_pedido").first()

    return {
        "next_pedido": next_pedido,
        "previous_pedido": previous_pedido,
        "first_pedido": first_pedido,
        "last_pedido": last_pedido,
    }


def _save_apresentante(pedido: Pedido, form: PedidoForm) -> Apresentante:
    apresentante = form.save(commit=False)
    apresentante.pedido = pedido
    return apresentante


# classe PedidoCreateView que redireciona para ApresentanteLocateView
@login_required
def pedido_create(request: HttpRequest) -> HttpResponse:
    return redirect("pedidos:apresentante_locate")


class ApresentanteUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "pedidos/apresentante/apresentante_update.html"
    model = Apresentante
    form_class = ApresentanteForm

    def post(
        self: "ApresentanteUpdateView",
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ):
        self.object: Apresentante = self.get_object()
        form: ApresentanteForm = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self: "ApresentanteUpdateView", form: PedidoForm) -> HttpResponse:
        response = super().form_valid(form)

        if "action_save" in self.request.POST:
            return redirect("pedidos:pedido_detail", pk=self.object.pedido.pk)
        elif "action_save_and_add_ato" in self.request.POST:
            return redirect("pedidos:ato_create", pedido_id=self.object.pedido.pk)

        return response

    def get_queryset(self: "ApresentanteUpdateView") -> models.QuerySet:
        queryset = super().get_queryset()
        return queryset.select_related("dados_bancarios")

    def get_success_url(self: "ApresentanteUpdateView") -> str:
        return reverse("pedidos:pedido_detail", args=[self.object.pedido.pk])


@login_required
def pedido_protocolar_view(request, pk):
    try:
        # Inicia uma transação atômica para garantir consistência em caso de erro
        with transaction.atomic():
            # Busca o pedido pelo ID ou retorna um 404 se não encontrado
            pedido = get_object_or_404(Pedido, pk=pk)

            # Tenta processar o pedido (protocolar)
            pedido.protocolar()

            

            # Mensagem de sucesso ao usuário
            messages.success(request, "Pedido protocolado com sucesso.")

            # Redireciona para a URL do pedido após o processamento bem-sucedido
            return redirect(pedido.get_absolute_url())

    except Pedido.DoesNotExist:
        # Caso o pedido não seja encontrado (embora get_object_or_404 já trate isso)
        messages.error(request, f"Pedido não encontrado com o ID {pk}.")
        return redirect("pedidos:pedidos_list")

    except DatabaseError:
        # Em caso de erro de banco de dados, captura a exceção e envia uma mensagem de erro ao usuário
        messages.error(
            request,
            "Houve um erro ao tentar protocolar o pedido. Tente novamente mais tarde.",
        )
        # Log do erro pode ser adicionado aqui, se necessário
        # logging.error(f"Erro ao protocolar pedido {pk}: {str(e)}")
        return redirect("pedidos:pedidos_list")

    except Exception as e:
        # Captura qualquer outra exceção que possa ocorrer
        messages.error(request, f"Ocorreu um erro inesperado: {e!s}")
        return redirect("pedidos:pedidos_list")


class DuplicarPedidodeProtocoloView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # BUSCAR O PEDIDO
        pedido = get_object_or_404(Pedido, id=pk)
        pedido_ato = Ato.objects.filter(pedido=pedido)

        # BUSCAR O APRESENTANTE DO PEDIDO
        apresentante = get_object_or_404(Apresentante, id=pedido.apresentante_id)
        novo_apresentante = duplicar_objeto(
            model_instance=apresentante,
            lista_campos_excluidos=["id", "id_sequencial"],
            coluna_01_atualizar=None,
            valor_01_atualizar=None,
        )

        # GERAR NOVO PEDIDO
        novo_pedido = duplicar_objeto(
            model_instance=pedido,
            lista_campos_excluidos=[
                "id",
                "numero_pedido",
                "numero_onr",
                "numero_protocolo_firebird",
                "numero_selo_firebird",
                "codigo_seguranca_firebird",
                "codigo_internet_firebird",
                "apresentante",
            ],
            coluna_01_atualizar="apresentante_id",
            valor_01_atualizar=novo_apresentante.id,
        )

        # GERAR NOVO ATO DO PEDIDO
        for ato in pedido_ato:
            # PEGAR OS DADOS QUE NAO SEJAM DE PRENOTACAO DO PROTOCOLO
            if str(ato.tipo_emolumento.codigo) != str(get_cod_prenotacao()):
                novo_ato = duplicar_objeto(
                    model_instance=ato,
                    lista_campos_excluidos=[
                        "id",
                        "pedido",
                        "id_sequencial",
                        "ato",
                    ],
                    coluna_01_atualizar="pedido_id",
                    valor_01_atualizar=novo_pedido.id,
                )

                print(novo_ato)

        return redirect(novo_pedido.get_absolute_url())


class PedidoExportarView(LoginRequiredMixin, View):
    def get(self, request, pk):
        pedido = get_object_or_404(Pedido, id=pk)
        # db = FbConnection()

        # PedidoProtocolarNoFirebirdService.exportar_pedido_de_protocolo_para_fb(pedido, db, request, request.user)

        return redirect(pedido.get_absolute_url())


class PedidoRelatorioView(LoginRequiredMixin, SingleTableMixin, TemplateView):
    table_class = PedidoTable
    template_name = "pedidos/relatorios/pedidos_relatorio.html"

    def get_table_data(self):
        return Pedido.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["today"] = timezone.now().date()
        context["total_items"] = Pedido.objects.count()

        return context


class PedidoReciboDetailView(LoginRequiredMixin, View):
    template_name = "pedidos/recibos/recibo_pedido_orcamento.html"

    def get(self, request, pk=None, numero_protocolo=None):
        # Validação de entradas
        if not pk and not numero_protocolo:
            messages.error(request, "Parâmetro inválido.")
            return HttpResponseBadRequest("Parâmetro inválido.")

        try:
            # Filtrando o pedido pela pk ou numero_protocolo
            if pk:
                pedido = Pedido.objects.filter(pk=pk).first()
            elif numero_protocolo:
                pedido = Pedido.objects.filter(
                    numero_protocolo_firebird=numero_protocolo,
                ).first()

            if pedido:
                context = self.get_context_data(pedido=pedido)
                return render(request, self.template_name, context)
            else:
                messages.error(request, "Pedido não encontrado.")
                return redirect("pedidos:pedidos_list")
        except Exception as e:
            logger.exception(f"Erro ao buscar pedido: {e}")
            messages.error(
                request,
                "Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde.",
            )
            return redirect("pedidos:pedidos_list")

    def get_context_data(self, pedido):
        return {
            "object": pedido,
            "atos_agrupados": pedido.get_atos_agrupados(),
            "agora": timezone.now(),
            "title": "Comprovante de Pedido".upper(),
        }


class PedidoReciboDetailProtocoloView(LoginRequiredMixin, View):
    template_name = "pedidos/recibos/recibo.html"

    def get(self, request, pk=None, numero_protocolo=None):
        # Validação de entradas
        if not pk and not numero_protocolo:
            messages.error(request, "Parâmetro inválido.")
            return HttpResponseBadRequest("Parâmetro inválido.")

        try:
            # Filtrando o pedido pela pk ou numero_protocolo
            if pk:
                pedido = Pedido.objects.filter(pk=pk).first()
            elif numero_protocolo:
                pedido = Pedido.objects.filter(
                    numero_protocolo_firebird=numero_protocolo,
                ).first()

            if pedido:
                context = self.get_context_data(pedido=pedido)
                return render(request, self.template_name, context)
            else:
                messages.error(request, "Pedido não encontrado.")
                return redirect("pedidos:pedidos_list")
        except Exception as e:
            logger.exception(f"Erro ao buscar pedido: {e}")
            messages.error(
                request,
                "Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde.",
            )
            return redirect("pedidos:pedidos_list")

    def get_context_data(self, pedido):
        return {
            "object": pedido,
            "atos_agrupados": pedido.get_atos_agrupados(),
            "agora": timezone.now(),
            "title": "Comprovante de Pedido".upper(),
        }


@login_required
def pedido_protocolo_cancelar(request, pk):
    template_name = "form-pedido-protocolo-cancelar.html"

    # Verificar a opção de reentrada - Exibir o caption
    caption = "Cancelar todos os itens do PEDIDO DE PROTOCOLO: "

    if request.method == "POST":
        item = Pedido.objects.get(pk=pk)

        request.POST.get("descricao_cancelamento_id")
        valor_devolver = request.POST.get("input_valor_devolver")
        request.POST.get("input_tipooperacaofinanceira_id")
        helpers.get_data_e_hora_por_opcao(3)

        # FORMATAR VALOR
        valor_devolver = (
            Decimal(str(valor_devolver).replace(".", "").replace(",", ".")) * -1
        )

        # # GRAVAR CAIXA DEVOLUCAO
        # financeiro = Financeiro.criar_financeiro_despesa_receita(
        #     pedido_id=None,
        #     pedido_certidao_id=pk,
        #     tipo_transacao_id=tipo_transacao_id,
        #     tipo_categoria_financeira_id=tipocategoria_id,
        #     tipo_operacao_financeira_id=tipooperacaofinanceira_id,
        #     colaborador_id=request.user.id,
        #     colaborador_confirmado_id=None,
        #     data_transacao=data_transacao,
        #     data_original_transacao=data_transacao,
        #     valor_transacao=valor_devolver,
        #     dadp="N",
        #     imposto_renda="N",
        #     descricao=descricao_cancelamento,
        #     quantidade_parcelas=1,
        #     recorrencia_id=1,
        #     user_id=request.user.id,
        # )

        # GERAR O CANCELAMENTO e DEVOLUCAO
        item.registrar_cancelar_devolucao(request.user)

        return redirect(Pedido.get_absolute_url(self=item))

    # EXIBIR APENAS OS VALORES PARA LANCAR
    if request.method == "GET":
        # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
        try:
            item = Pedido.objects.get(pk=pk)
            tipooperacaofinanceiras = TipoOperacaoFinanceira.objects.all().order_by(
                "descricao",
            )

            numero_pedido = item.numero_pedido
            observacao = item.observacao
            data_entrada = item.data_entrada
            nome_apresentante = item.apresentante.nome

            # VALORES A RECEBER DO PROTOCOLO E ENVIAR PARA O CAIXA
            valor_atual_pedido_certidao = 0
            valor_total_pago_pedido_certidao = 0
            valor_diferenca = 0

            # VALOR A DEVOLVER
            valor_devolver = valor_atual_pedido_certidao

        except Pedido.DoesNotExist:
            # Handle the case where the object does not exist
            numero_pedido = None
            observacao = None
            data_entrada = None
            nome_apresentante = None
            valor_atual_pedido_certidao = None
            valor_total_pago_pedido_certidao = None
            valor_diferenca = None
            valor_devolver = None

        context = {
            "caption": caption,
            "numero_pedido": numero_pedido,
            "observacao": observacao,
            "data_entrada": data_entrada,
            "nome_apresentante": nome_apresentante,
            "valor_atual_pedido_certidao": valor_atual_pedido_certidao,
            "valor_total_pago_pedido_certidao": valor_total_pago_pedido_certidao,
            "valor_diferenca": valor_diferenca,
            "valor_devolver": valor_devolver,
            "tipooperacaofinanceiras": tipooperacaofinanceiras,
        }

        return render(request, template_name, context)
    return None


class PedidoPartesListView(LoginRequiredMixin, TemplateView):
    template_name = "pedidos/partes/partes_list.html"

    def get_context_data(self, **kwargs):
        # Primeiro, captura o contexto do superclasse
        context = super().get_context_data(**kwargs)

        # Em seguida, executa a lógica específica para encontrar as partes
        pedido_id = self.kwargs.get("pk")
        pedido = get_object_or_404(Pedido, id=pedido_id)
        # atos = Ato.objects.filter(pedido=pedido)
        # participacoes = Participacao.objects.filter(ato__in=atos)
        # partes = Parte.objects.filter(participacao__in=participacoes)

        # Configuração da tabela
        partes_table = PartesTable(pedido.get_partes())
        RequestConfig(self.request, paginate={"per_page": 10}).configure(partes_table)

        # Adiciona a tabela ao contexto
        context["partes_table"] = partes_table
        context["pedido"] = pedido

        return context


class PedidoPartesProtocoloListView(LoginRequiredMixin, TemplateView):
    template_name = "pedidos/partes/partes_list.html"

    def get_context_data(self, **kwargs):
        # Primeiro, captura o contexto do superclasse
        context = super().get_context_data(**kwargs)

        # Em seguida, executa a lógica específica para encontrar as partes
        numero_protocolo = self.kwargs.get("numero_protocolo")

        pedido = Pedido.objects.filter(
            numero_protocolo_firebird=numero_protocolo,
        ).first()

        # pedido = get_object_or_404(Pedido, id=pedido_id)

        # Configuração da tabela
        partes_table = PartesTable(pedido.get_partes())
        RequestConfig(self.request, paginate={"per_page": 10}).configure(partes_table)

        # Adiciona a tabela ao contexto
        context["partes_table"] = partes_table
        context["pedido"] = pedido

        return context


class AtoPartesListView(LoginRequiredMixin, TemplateView):
    template_name = r"pedidos\partes\partes_list.html"

    def get_context_data(self, **kwargs):
        # Primeiro, captura o contexto do superclasse
        context = super().get_context_data(**kwargs)

        # Em seguida, executa a lógica específica para encontrar as partes
        ato_id = self.kwargs.get("pk")
        atos = Ato.objects.get_object_or_404(id=ato_id)
        participacoes = Participacao.objects.filter(ato__in=atos)
        partes = Parte.objects.filter(participacao__in=participacoes)

        # Configuração da tabela
        partes_table = PartesTable(partes)
        RequestConfig(self.request, paginate={"per_page": 10}).configure(partes_table)

        # Adiciona a tabela ao contexto
        context["partes_table"] = partes_table
        # context["pedido"] = pedido

        return context


class ParteDetailView(LoginRequiredMixin, DetailView):
    model = Parte
    template_name = "pedidos/partes/partes_detalhes.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)


class ParteUpdateView(LoginRequiredMixin, UpdateView):
    model = Parte
    form_class = ParteForm
    template_name = "pedidos/partes/parte_update.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["show_save_and_add_another"] = False
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        parte = self.object
        url = parte.get_ato_url()
        return url or parte.get_absolute_url()

    def get_queryset(self):
        return Parte.objects.filter(id=self.kwargs["pk"])


class ParteDeleteView(DeleteView):
    model = Parte
    template_name = "pedidos/parte_confirm_delete.html"

    def get_success_url(self):
        pedido_id = self.object.pedido_id
        return reverse("pedidos:pedido_detail", args=[pedido_id])


class ProtocoloCreateView(LoginRequiredMixin, CreateView):
    model = Ato
    form_class = PedidoForm
    template_name = "pedidos/ato_form.html"
    rota = ""
    args = []

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "imovel_id" in self.kwargs:
            kwargs["tipo_item_ato_nome_list"] = ["Padrão", "Imóvel"]
        elif "parte_id" in self.kwargs:
            kwargs["tipo_item_ato_nome_list"] = ["Padrão", "Parte"]
        else:
            # Você pode definir um valor padrão ou levantar um erro, dependendo do que faz sentido para sua aplicação
            kwargs["tipo_item_ato_nome_list"] = ["Padrão"]
        return kwargs

    def form_valid(self, form):
        imovel = (
            Imovel.objects.get(pk=self.kwargs["imovel_id"])
            if "imovel_id" in self.kwargs
            else None
        )
        parte = (
            Parte.objects.get(pk=self.kwargs["parte_id"])
            if "parte_id" in self.kwargs
            else None
        )

        quantidade = 1

        # Pegue a instância de ato_praticavel do formulário
        ato_praticavel_instance = form.cleaned_data.get("ato_praticavel")

        for _ in range(quantidade):
            Ato.objects.create(
                ato_praticavel=ato_praticavel_instance,
                imovel=imovel,
                parte=parte,
            )

        self.rota = "pedidos:imovel_update" if imovel else "pedidos:alterar_parte"

        return super().form_valid(form)

    def get_success_url(self):
        if "imovel_id" in self.kwargs:
            return reverse("pedidos:imovel_update", args=[self.kwargs["imovel_id"]])
        elif "parte_id" in self.kwargs:
            return reverse("pedidos:alterar_parte", args=[self.kwargs["parte_id"]])
        return None


class ProtocolosParteListView(SingleTableMixin, ListView):
    model = Ato
    template_name = "pedidos/listar.html"
    table_class = ProtocoloTable
    table_pagination = {"per_page": 10}
    extra_context = {
        "title": "Imóveis do Pedido",
        "parent": "Pedidos",
        "segment": "atos",
    }

    def get_queryset(self):
        parte_id = self.kwargs["parte_id"]
        partes = Parte.objects.filter(pk=parte_id)
        return Ato.objects.filter(partes__in=partes)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        parte_id = self.kwargs["parte_id"]
        parte = Parte.objects.filter(pk=parte_id).first()

        url_retorno = self.request.GET.get(
            "next",
            reverse("pedidos:pedido_detail", args=[parte.pedido_id]),
        )

        context.update(
            {
                "botoes": {
                    "adicionar": {
                        "url": reverse("pedidos:adicionar_ato_parte", args=[parte_id]),
                        "label": "Adicionar",
                        "class": "btn-primary",
                    },
                    "voltar": {
                        "url": url_retorno,
                        "label": "Voltar ao Pedido",
                        "class": "btn-secondary",
                    },
                },
            },
        )

        return context


class ProtocolosImovelListView(SingleTableMixin, ListView):
    model = Ato
    template_name = "pedidos/listar.html"
    table_class = ProtocoloTable
    table_pagination = {"per_page": 10}
    extra_context = {
        "title": "Imóveis do Pedido",
        "parent": "pedidos",
        "segment": "pedidos",
    }

    def get_queryset(self):
        imovel_id = self.kwargs["imovel_id"]
        imovel = Imovel.objects.filter(pk=imovel_id).first()
        return Ato.objects.filter(imovel=imovel)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        imovel_id = self.kwargs["imovel_id"]
        imovel = Imovel.objects.filter(pk=imovel_id).first()

        url_retorno = self.request.GET.get(
            "next",
            reverse("pedidos:pedido_detail", args=[imovel.pedido_id]),
        )

        context.update(
            {
                "botoes": {
                    "adicionar": {
                        "url": reverse("pedidos:ato_create", args=[imovel_id]),
                        "label": "Adicionar",
                        "class": "btn-primary",
                    },
                    "voltar": {
                        "url": url_retorno,
                        "label": "Voltar ao Pedido",
                        "class": "btn-secondary",
                    },
                },
            },
        )

        return context


class ProtocoloListView(SingleTableMixin, LoginRequiredMixin, ListView):
    model = Ato
    table_class = ProtocoloTable
    template_name = "pedidos/listar.html"
    table_pagination = {"per_page": 10}
    context_object_name = "atos"  # nome da variável no template

    def get_queryset(self):
        return Ato.objects.filter(pedido_id=self.kwargs["pedido_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        RequestConfig(self.request).configure(self.table)
        context["parent"] = "Pedidos"
        context["segment"] = "pedidos"

        return context


class ProtocoloDeleteView(LoginRequiredMixin, DeleteView):
    model = Ato
    template_name = "pedidos/confirm_delete.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Ato, pk=self.kwargs.get("pk"))

    def get_success_url(self):
        ato = self.get_object()
        if ato.imovel:
            return reverse(
                "pedidos:imovel_update",
                args=[ato.imovel.pedido.pk, ato.imovel.pk],
            )
        elif ato.parte:
            return reverse(
                "pedidos:alterar_parte",
                args=[ato.parte.pedido.pk, ato.parte.pk],
            )
        else:
            return reverse("pedidos:index")


class ProtocoloPrintView(LoginRequiredMixin, TemplateView):
    template_name = "pedidos/impressao/ato_print.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ato = get_object_or_404(Ato, pk=self.kwargs.get("pk"))
        context["ato"] = ato
        return context


# class SeloCreateView(View):
#     def get(self, request, pedido_id):
#         form = SeloForm()
#         return render(request, "selo_form.html", {"form": form})

#     def post(self, request, pedido_id):
#         form = SeloForm(request.POST)
#         if form.is_valid():
#             selo = form.save(commit=False)
#             selo.pedido = get_object_or_404(Pedido, id=pedido_id)
#             selo.save()
#             return redirect("pedidos:pedido_detail", pedido_id)
#         return render(request, "selo_form.html", {"form": form})


# class SeloUpdateView(View):
#     def get(self, request, pedido_id, selo_id):
#         selo = get_object_or_404(Selo, id=selo_id, pedido__id=pedido_id)
#         form = SeloForm(instance=selo)
#         return render(request, "selo_form.html", {"form": form})

#     def post(self, request, pedido_id, selo_id):
#         selo = get_object_or_404(Selo, id=selo_id, pedido__id=pedido_id)
#         form = SeloForm(request.POST, instance=selo)
#         if form.is_valid():
#             form.save()
#             return redirect("pedidos:pedido_detail", pedido_id)
#         return render(request, "selo_form.html", {"form": form})


def salvar_atos(form, pedido_id):
    """Função para salvar as instâncias de Ato e retornar uma lista de atos criados."""
    atos_criados = []
    with transaction.atomic():
        instancias = form.save(commit=False)
        for ato in instancias:
            ato.pedido_id = pedido_id
            ato.save()
            atos_criados.append(ato)
    return atos_criados


def determinar_redirecionamento(action, pedido_id, ato):
    """Função para determinar o redirecionamento com base na ação especificada."""
    if action == "save_and_add_another":
        return redirect("pedidos:ato_create", pedido_id=pedido_id)
    elif action == "save_and_add_complementar":
        return redirect(
            "pedidos:ato_complementar_create",
            pedido_id=pedido_id,
            pk=ato.pk if ato else None,
        )
    return None


@login_required
def ato_create(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == "POST":
        form = AtoForm(request.POST, pedido_id=pedido_id)

        if form.is_valid():
            atos_criados = salvar_atos(form, pedido_id)
            ato = atos_criados[0] if atos_criados else None

            # Determina o redirecionamento com base na ação do formulário
            action = request.POST.get("action")
            redirecionamento = determinar_redirecionamento(action, pedido_id, ato)
            if redirecionamento:
                return redirecionamento

            # Define a URL de sucesso
            if atos_criados:
                success_url = reverse("pedidos:ato_detail", args=[ato.pk])
            else:
                success_url = reverse("url_de_fallback")

            return redirect(success_url)
    else:
        form = AtoForm(pedido_id=pedido_id)

    # Define a URL de retorno com base no número de protocolo
    if pedido.numero_protocolo_firebird:
        url_retorno = reverse_lazy(
            "home:abrir_livro01_por_numero_protocolo",
            args=[pedido.numero_protocolo_firebird],
        )
    else:
        url_retorno = reverse_lazy("pedidos:pedido_detail", args=[pedido_id])

    context = {
        "form": form,
        "pedido": pedido,
        "url_retorno": url_retorno,
    }

    return render(request, "pedidos/ato/ato_form.html", context)


class AtosListView(LoginRequiredMixin, SingleTableMixin, ListView):
    model = Ato
    template_name = "pedidos/ato/atos_listar.html"
    table_class = AtosTable
    table_pagination = {"per_page": 10}

    def get_queryset(self):
        pedido_id = self.kwargs["pedido_id"]
        return Ato.objects.get_atos_principais(pedido_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_id = self.kwargs["pedido_id"]
        pedido = Pedido.objects.get(id=pedido_id)

        # context["grupos_atos_principais"] = Ato.objects.get_atos_principais_agrupados(pedido_id)
        context["atos_com_complementares"] = Ato.objects.get_atos_com_complementares(
            pedido_id,
        )
        context["atos_orfaos"] = Ato.objects.get_atos_orfaos(pedido_id)
        context["pedido"] = pedido
        context["url_retorno_pedido"] = pedido.get_absolute_url()

        return context


@login_required
def listar_atos_por_numero_protocolo(request, numero_protocolo):
    # Busca o pedido pelo número de protocolo
    pedido = Pedido.objects.filter(numero_protocolo_firebird=numero_protocolo).first()

    if pedido:
        # Obtém os atos principais relacionados ao pedido
        atos_principais = Ato.objects.get_atos_principais(pedido.id)
    else:
        print("Importar para PEDIDO.....")
        atos_principais = None

    # Contexto para o template
    context = {}
    if pedido:
        pedido = get_object_or_404(Pedido, id=pedido.id)
        context["atos_com_complementares"] = Ato.objects.get_atos_com_complementares(
            pedido.id,
        )
        context["atos_orfaos"] = Ato.objects.get_atos_orfaos(pedido.id)
        context["pedido"] = pedido
        context["url_retorno_pedido"] = pedido.get_absolute_url()
        context["contador_inicial"] = 1
    else:
        context = None

    # Renderiza o template com o contexto
    return render(
        request,
        "pedidos/ato/atos_listar.html",
        {
            "object_list": atos_principais,
            **context,
        },
    )


@login_required
def ato_detail_view(request, pk):
    try:
        ato = get_object_or_404(Ato, pk=pk)

        # Obter atos complementares agrupados por ato
        try:
            grupo = Ato.get_complementares_agrupados_por_ato(ato)
            atos_complementares_agrupados_table = AtosComplementaresAgrupadosTable(
                grupo,
            )
        except Exception as e:
            messages.error(
                request,
                "Erro ao carregar atos complementares agrupados. Por favor, tente novamente mais tarde.",
            )
            atos_complementares_agrupados_table = None
            # Log do erro (opcional)
            print(f"Erro ao carregar atos complementares agrupados: {e}")

        # Obter participações relacionadas a este Ato
        try:
            participacoes = Participacao.objects.filter(ato__id=pk)
            participacao_table = ParticipacaoTable(participacoes)
        except Exception as e:
            messages.error(
                request,
                "Erro ao carregar as participações. Por favor, tente novamente mais tarde.",
            )
            participacao_table = None
            # Log do erro (opcional)
            print(f"Erro ao carregar participações: {e}")

        context = {
            "ato": ato,
            "participacao_table": participacao_table,
            "atos_complementares_agrupados_table": atos_complementares_agrupados_table,
        }

    except Exception as e:
        messages.error(
            request,
            "Erro ao carregar os detalhes do ato. Por favor, tente novamente mais tarde.",
        )
        context = {
            "ato": None,
            "participacao_table": None,
            "atos_complementares_agrupados_table": None,
        }
        # Log do erro (opcional)
        print(f"Erro ao carregar os detalhes do ato: {e}")

    return render(request, "pedidos/ato/ato_detail.html", context)


@login_required
def ato_update_view(request, pk):
    """Exibe e processa o formulário de atualização de um ato no pedido de protocolo."""
    ato = get_object_or_404(Ato, pk=pk)

    if request.method == "POST":
        form = AtoForm(request.POST, instance=ato)
        if form.is_valid():
            form.save()
            if "save_and_next" in request.POST:
                # Busca o próximo ato na lista incluindo o ato atual
                # todos_atos = list(Ato.objects.filter(pedido=ato.pedido).order_by("id"))
                todos_atos = list(
                    Ato.objects.filter(pedido=ato.pedido).order_by(
                        "ato_praticavel__ordem_do_grupo",
                        "ordem_do_lancamento",
                    ),
                )

                for i, outro_ato in enumerate(todos_atos):
                    if outro_ato.pk == ato.pk and i + 1 < len(todos_atos):
                        return redirect(
                            reverse_lazy(
                                "pedidos:ato_update",
                                args=[todos_atos[i + 1].pk],
                            ),
                        )
                return redirect(
                    reverse_lazy("pedidos:pedido_detail", args=[ato.pedido.pk]),
                )
            else:
                return redirect(
                    reverse_lazy("pedidos:pedido_detail", args=[ato.pedido.pk]),
                )
    else:
        form = AtoForm(instance=ato)

    pedido = ato.pedido
    agrupados_por_pedido = Ato.get_complementares_agrupados_por_pedido(pedido)
    atos_complementares_agrupados_table = AtosComplementaresAgrupadosTable(
        agrupados_por_pedido,
    )

    # Inclui o ato atual na lista de atos relacionados ao pedido
    # todos_atos = Ato.objects.filter(pedido=pedido).order_by("id")
    todos_atos = Ato.objects.filter(pedido=pedido).order_by(
        "ato_praticavel__ordem_do_grupo",
        "ordem_do_lancamento",
    )

    if pedido.numero_protocolo_firebird:
        url_retorno = reverse_lazy(
            "home:abrir_livro01_por_numero_protocolo",
            args=[pedido.numero_protocolo_firebird],
        )
    else:
        url_retorno = reverse_lazy("pedidos:pedido_detail", args=[pedido.pk])

    # url_todos_atos = href="{% url 'pedidos:atos_list' pedido_id=pedido.pk %}">
    url_todos_atos = reverse_lazy("pedidos:atos_list", args=[pedido.pk])

    context = {
        "ato": ato,
        "form": form,
        "pedido": pedido,
        "atos_complementares_agrupados_table": atos_complementares_agrupados_table,
        "todos_atos": todos_atos,
        "url_retorno": url_retorno,
        "url_todos_atos": url_todos_atos,
    }
    return render(request, "pedidos/ato/ato_form.html", context)


# função utilitária que duplica qualquer instância de modelo Django.
def duplicar_objeto(
    model_instance,
    lista_campos_excluidos,
    coluna_01_atualizar,
    valor_01_atualizar,
):
    """Duplica uma instância de modelo Django e retorna a nova instância."""
    # Cria um dicionário com os dados do objeto, excluindo campos específicos
    instance_dict = model_to_dict(
        model_instance,
        exclude=lista_campos_excluidos,
    )

    # Mapeia campos de relacionamento para garantir que instâncias sejam atribuídas
    for field in model_instance._meta.get_fields():
        if (field.one_to_one or field.many_to_one) and field.name in instance_dict:
            instance_dict[field.name] = getattr(model_instance, field.name)

    # Cria uma nova instância do mesmo tipo
    new_instance = model_instance.__class__(**instance_dict)
    new_instance.criado_em = (
        timezone.now()
    )  # Atualiza o campo 'criado_em' se necessário

    # Atualiza o campo especificado se ele existir na nova instância
    # EXISTE UM BUG AQUI, POIS O CAMPO PODE NÃO EXISTIR NA INSTÂNCIA
    if coluna_01_atualizar and hasattr(new_instance, coluna_01_atualizar):
        setattr(new_instance, coluna_01_atualizar, valor_01_atualizar)

    new_instance.save()

    return new_instance


@login_required
def duplicar_ato_protocolo_quantidade(request, pk):
    return render(request, "importacao/duplicar_item_do_protocolo.html", {"pk": pk})


# DUPLICAR O ATO SELECIONADO
def duplicar_ato_protocolo(request, pk):
    ato = get_object_or_404(Ato, pk=pk)

    # Verifica se o método da solicitação é POST
    if request.method == "POST":
        quantidade = request.POST.get("quantidade_duplicar")
        total_duplicar = int(quantidade) + 1

        # Verifica se a quantidade é um número inteiro
        for _ in range(1, total_duplicar):
            novo_ato = duplicar_objeto(
                model_instance=ato,
                lista_campos_excluidos=[
                    "id",
                    "criado_em",
                    "data_modificacao",
                    "id_sequencial",
                    "numero_pedido",
                    "numero_onr",
                ],
                coluna_01_atualizar=None,
                valor_01_atualizar=None,
            )

        return redirect("pedidos:ato_detail", pk=novo_ato.pk)

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


class AtoDeleteView(generic.DeleteView):
    model = Ato
    template_name = "pedidos/ato/ato_excluir.html"

    def get_success_url(self):
        return self.object.get_listar_url()


@login_required
def ato_complementar_create(
    request: HttpRequest,
    pedido_id: int,
    ato_id: int | None = None,
) -> HttpResponse:
    try:
        if request.method == "POST":
            logger.debug("Recebida solicitação POST para criar ato complementar.")
            form = AtoComplementarForm(request.POST, pedido_id=pedido_id, ato_id=ato_id)

            if form.is_valid():
                logger.debug(
                    "Formulário válido. Processando dados para salvar os atos complementares.",
                )
                atos_complementares = form.save(commit=False)

                for ato_complementar in atos_complementares:
                    ato_complementar.pedido_id = pedido_id
                    if ato_id:
                        ato_complementar.ato_id = ato_id
                    ato_complementar.save()
                    logger.info(
                        f"Ato complementar salvo com sucesso: {ato_complementar.id}",
                    )

                messages.success(request, "Atos complementares salvos com sucesso.")
                return redirect(reverse("pedidos:atos_list", args=[pedido_id]))
            else:
                logger.warning("Formulário inválido. Retornando erros ao usuário.")
                messages.error(
                    request,
                    "Erro ao salvar atos complementares. Verifique o formulário e tente novamente.",
                )
        else:
            logger.debug(
                "Recebida solicitação GET para exibir o formulário de criação de ato complementar.",
            )
            form = AtoComplementarForm(pedido_id=pedido_id, ato_id=ato_id)

        context = {"form": form}
        if ato_id:
            context["ato"] = get_object_or_404(Ato, id=ato_id)
            logger.debug(f"Ato carregado para contexto: {ato_id}")

        return render(
            request,
            "pedidos/atos_complementares/ato_complementar_create.html",
            context,
        )
    except Exception as e:
        logger.exception(
            f"Erro inesperado ao processar a criação de ato complementar: {e}",
        )
        messages.error(
            request,
            "Ocorreu um erro inesperado. Tente novamente mais tarde.",
        )
        return redirect(reverse("pedidos:atos_list", args=[pedido_id]))


class AtoComplementarDetailView(DetailView):
    model = Ato
    template_name = "pedidos/atos_complementares/ato_complementar_detail.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)


class AtoComplementarDeleteView(generic.DeleteView):
    model = Ato
    template_name = "pedidos/atos_complementares/ato_complementar_excluir.html"

    def get_success_url(self):
        return self.object.get_listar_url()

@login_required
def ato_participacao_create_view(request, pk=None):
    try:
        ato = None
        if pk:
            ato = get_object_or_404(Ato, pk=pk)

        if request.method == "POST":
            form = ParticipacaoCreateForm(request.POST, ato=ato)
            if form.is_valid():
                try:
                    form.instance.ato = ato
                    participacao = form.save()
                    messages.success(request, "Participação criada com sucesso!")
                    return redirect(participacao.get_parte_update_url())
                except Exception as e:
                    # Captura qualquer exceção durante o salvamento e exibe uma mensagem de erro
                    messages.error(request, f"Erro ao salvar a participação: {e!s}")
            else:
                messages.warning(request, "Por favor, corrija os erros abaixo.")
        else:
            # Inicializa o formulário com o ato
            form = ParticipacaoCreateForm(ato=ato)

        context = {"form": form, "ato": ato}

        return render(
            request,
            "pedidos/participacoes/participacao_create.html",
            context,
        )

    except Http404:
        # Tratamento específico para quando o Ato não é encontrado
        messages.error(request, "Ato não encontrado.")
        return redirect(
            "pedidos:ato_list",
        )  # Redireciona para uma lista de Atos ou outra página apropriada

    except ValidationError as ve:
        # Tratamento de erros de validação
        messages.error(request, f"Erro de validação: {ve.message}")
        return render(
            request,
            "pedidos/participacoes/participacao_create.html",
            {"form": form},
        )

    except Exception as e:
        # Captura qualquer outra exceção e registra uma mensagem de erro
        messages.error(request, f"Ocorreu um erro inesperado: {e!s}")
        return render(
            request,
            "pedidos/participacoes/participacao_create.html",
            {"form": form},
        )


def ato_participacao_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Exibe e processa o formulário de atualização de uma participação no ato."""
    participacao = get_object_or_404(Participacao, pk=pk)

    if request.method == "POST":
        form = ParticipacaoForm(request.POST, instance=participacao)
        form.show_save_and_add_another = False
        if form.is_valid():
            form.save()
            return redirect(participacao.ato.get_absolute_url())
    else:
        form = ParticipacaoForm(instance=participacao)
        form.show_save_and_add_another = False

    return render(
        request,
        "pedidos/participacoes/participacao_update.html",
        {"form": form},
    )


def remove_participacao(request, pk):
    """Remover Participacao no ato."""
    Participacao.objects.get(id=pk).delete()

    " VOLTAR OU FICAR NA MESMA PAGINA"
    return redirect(request.META.get("HTTP_REFERER", "/"))


class ParticipacaoDeleteView(DeleteView):
    template_name = "pedidos/partes/parte_excluir.html"
    form_class = ParticipacaoCreateForm
    success_url = reverse_lazy("alguma-url-de-sucesso")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ParticipacoesListView(ListView):
    model = Participacao
    table_class = ParticipacaoTable
    template_name = "partes_de_ato_list.html"
    context_object_name = "participacoes"

    def get_queryset(self):
        ato_id = self.kwargs.get("ato_id")
        return Participacao.objects.filter(ato__id=ato_id)


def audit_report(request):
    # Filtrar registros de auditoria conforme necessário. Exemplo:
    logs = LogEntry.objects.all().order_by("-timestamp")
    context = {"logs": logs}
    return render(request, "auditorias/audit_report.html", context)


def test_view(request):
    return HttpResponse("A requisição chegou até a view de teste!")


# Views para Requerimento
class RequerimentoListView(SingleTableView):
    model = Requerimento
    table_class = RequerimentoTable
    template_name = "requerimentos/requerimento_list.html"
    context_object_name = "requerimentos"


class RequerimentoDetailView(DetailView):
    model = Requerimento
    template_name = "requerimentos/requerimento_detail.html"
    context_object_name = "requerimento"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Captura o parâmetro 'next' da URL
        next_url = self.request.GET.get("next", "")
        context["next_url"] = next_url

        return context


class RequerimentoCreateView(CreateView):
    model = Requerimento
    fields = ["ato_praticavel", "observacao", "obrigatorio", "ativo"]
    template_name = "requerimentos/requerimento_form.html"
    success_url = reverse_lazy("pedidos:requerimentos_list")


class RequerimentoUpdateView(UpdateView):
    model = Requerimento
    form_class = RequerimentoForm
    # fields = ["ato_praticavel", "observacao"]
    template_name = "requerimentos/requerimento_form.html"
    success_url = reverse_lazy("pedidos:requerimentos_list")


class RequerimentoDeleteView(DeleteView):
    model = Requerimento
    template_name = "requerimentos/requerimento_confirm_delete.html"
    success_url = reverse_lazy("pedidos:requerimentos_list")


class RequerimentoPrintView(LoginRequiredMixin, TemplateView):
    template_name = "requerimentos/requerimento_print.html"

    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)
        requerimento = get_object_or_404(Requerimento, pk=self.kwargs.get("pk"))

        return {
            "agora": timezone.now().date(),
            "requerimento": requerimento,
            "titulo": requerimento,
        }


class RequerimentoPedidoPrintView(LoginRequiredMixin, TemplateView):
    template_name = "requerimentos/requerimento_inicial_print.html"

    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)
        requerimento = get_object_or_404(Requerimento, pk=self.kwargs.get("pk"))

        return {
            "agora": timezone.now().date(),
            "requerimento": requerimento,
            "titulo": requerimento,
            "pedido_id": self.kwargs.get("pedido_id"),
        }


# Views para DocumentoParaRequerimento
class DocumentoParaRequerimentoListView(SingleTableView):
    model = DocumentoParaRequerimento
    table_class = DocumentoParaRequerimentoTable
    template_name = "documentos/documento_list.html"
    context_object_name = "documentos"

    def get_queryset(self):
        return DocumentoParaRequerimento.objects.filter(
            requerimento_id=self.kwargs["requerimento_id"],
        )


class DocumentoParaRequerimentoDetailView(DetailView):
    model = DocumentoParaRequerimento
    template_name = "documentos/documento_detail.html"
    context_object_name = "documento"


class DocumentoParaRequerimentoCreateView(CreateView):
    model = DocumentoParaRequerimento
    fields = [
        "nome",
        "requerimento",
        "observacao",
        "orgao_emissor",
        "obrigatorio",
        "justificativa",
        "ativo",
        "imagem",
    ]
    template_name = "documentos/documento_form.html"

    def get_success_url(self):
        return reverse_lazy(
            "pedidos:requerimento_detail",
            kwargs={"pk": self.object.requerimento_id},
        )


class DocumentoParaRequerimentoUpdateView(UpdateView):
    model = DocumentoParaRequerimento
    fields = [
        "nome",
        "requerimento",
        "observacao",
        "orgao_emissor",
        "obrigatorio",
        "justificativa",
        "ativo",
        "imagem",
    ]
    template_name = "documentos/documento_form.html"

    def get_success_url(self: "DocumentoParaRequerimentoUpdateView") -> str:
        return reverse_lazy(
            "pedidos:documentos_para_requerimento_list",
            kwargs={"requerimento_id": self.object.requerimento_id},
        )


class DocumentoParaRequerimentoDeleteView(DeleteView):
    model = DocumentoParaRequerimento
    template_name = "documentos/documento_confirm_delete.html"

    def get_success_url(self: "DocumentoParaRequerimentoDeleteView") -> str:
        return reverse_lazy(
            "pedidos:documentos_para_requerimento_list",
            kwargs={"requerimento_id": self.object.requerimento_id},
        )


class DocumentoParaRequerimentoPrintView(LoginRequiredMixin, TemplateView):
    template_name = "documentos/impressao/documento_print.html"

    def get_context_data(
        self: "DocumentoParaRequerimentoPrintView",
        **kwargs,
    ) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        documento = get_object_or_404(
            DocumentoParaRequerimento,
            pk=self.kwargs.get("pk"),
        )
        context["documento"] = documento
        return context
