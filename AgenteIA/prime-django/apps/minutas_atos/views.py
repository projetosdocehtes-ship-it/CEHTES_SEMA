import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from django.template import Context, Template
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from apps.home.helpers import (
    formatar_codigo_seguranca_mg,
    formatar_protocolo,
    get_data_hoje,
    get_data_hoje_extenso,
)
from apps.home.models import (
    EstadoCivil,
    Livro01Protocolo,
    Livro02,
    Livro03,
    Livro03Garantia,
    PerguntaMinuta,
)
from apps.home.templatetags.home_formatos import formatar_numero_registro_inteiro
from apps.minutas_atos.forms import EstadoCivilForm, MinutaAtoForm, MinutaLigacaoAtoForm
from apps.minutas_atos.models import MinutaLigacaoAto, MinutaModeloAto
from apps.minutas_atos.utils.ler_texto_gerar_audio import falar_texto
from apps.minutas_atos.utils.variaveis_item_pedido import (
    get_imovel_indice_cadastral,
    get_lista_variaveis_temporarias,
    get_qualificado_parte,
    processar_variavel_pessoa_texto,
)


# EDITAR ESTADO CIVIL
class EstadoCivilListView(LoginRequiredMixin, ListView):
    template_name = "minutas_atos/listar_estado_civil.html"
    model = EstadoCivil
    context_object_name = "estado_civil"

    def get_queryset(self):
        # Ordena as estado_civil pelo 'descricao_estado_civil' em ordem descendente
        # Substitua '-descricao_estado_civil' por 'id' ou outro campo conforme necessário
        return EstadoCivil.objects.order_by("descricao_estado_civil")


# EDITAR ESTADO CIVIL
class EstadoCivilUpdateView(LoginRequiredMixin, UpdateView):
    model = EstadoCivil
    form_class = EstadoCivilForm
    template_name = "minutas_atos/edita_estado_civil_form.html"

    # DADOS SALVOS COM SUCESSO
    def form_valid(self, form):
        # Seu código para salvar o formulário vai aqui
        response = super().form_valid(form)
        # Adiciona a mensagem após o formulário ser salvo
        messages.success(self.request, "Dados salvos!")
        return response

    # RETORNAR OS DADOS PARA URL
    def get_success_url(self):
        return reverse(
            "minutas_atos:editar_minuta_estado_civil",
            kwargs={"pk": self.object.pk},
        )


# ADICIONAR UMA NOVA MINUTA DE ATO.
class MinutaAtoCreateView(LoginRequiredMixin, CreateView):
    model = MinutaModeloAto
    form_class = MinutaAtoForm
    template_name = "minutas_atos/inserir_ato_form.html"

    # RETORNAR OS DADOS PARA URL - EXIBIR O TEXTO
    def get_success_url(self):
        # A função reverse é usada aqui em vez de reverse_lazy porque neste ponto
        # o objeto já foi salvo e o self.object é o objeto atualizado.
        return reverse("minutas_atos:mensagem_minuta_ato")


# EDITAR MINUTA DO ATO
class MinutaAtoUpdateView(LoginRequiredMixin, UpdateView):
    model = MinutaModeloAto
    form_class = MinutaAtoForm
    template_name = "minutas_atos/edita_ato_form.html"

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
        return reverse("minutas_atos:editar_minuta_ato", kwargs={"pk": self.object.pk})


# ADICIONAR UMA NOVA MINUTA DO ATO
class MinutaAtoLigacaoCreateView(LoginRequiredMixin, CreateView):
    model = MinutaModeloAto
    form_class = MinutaLigacaoAtoForm
    template_name = "minutas_atos/vincular_ato_form.html"

    # DADOS SALVOS COM SUCESSO
    def form_valid(self, form):
        # Seu código para salvar o formulário vai aqui
        response = super().form_valid(form)
        # Adiciona a mensagem após o formulário ser salvo
        messages.success(self.request, "Dados salvos!")
        return response

    # RETORNAR OS DADOS PARA URL - EXIBIR O TEXTO
    def get_success_url(self):
        # print(self.object.id)
        # print(self.object.ato_id)
        # print(self.object.minuta_id)
        # print(self.object.minuta.id)
        # import time
        # time.sleep(1)

        return reverse(
            "minutas_atos:editar_minuta_ato",
            kwargs={"pk": self.object.minuta.pk},
        )


