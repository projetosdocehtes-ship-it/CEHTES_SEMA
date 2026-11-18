# Create your views here.
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.encoding import smart_str

from apps.integracoes.models import PgnmAuditor
from apps.integracoes.utils.Gerar_Livro_4_ONR import gerar_lote_livro_4_onr


def download_file_xml(request, file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb", encoding="utf_8") as f:
            response = HttpResponse(f.read(), content_type="application/xml")
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(
                smart_str(file_path.split("/")[-1]),
            )

        return response
    else:
        return HttpResponse("File not found", status=404)


@login_required
def gerar_pgnm(request, numero_livro="2"):
    from apps.integracoes.utils.Gerar_PGM import get_lista_numeros

    # Definições iniciais com base no número do livro
    tipo_livro = "M" if numero_livro == "2" else "A"
    mensagem_enviado = f"Não existem dados PGNM livro {numero_livro} para enviar"

    # Obtém os números necessários
    list_numero, list_numero_cnm, list_opcao_envio, lista_id_imovel, numero_ri, cns = (
        get_lista_numeros(
            request.user.pk,
            numero_livro,
            tipo_livro,
        )
    )

    # Atualiza o auditor de envio do PGNM
    PgnmAuditor.objects.create(livro=numero_livro)

    if list_numero_cnm:
        from apps.integracoes.utils.Gerar_PGM import gerar_lote_cnm

        messages.success(request, "PGNM gerado ")

        # Geração do lote CNN e resposta
        response = gerar_lote_cnm(
            request=request,
            tipo=tipo_livro,
            livro=numero_livro,
            list_numero=list_numero,
            list_numero_CNM=list_numero_cnm,
            list_opcao_envio=list_opcao_envio,
            imoveis_ids=lista_id_imovel,
            numero_ri=numero_ri,
            cns=cns,
        )
        response = FileResponse(response, content_type="application/xml")
        response["Content-Disposition"] = (
            f'attachment; filename="PGNM_livro_{numero_livro}.xml"'
        )
        return response
    else:
        messages.error(request, mensagem_enviado)
        return HttpResponseRedirect(reverse("home:integracoes"))


@login_required
def gerar_envio_l4(request):
    numero_livro = "4"
    mensagem_enviado = "Não existem dados do livro 4 para enviar"

    # Gerar o envio do livro 4
    response_file = gerar_lote_livro_4_onr(request.user.pk)

    # Atualiza o auditor de envio do PGNM
    PgnmAuditor.objects.create(livro=numero_livro)

    if response_file:
        response = FileResponse(response_file, content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="Envio_livro_4.json"'
        return response
    else:
        messages.error(request, mensagem_enviado)
        return HttpResponseRedirect(reverse("home:integracoes"))
