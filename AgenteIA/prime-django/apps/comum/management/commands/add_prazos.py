from django.core.management.base import BaseCommand

from apps.comum.models import PrazoLegal, UnidadePrazo


class Command(BaseCommand):
    help = "Cria valores comuns para os modelos UnidadePrazo e PrazoLegal"

    def handle(self, *args, **kwargs) -> None:
        # Criando valores para UnidadePrazo
        unidades = [
            {"nome": "Dias", "em_horas": 24},
            {"nome": "Horas", "em_horas": 1},
            {"nome": "Minutos", "em_horas": 1 / 60},
        ]
        for unidade in unidades:
            UnidadePrazo.objects.get_or_create(**unidade)
        self.stdout.write(self.style.SUCCESS("Unidades de prazo criadas ."))

        # Criando valores para PrazoLegal (exemplo)
        prazos = [
            {
                "valor": 5,
                "unidade": UnidadePrazo.objects.get(nome="Dias"),
                "eh_prazo_util": True,
            },
            {
                "valor": 72,
                "unidade": UnidadePrazo.objects.get(nome="Horas"),
                "eh_prazo_util": False,
            },
        ]
        for prazo in prazos:
            PrazoLegal.objects.get_or_create(**prazo)
        self.stdout.write(self.style.SUCCESS("Prazos legais criados ."))
