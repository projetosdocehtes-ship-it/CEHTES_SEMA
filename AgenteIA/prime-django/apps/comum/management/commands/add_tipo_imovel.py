from django.core.management.base import BaseCommand

from apps.comum.models import TipoRegistro


class Command(BaseCommand):
    help = "Cria os tipos basicos de imovel. Urbano e Rural"

    def handle(self, *args, **kwargs) -> None:
        lista = [
            {"id": 1, "nome": "Urbano"},
            {"id": 2, "nome": "Rural"},
        ]

        for item in lista:
            TipoRegistro.objects.update_or_create(
                id=item["id"],
                defaults={"nome": item["nome"]},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Tipo de Imóvel {item['nome']} criado ou atualizada ",
                ),
            )
