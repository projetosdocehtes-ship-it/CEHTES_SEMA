from django.core.management.base import BaseCommand

from apps.comum.models import EstadoCivil


class Command(BaseCommand):
    help = "Adiciona estados civis ao model EstadoCivil"

    def handle(self, *args, **kwargs) -> None:
        estados_civis = [
            (1, "Solteiro(a)"),
            (2, "Casado(a)"),
            (3, "Divorciado(a)"),
            (4, "Separado(a) judicialmente"),
            (5, "Viúvo(a)"),
            (6, "União estável"),
            (7, "Outro"),
        ]

        for id, nome in estados_civis:
            EstadoCivil.objects.update_or_create(id=id, defaults={"nome": nome})

        self.stdout.write(self.style.SUCCESS("Estados civis adicionados!"))
