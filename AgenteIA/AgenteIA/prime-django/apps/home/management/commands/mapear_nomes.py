from django.core.management.base import BaseCommand

from apps.home.models import Colaborador


class Command(BaseCommand):
    help = "Atualiza os nomes dos colaboradores com base no NOME_MAP"

    def handle(self, *args, **options) -> None:
        for colaborador in Colaborador.objects.all():
            nome_mapeado = Colaborador.get_nome_mapeado(colaborador.username)
            # Verifica se o nome precisa ser atualizado para evitar salvar desnecessariamente
            if colaborador.username != nome_mapeado:
                colaborador.username = nome_mapeado
                colaborador.save()
                # Caso tenha mudanças, imprime o nome com as mudanças
                self.stdout.write(
                    self.style.SUCCESS(f"Atualizado: {colaborador.username}"),
                )
            else:
                # Caso não tenha mudanças, imprime o nome sem alterações
                self.stdout.write(f"Sem alterações: {colaborador.username}")
