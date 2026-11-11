import logging
import os

from django.conf import settings
from django.core.management import execute_from_command_line

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def start_server() -> None:
    # Define a variável de ambiente DJANGO_SETTINGS_MODULE com o caminho para o arquivo de configurações do Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    # Importa e configura o Django
    import django

    django.setup()

    # Verifica se o modo DEBUG está ativado nas configurações do Django
    if settings.DEBUG:
        # Executa o servidor de desenvolvimento embutido do Django
        execute_from_command_line(
            ["manage.py", "runserver", "--noreload", "0.0.0.0:8000"],
        )
    else:
        # Executa o servidor usando Waitress em produção
        from waitress import serve

        from core.wsgi import application

        # Inicia o servidor Waitress com a aplicação WSGI do Django
        serve(application, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # Inicia o servidor chamando a função start_server
    start_server()
