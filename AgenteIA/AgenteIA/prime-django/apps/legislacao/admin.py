from django.contrib import admin

from apps.legislacao.models import Lei


# Register your models here.
@admin.register(Lei)
class LeiAdmin(admin.ModelAdmin):
    list_display = ("numero", "titulo", "data_publicacao", "data_atualizacao")
    search_fields = ("numero", "titulo")
