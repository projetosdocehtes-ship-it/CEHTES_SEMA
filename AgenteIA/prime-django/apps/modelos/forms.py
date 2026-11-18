from django import forms

from apps.modelos.models import ModeloTexto


class ModeloTextoForm(forms.ModelForm):
    class Meta:
        model = ModeloTexto
        fields = ["titulo", "conteudo"]
