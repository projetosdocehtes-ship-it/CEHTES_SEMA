from django import forms
from django.contrib.contenttypes.models import ContentType

from apps.mapeamentos.models import Mapeamento


class MapeamentoForm(forms.ModelForm):
    # Campos para o lado antigo
    content_type_antigo = forms.ModelChoiceField(
        queryset=ContentType.objects.all(),
        required=True,
        label="Tipo de Conteúdo Antigo",
        help_text="Selecione o tipo de conteúdo para o registro antigo",
    )
    object_id_antigo = forms.IntegerField(
        required=True,
        label="ID do Objeto Antigo",
        help_text="Insira o ID do objeto antigo",
    )

    # Campos para o lado novo
    content_type_novo = forms.ModelChoiceField(
        queryset=ContentType.objects.all(),
        required=True,
        label="Tipo de Conteúdo Novo",
        help_text="Selecione o tipo de conteúdo para o registro novo",
    )
    object_id_novo = forms.IntegerField(
        required=True,
        label="ID do Objeto Novo",
        help_text="Insira o ID do objeto novo",
    )

    class Meta:
        model = Mapeamento
        fields = []  # Explicitamente vazio pois estamos usando campos pessoalizados

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Inicialização adicional pode ser feita aqui, se necessário

    def save(self, commit=True):
        # Sobrescreva o método save para lidar corretamente com os dados dos campos pessoalizados
        instance = super().save(commit=False)
        instance.content_type_antigo = self.cleaned_data["content_type_antigo"]
        instance.object_id_antigo = self.cleaned_data["object_id_antigo"]
        instance.content_type_novo = self.cleaned_data["content_type_novo"]
        instance.object_id_novo = self.cleaned_data["object_id_novo"]

        if commit:
            instance.save()

        return instance
