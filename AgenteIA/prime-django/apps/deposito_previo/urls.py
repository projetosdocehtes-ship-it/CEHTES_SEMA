from django.urls import path

from apps.deposito_previo.views import DepositoPrevioList

app_name = "deposito_previo"  # Muito útil para namespaces de URL

urlpatterns = [
    path("list/", DepositoPrevioList.as_view(), name="depositoprevio_list"),
    # path("/novo/", DepositoPrevioCreate.as_view(), name="depositoprevio_create"),
    # path(
    #     "depositoprevio/<int:pk>/editar/",
    #     DepositoPrevioUpdate.as_view(),
    #     name="depositoprevio_update",
    # ),
    # path(
    #     "modeloexemplo/<int:pk>/deletar/",
    #     DepositoPrevioDelete.as_view(),
    #     name="modeloexemplo_delete",
    # ),
]
