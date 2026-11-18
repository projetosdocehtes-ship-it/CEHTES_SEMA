# Importações necessárias


from django.core.management.base import BaseCommand


# Classe do comando
class Command(BaseCommand):
    help = "Importa o cartório do FB para o PostgreSQL."

    # Método que será executado ao rodar o comando
    def handle(self, *args, **kwargs) -> None:
        try:
            from apps.home.services.firebird import importar_cartorio_fb

            importar_cartorio_fb()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao importar o cartório: {e}"))
            return
