import logging

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

TIPO_DOCUMENTO_CHOICES = [
    ("CARTAO_IDOSO", "Cartão do Idoso"),
    ("CARTEIRA_ESTUDANTE", "Carteira de Estudante"),
    ("CARTEIRA_PESCA", "Carteira de Pesca"),
    ("CASAMENTO", "Certidão de Casamento"),
    ("CIE", "Cédula de Identidade de Estrangeiro"),
    ("CNH_INTERNACIONAL", "Carteira de Motorista Internacional"),
    ("CNH", "Carteira Nacional de Habilitação (CNH)"),
    ("CNPJ", "Cadastro Nacional de Pessoa Jurídica"),
    ("CPF", "Cadastro de Pessoas Físicas (CPF)"),
    ("CREA", "Conselho Regional de Engenharia e Agronomia"),
    ("CRM", "Conselho Regional de Medicina"),
    ("CTPS_DIGITAL", "Carteira de Trabalho Digital"),
    ("CTPS", "Carteira de Trabalho e Previdência Social (CTPS)"),
    ("DNI", "Documento Nacional de Identidade"),
    ("IDENTIDADE_MILITAR", "Carteira de Identidade de Militar"),
    ("INSCRICAO_ESTADUAL", "Cartão de Inscrição Estadual"),
    ("NASCIMENTO", "Certidão de Nascimento"),
    ("OAB", "Ordem dos Advogados do Brasil"),
    ("PASSAPORTE", "Passaporte"),
    ("PIS_PASEP", "PIS/PASEP"),
    ("PRODUTOR_RURAL", "Cartão do Produtor Rural"),
    ("RESERVISTA", "Certificado de Reservista"),
    ("RG", "Registro Geral (RG)"),
    ("RNE", "Registro Nacional de Estrangeiro"),
    ("SUS", "Cartão do Sistema Único de Saúde"),
    ("TITULO", "Título de Eleitor"),
]
