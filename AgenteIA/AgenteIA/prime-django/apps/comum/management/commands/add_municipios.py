import csv
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.comum.models import Municipio, UnidadeFederativa


class Command(BaseCommand):
    help = "Carrega municípios a partir de um arquivo CSV"

    def handle(self, *args, **options) -> None:
        # Caminho hardcoded para o arquivo CSV
        dir_path = Path(os.path.realpath(__file__))
        csv_file_path = Path(dir_path) / "municipios.csv"

        with csv_file_path.open(encoding="utf-8") as file:
            reader = csv.DictReader(file)  # Lê o arquivo CSV como um dicionário
            for row in reader:
                cod_uf = row["COD UF"]
                cod_ibge = row["COD IBGE"]
                nome = row["NOME"]

                uf = UnidadeFederativa.objects.get(id=cod_uf)
                Municipio.objects.get_or_create(
                    codigo_ibge=cod_ibge,
                    defaults={
                        "nome": nome,
                        "uf": uf,
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Município {nome} criado ou atualizado ."),
                )
