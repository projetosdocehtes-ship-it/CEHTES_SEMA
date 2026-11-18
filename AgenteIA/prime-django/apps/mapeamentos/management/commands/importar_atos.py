from django.core.management.base import BaseCommand

from apps.mapeamentos.imports import importar_atos_para_ato_praticavel


class Command(BaseCommand):
    help = "Importa atos para AtoPraticavel e cria os mapeamentos correspondentes"

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write(self.style.SUCCESS("Iniciando a importação de atos..."))
        importar_atos_para_ato_praticavel()
        self.stdout.write(self.style.SUCCESS("Importação concluída!"))
