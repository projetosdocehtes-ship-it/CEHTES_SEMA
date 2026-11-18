from django.core.management.base import BaseCommand

from apps.mapeamentos.imports import (
    importar_emolumentos_para_emolumentos,
    importar_emolumentos_para_tipo_emolumentos,
)


class Command(BaseCommand):
    help = "Importa Emolumentos de Home para TipoEmolumento de Pedidos e cria os mapeamentos correspondentes"

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write(
            self.style.SUCCESS("Iniciando a importação de Emolumentos..."),
        )
        importar_emolumentos_para_tipo_emolumentos()
        importar_emolumentos_para_emolumentos()
        self.stdout.write(self.style.SUCCESS("Importação concluída!"))
