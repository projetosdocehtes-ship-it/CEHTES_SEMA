import os

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView
from django.views.generic.list import ListView

from apps.ged.filters import ArquivoFilter
from apps.ged.forms import UploadArquivoForm
from apps.ged.models import Arquivo, RegistroDownload

LOCAL = "local"
S3 = "s3"


class ArquivoDetailView(DetailView):
    model = Arquivo
    template_name = "ged/arquivo_detail.html"
    context_object_name = "arquivo"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)
        # Aqui você pode adicionar qualquer contexto adicional se necessário


class ArquivoUploadView(FormView):
    template_name = "ged/upload.html"
    form_class = UploadArquivoForm
    success_url = reverse_lazy(
        "ged:arquivo_upload",
    )  # URL para redirecionar após o upload bem-sucedido

    def form_valid(self, form):
        arquivo_upload = self.request.FILES["arquivo"]
        descricao = form.cleaned_data["descricao"]
        usuario = self.request.user

        # Determinar o ContentType e object_id para o arquivo
        content_type = ContentType.objects.get_for_model(usuario)
        object_id = usuario.id

        try:
            Arquivo.criar_e_salvar(
                arquivo=arquivo_upload,
                usuario=usuario,
                content_type=content_type,
                object_id=object_id,
                descricao=descricao,
            )
            messages.success(self.request, "Arquivo enviado!")
        except Exception:
            messages.error(self.request, "Falha ao enviar arquivo: ")
            return super().form_invalid(form)

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "ERRO no formulário. Verifique os dados inseridos.",
        )
        return super().form_invalid(form)


class ArquivosListView(ListView):
    model = Arquivo
    template_name = "ged/lista_arquivos.html"
    context_object_name = "arquivos"

    def get_queryset(self):
        queryset = super().get_queryset()

        # Aplica o filtro do django-filter
        self.filter = ArquivoFilter(self.request.GET, queryset=queryset)
        filtered_queryset = self.filter.qs

        # Filtra adicionalmente com base em content_type_id e object_id
        content_type_id = self.request.GET.get("content_type_id")
        object_id = self.request.GET.get("object_id")

        if content_type_id and object_id:
            content_type = ContentType.objects.get_for_id(int(content_type_id))
            filtered_queryset = filtered_queryset.filter(
                content_type=content_type,
                object_id=object_id,
            )

        return filtered_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filter
        return context


class ArquivoDownloadView(View):
    def get(self, request, pk):
        arquivo = get_object_or_404(Arquivo, pk=pk)

        # Registrar o download
        RegistroDownload.objects.create(
            usuario=request.user,
            arquivo=arquivo.nome_completo,
            data_hora=timezone.now(),
        )

        if arquivo.storage == LOCAL:
            file_path = arquivo.arquivo.path
            if os.path.exists(file_path):
                with open(file_path, "rb", encoding="utf_8") as fh:
                    response = HttpResponse(
                        fh.read(),
                        content_type="application/octet-stream",
                    )
                    response["Content-Disposition"] = (
                        f'attachment; filename="{arquivo.nome_completo}"'
                    )
                    return response
            raise Http404
        elif arquivo.storage == S3:
            return HttpResponseRedirect(arquivo.arquivo.url)
        return None


class GenericFileUploadView(CreateView):
    model = Arquivo
    form_class = UploadArquivoForm
    template_name = "ged/upload.html"

    def _get_object(self):
        if not hasattr(self, "_content_type") or not hasattr(self, "_objeto"):
            content_type_id = self.kwargs.get("content_type_id")
            object_id = self.kwargs.get("object_id")
            self._content_type = get_object_or_404(ContentType, id=content_type_id)
            self._objeto = get_object_or_404(
                self._content_type.model_class(),
                id=object_id,
            )
        return self._objeto

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["objeto"] = self._get_object()
        return context

    def form_valid(self, form):
        objeto = self._get_object()
        content_type_id = self.kwargs.get("content_type_id")
        object_id = self.kwargs.get("object_id")
        content_type = get_object_or_404(ContentType, id=content_type_id)
        # objeto = get_object_or_404(content_type.model_class(), id=object_id)

        try:
            Arquivo.criar_e_salvar(
                arquivo=form.cleaned_data["arquivo"],
                usuario=self.request.user,
                content_type=content_type,
                object_id=object_id,
                descricao=form.cleaned_data.get("descricao"),
            )
            messages.success(self.request, "Arquivo enviado!")
        except Exception:
            messages.error(self.request, "Falha ao enviar arquivo: ")
            return super().form_invalid(form)
        return redirect(objeto.get_absolute_url())
