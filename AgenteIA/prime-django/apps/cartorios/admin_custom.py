# admin_custom.py

import logging

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin

from apps.cartorios.forms import UsuarioAdminChangeForm, UsuarioAdminCreationForm
from apps.cartorios.models import Funcao, Usuario

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    form = UsuarioAdminChangeForm
    add_form = UsuarioAdminCreationForm

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        #"fullname",
        "is_staff",
        "funcao",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "funcao")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Serventia",
            {"fields": ("cartorio",)},
        ),
        (
            "Informações pessoais",
            {"fields": ("first_name", "last_name", "email", "funcao")},
        ),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Datas Importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "funcao",
                    "cartorio",
                ),
            },
        ),
    )
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    filter_horizontal = (
        "groups",
        "user_permissions",
    )


@admin.register(Funcao)
class FuncaoAdmin(ImportExportModelAdmin):
    # Campos que serão exibidos na lista de objetos
    list_display = ("nome", "titulo")
    # Campos que serão editáveis diretamente na lista de objetos
    list_editable = ("titulo",)
    # Campos que serão utilizados para adicionar filtros laterais
    list_filter = ("nome", "titulo")
    # Campos que serão utilizados para adicionar uma barra de busca
    search_fields = ("nome", "titulo")
    # Campos que serão exibidos em grupos específicos ao editar um objeto
    fieldsets = (
        (
            None,
            {
                "fields": ("nome", "titulo"),
                "description": "Preencha as informações da função.",
            },
        ),
    )

    # Adiciona uma funcionalidade para exportar dados em CSV
    actions = ["export_as_csv"]

    def export_as_csv(self, request, queryset):
        import csv
        from datetime import datetime

        from django.http import HttpResponse

        opts = self.model._meta
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment;filename={opts.verbose_name_plural}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
        )
        writer = csv.writer(response)

        # Write the header
        field_names = [field.name for field in opts.fields]
        writer.writerow(field_names)

        # Write data rows
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Exportar dados selecionados como CSV"
