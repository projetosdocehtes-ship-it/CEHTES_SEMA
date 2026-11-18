from django.urls import path

from apps.senhas import views

app_name = "senhas"

urlpatterns = [
    path("gerar/", views.gerar_senha, name="gerar_senha"),
    path("detalhe/<int:senha_id>/", views.detalhe_senha, name="detalhe_senha"),
]
