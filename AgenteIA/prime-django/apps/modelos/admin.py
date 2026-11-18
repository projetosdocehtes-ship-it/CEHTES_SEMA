from django.contrib import admin

from apps.modelos.models import Cliente, ModeloTexto


@admin.register(ModeloTexto)
class ModeloTextoAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "conteudo")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "email", "data_nascimento", "endereco")
    list_filter = ("data_nascimento",)
