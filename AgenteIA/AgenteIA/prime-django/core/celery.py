import os

from celery import Celery
import logging

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

# Defina a variável de ambiente padrão do Django para o arquivo 'settings.py' do seu projeto.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("prime")

# Namespace='CELERY' significa que todas as configurações relacionadas ao celery devem
# ter o prefixo 'CELERY_' no arquivo settings.py.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Carrega automaticamente as tarefas definidas em seus aplicativos Django
app.autodiscover_tasks()
