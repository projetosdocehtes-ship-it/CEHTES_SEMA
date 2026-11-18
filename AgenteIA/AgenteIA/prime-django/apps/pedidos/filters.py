import datetime
import logging
from datetime import time

import django_filters
from django import forms
from django.utils import timezone

from apps.pedidos.models import Pedido

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class PeriodoFilter(django_filters.Filter):
    def __init__(self, field_name, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.field_name = field_name

    def filter(self, qs, value):
        if value:
            # Convertendo a string para um objeto datetime.date
            value = datetime.datetime.strptime(value, "%Y-%m-%d").date()
            data_inicio = timezone.make_aware(
                datetime.datetime.combine(value, time.min)
            )
            data_fim = timezone.make_aware(datetime.datetime.combine(value, time.max))
            filtro = {
                f"{self.field_name}__gte": data_inicio,
                f"{self.field_name}__lt": data_fim,
            }
            return qs.filter(**filtro)
        return qs


class PedidoFilter(django_filters.FilterSet):
    numero_pedido = django_filters.NumberFilter(
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Número"},
        ),
    )

    numero_protocolo_firebird = django_filters.NumberFilter(
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Protocolo"},
        ),
    )

    data_entrada = PeriodoFilter(
        field_name="data_entrada",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": "Data de Entrada",
                "title": "Data de Entrada",
            },
        ),
    )

    # data_prevista = PeriodoFilter(
    #     field_name="data_prevista",
    #     widget=forms.DateInput(
    #         attrs={
    #             "type": "date",
    #             "class": "form-control",
    #             "placeholder": "Data Prevista",
    #             "title": "Data Prevista",
    #         },
    #     ),
    # )

    nome = django_filters.CharFilter(
        field_name="apresentante__nome",
        lookup_expr="icontains",
        label="Nome do Apresentante",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Apresentante"},
        ),
    )

    ato_onr = django_filters.CharFilter(
        field_name="ato_onr",
        lookup_expr="icontains",
        label="Ato ONR",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ato ONR"},
        ),
    )

    class Meta:
        model = Pedido
        fields = [
            "numero_pedido",
            "numero_protocolo_firebird",
            "data_entrada",
            # "data_prevista",
            "nome",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["numero_pedido"].field.widget = forms.TextInput(
            attrs={"autofocus": "autofocus"},
        )
