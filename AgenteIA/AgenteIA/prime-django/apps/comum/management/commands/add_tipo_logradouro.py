from django.core.management.base import BaseCommand

from apps.comum.models import TipoLogradouro


class Command(BaseCommand):
    help = "Adiciona tipos de logradouro ao model TipoLogradouro"

    def handle(self, *args, **kwargs) -> None:
        tipos_logradouro = [
            (1, "R", "Rua"),
            (2, "FAZ", "Fazenda"),
            (3, "AV", "Avenida"),
            (4, "AL", "Alameda"),
            (5, "T", "Travessa"),
            (6, "TRV", "Trevo"),
            (7, "TUN", "Tunel"),
            (8, "SIT", "Sitio"),
            (9, "CH", "Chácara"),
            (10, "CJ", "Conjunto"),
            (11, "CRG", "Córrego"),
            (12, "EST", "Estrada"),
            (13, "ROD", "Rodovia"),
        ]

        for id, codigo, nome in tipos_logradouro:
            TipoLogradouro.objects.get_or_create(
                id=id,
                defaults={"codigo": codigo, "nome": nome},
            )

        self.stdout.write(self.style.SUCCESS("Tipos de logradouro adicionados!"))
