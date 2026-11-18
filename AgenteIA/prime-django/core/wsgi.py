import logging
import locale
import os
import warnings

from django.core.wsgi import get_wsgi_application

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

try:
    # Tenta a configuração comum em sistemas Unix/Linux
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except locale.Error:
    try:
        # Alternativa para Windows
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except locale.Error:
        print("Localidade não suportada")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Suprimir especificamente o RuntimeWarning sobre acesso ao banco de dados
warnings.filterwarnings(
    "ignore",
    category=RuntimeWarning,
    message="Accessing the database during app initialization is discouraged",
    module="django.db.backends.utils",
    lineno=98,
)

print("\n=======================================")
print("Iniciando Projeto CEHTES")
print("=======================================\n")

application = get_wsgi_application()
