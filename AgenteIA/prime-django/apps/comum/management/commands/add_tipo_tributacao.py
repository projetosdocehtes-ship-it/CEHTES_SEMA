from django.core.management.base import BaseCommand

from apps.home.models import TipoTributacao


class Command(BaseCommand):
    help = "Popula o banco de dados com os tipos básicos de tributação"

    def handle(self, *args, **kwargs) -> None:
        tipos_tributacao = [
            {
                "id": 1,
                "nome": "Normal",
                "descricao": "Normal - Sem desconto",
                "percentual_desconto": 0,
            },
            {
                "id": 2,
                "nome": "Isento",
                "descricao": "Isento 100%",
                "percentual_desconto": 100.00,
            },
            {
                "id": 3,
                "nome": "SFH",
                "descricao": "SFH 50%",
                "percentual_desconto": 50.00,
            },
            {
                "id": 4,
                "nome": "MCMV",
                "descricao": "MCMV 50%",
                "percentual_desconto": 50.00,
            },
        ]

        for tipo in tipos_tributacao:
            TipoTributacao.objects.update_or_create(
                id=tipo["id"],
                defaults={
                    # "nome": tipo["nome"],
                    "descricao": tipo["descricao"],
                    "percentual_desconto": tipo["percentual_desconto"],
                },
            )

        self.stdout.write(
            self.style.SUCCESS("Tipos de tributação básicos adicionados!"),
        )
