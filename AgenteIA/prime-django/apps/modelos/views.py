from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.template import Context, Template
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from apps.modelos.forms import (
    ModeloTextoForm,
)

# Supondo que você criou forms para esses modelos
from apps.modelos.models import Cliente, ModeloTexto


class ModeloTextoListView(ListView):
    model = ModeloTexto
    context_object_name = "modelos_texto"
    template_name = "modelos/modelo_list.html"


class ModeloTextoDetailView(DetailView):
    model = ModeloTexto
    context_object_name = "modelo_texto"
    template_name = "modelos/modelo_detail.html"


class ModeloTextoCreateView(CreateView):
    model = ModeloTexto
    form_class = ModeloTextoForm
    template_name = "modelos/modelo_form.html"


class ModeloTextoUpdateView(UpdateView):
    model = ModeloTexto
    form_class = ModeloTextoForm
    context_object_name = "modelo_texto"
    template_name = "modelos/modelo_form.html"


class ModeloTextoDeleteView(DeleteView):
    model = ModeloTexto
    context_object_name = "modelo_texto"
    success_url = reverse_lazy("modelo_list")
    template_name = "modelos/modelo_confirm_delete.html"


class ClienteListView(ListView):
    model = Cliente
    context_object_name = "clientes"
    template_name = "modelos/cliente_list.html"


def exibir_modelo_para_impressao(request, modelo_id):
    modelo = get_object_or_404(ModeloTexto, pk=modelo_id)

    contexto = {
        "nome_cliente": "João Silva",
        "data_hoje": timezone.now().strftime(settings.DATE_FORMAT_STR),
    }

    template = Template(modelo.conteudo)
    contexto = Context(contexto)

    conteudo_renderizado = template.render(contexto)

    return render(
        request,
        "modelos/modelo_impressao.html",
        {"conteudo_renderizado": conteudo_renderizado},
    )
