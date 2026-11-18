from django.apps import AppConfig


class IntegracoesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integracoes"
    label = "integracoes"
    verbose_name = "Integrações"

    def ready(self) -> None:
        from apps.integracoes import signals

        if signals.SIGNALS_IMPORTED:
            pass
