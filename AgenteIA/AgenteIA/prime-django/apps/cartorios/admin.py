import logging

from django.contrib import admin

from apps.cartorios import models
from apps.cartorios.admin_custom import *
from apps.home.models.models_certidoes import Empresa, PerguntaCustom

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


@admin.register(models.Cartorio)
class CartorioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "numero_cartorio",
        "nome",
        "cns",
        "municipio",
        "email",
        "site",
        "telefone",
        "schema_name",
    )
    search_fields = (
        "nome",
        "cnpj",
        "email",
        "telefone",
        "numero_cartorio",
    )
    raw_id_fields = ("tipo_cartorio", "expediente")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "nome",
                    "cnpj",
                    "cns",
                    "email",
                    "site",
                    "telefone",
                    "telefone_2",
                    "numero_cartorio",
                ),
            },
        ),
        (
            "Endereço",
            {
                "fields": (
                    "tipo_logradouro",
                    "logradouro",
                    "numero",
                    "quadra",
                    "lote",
                    "complemento",
                    "bairro",
                    "municipio",
                    "cep",
                    "codigo_uf",
                ),
            },
        ),
        (
            "Informações Adicionais",
            {
                "fields": (
                    "pago_ate",
                    "em_teste",
                    "tipo_cartorio",
                    "expediente",
                ),
            },
        ),
        (
            "Banco de Dados",
            {"fields": ("schema_name",)},
        ),
    )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term,
        )
        if not search_term.isdigit():
            return queryset, use_distinct
        queryset |= self.model.objects.filter(telefone__icontains=search_term)
        return queryset, use_distinct


# @admin.register(Usuario)
# class UsuarioAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "username",
#         "is_staff",
#         "is_active",
#         "cartorio",
#         "last_login",
#         "is_superuser",
#         "first_name",
#         "last_name",
#         "email",
#         "date_joined",
#         "funcao",
#         "is_online",
#         "failed_logins",
#         "status",
#         "website",
#         "phone",
#         "registration_date",
#         "fullname",
#         "address",
#         "zipcode",
#         "bio",
#         "image",
#         "avisar_protocolo_vencendo",
#         "last_activity",
#         "avisar_protocolo_nota_devolucao_anexada",
#         "assinar_nota_devolucao_digital",
#         "assinar_qualificar_titulo",
#         "avisar_pronto_registrar",
#         "avisar_digitalizar",
#         "last_password_change",
#         "imagem_assinatura",
#     )
#     list_filter = (
#         "last_login",
#         "is_superuser",
#         "is_staff",
#         "is_active",
#         "date_joined",
#         "is_online",
#         "registration_date",
#         "last_activity",
#         "last_password_change",
#     )
#     raw_id_fields = ("cartorio", "funcao")


@admin.register(models.Dominio)
class DominioAdmin(admin.ModelAdmin):
    list_display = ("id", "domain", "tenant", "is_primary")
    list_filter = ("tenant", "is_primary")

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nome", "preco_por_watt", "garantia_anos", "nota_servico", "eficiencia_modulo")
    search_fields = ("nome", "id_externo")
    list_filter = ("garantia_anos",)

@admin.register(PerguntaCustom)
class PerguntaCustomAdmin(admin.ModelAdmin):
    list_display = ("titulo", "criado_por", "criado_em")
    search_fields = ("titulo", "descricao")
    readonly_fields = ("criado_em",)