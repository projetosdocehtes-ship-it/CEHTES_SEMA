# Importações necessárias
import uuid

from django.core.management.base import BaseCommand

from apps.home.models import (
    Finalidade,  # Ajuste o caminho para o seu modelo Finalidade
)


# Classe do comando
class Command(BaseCommand):
    help = "Adiciona finalidades ao model Finalidade"

    # Método que será executado ao rodar o comando
    def handle(self, *args, **kwargs) -> None:
        # Lista de finalidades e seus respectivos IDs a serem adicionadas
        finalidades = [
            (
                "f506f7d5-ceee-46f7-afc3-5912b410233c",
                "Investigação jurídico-econômica para fins de avaliação de crédito, solvência ou responsabilidade civil.",
            ),
            (
                "c6dc8fef-ab31-4473-a146-a0fd3d6f27fd",
                "Investigação jurídica sobre o imóvel, sua titularidade ou limitações ao direito de propriedade para fins de contratação ou processamento de inventário.",
            ),
            (
                "cf3fba42-a705-4140-ac4c-5d683313d21d",
                "Investigação para instrução de processos judiciais ou administrativos.",
            ),
            (
                "12483a6e-8810-44bf-92b6-185032ad29df",
                "O solicitante da certidão digital é titular de algum direito real registrado sobre o imóvel.",
            ),
            (
                "449981a1-e890-44c3-af9c-c7f9f2810eba",
                "Não desejo declarar a finalidade.",
            ),
        ]

        # Loop para criar ou atualizar as finalidades
        for str_id, nome in finalidades:
            # Converte a string para um objeto UUID
            uuid_id = uuid.UUID(str_id)
            Finalidade.objects.get_or_create(id=uuid_id, defaults={"nome": nome})

        # Mensagem de sucesso
        self.stdout.write(self.style.SUCCESS("Finalidades adicionadas!"))
