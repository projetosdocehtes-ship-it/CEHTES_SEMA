import logging

from django import template
from django.template.defaultfilters import stringfilter

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
register = template.Library()


@register.filter
@stringfilter
def primeira_letra(value):
    """
    Verifica se <value> inicia com <arg>.
    :param value: valor do filtro
    :param arg: argumento do filtro
    :return: True se value iniciar com arg, False caso contrário.
    """
    return next(iter(value))
