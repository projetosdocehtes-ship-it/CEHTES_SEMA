from django.urls import path

from apps.ged.views import (
    ArquivoDetailView,
    ArquivoDownloadView,
    ArquivosListView,
    ArquivoUploadView,
    GenericFileUploadView,
)

app_name = "ged"

urlpatterns = [
    path("arquivo-upload/", ArquivoUploadView.as_view(), name="arquivo_upload"),
    path("arquivos-list/", ArquivosListView.as_view(), name="arquivos_list"),
    path(
        "arquivo-detail/<uuid:pk>/",
        ArquivoDetailView.as_view(),
        name="arquivo_detail",
    ),
    path(
        "arquivo-download/<uuid:pk>/",
        ArquivoDownloadView.as_view(),
        name="arquivo_download",
    ),
    path(
        "upload/<int:content_type_id>/<uuid:object_id>/",
        GenericFileUploadView.as_view(),
        name="arquivo_upload_generico",
    ),
]
