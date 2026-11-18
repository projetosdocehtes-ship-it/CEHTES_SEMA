# phone_filters.py
import logging

import phonenumbers
from django import template

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
register = template.Library()


def formatar_telefone(numero, pais="BR") -> str:
    if numero is None or numero.strip() == "":
        return "(Não Informado)"

    try:
        telefone = phonenumbers.parse(numero, pais)
        if phonenumbers.is_valid_number(telefone):
            return phonenumbers.format_number(
                telefone,
                phonenumbers.PhoneNumberFormat.NATIONAL,
            )
        else:
            return numero
    except phonenumbers.NumberParseException:
        return "(Não Informado)"


@register.filter(name="formatar_telefone")
def formatar_telefone_filter(numero) -> str:
    return formatar_telefone(numero)
