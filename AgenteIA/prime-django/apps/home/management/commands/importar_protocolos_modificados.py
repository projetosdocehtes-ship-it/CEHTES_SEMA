from django.core.management.base import BaseCommand

# from apps.home.views import importar_protocolos_modificados_view
from apps.home.utils.importacao_de_protocolo_firebird import (
    importar_protocolos_modificados_ultimos_2_dias,
)


class Command(BaseCommand):
    help = "Importa protocolos modificados sem necessidade de um request HTTP"

    def handle(self, *args, **options) -> None:
        self.stdout.write(
            self.style.SUCCESS("Iniciando a importação de protocolos modificados..."),
        )
        importar_protocolos_modificados_ultimos_2_dias()
        self.stdout.write(
            self.style.SUCCESS("Importação de protocolos modificados concluída ."),
        )
