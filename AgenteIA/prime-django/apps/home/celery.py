import os

from celery import Celery
from celery.schedules import crontab

# define a variável de ambiente padrão do Django para o módulo de configurações do projeto.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("apps.home")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "run-sync-task-every-5-minutes": {
        "task": "nome_do_app.tasks.sync_task",
        "schedule": crontab(minute="*/5"),
    },
}
