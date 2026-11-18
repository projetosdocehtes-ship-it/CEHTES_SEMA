from django.core.management.base import BaseCommand

from apps.comum.models import TipoRegistroImobiliario


class Command(BaseCommand):
    help = "Cria os tipos básicos de Registro Imobiliário: Matrícula, Transcrição e Inscrição"

    def handle(self, *args, **kwargs) -> None:
        lista = [
            {"id": 1, "nome": "Matrícula"},
            {"id": 2, "nome": "Transcrição"},
            {"id": 3, "nome": "Inscrição"},
        ]

        for item in lista:
            TipoRegistroImobiliario.objects.update_or_create(
                id=item["id"],
                defaults={"nome": item["nome"]},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Tipo de Registro Imobiliário {item['nome']} criado ou atualizado ",
                ),
            )
