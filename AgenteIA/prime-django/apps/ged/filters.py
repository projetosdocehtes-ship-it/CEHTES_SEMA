import django_filters

from apps.ged.models import Arquivo


class ArquivoFilter(django_filters.FilterSet):
    class Meta:
        model = Arquivo
        fields = {
            "nome_original": ["icontains"],  # Filtro por nome contendo uma string
            "usuario__username": ["exact"],  # Filtro por nome de usuário exato
            # ... adicione mais campos conforme necessário ...
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.form.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        # Atualizar o rótulo de um campo específico
        self.form.fields["usuario__username"].label = "Nome do Usuário"
