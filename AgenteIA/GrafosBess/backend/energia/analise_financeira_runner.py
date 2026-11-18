import json
import sys
from pathlib import Path

from django.conf import settings


def _json_default(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def main():
    entradas_path = Path(sys.argv[1])
    saida_path = Path(sys.argv[2])
    media_root = Path(sys.argv[3])
    prime_django_path = Path(sys.argv[4])

    sys.path.insert(0, str(prime_django_path))
    settings.configure(
        BASE_DIR=prime_django_path,
        MEDIA_ROOT=media_root,
        MEDIA_URL="/media/",
    )

    from apps.AnaliseEconomica.analise_financeira import AnaliseFinanceiraMicrorrede

    analise = AnaliseFinanceiraMicrorrede(
        entradas_path=entradas_path,
        distribuidora="EQUATORIAL GO",
        modalidade="verde",
        vida_util=20,
        taxa_desconto=0.08,
    )
    resultado = analise.executar_analise_completa()

    with saida_path.open("w", encoding="utf-8") as arquivo:
        json.dump(resultado, arquivo, ensure_ascii=False, default=_json_default)


if __name__ == "__main__":
    main()
