import logging
from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class PasswordExpirationMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            time_since_last_change = timezone.now() - request.user.last_password_change
            days_until_expiration = 90 - time_since_last_change.days

            change_password_url = "/user_profile/#user-set-password"  # URL relativa da página de mudança de senha

            if 0 < days_until_expiration <= 3 and not self._message_exists(
                request,
                "password_warning",
            ):
                # Mensagem com HTML marcada como segura
                message = mark_safe(
                    f"Sua senha expirará em {days_until_expiration} dias. Por favor, <a href='{change_password_url}'>atualize sua senha</a>.",
                )
                messages.warning(request, message)  # Não adicionar extra_tags aqui

            if time_since_last_change > timedelta(
                days=90,
            ) and not request.path.startswith("/user_profile/"):
                return redirect(change_password_url)

        return response

    def _message_exists(self, request, tag) -> bool:
        return any(tag in message.tags for message in messages.get_messages(request))
