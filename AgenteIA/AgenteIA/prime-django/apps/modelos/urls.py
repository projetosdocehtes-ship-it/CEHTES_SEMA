from django.urls import path

from apps.modelos.views import (
    ModeloTextoCreateView,
    ModeloTextoDeleteView,
    ModeloTextoDetailView,
    ModeloTextoListView,
    ModeloTextoUpdateView,
    exibir_modelo_para_impressao,
)

app_name = "modelos"

# URLs de Auditorias
urlpatterns = [
    path("modelos/", ModeloTextoListView.as_view(), name="modelo_list"),
    path("modelo/<int:pk>/", ModeloTextoDetailView.as_view(), name="modelo_detail"),
    path("modelo/novo/", ModeloTextoCreateView.as_view(), name="modelo_new"),
    path(
        "modelo/editar/<int:pk>/",
        ModeloTextoUpdateView.as_view(),
        name="modelo_edit",
    ),
    path(
        "modelo/deletar/<int:pk>/",
        ModeloTextoDeleteView.as_view(),
        name="modelo_delete",
    ),
    path(
        "modelo/<int:modelo_id>/impressao/",
        exibir_modelo_para_impressao,
        name="modelo_impressao",
    ),
]
