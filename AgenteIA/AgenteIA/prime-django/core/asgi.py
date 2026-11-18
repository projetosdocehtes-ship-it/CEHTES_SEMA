"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import locale
import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, get_default_application
from django.core.asgi import get_asgi_application

import apps.home.routing  # Supondo que sua aplicação se chame 'myapp'
import logging

try:
    # Tenta a configuração comum em sistemas Unix/Linux
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except locale.Error:
    try:
        # Alternativa para Windows
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except locale.Error:
        print("Localidade não suportada")


logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

# Definindo a variável de ambiente para o módulo de configurações do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Inicializando o Django
django.setup()

# Obtendo a aplicação ASGI padrão do Django para tratar HTTP
django_asgi_app = get_default_application()

# Criando um roteador de protocolo com suporte a HTTP e WebSocket
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        # Just HTTP for now. (We can add other protocols later.)
        "websocket": AuthMiddlewareStack(URLRouter(apps.home.routing.websocket_urlpatterns)),
    },
)
