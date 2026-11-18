import asyncio
import json
import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class ProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        await self.accept()

    async def disconnect(self, close_code) -> None:
        pass

    async def receive(self, text_data) -> None:
        json.loads(text_data)
        # Poderia iniciar uma tarefa assíncrona aqui
        await self.start_long_task()

    async def send_progress(self, progress) -> None:
        await self.send(text_data=json.dumps({"progress": progress}))

    async def start_long_task(self) -> None:
        # Exemplo: Atualizar progresso de uma importação
        for i in range(100):
            await self.send_progress(i)
            # Substitua o código abaixo com o código real da sua tarefa longa
            await asyncio.sleep(1)  # Simulando uma tarefa longa


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            await self.accept()
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            # Atualizar status do usuário para online
            async_to_sync(self.update_user_status)(self.user, True)

    async def disconnect(self, close_code) -> None:
        if self.user.is_authenticated:
            # Atualizar status do usuário para offline
            async_to_sync(self.update_user_status)(self.user, False)
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data) -> None:
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Enviar mensagem para o grupo
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": message},
        )

    async def chat_message(self, event) -> None:
        message = event["message"]

        # Enviar mensagem para WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    @staticmethod
    def update_user_status(user, status) -> None:
        logger.info(user)
        user_model = get_user_model()
        user_model.objects.filter(self=user).update(is_online=status)
