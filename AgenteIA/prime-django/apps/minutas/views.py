from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.minutas.forms import MinutaForm
from apps.minutas.models import Minuta


class MinutaCreateView(CreateView):
    model = Minuta
    form_class = MinutaForm
    template_name = "minuta_form.html"


class MinutaListView(ListView):
    model = Minuta
    template_name = "minuta_list.html"
    context_object_name = "minutas"


class MinutaDetailView(DetailView):
    model = Minuta
    template_name = "minuta_detail.html"


class MinutaUpdateView(UpdateView):
    model = Minuta
    form_class = MinutaForm
    template_name = "minuta_form.html"


class MinutaDeleteView(DeleteView):
    model = Minuta
    template_name = "minuta_confirm_delete.html"
    success_url = reverse_lazy("minuta_list")
