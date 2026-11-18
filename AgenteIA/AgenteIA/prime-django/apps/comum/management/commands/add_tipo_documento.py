from django.core.management.base import BaseCommand

from apps.comum.models import TipoDocumento


class Command(BaseCommand):
    help = "Cria as unidades federativas do Brasil"

    def handle(self, *args, **kwargs) -> None:
        lista = [
            {"id": 2, "sigla": "CARTAO_IDOSO", "nome": "Cartão do Idoso"},
            {"id": 3, "sigla": "CARTEIRA_ESTUDANTE", "nome": "Carteira de Estudante"},
            {"id": 4, "sigla": "CARTEIRA_PESCA", "nome": "Carteira de Pesca"},
            {"id": 5, "sigla": "CASAMENTO", "nome": "Certidão de Casamento"},
            {"id": 6, "sigla": "CIE", "nome": "Cédula de Identidade de Estrangeiro"},
            {
                "id": 7,
                "sigla": "CNH_INTERNACIONAL",
                "nome": "Carteira de Motorista Internacional",
            },
            {"id": 8, "sigla": "CNH", "nome": "Carteira Nacional de Habilitação"},
            {"id": 9, "sigla": "CNPJ", "nome": "Cadastro Nacional de Pessoa Jurídica"},
            {"id": 10, "sigla": "CPF", "nome": "Cadastro de Pessoas Físicas"},
            {
                "id": 11,
                "sigla": "CREA",
                "nome": "Conselho Regional de Engenharia e Agronomia",
            },
            {"id": 12, "sigla": "CRM", "nome": "Conselho Regional de Medicina"},
            {"id": 13, "sigla": "CTPS_DIGITAL", "nome": "Carteira de Trabalho Digital"},
            {
                "id": 14,
                "sigla": "CTPS",
                "nome": "Carteira de Trabalho e Previdência Social",
            },
            {"id": 15, "sigla": "DNI", "nome": "Documento Nacional de Identidade"},
            {
                "id": 16,
                "sigla": "IDENTIDADE_MILITAR",
                "nome": "Carteira de Identidade de Militar",
            },
            {
                "id": 17,
                "sigla": "INSCRICAO_ESTADUAL",
                "nome": "Cartão de Inscrição Estadual",
            },
            {"id": 18, "sigla": "NASCIMENTO", "nome": "Certidão de Nascimento"},
            {"id": 19, "sigla": "OAB", "nome": "Ordem dos Advogados do Brasil"},
            {"id": 20, "sigla": "PASSAPORTE", "nome": "Passaporte"},
            {"id": 21, "sigla": "PIS_PASEP", "nome": "PIS/PASEP"},
            {"id": 22, "sigla": "PRODUTOR_RURAL", "nome": "Cartão do Produtor Rural"},
            {"id": 23, "sigla": "RESERVISTA", "nome": "Certificado de Reservista"},
            {"id": 24, "sigla": "RG", "nome": "Registro Geral"},
            {"id": 25, "sigla": "RNE", "nome": "Registro Nacional de Estrangeiro"},
            {"id": 26, "sigla": "SUS", "nome": "Cartão do Sistema Único de Saúde"},
            {"id": 27, "sigla": "TITULO", "nome": "Título de Eleitor"},
        ]

        for item in lista:
            TipoDocumento.objects.update_or_create(
                id=item["id"],
                defaults={"sigla": item["sigla"], "nome": item["nome"]},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Tipo de Documento {item['nome']} criado ou atualizado ",
                ),
            )
