from django import forms
from django.contrib import admin
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.minuta_exigencia.models import MinutaExigencia, MinutaExigenciaAto


# class MinutaExigenciaAdmin(admin.ModelAdmin):
#     list_display = ("titulo", "subtitulo", "observacao")
class MinutaExigenciaAdminForm(forms.ModelForm):
    observacao = forms.CharField(widget=CKEditor5Widget)

    class Meta:
        model = MinutaExigencia
        fields = "__all__"


@admin.register(MinutaExigencia)
class MinutaExigenciaAdmin(admin.ModelAdmin):
    form = MinutaExigenciaAdminForm


# @admin.register(MinutaExigenciaAto)
class MinutaExigenciaAtoAdmin(admin.ModelAdmin):
    list_display = ("get_minuta_titulo", "ato_id")

    @admin.display(description="Título da Minuta")
    def get_minuta_titulo(self, obj):
        return obj.minuta.titulo


admin.site.register(MinutaExigenciaAto)
