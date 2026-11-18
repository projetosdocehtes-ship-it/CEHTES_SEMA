from django.shortcuts import get_object_or_404, redirect, render

from apps.senhas.models import Senha


def gerar_senha(request):
    if request.method == "POST":
        ultimo_numero = Senha.objects.filter(tipo_atendimento="Geral").count() + 1
        senha = Senha.objects.create(numero=ultimo_numero, tipo_atendimento="Geral")
        return redirect("atendimento:detalhe_senha", senha_id=senha.id)
    return render(request, "atendimento/gerar_senha.html")


def detalhe_senha(request, senha_id: int):
    # Obter a senha pelo ID, retornando 404 se não for encontrada
    senha = get_object_or_404(Senha, id=senha_id)

    # Renderizar o template com os detalhes da senha
    return render(request, "atendimento/detalhe_senha.html", {"senha": senha})
