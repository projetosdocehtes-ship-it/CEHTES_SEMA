from django.contrib import admin

from apps.mapeamentos.models import Mapeamento


@admin.register(Mapeamento)
class MapeamentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "content_type_antigo",
        "object_id_antigo",
        "content_type_novo",
        "object_id_novo",
    )
    raw_id_fields = ("content_type_antigo", "content_type_novo")
