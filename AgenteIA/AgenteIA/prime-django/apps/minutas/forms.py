from django import forms
from django.contrib.contenttypes.models import ContentType
from django_select2.forms import ModelSelect2Widget

from apps.minutas.models import Minuta


class MinutaForm(forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.all(),
        widget=ModelSelect2Widget(
            search_fields=["app_label__icontains", "model__icontains"],
            attrs={"data-minimum-input-length": 0},
        ),
    )
    # Resto do formulário

    class Meta:
        model = Minuta
        fields = ["nome", "tipo_minuta", "content", "content_type"]
