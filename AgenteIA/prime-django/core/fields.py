import re

from brutils import cnpj, cpf
from django.core.exceptions import ValidationError
from django.db import models
import logging

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

class SNBooleanField(models.Field):
    description = "Um campo Booleano que é armazenado como 'S' ou 'N' no banco de dados."

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 1
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        # Retorna o tipo de dado no banco de dados.
        # Pode precisar de ajuste dependendo do banco de dados utilizado.
        return "char(1)"

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return value == "S"

    def to_python(self, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return value
        if value in ("S", "s"):
            return True
        elif value in ("N", "n"):
            return False
        else:
            raise ValidationError("Este campo só aceita 'S' ou 'N' como valores.")

    def get_prep_value(self, value):
        # Converte os valores Python para um formato que o banco de dados entenda.
        if value is True:
            return "S"
        elif value is False:
            return "N"
        elif value is None:
            return None
        else:
            raise ValidationError("Este campo só aceita valores booleanos.")

    def get_internal_type(self):
        return "CharField"


class DocumentoField(models.CharField):
    description = "Campo que armazena um documento, formatando-o como CPF ou CNPJ."

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 18  # Ajuste conforme necessário
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value is None:
            return value
        value = re.sub("[^0-9]", "", str(value))
        if len(value) == 11:
            return cpf.format(value)
        elif len(value) == 14:
            return cnpj.format(value)
        return value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        # A formatação será aplicada ao recuperar o valor do banco
        return self.to_python(value)

    def get_prep_value(self, value):
        # Remova a formatação antes de salvar no banco
        return re.sub("[^0-9]", "", str(value))

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        value = re.sub("[^0-9]", "", str(value))
        if len(value) == 11:
            if not cpf.validate(value):
                raise ValidationError("CPF inválido.")
        elif len(value) == 14:
            if not cnpj.validate(value):
                raise ValidationError("CNPJ inválido.")
        else:
            raise ValidationError("Número de documento inválido.")
        return self.to_python(value)