class DesvincularMinutaAtoView(LoginRequiredMixin, View):
    def get(self, request, uuid):
        template_name = "minutas_atos/desvincular_ato_form.html"
        minuta_ato = get_object_or_404(MinutaModeloAto, id=uuid)
        minuta_ato.delete()
        messages.success(request, "Minuta de ato desvinculada .")
        return render(request, template_name)


class MinutaAtoDeleteView(LoginRequiredMixin, DeleteView):
    model = MinutaLigacaoAto
    template_name = "minutas_atos/remover_ato.html"

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
        return reverse("minutas_atos:mensagem_minuta_ato")


class MensagemMinutaAtoView(LoginRequiredMixin, View):
    def get(self, request):
        template_name = "minutas_atos/mensage_ato_form.html"
        return render(request, template_name)


# Gerar as perguntas para o LIVRO 2 - MINUTAS
def exibir_perguntas_minuta_lv2(
    request,
    pedido_item_id,
    modelo_id,
    lista_perguntas_atuais,
):
    # from apps.pedidos.models import Pedido as PedidoPrime
    from apps.pedidos.models import Ato as AtoPrime

    # Pegando o usuario atual
    current_user = str(request.user).upper()

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = AtoPrime.objects.get(id=pedido_item_id)

    protocolo = Livro01Protocolo.objects.get(
        numero_protocolo=pedido_item.pedido.numero_protocolo_firebird,
    )

    # Selecionar as perguntas do ATO
    perguntas = PerguntaMinuta.objects.filter(corrans__in=lista_perguntas_atuais)

    # CODIGO ATUAL
    codigo_tabela = pedido_item.codigo_emolumento_individual

    # NUMERO DA MATRICULA
    numero_matricula = formatar_numero_registro_inteiro(
        pedido_item.imovel_numero_registro,
    )

    # NUMERO DO ATO
    # numero_ato = pedido_item.tipo_ato + "." + pedido_item.numero_ato
    numero_ato = pedido_item.descricao_tipo_ato

    # LISTAR AS PERGUNTAS NO MODELO
    return render(
        request,
        "minutas_atos/exibir_perguntas_minuta_lv2.html",
        {
            "perguntas_T": perguntas,
            "numero_matricula": str(numero_matricula),
            "ato_praticado": numero_ato,
            "tipo_imovel": pedido_item.imovel_tipo_registro,
            "codigo_tabela": codigo_tabela,
            "numero_ri": pedido_item.imovel_cartorio,
            "numero_ato": numero_ato,
            "current_user": current_user,
            "protocolo": protocolo.numero_protocolo,
            "pedido_item_id": pedido_item_id,
            "perguntas_auxiliares": pedido_item.ato_praticavel,
            "modelo_id": modelo_id,
        },
    )


# PERCORRE O TEXTO PARA VERIFICAR SE EXISTE ALGUMA VARIAVEL TEMPORARIA
def verificar_minutas_temporarias(observacao):
    # Assume que get_lista_variaveis_temporarias() retorna uma lista de strings
    lista = get_lista_variaveis_temporarias()  # Chama a função uma vez

    # Usa compreensão de lista para encontrar todas as variáveis temporárias no texto
    return [item for item in lista if item in observacao]


# RENDERIZAR O TEXTO
def renderizar_conteudo(observacao, contexto):
    template = Template(observacao)
    contexto = Context(contexto)
    return template.render(contexto)


# EXIBIR O MODELO PARA IMPRESSAO
def exibir_modelo_para_impressao(request, modelo_id: uuid, pedido_item_id=0):
    # MODELO DA MINUTA
    modelo = get_object_or_404(MinutaModeloAto, pk=modelo_id)

    # PESQUISAR SE EXISTEM PERGUNTAS TEMPORARIAS PARA O LIVRO 2 A SEREM PREENCHIDAS
    lista_perguntas_atuais = verificar_minutas_temporarias(modelo.observacao)
    if lista_perguntas_atuais:
        return exibir_perguntas_minuta_lv2(
            request,
            pedido_item_id,
            modelo_id,
            lista_perguntas_atuais,
        )
    else:
        return processar_impressao(request, pedido_item_id, modelo_id, [], [])


