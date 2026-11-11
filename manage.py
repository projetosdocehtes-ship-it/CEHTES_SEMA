import codecs
import logging
import os
import sys

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


def main() -> None:
    import import_timing  # noqa: F401

    """Executa comandos administrativos."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        msg = """ Não foi possível importar o Django. Tem certeza de que está instalado e
                    disponível em sua variável de ambiente PYTHONPATH? Você
                    esqueceu de ativar um ambiente virtual?
                """
        raise ImportError(msg) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
