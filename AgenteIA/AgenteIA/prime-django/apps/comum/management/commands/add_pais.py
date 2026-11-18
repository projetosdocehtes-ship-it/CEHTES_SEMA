from django.core.management.base import BaseCommand

from apps.comum.models import Pais


class Command(BaseCommand):
    help = "Cria o país padrão Brasil se ele não existir"

    def handle(self, *args, **kwargs) -> None:
        pais, created = Pais.objects.get_or_create(nome="Brasil", sigla="BR")
        if created:
            self.stdout.write(self.style.SUCCESS("País Brasil criado "))
        else:
            self.stdout.write(self.style.SUCCESS("País Brasil já existe"))
