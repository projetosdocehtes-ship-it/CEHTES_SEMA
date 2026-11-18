from django.contrib import admin
from .models import Componente, Fabricante, Projeto, ProjetoDiagrama, TipoComponente


@admin.register(Fabricante)
class FabricanteAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)


@admin.register(TipoComponente)
class TipoComponenteAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo", "nome")
    search_fields = ("codigo", "nome")


@admin.register(Componente)
class ComponenteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome_modelo",
        "fabricante",
        "tipo",
        "potencia_kw",
        "tensao_nominal_v",
        "energia_kwh",
        "ativo",
    )
    list_filter = ("tipo", "fabricante", "ativo")
    search_fields = ("nome_modelo", "fabricante__nome", "tipo__nome")


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "criado_em", "atualizado_em")
    search_fields = ("nome",)


@admin.register(ProjetoDiagrama)
class ProjetoDiagramaAdmin(admin.ModelAdmin):
    list_display = ("id", "projeto")
