import os
import sys
import threading

from django.apps import AppConfig


class EnergiaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "energia"

    def ready(self):
        if "runserver" not in sys.argv:
            return
        if os.environ.get("RUN_MAIN") != "true" and "--noreload" not in sys.argv:
            return

        def aquecer():
            try:
                from .services import aquecer_motor_fluxo_potencia

                aquecer_motor_fluxo_potencia()
            except Exception:
                # A chamada normal continuará exibindo o erro detalhado ao usuário.
                return

        threading.Thread(target=aquecer, name="aquecimento-fluxo-potencia", daemon=True).start()
