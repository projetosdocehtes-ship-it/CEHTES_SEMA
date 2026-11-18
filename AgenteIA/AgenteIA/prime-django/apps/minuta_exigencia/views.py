from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, UpdateView, View

from apps.minuta_exigencia.forms import MinutaExigenciaAtoForm, MinutaExigenciaForm
from apps.minuta_exigencia.models import MinutaExigencia, MinutaExigenciaAto


# ADICIONAR UMA NOVA MINUTA DE EXIGENIA.
class MinutaExigenciaCreateView(CreateView):
    model = MinutaExigencia
    form_class = MinutaExigenciaForm
    template_name = "minuta_exigencia/inserir_exigencia_form.html"

    # RETORNAR OS DADOS PARA URL - EXIBIR O TEXTO
    def get_success_url(self):
        # A função reverse é usada aqui em vez de reverse_lazy porque neste ponto
        # o objeto já foi salvo e o self.object é o objeto atualizado.
        return reverse("minuta_exigencia:mensagem_minuta_exigencia_ato")


# EDITAR MINUTA DE EXIGENIA
class MinutaExigenciaUpdateView(UpdateView):
    model = MinutaExigencia
    form_class = MinutaExigenciaForm
    template_name = "minuta_exigencia/edita_exigencia_form.html"

    # DADOS SALVOS COM SUCESSO
    def form_valid(self, form):
        # Seu código para salvar o formulário vai aqui
        response = super().form_valid(form)
        # Adiciona a mensagem após o formulário ser salvo
        messages.success(self.request, "Dados salvos!")
        return response

    # RETORNAR OS DADOS PARA URL
    def get_success_url(self):
        # A função reverse é usada aqui em vez de reverse_lazy porque neste ponto
        # o objeto já foi salvo e o self.object é o objeto atualizado.
        return reverse(
            "minuta_exigencia:editar_minuta_exigencia",
            kwargs={"pk": self.object.pk},
        )


# ADICIONAR UMA NOVA MINUTA DE EXIGENIA.
class MinutaExigenciaAtoCreateView(CreateView):
    model = MinutaExigenciaAto
    form_class = MinutaExigenciaAtoForm
    template_name = "minuta_exigencia/vincular_exigencia_ato_form.html"

    # DADOS SALVOS COM SUCESSO
    def form_valid(self, form):
        # Seu código para salvar o formulário vai aqui
        response = super().form_valid(form)
        # Adiciona a mensagem após o formulário ser salvo
        messages.success(self.request, "Dados salvos!")
        return response

    # RETORNAR OS DADOS PARA URL - EXIBIR O TEXTO
    def get_success_url(self):
        return reverse(
            "minuta_exigencia:editar_minuta_exigencia",
            kwargs={"pk": self.object.minuta},
        )


class DesvincularMinutaExigenciaAtoView(View):
    def get(self, request, uuid):
        template_name = "minuta_exigencia/desvincular_exigencia_ato_form.html"

        minuta_ato = get_object_or_404(MinutaExigenciaAto, id=uuid)
        minuta_ato.delete()
        messages.success(request, "Minuta de exigência desvinculada .")
        return render(request, template_name)


class MinutaExigenciaAtoDeleteView(DeleteView):
    model = MinutaExigenciaAto
    template_name = "minuta_exigencia/remover_exigencia_ato.html"

    # DADOS SALVOS COM SUCESSO
    def form_valid(self, form):
        # Seu código para salvar o formulário vai aqui
        response = super().form_valid(form)
        # Adiciona a mensagem após o formulário ser salvo
        messages.success(self.request, "Dados desvinculados!")
        return response

    # RETORNAR OS DADOS PARA URL - EXIBIR O TEXTO
    def get_success_url(self):
        # A função reverse é usada aqui em vez de reverse_lazy porque neste ponto
        # o objeto já foi salvo e o self.object é o objeto atualizado.
        return reverse("minuta_exigencia:mensagem_minuta_exigencia_ato")


class MensagemMinutaExigenciaAtoView(View):
    def get(self, request):
        template_name = "minuta_exigencia/mensage_exigencia_ato_form.html"
        # messages.success(request, "Minuta de exigência desvinculada .")
        return render(request, template_name)
