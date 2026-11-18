# urls.py no aplicativo 'minuta_exigencia'
from django.urls import path

from apps.minuta_exigencia import views

app_name = "minuta_exigencia"

urlpatterns = [
    path(
        "adicionar/",
        views.MinutaExigenciaCreateView.as_view(),
        name="adicionar_minuta_exigencia",
    ),
    path(
        "editar/<str:pk>/",
        views.MinutaExigenciaUpdateView.as_view(),
        name="editar_minuta_exigencia",
    ),
    path(
        "remover/<str:pk>/",
        views.MinutaExigenciaAtoDeleteView.as_view(),
        name="remover_exigencia_ato",
    ),
    path(
        "vincular_minuta_exigencia_ato/<str:pk>/",
        views.MinutaExigenciaAtoCreateView.as_view(),
        name="vincular_minuta_exigencia_ato",
    ),
    path(
        "mensagem_minuta_exigencia_ato/",
        views.MensagemMinutaExigenciaAtoView.as_view(),
        name="mensagem_minuta_exigencia_ato",
    ),
]
