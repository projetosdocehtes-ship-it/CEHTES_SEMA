# views.py
import logging

from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def check_inactivity(request):
    if request.user.is_authenticated:
        time_since_last_activity = timezone.now() - request.user.last_activity
        logout_in = max(
            30 - time_since_last_activity.total_seconds() / 60,
            0,
        )  # Substitua 30 pelo seu tempo de inatividade
        return JsonResponse({"logout_in": logout_in})
    return JsonResponse({"logout_in": -1})