# CAPTURA AS PERGUNTAS NA TELA
def imprimir_respostas_tela(request, pedido_item_id, modelo_id):
    variaveis, respostas = [], []

    if request.method == "POST":
        # OBTER TODAS AS PERGUNTAS DO FORMULARIO
        selected_options = [
            (key, value)
            for key, value in request.POST.items()
            if key != "csrfmiddlewaretoken"
        ]

        """
            VERIFICAR SE E UMA PERGUNTA TEMPORARIA - TRAS O ID DA PERGUNTA E VERIFICO NO BANCO DE DADOS O NOME DA VARIAVEL
            ESTANDO CORRETO PROCESSO O REPLACE NO TEXTO
        """
        for opcao in selected_options:
            # VERIFICAR SE O ID E UM NUMERO
            if str(opcao[0]).isdigit():
                variavel = PerguntaMinuta.objects.get(id=opcao[0])

                # SE ENCONTROU A VARIAVEL NO BANCO DE DADOS FAZ O REPLACE NO TEXTO
                if variavel.corrans:
                    variaveis.append(str(variavel.corrans))
                    respostas.append(str(opcao[1]))

    # RETORNAR OS DADOS PARA URL - EXIBIR O TEXTO
    return processar_impressao(request, pedido_item_id, modelo_id, variaveis, respostas)


