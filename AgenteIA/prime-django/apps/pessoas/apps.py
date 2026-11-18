import contextlib

from django.apps import AppConfig


class PessoasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pessoas"
    label = "pessoas"
    verbose_name = "Pessoas"

    def ready(self: AppConfig) -> None:
        # Registra todos os models deste app para auditoria (auditlog)
        from auditlog.registry import auditlog

        app_models = self.get_models()
        for model in app_models:
            with contextlib.suppress(Exception):
                auditlog.register(model)

        from apps.pessoas import signals

        if signals.SIGNALS_IMPORTED:
            pass
