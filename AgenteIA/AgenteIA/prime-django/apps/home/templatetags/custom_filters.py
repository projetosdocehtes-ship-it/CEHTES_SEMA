# custom_filter.py

import logging

from django import template

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
register = template.Library()


@register.filter(name="class_name")
def class_name_filter(value) -> str:
    return value.__class__.__name__


