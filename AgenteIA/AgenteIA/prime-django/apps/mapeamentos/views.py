# mapeamento/views.py

from django.shortcuts import redirect, render

from apps.mapeamentos.forms import MapeamentoForm
from apps.mapeamentos.models import Mapeamento


def criar_mapeamento(request):
    if request.method == "POST":
        form = MapeamentoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("ver_mapeamentos")
    else:
        form = MapeamentoForm()
    return render(request, "mapeamento/criar_mapeamento.html", {"form": form})


def ver_mapeamentos(request):
    mapeamentos = Mapeamento.objects.all()
    return render(
        request,
        "mapeamento/ver_mapeamentos.html",
        {"mapeamentos": mapeamentos},
    )
