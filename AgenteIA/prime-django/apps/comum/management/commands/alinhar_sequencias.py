from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models.fields import AutoField, BigAutoField
from django.db.utils import ProgrammingError


class Command(BaseCommand):
    help = "Alinha as sequences de todos os modelos com um campo de chave primária autoincrementado ao valor máximo da PK."

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write(
            self.style.SUCCESS("Iniciando o alinhamento das sequences..."),
        )

        with connection.cursor() as cursor:
            for model in apps.get_models():
                if isinstance(model._meta.pk, AutoField | BigAutoField):
                    table_name = model._meta.db_table
                    pk_column = model._meta.pk.name

                    try:
                        model.objects.latest(pk_column).pk
                    except model.DoesNotExist:
                        continue
                    except ProgrammingError:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Erro ao acessar o modelo {model._meta.object_name}: ",
                            ),
                        )
                        continue

                    sequence_name = f"{table_name}_{pk_column}_seq"
                    align_sequence_sql = f"SELECT setval('{sequence_name}', COALESCE((SELECT MAX({pk_column})+1 FROM {table_name}), 1), false);"

                    try:
                        cursor.execute(align_sequence_sql)
                        self.stdout.write(
                            self.style.SUCCESS(f"Sequence alinhada para {table_name}."),
                        )
                    except Exception:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Não foi possível alinhar a sequence para {table_name}: ",
                            ),
                        )

        self.stdout.write(self.style.SUCCESS("Alinhamento das sequences concluído."))
