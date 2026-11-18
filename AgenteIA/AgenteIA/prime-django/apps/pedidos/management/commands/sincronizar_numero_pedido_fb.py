from django.core.management.base import BaseCommand

from apps.pedidos.models import Pedido


class Command(BaseCommand):
    help = "Sicroniza o numero sequencial do pedido com o Firebird"

    def handle(self, *args, **options) -> None:
        Pedido.definir_proximo_numero(
            numero_proximo_pedido=Pedido.firebird.get_numero_proximo_pedido_fb(),
        )
