# widgets.py
import logging
from decimal import Decimal

from django import forms

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


# Função para formatar valores no formato BRL
def format_brl_value(value: str) -> str:
    """Formata um valor como BRL."""
    try:
        # Substitui vírgulas por pontos antes de converter para decimal
        decimal_value = Decimal(str(value).replace(",", "."))
        # Formata o valor como BRL
        return (
            f"{decimal_value:,.2f}".replace(",", "v")
            .replace(".", ",")
            .replace("v", ".")
        )
    except ValueError:
        return value


# Widget personalizado para entradas no formato BRL
class BRLInput(forms.TextInput):
    def format_value(self, value):
        if value is None:
            return ""
        return format_brl_value(value)

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value is None:
            return None
        # Substitui pontos por nada e vírgulas por pontos para converter o valor em float
        return value.replace(".", "").replace(",", ".")
