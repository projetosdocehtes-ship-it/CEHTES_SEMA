# querystring_tags.py
import logging

from django import template

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

register = template.Library()


@register.simple_tag
def query_transform(request, **kwargs):
    updated = request.GET.copy()
    for k, v in kwargs.items():
        updated[k] = v
    return updated.urlencode()
