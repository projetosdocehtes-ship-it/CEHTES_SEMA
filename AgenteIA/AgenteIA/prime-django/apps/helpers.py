"""Copyright (c) 2019 - present AppSeed.us."""

import logging
from pathlib import Path

from django.conf import settings
from storages.backends.ftp import FTPStorage

from apps.cartorios.models import Usuario as CustomUser

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
# from apps.authentication.models import CustomUser


def upload(username, image):
    file_obj = image

    # do your validation here e.g. file size/type check

    # organize a path for the file in bucket
    file_directory_within_bucket = f"{username}"

    # synthesize a full file path; note that we included the filename
    file_path_within_bucket = Path(file_directory_within_bucket) / file_obj.name

    media_storage = FTPStorage()

    # avoid overwriting existing file
    if not media_storage.exists(file_path_within_bucket):
        media_storage.save(file_path_within_bucket, file_obj)

    return media_storage.url(file_path_within_bucket)


def cfg_val(var_name):
    return getattr(settings, var_name, None)


def cfg_login_attempts():
    return cfg_val("LOGIN_ATTEMPTS")


def cfg_ftp_upload():
    return cfg_val("FTP_UPLOAD")


def username_exists(username):
    user_query = CustomUser.objects.filter(username=username)
    if user_query.exists():
        return user_query.first()

    return False


def delete_user(to_delete_user_username):
    user = CustomUser.objects.filter(username=to_delete_user_username)
    if not user.exists():
        return False, "User not found."
    if user.last().is_superuser:
        return False, "Cannot delete superuser."
    try:
        user.delete()
    except Exception as e:
        return False, str(e)
    return True, f"{to_delete_user_username} deleted successfully."


def email_exists(email):
    user_query = CustomUser.objects.filter(email=email)

    if user_query.exists():
        return user_query.first()

    return False


def formatos_de_datas():
    return ["%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]


