import logging

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
# validators.py

from django.core.exceptions import ValidationError


def validar_sobreposicao_data(instance) -> None:
    from apps.home.models import ValorCertidao

    sobrepostos = ValorCertidao.objects.filter(
        tipo_certidao=instance.tipo_certidao,
        # estado=instance.estado,
        data_inicio_validade__lte=instance.data_fim_validade,
        data_fim_validade__gte=instance.data_inicio_validade,
    )

    if instance.pk:  # Se estiver atualizando um registro existente
        sobrepostos = sobrepostos.exclude(pk=instance.pk)

    if sobrepostos.exists():
        msg = "Há sobreposição nas datas de validade para este tipo de certidão neste estado."
        raise ValidationError(msg)
