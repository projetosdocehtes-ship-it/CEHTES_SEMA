from django.dispatch import Signal, receiver

from apps.cartorios.models import Usuario
from apps.deposito_previo.models import DepositoPrevio

servico_realizado_signal = Signal()


@receiver(servico_realizado_signal)
def servicos_realizados_receiver(sender, **kwargs) -> None:
    valor = kwargs.get("valor")
    descricao = kwargs.get("descricao")
    data_servico = kwargs.get("data_servico")
    tipo_servico = kwargs.get("tipo_servico")
    usuario_id = kwargs.get("usuario_id")

    usuario = Usuario.objects.get(id=usuario_id)

    if tipo_servico == "DepositoPrevio":
        DepositoPrevio.objects.create(
            valor=valor,
            data=data_servico,
            descricao=descricao,
            responsavel=usuario,
            status="pendente",
        )
