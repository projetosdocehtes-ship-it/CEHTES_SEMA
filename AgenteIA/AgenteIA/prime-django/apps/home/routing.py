import logging

from django.urls import path

from apps.home import consumers

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

websocket_urlpatterns = [
    path("ws/progress/", consumers.ProgressConsumer.as_asgi()),
    path("ws/chat/<str:room_name>/", consumers.ChatConsumer.as_asgi()),
]
