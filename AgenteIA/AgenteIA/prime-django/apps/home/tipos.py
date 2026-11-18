import logging

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class TipoRegistro:
    MATRICULA = "M"
    AVERBACAO = "A"
    TRANSCRICAO = "T"
    INSCRICAO = "I"

    CHOICES = (
        (MATRICULA, "Matrícula"),
        (AVERBACAO, "Registro Auxiliar (L3)"),
        (TRANSCRICAO, "Transcrição"),
        (INSCRICAO, "Inscrição"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Matrícula")


class TipoAto:
    MATRICULA = "M"
    AVERBACAO = "A"
    TRANSCRICAO = "T"
    INSCRICAO = "I"
    REGISTRO = "R"

    CHOICES = (
        (MATRICULA, "Matrícula"),
        (AVERBACAO, "Registro Auxiliar (L3)"),
        (TRANSCRICAO, "Transcrição"),
        (INSCRICAO, "Inscrição"),
        (REGISTRO, "Registro"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Matrícula")


class TipoImportacao:
    Total = "T"
    Parcial = "P"

    CHOICES = (
        (Total, "Total"),
        (Parcial, "Parcial"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Total")


class TipoClasseRegistro:
    URBANO = "U"
    RURAL = "R"
    LOTE = "L"
    CONDOMINIO = "C"
    TODAS = "T"

    CHOICES = (
        (URBANO, "Urbano"),
        (RURAL, "Rural"),
        (LOTE, "Lote"),
        (CONDOMINIO, "Condomínio"),
        (TODAS, "Todas"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")


class CartorioNumero:
    Um = "1"
    Dois = "2"
    Tres = "3"

    CHOICES = (
        (Um, "1"),
        (Dois, "2"),
        (Tres, "3"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")


class TipoParte:
    ADQUIRENTE = "A"
    TRANSMITENTE = "T"
    DEVEDOR = "D"
    CREDOR = "C"
    SOLICITANTE = "S"
    REQUERENTE = "R"
    OUTROS = "O"
    PROCURADOR = "P"
    TESTEMUNHA = "E"
    FIADOR = "F"
    GARANTIDOR = "G"
    INTERVENIENTE = "I"
    FIELDEPOSITARIO = "L"
    EMITENTE = "M"
    ANUENTE = "N"
    EMITENTEFIELDEPOSITARIO = "O"
    APRESENTANTE = "S"
    AVALISTA = "V"

    CHOICES = (
        (ADQUIRENTE, "Adquirente"),
        (TRANSMITENTE, "Transmitente"),
        (DEVEDOR, "Devedor"),
        (CREDOR, "Credor"),
        (REQUERENTE, "Requerente"),
        (SOLICITANTE, "Solicitante"),
        (OUTROS, "Outros"),
        (PROCURADOR, "Procurador"),
        (TESTEMUNHA, "Testemunha"),
        (FIADOR, "Fiador"),
        (GARANTIDOR, "Garantidor"),
        (INTERVENIENTE, "Interveniente"),
        (FIELDEPOSITARIO, "Fiel Depositário"),
        (EMITENTE, "Emitente"),
        (ANUENTE, "Anuente"),
        (EMITENTEFIELDEPOSITARIO, "Emitente e Fiel Depositário"),
        (PROCURADOR, "Procurador"),
        (REQUERENTE, "Requerente"),
        (APRESENTANTE, "Apresentante"),
        (AVALISTA, "Avalista"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")


class TipoEvento:
    REGISTRO = "R"
    AVERBACAO = "A"
    TRANSCRICAO = "T"
    CANCELAMENTO = "C"
    RETIFICACAO = "E"
    CERTIDAO = "C"
    OUTROS = "O"

    CHOICES = (
        (REGISTRO, "Registro"),
        (AVERBACAO, "Averbação"),
        (TRANSCRICAO, "Transcrição"),
        (CANCELAMENTO, "Cancelamento"),
        (RETIFICACAO, "Retificação"),
        (CERTIDAO, "Certidão"),
        (OUTROS, "Outros"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")


class TipoSexo:
    MASCULINO = "M"
    FEMININO = "F"
    OUTROS = "O"
    NAO_INFORMADO = "N"

    CHOICES = (
        (MASCULINO, "Masculino"),
        (FEMININO, "Feminino"),
        (OUTROS, "Outros"),
        (NAO_INFORMADO, "Não Informado"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Não Informado")


class TipoSimNao:
    SIM = "S"
    NAO = "N"

    CHOICES = (
        (SIM, "Sim"),
        (NAO, "Não"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "")


class TipoAtivoCancelado:
    ATIVO = "A"
    CANCELADO = "C"

    CHOICES = (
        (ATIVO, "Sim"),
        (CANCELADO, "Não"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "")


class TipoStatusProtocolo:
    """
    Tipos:

    0	Em Andamento
    1	Exigência
    2	Cancelado           FINALIZAR = S
    3	Registrado          FINALIZAR = S
    4	SubJudice
    5	Em Registro
    6	Pronto para Registrar
    7	Distribuido
    """

    EM_ANDAMENTO = "0"
    EXIGENCIA = "1"
    CANCELADO = "2"
    REGISTRADO = "3"
    SUBJUDICE = "4"
    EM_REGISTRO = "5"
    PRONTO_PARA_REGISTRAR = "6"
    DISTRIBUIDO = "7"

    CHOICES = (
        (EM_ANDAMENTO, "Em Andamento"),
        (EXIGENCIA, "Exigência"),
        (CANCELADO, "Cancelado"),
        (REGISTRADO, "Registrado"),
        (SUBJUDICE, "SubJudice"),
        (EM_REGISTRO, "Em Registro"),
        (PRONTO_PARA_REGISTRAR, "Pronto para Registrar"),
        (DISTRIBUIDO, "Distribuido"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Em Andamento")


class TipoFaseAgenda:
    PROTOCOLO = 40
    EVENTO = 100
    AGENDA = 200
    AGENDA_PROTOCOLO = 300
    AGENDA_EVENTO = 400

    CHOICES = (
        (PROTOCOLO, "Protocolo"),
        (EVENTO, "Evento"),
        (AGENDA, "Agenda"),
        (AGENDA_PROTOCOLO, "Agenda Protocolo"),
        (AGENDA_EVENTO, "Agenda Evento"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "")


class TipoDocumento:
    RECIBO = "R"
    CONTRATO = "C"
    NOTA_PROMISSORIA = "N"
    CHEQUE = "H"
    BOLETO = "B"
    CUPOM_FISCAL = "F"
    FATURA = "T"
    OUTROS = "O"

    CHOICES = (
        (RECIBO, "Recibo"),
        (CONTRATO, "Contrato"),
        (NOTA_PROMISSORIA, "Nota Promissória"),
        (CHEQUE, "Cheque"),
        (BOLETO, "Boleto"),
        (CUPOM_FISCAL, "Cupom Fiscal"),
        (FATURA, "Fatura"),
        (OUTROS, "Outros"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")


class TipoTransacao:
    CREDITO = "1"
    DEBITO = "2"

    CHOICES = (
        (CREDITO, "Crédito"),
        (DEBITO, "Débito"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, None)


class TipoOperacaoFinanceira:
    PAGAMENTO = "P"
    RECEBIMENTO = "R"
    TRANSFERENCIA = "T"

    CHOICES = (
        (PAGAMENTO, "Pagamento"),
        (RECEBIMENTO, "Recebimento"),
        (TRANSFERENCIA, "Transferência"),
    )

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")


# class Descricoes:
#     EXIGENCIA = "Exigência"
#     CANCELADO = "Cancelado"
#     REGISTRADO = "Registrado"
#     SUBJUDICE = "SubJudice"
#     EM_REGISTRO = "Em Registro"
#     PRONTO_PARA_REGISTRAR = "Pronto para Registrar"
#     DISTRIBUIDO = "Distribuido"
#     EM_ANDAMENTO = "Em Andamento"

#     EMITIDO = "Emitido"


class Parte:
    def __init__(self, nome: str, cpf: str, rg: str, tipo: str):
        self.nome = nome
        self.cpf = cpf
        self.rg = rg
        self.tipo = tipo


class TipoUnidade:
    Quadra = "Quadra"
    Lote = "Lote"
