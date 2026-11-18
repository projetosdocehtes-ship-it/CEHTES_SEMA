from django import forms

from apps.ged.models import Arquivo


class UploadArquivoForm(forms.ModelForm):
    class Meta:
        model = Arquivo
        fields = ["arquivo", "descricao"]
