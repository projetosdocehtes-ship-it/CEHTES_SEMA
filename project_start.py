import cProfile
import os
import pstats
import time

import django
from django.core.management import call_command


def profile_imports():
    modules = [
        "os",
        "apps.home.models.home_models",
        # Adicione todos os módulos que você deseja profilear
    ]
    for module in modules:
        start_time = time.time()
        __import__(module)
        end_time = time.time()
        print(f"Time to import {module}: {end_time - start_time:.4f} seconds")


def profile_startup():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    # Inicialize o Django
    django.setup()
    # Execute o comando runserver para simular a inicialização
    call_command("runserver", "127.0.0.1:8000", use_threading=False)


if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    profile_startup()
    profile_imports()
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumtime").print_stats(25)
