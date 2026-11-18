from django.core.management.base import BaseCommand

from apps.mapeamentos.imports import importar_titulos_protocolo_para_tipotitulo


class Command(BaseCommand):
    help = "Importa Emolumentos de Home para TipoEmolumento de Pedidos e cria os mapeamentos correspondentes"

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write(self.style.SUCCESS("Iniciando a importação de Titulos..."))
        importar_titulos_protocolo_para_tipotitulo()
        self.stdout.write(self.style.SUCCESS("Importação concluída!"))
