from django.core.management.base import BaseCommand
from django.db import transaction

from apps.home.models import PrazoLegal, TipoCertidao, TipoItemCertidao


class Command(BaseCommand):
    help = "Insere tipos de certidão no banco de dados"

    def handle(self, *args, **kwargs) -> None:
        certidoes_ambos = [
            (
                "Certidão de Situação Fiscal e Enfitêutica",
                "8601-7",
            ),
            (
                "Certidão de Ações Reais e Pessoais Reipersecutórias",
                "8402-0",
            ),
        ]

        certidoes_pessoas = [
            (
                "Certidão de Propriedade",
                "8402-0",
            ),
            (
                "Certidão de Busca de Bens",
                "8301-4",
            ),
            (
                "Certidão de Pacto Antinupcial",
                "8402-0",
            ),
        ]

        certidoes_imoveis = [
            (
                "Certidão Negativa de Ônus e Alienações",
                "8402-0",
            ),
            (
                "Certidão de Ônus Reais",
                "8402-0",
            ),
            (
                "Certidão de Matrícula",
                "8401-2",
            ),
            (
                "Certidão de Inteiro Teor",
                "8401-2",
            ),
            (
                "Certidão Negativa de Registro",
                "8402-0",
            ),
            (
                "Certidão de Convenção de Condomínio",
                "8402-0",
            ),
            (
                "Certidão Vintenária",
                "8402-0",
            ),
        ]

        with transaction.atomic():
            certidoes_ambos_ordenadas = sorted(certidoes_ambos, key=lambda x: x[0])
            for nome, codigo in certidoes_ambos_ordenadas:
                tipo_item_default = TipoItemCertidao.get_default_tipo_item_certidao()
                prazo_legal_default = PrazoLegal.get_default_prazo_legal()

                TipoCertidao.objects.get_or_create(
                    nome=nome,
                    defaults={
                        "codigo": codigo,
                        "tipo_item": tipo_item_default,
                        "prazo_legal": prazo_legal_default,
                    },
                )
        # Mensagem de sucesso
        self.stdout.write(self.style.SUCCESS("Certidões de Ambos adicionadas!"))

        with transaction.atomic():
            certidoes_pessoas_ordenadas = sorted(certidoes_pessoas, key=lambda x: x[0])
            for nome, codigo in certidoes_pessoas_ordenadas:
                tipo_item_pessoa = (
                    TipoItemCertidao.get_default_tipo_item_certidao_pessoa()
                )
                prazo_legal_default = PrazoLegal.get_default_prazo_legal()

                TipoCertidao.objects.get_or_create(
                    nome=nome,
                    defaults={
                        "codigo": codigo,
                        "tipo_item": tipo_item_pessoa,
                        "prazo_legal": prazo_legal_default,
                    },
                )
        # Mensagem de sucesso
        self.stdout.write(self.style.SUCCESS("Certidões de Pessoas adicionadas!"))

        with transaction.atomic():
            certidoes_imoveis_ordenadas = sorted(certidoes_imoveis, key=lambda x: x[0])
            for nome, codigo in certidoes_imoveis_ordenadas:
                tipo_item_imovel = (
                    TipoItemCertidao.get_default_tipo_item_certidao_imovel()
                )
                prazo_legal_default = PrazoLegal.get_default_prazo_legal()

                TipoCertidao.objects.get_or_create(
                    nome=nome,
                    defaults={
                        "codigo": codigo,
                        "tipo_item": tipo_item_imovel,
                        "prazo_legal": prazo_legal_default,
                    },
                )

        # Mensagem de sucesso
        self.stdout.write(self.style.SUCCESS("Certidões de Imóveis adicionadas!"))
