import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.comum.models import Feriado, UnidadeFederativa


class Command(BaseCommand):
    help = "Importa os feriados por UF do Invertexto e grava no banco de dados."

    def add_arguments(self, parser) -> None:
        parser.add_argument("uf", type=str, help="UF para importar os feriados")

    def handle(self, *args, **options) -> None:
        token = "5216|etZQ4K9l0wK5Oe8Jn7n703Ygxxeu2pHm"
        ano_atual = timezone.now().year
        uf_code = options["uf"].upper()

        try:
            uf_instance = UnidadeFederativa.objects.get(sigla=uf_code)
        except UnidadeFederativa.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"A UF '{uf_code}' não foi encontrada no banco de dados.",
                ),
            )
            return

        url = f"https://api.invertexto.com/v1/holidays/{ano_atual}?token={token}&state={uf_code}"

        response = requests.get(url)
        if response.status_code == 200:
            feriados_data = response.json()

            for feriado_data in feriados_data:
                tipo_feriado = self.determinar_tipo_feriado(feriado_data["level"])

                _, created = Feriado.objects.update_or_create(
                    nome=feriado_data["name"],
                    data=feriado_data["date"],
                    defaults={
                        "tipo": tipo_feriado,
                        "estado": (
                            uf_instance
                            if tipo_feriado == Feriado.TIPO_ESTADUAL
                            else None
                        ),
                        # 'municipio': adicione aqui a lógica se precisar associar a um município e o feriado for municipal
                    },
                )
                status = "criado" if created else "atualizado"
                self.stdout.write(
                    self.style.SUCCESS(f"Feriado '{feriado_data['name']}' {status} ."),
                )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"ERRO ao obter os feriados da UF '{uf_code}' da Invertexto.",
                ),
            )

    def determinar_tipo_feriado(self, level):
        if level == "nacional":
            return Feriado.TIPO_NACIONAL
        elif level == "estadual":
            return Feriado.TIPO_ESTADUAL
        else:
            # Por padrão, retorna tipo municipal, mas pode precisar de ajustes conforme a estrutura de seu banco de dados
            return Feriado.TIPO_MUNICIPAL
