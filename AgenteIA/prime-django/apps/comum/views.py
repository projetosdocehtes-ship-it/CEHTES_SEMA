import logging
import subprocess
from collections import defaultdict
from io import StringIO

import markdown
from django.contrib.auth.decorators import login_required, permission_required
from django.core.management import call_command, get_commands
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, UpdateView

from apps.comum.forms import DadosBancariosForm
from apps.comum.models import DadosBancarios, Instrucao, Municipio

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def get_instrucoes(request, card_id):
    try:
        instrucao = Instrucao.objects.get(card_id=card_id)
        texto_html = markdown.markdown(instrucao.texto)
        return JsonResponse({"instrucoes": texto_html})
    except Instrucao.DoesNotExist:
        return JsonResponse({"instrucoes": "Instruções não disponíveis"})


class CadastrarDadosBancariosView(CreateView):
    model = DadosBancarios
    form_class = DadosBancariosForm
    template_name = "cadastrar_dadosbancarios.html"

    def form_valid(self, form):
        from apps.home.models import Apresentante

        dados_bancarios = form.save()  # Alteração aqui: remova o commit=False
        apresentante = get_object_or_404(
            Apresentante,
            pk=self.kwargs["apresentante_pk"],
        )
        apresentante.dados_bancarios = dados_bancarios
        apresentante.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "home:editar_apresentante",
            kwargs={"pk": self.kwargs["apresentante_pk"]},
        )


class EditarDadosBancariosView(UpdateView):
    model = DadosBancarios
    form_class = DadosBancariosForm
    template_name = "editar_dadosbancarios.html"
    # success_url = reverse_lazy("nome_da_url_onde_voce_quer_redirecionar")


class ExcluirDadosBancariosView(DeleteView):
    model = DadosBancarios
    template_name = "confirmar_exclusao.html"
    # success_url = reverse_lazy("nome_da_url_onde_voce_quer_redirecionar")


@login_required
@permission_required("admin.can_run_commands", raise_exception=True)
def deploy_view(request):
    if request.method == "POST":
        # Execute o comando desejado
        result = subprocess.run(
            ["seu_comando", "argumentos"],
            stdout=subprocess.PIPE,
            check=False,
        )
        return HttpResponse(result.stdout, content_type="text/plain")
    else:
        return HttpResponse("Método não permitido", status=405)


# views.py


def command_list_view(request):
    message = ""
    if request.method == "POST":
        command_name = request.POST.get("command")
        # Obtem o parâmetro, ou None se não existir
        param = request.POST.get("param", None)

        if command_name in get_commands():
            out = StringIO()
            try:
                if param:  # Se um parâmetro foi fornecido, passa ele para o comando
                    call_command(command_name, param, stdout=out)
                else:  # Caso contrário, chama o comando sem parâmetros
                    call_command(command_name, stdout=out)
                message = out.getvalue()
            except Exception as e:
                message = f"ERRO ao executar o comando: {e}"
        else:
            message = "Comando não encontrado"

    # Agrupa commands por app
    commands_by_app = defaultdict(list)
    for command_name, app in get_commands().items():
        commands_by_app[app].append(command_name)

    # Ordena os comandos para cada app
    for app in commands_by_app:
        commands_by_app[app].sort()

    return render(
        request,
        "command_list.html",
        {"commands_by_app": dict(commands_by_app), "message": message},
    )


def busca_municipios_ajax(request):
    termo = request.GET.get("term")
    municipios = Municipio.objects.filter(nome__icontains=termo)[
        :10
    ]  # limitar os resultados
    resultados = [{"id": m.id, "text": m.nome} for m in municipios]
    return JsonResponse({"results": resultados})
