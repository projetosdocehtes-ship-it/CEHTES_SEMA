# from django.urls import path
# from . import views

import logging

from django.urls import path

from apps.comum import views

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
app_name = "comum"

# urlpatterns = [
#     path(
#         "endereco/adicionar/",
#         views.EnderecoCreateView.as_view(),
#         name= "adicionar_endereco",
#     ),
#     path(
#         "endereco/editar/<uuid:pk>/",
#         views.EnderecoUpdateView.as_view(),
#         name= "editar_endereco",
#     ),
#     # Outras URLs relacionadas ao app 'comum'
# ]


urlpatterns = [
    # ...
    path(
        "api/get_instrucoes/<int:card_id>/",
        views.get_instrucoes,
        name="get_instrucoes",
    ),
    path(
        "dadosbancarios/cadastrar/<int:apresentante_pk>",
        views.CadastrarDadosBancariosView.as_view(),
        name="cadastrar_dadosbancarios",
    ),
    path(
        "dadosbancarios/editar/<int:pk>/",
        views.EditarDadosBancariosView.as_view(),
        name="editar_dadosbancarios",
    ),
    path(
        "dadosbancarios/excluir/<int:pk>/",
        views.ExcluirDadosBancariosView.as_view(),
        name="excluir_dadosbancarios",
    ),
    path("deploy/", views.deploy_view, name="deploy_view"),
    path("commands/", views.command_list_view, name="command_list"),
    path("municipios_ajax", views.busca_municipios_ajax, name="busca_municipios_ajax"),
]
