from django.urls import path

from apps.mapeamentos import views

app_name = "mapeamentos"

urlpatterns = [
    path("mapeamentos/", views.ver_mapeamentos, name="mapeamento"),
]
