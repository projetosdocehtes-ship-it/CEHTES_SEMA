import datetime
import logging
import re

from django import template

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


register = template.Library()


@register.simple_tag
def tempo_atual():
    return datetime.datetime.now().strftime("%H:%M:%S")


@register.simple_tag
def user_logado() -> str:
    return "Bierley"


@register.simple_tag
def apenas_numeros(string):
    return re.sub("[^0-9]", "", string)
