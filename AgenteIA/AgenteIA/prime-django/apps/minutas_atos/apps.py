from django.apps import AppConfig


class MinutasAtosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.minutas_atos"
    label = "minutas_atos"
    verbose_name = "Minuta Ato"

    def ready(self) -> None:
        from apps.minutas_atos import signals

        if signals.SIGNALS_IMPORTED:
            pass
