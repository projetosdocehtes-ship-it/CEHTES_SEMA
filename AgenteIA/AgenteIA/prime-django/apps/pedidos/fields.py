import logging
from decimal import Decimal, InvalidOperation

from django import forms

from apps.pedidos.widgets import BRLInput

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class BRLField(forms.DecimalField):
    widget = BRLInput

    def __init__(self, *args, **kwargs):
        # Define valores padrão para max_digits e decimal_places
        kwargs.setdefault("max_digits", 20)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None

        # Remove todos os caracteres que não são dígitos ou vírgulas/pontos
        value = (
            str(value)
            .replace("R$", "")
            .replace(" ", "")
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            value = Decimal(value)
        except (ValueError, InvalidOperation):
            raise forms.ValidationError(
                self.error_messages["invalid"], code="invalid", params={"value": value},
            ) from None

        return round(value, 2)
