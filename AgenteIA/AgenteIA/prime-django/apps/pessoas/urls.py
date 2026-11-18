from django.urls import path

from apps.pessoas import views

app_name = "pessoas"

urlpatterns = [
    path("", views.PessoaListView.as_view(), name="pessoas-list"),
    path("<int:pk>/", views.PessoaDetailView.as_view(), name="pessoa-detail"),
    path("create/", views.PessoaCreateView.as_view(), name="pessoa-create"),
    path("<uuid:pk>/edit/", views.PessoaUpdateView.as_view(), name="pessoa-edit"),
    path("<uuid:pk>/versoes/", views.VersaoPessoaListView.as_view(), name="versoes"),
    path(
        "<uuid:pk>/versao-create/",
        views.VersaoPessoaCreateView.as_view(),
        name="versao-create",
    ),
    path(
        "<uuid:pk>/versao-edit/",
        views.VersaoPessoaUpdateView.as_view(),
        name="versao-edit",
    ),
    path(
        "wizard/<int:content_type_id>/<object_id>/",
        views.PessoaCreateWizardView.as_view(),
        name="pessoa-create-wizard",
    ),
    path(
        "vinculos/",
        views.VinculoListView.as_view(),
        name="vinculos-list",
    ),
    path(
        "pessoas/vincular_protocolo_parte_conjuge/",
        views.vincular_protocolo_parte_conjuge,
        name="vincular_protocolo_parte_conjuge",
    ),
]