# EXIBIR O MODELO PARA IMPRESSAO
def processar_impressao(request, pedido_item_id, modelo_id, variaveis, respostas):
    from apps.pedidos.models import Ato as AtoPrime

    # MODELO DA MINUTA
    modelo = get_object_or_404(MinutaModeloAto, pk=modelo_id)

    # SELECIONAR AS CHAVES PELO PEDIDOS ITENS
    pedido_item = AtoPrime.objects.get(id=pedido_item_id)

    # SUBSTITUIR AS VARIAVEIS TEMPORARIAS PELO VALOR
    for variavel in variaveis:
        modelo.observacao = modelo.observacao.replace(
            variavel,
            respostas[variaveis.index(variavel)],
        )

    # QUALIFICACAO DA PESSOA - (A=Adquirente, T=Transmitente, P=Proprietário)
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_adquirente }}",
        get_qualificado_parte(pedido_item.pk, opcao="1"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_transmitente }}",
        get_qualificado_parte(pedido_item.pk, opcao="2"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_proprietario }}",
        get_qualificado_parte(pedido_item.pk, opcao="1"),
    )

    # QUALIFICACAO DA PESSOA - (A=Credor, T=Devedor, P=Avalista)
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_credor }}",
        get_qualificado_parte(pedido_item.pk, opcao="4"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_devedor }}",
        get_qualificado_parte(pedido_item.pk, opcao="3"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_devedor }}",
        get_qualificado_parte(pedido_item.pk, opcao="3"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_avalista }}",
        get_qualificado_parte(pedido_item.pk, opcao="11"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_anuente }}",
        get_qualificado_parte(pedido_item.pk, opcao="7"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_fiel_depositario }}",
        get_qualificado_parte(pedido_item.pk, opcao="5"),
    )
    modelo.observacao = modelo.observacao.replace(
        "{{ qualificacao_emitente_depositario }}",
        get_qualificado_parte(pedido_item.pk, opcao="8"),
    )

    try:
        livro03 = Livro03.objects.get_registro_auxiliar_por_pedido_item(pedido_item)
    except:
        livro03 = None

    if livro03:
        imovel = livro03.imovel
    # elif pedido_item.numero_registro:
    #    imovel = Livro02.objects.get_pelo_pedido_item(pedido_item)
    else:
        imovel = None

    # OBTER OS DADOS DO REGISTRO ANTERIOR
    modelo.observacao = (
        processar_variavel_pessoa_texto(imovel.registros_anteriores, modelo.observacao)
        if imovel
        else modelo.observacao
    )

    # OBTER OS DADOS DO INDICE CADASTRAL
    indice_cadastral = get_imovel_indice_cadastral(imovel) if imovel else ""
    modelo.observacao = (
        processar_variavel_pessoa_texto(indice_cadastral, modelo.observacao)
        if indice_cadastral
        else modelo.observacao
    )

    # Obter os dados do registro auxiliar
    # PEGANDO OS DADOS DAS GARANTIAS
    garantias = (
        Livro03Garantia.objects.filter(registro_auxiliar_id=livro03.id)
        if livro03
        else []
    )

    print("OBTER DADOS DO LIVRO 3")

    (
        Livro03Garantia.objects.get_numero_matricula_garantia_l3_individual(garantias)
        if garantias
        else ""
    )

    (
        Livro03Garantia.objects.get_local_emissao_cedula_l3_individual(
            garantias,
        )
        if garantias
        else ""
    )

    # OBTER O VALOR INDIVIDUAL DAS GARANTIAS
    (
        Livro03Garantia.objects.get_valor_garantia_l3_individual_str(
            garantias,
        )
        if garantias
        else ""
    )

    # OBTER O VALOR INDIVIDUAL DAS GARANTIAS
    (
        Livro03Garantia.objects.get_descricao_garantia_l3_individual(garantias)
        if garantias
        else ""
    )

    # OBTER O NUMERO DE ATO ANTERIOR AO ATUAL DO TEXTO
    # numero_ato_anterior_atual = PedidoItem.objects.get_numero_ato_anterior(
    #     pedido_item,
    # )

    protocolo = Livro01Protocolo.objects.get(
        numero_protocolo=pedido_item.pedido.numero_protocolo_firebird,
    )

    # TIPO DO ATO E NUMERO DO ATO
    # tipo_ato = pedido_item.tipo_ato if pedido_item.tipo_ato else ""
    # numero_ato = pedido_item.numero_ato if pedido_item.numero_ato else ""
    # numero_ato = tipo_ato + "." + numero_ato
    numero_ato = pedido_item.descricao_tipo_ato

    # FORMATAR O NUMERO DO LIVRO 2
    numero_livro_2 = (
        pedido_item.imovel_numero_registro if pedido_item.imovel_numero_registro else ""
    )
    if numero_livro_2:
        numero_livro_2 = formatar_numero_registro_inteiro(numero_livro_2)

    # GERAR O CONTEXTO PARA SUBSTITUIR AS VARIAVEIS TEMPORARIAS PELO VALOR
    contexto = {
        "codigo_de_seguranca": formatar_codigo_seguranca_mg(
            pedido_item.pedido.codigo_seguranca_firebird,
            "." if pedido_item.pedido.codigo_seguranca_firebird else "",
        ),
        "utilizado_em": "",
        #     (
        #     pedido_item.selo_do_pedido_item.first().data_selo_formatada
        #     if pedido_item.selo_do_pedido_item.first()
        #     else ""
        # ),
        "data_selo_extenso": "",
        # (
        #     pedido_item.selo_do_pedido_item.first().data_selo_extenso
        #     if pedido_item.selo_do_pedido_item.first()
        #     else ""
        # ),
        "numero_selo": (
            pedido_item.pedido.numero_selo_firebird
            if pedido_item.pedido.numero_selo_firebird
            else ""
        ),
        "numero_ato": numero_ato,
        "tipo_imovel_livro2": (
            pedido_item.imovel_tipo_registro_sigla
            if pedido_item.imovel_tipo_registro_sigla
            else ""
        ),
        "numero_imovel_livro2": numero_livro_2,
        "numero_protocolo": formatar_protocolo(protocolo.numero_protocolo),
        "data_protocolo": protocolo.data_protocolo_formatada,
        "data_hoje": get_data_hoje(settings.DATE_FORMAT_STR),
        "data_hoje_extenso": get_data_hoje_extenso(settings.DATE_FORMAT_STR),
        "valor_avaliacao": (
            pedido_item.valor_avaliacao if pedido_item.valor_avaliacao else ""
        ),
        "valor_itbi": (pedido_item.valor_titulo if pedido_item.valor_titulo else ""),
        "valor_emolumento": pedido_item.valor_emolumento
        if pedido_item.valor_emolumento
        else 0,
        "taxa_judiciaria": pedido_item.valor_tfj if pedido_item.valor_tfj else 0,
        "recompe": pedido_item.valor_fundo_estado
        if pedido_item.valor_fundo_estado
        else 0,
        "issqn": pedido_item.valor_issqn if pedido_item.valor_issqn else 0,
        "total_item": pedido_item.valor_total if pedido_item.valor_total else 0,
        "cidade": request.user.cartorio.municipio,
        "estado": request.user.cartorio.municipio.uf.sigla,
        "nome_oficial": request.user.cartorio.responsavel,
        "login_atual": request.user.first_name,
        "data_emissao_cedula_l3": "",
        # livro03.data_emissao_cedula if livro03 else "",
        "numero_cedula_l3": "",
        # livro03.numero_cedula_formatado if livro03 else "",
        "data_vencimento_cedula_l3": "",
        # (
        #     livro03.data_vencimento_cedula_l3 if livro03 else ""
        # ),
        "local_emissao_cedula_l3": "",
        # local_emissao_cedula_l3_individual_str,
        "destinacao_finalidade_l3": "",
        # livro03.descricao if livro03 else "",
        "valor_garantia_l3_individual": "",
        # Livro03Garantia.objects.get_valor_garantia_l3_individual_str(
        #     garantias,
        # ),
        "descricao_garantia": "",
        # descricao_garantia,
        "numero_matricula_garantia": "",
        # numero_matricula_garantia,
        "somente_valor_garantia_l3": "",
        # somente_valor_garantia_l3_individual_str,
        "numero_ato_anterior_atual": "",
        # str(numero_ato_anterior_atual),
        "rural_nome_fazenda": "",
        # imovel.rural_nome_fazenda,
        "rural_area_total_fazenda": "",
        # imovel.rural_area_total_fazenda,
        "rural_municipio_fazenda": "",
        # imovel.rural_municipio_fazenda,
        "numero_selo_consulta": pedido_item.pedido.numero_selo_firebird
        if pedido_item.pedido.numero_selo_firebird
        else "",
        "codigo_de_seguranca_consulta": "",
        # (
        #     formatar_codigo_seguranca_mg(
        #         str(
        #             pedido_item.pedido.protocolo.selo_codigo_para_consulta.codigo_de_seguranca,
        #         ),
        #         ".",
        #     )
        #     if pedido_item.pedido.protocolo.selo_codigo_para_consulta
        #     else ""
        # ),
    }

    # SE EXISTIR PERGUNTAS TEMPORARIAS PARA O LIVRO 2 A SEREM PREENCHIDAS
    conteudo_renderizado = renderizar_conteudo(modelo.observacao, contexto)

    return render(
        request,
        "minutas_atos/modelo_impressao.html",
        {"conteudo_renderizado": conteudo_renderizado},
    )


# Gerar as perguntas para o LIVRO 2 - MINUTAS
def falar_texto_minuta_ato(request, modelo_id):
    # Seguramente obtém o objeto, retornando 404 se não encontrado
    imovel = get_object_or_404(Livro02, pk=modelo_id)

    nome_arquivo_enviar = falar_texto(request, imovel.texto.strip())

    # Baixa o arquivo
    return download_mp3(request, nome_arquivo_enviar)


# # BAIAR O ARQUIVO DE AUDIO
# def download_mp3(file_name):
#     # Verifica se o arquivo existe
#     if not default_storage.exists(file_name):
#         msg = "O arquivo não foi encontrado."
#         raise Http404(msg)

#     try:
#         file = default_storage.open(file_name, "rb")
#         return FileResponse(file, as_attachment=True, filename=file_name)
#     except FileNotFoundError:
#         msg = f"File not found: {file_name}"
#         raise Http404(msg) from None
#     except OSError as e:
#         msg = "Failed to read the file."
#         raise Http404(msg) from e


# BAXIAR O ARQUIVO DE AUDIO
def download_mp3(request, filepath):
    import os

    filename = os.path.basename(filepath)
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)
