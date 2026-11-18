import logging
import datetime
import sys
import traceback
from pathlib import Path
from django.utils.deprecation import MiddlewareMixin
import threading

from django.contrib.auth import get_user_model
from django.http.response import HttpResponseForbidden
from django.utils import timezone

from threading import local
from django.utils.deprecation import MiddlewareMixin

_thread_locals = local()

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

_local = threading.local()

# FILTRA IP MIDDLEWARE
class FiltraIPMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Lista de IPs autorizados
        # ips_autorizados = ['127.0.0.1']
        ips_autorizados = [
            "192.168.1.233",
            "192.168.1.2",
            "127.0.0.1",
            "192.168.1.3",
            "192.168.0.127",
        ]

        # IP do usuário
        ip_usuario = request.META.get("REMOTE_ADDR")

        # Verifica se é um IP autorizado
        if ip_usuario not in ips_autorizados:
            # Se não for
            return HttpResponseForbidden("IP não autorizado")

        # Se for um IP autorizado, não fazemos nada
        return None


class DateTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        date_formats = ["%Y-%m-%d", "%d/%m/%Y"]  # Lista dos formatos de data esperados
        updated_get = request.GET.copy()

        for key, value in request.GET.items():
            if key.startswith("data_") and value:
                for date_format in date_formats:
                    try:
                        naive_date = datetime.datetime.strptime(value, date_format)
                        aware_date = timezone.make_aware(naive_date)
                        # Atualiza o dicionário cópia com o valor original após a conversão
                        updated_get[key] = value
                        break  # Sai do loop de formatos de data se a conversão for bem-sucedida
                    except ValueError:
                        pass  # Se ocorrer um ValueError, tenta o próximo formato de data

        request.GET = updated_get  # Substitui o GET original pelo atualizado
        response = self.get_response(request)
        return response


def get_current_request():
    return getattr(_thread_locals, "request", None)


class RequestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _thread_locals.request = request


class FilteredTracebackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as e:
            self.handle_exception(e)

    def handle_exception(self, e):
        tb_list = traceback.extract_tb(sys.exc_info()[2])

        # Obtém o caminho do diretório base do projeto a partir da localização do settings.py
        path_do_projeto = Path(__file__).parent

        # Filtrar o traceback para exibir somente as linhas do seu projeto
        filtered_tb = [tb for tb in tb_list if path_do_projeto in tb.filename]

        # Formate e imprima o traceback filtrado
        formatted_exception = "".join(traceback.format_list(filtered_tb))
        logger.info(formatted_exception, file=sys.stderr)

        raise e


class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            User = get_user_model()
            try:
                User.objects.filter(pk=request.user.pk).update(last_activity=timezone.now())
            except Exception as e:
                logger.error(f"Erro ao atualizar a última atividade do usuário: {e}")
        return response


class CurrentUserMiddleware(MiddlewareMixin):
    """Middleware para armazenar o usuário atual em um thread local."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.user = request.user
        response = self.get_response(request)
        return response

def get_current_user():
    """Retorna o usuário atualmente logado."""
    user = getattr(_local, 'user', None)
    logger.debug(f"Usuário atual: {user}")
    return user if user else None