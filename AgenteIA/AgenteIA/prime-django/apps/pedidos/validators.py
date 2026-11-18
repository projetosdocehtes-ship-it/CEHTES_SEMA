# validators.py

import logging

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def validar_sobreposicao_data(instance) -> None:
    from apps.pedidos.models import Emolumento

    sobrepostos = Emolumento.objects.filter(
        ato_praticavel=instance.ato_praticavel,
        estado=instance.estado,
        data_inicio_validade__lte=instance.data_fim_validade,
        data_fim_validade__gte=instance.data_inicio_validade,
    )

    if instance.pk:  # Se estiver atualizando um registro existente
        sobrepostos = sobrepostos.exclude(pk=instance.pk)

    if sobrepostos.exists():
        msg = (
            "Há sobreposição nas datas de validade para este tipo de ato neste estado."
        )
        raise ValidationError(msg)
