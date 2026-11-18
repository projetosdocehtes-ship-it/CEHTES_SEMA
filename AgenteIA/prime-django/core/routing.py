# routing.py
import logging

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import apps.home.routing

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

application = ProtocolTypeRouter(
    {
        "websocket": AuthMiddlewareStack(URLRouter(apps.home.routing.websocket_urlpatterns)),
    }
)
