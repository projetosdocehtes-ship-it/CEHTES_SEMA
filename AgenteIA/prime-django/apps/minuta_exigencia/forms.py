# forms.py no aplicativo 'caixa'
from django import forms

from apps.home.models import AtoPratica
from apps.minuta_exigencia.models import MinutaExigencia, MinutaExigenciaAto


class MinutaExigenciaForm(forms.ModelForm):
    class Meta:
        model = MinutaExigencia
        fields = ["titulo", "subtitulo", "observacao"]
        labels = {
            "titulo": "Título - descrição da exigência",
            "subtitulo": "SubTítulo",
            "observacao": "Observação",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "subtitulo": forms.TextInput(attrs={"class": "form-control"}),
            "observacao": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "observacao"},
            ),
        }


# Este formulário é usado para vincular a minuta de exigência com o ato.
class MinutaExigenciaAtoForm(forms.ModelForm):
    minuta_exigencia = forms.ModelChoiceField(
        queryset=MinutaExigencia.objects.all().order_by("titulo"),
        label="Descrição da Exigência",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="Selecione a exigência",
    )

    ato_id = forms.ModelChoiceField(
        queryset=AtoPratica.objects.all().order_by("tipo_ato"),
        label="Descrição do Ato",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="Selecione o ato a vinculado",
    )

    class Meta:
        model = MinutaExigenciaAto
        fields = ["minuta_exigencia", "ato_id"]
        # labels = {
        #     "ato_id": "Descrição do Ato",
        # }
        # widgets = {
        #     "ato_id": forms.TextInput(attrs={"class": "form-control"}),
        # }
