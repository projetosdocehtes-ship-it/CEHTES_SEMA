from django.core.management.base import BaseCommand
from django.db import transaction

from apps.home.models import EmolumentoValor


# Classe do comando
class Command(BaseCommand):
    help = "Importar valores de emolumentos do FB"

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            EmolumentoValor.objects.importar_do_fb()
