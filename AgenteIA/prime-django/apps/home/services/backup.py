import logging
import subprocess
from pathlib import Path

import dj_database_url
from django.conf import settings
from django.utils import timezone

from core.settings import construir_postgre_url

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def realizar_backup_database() -> None:
    from apps.home.models import Backup

    db_url = construir_postgre_url()
    db_config = dj_database_url.parse(db_url)
    db_name = db_config["NAME"]
    db_user = db_config["USER"]

    # Define o caminho do diretório de backup e cria o diretório se não existir
    backup_dir = Path(settings.MEDIA_ROOT) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Define o nome do arquivo de backup
    filename = f"{db_name}_backup_{timezone.now().strftime('%Y%m%d%H%M%S')}.sql"
    backup_path = backup_dir / filename

    if db_config["ENGINE"] == "django.db.backends.postgresql":
        backup_cmd = f'pg_dump -U {db_user} -d {db_name} -f "{backup_path}"'
    else:
        msg = "Motor de banco de dados não suportado para backup."
        raise ValueError(msg)

    # Executa o comando de backup
    subprocess.check_call(backup_cmd, shell=True)

    # Adiciona o registro do backup ao model
    Backup.objects.create(
        arquivo="backups/" + filename,
        tamanho_arquivo=backup_path.stat().st_size,
    )
