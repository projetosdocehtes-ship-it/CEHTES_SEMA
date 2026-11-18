# urls.py no aplicativo 'integracoes'
from django.urls import path

from apps.integracoes import views

app_name = "integracoes"

urlpatterns = [
    path("gerar_pgnm/<str:numero_livro>/", views.gerar_pgnm, name="gerar_pgnm"),
    path("gerar_envio_l4/", views.gerar_envio_l4, name="gerar_envio_l4"),
]
