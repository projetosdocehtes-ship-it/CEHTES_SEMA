import django_filters

from apps.pessoas.models import Pessoa, Vinculo


class PessoaFilter(django_filters.FilterSet):
    nome = django_filters.CharFilter(
        field_name="versoes__nome",
        lookup_expr="icontains",
        label="Nome",
    )
    documento = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Documento",
    )
    email = django_filters.CharFilter(
        field_name="versoes__email",
        lookup_expr="icontains",
        label="Email",
    )

    class Meta:
        model = Pessoa
        fields = ("documento",)


class VersaoPessoaFilter(django_filters.FilterSet):
    nome = django_filters.CharFilter(
        field_name="versoes__nome",
        lookup_expr="icontains",
        label="Nome",
    )
    documento = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Documento",
    )
    email = django_filters.CharFilter(
        field_name="versoes__email",
        lookup_expr="icontains",
        label="Email",
    )

    class Meta:
        model = Vinculo
        fields = ("documento",)


class VinculoFilter(django_filters.FilterSet):
    nome = django_filters.CharFilter(
        field_name="versao_pessoa__nome",
        lookup_expr="icontains",
        label="Nome",
    )
    documento = django_filters.CharFilter(
        field_name="versao_pessoa__documento",
        lookup_expr="icontains",
        label="Documento",
    )
    email = django_filters.CharFilter(
        field_name="versao_pessoa__email",
        lookup_expr="icontains",
        label="Email",
    )

    class Meta:
        model = Vinculo
        fields = ("documento",)

    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if (
            self.request
            and "object_id" in self.request.GET
            and "content_type_id" in self.request.GET
        ):
            object_id = self.request.GET["object_id"]
            content_type_id = self.request.GET["content_type_id"]
            self.queryset = self.queryset.filter(
                content_type_id=content_type_id,
                object_id=object_id,
            )
