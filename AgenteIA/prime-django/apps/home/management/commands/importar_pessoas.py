import logging
import os
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Q

from apps.home.helpers import adicionar_fuso_horario_em_data
from apps.home.models import Livro05
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_nome, somente_numeros

logger = logging.getLogger(__name__)
path_dir = os.path.split(os.path.abspath(__file__))[0]
MIN_DATE = datetime.min.date()


# Classe do comando
class Command(BaseCommand):
    help = "Importar pessoas do FB"

    def handle(self, *args, **kwargs) -> None:
        batch_size = 1000  # Defina o tamanho do lote
        offset = 0
        total_processed = 0
        with FbConnection() as db:
            while True:
                # Ajuste a consulta SQL para usar ROWS
                query = f"""
                            SELECT CHAVE_PESSOAS, CPF, NOME, NACIONALIDADE, PROFISSAO, DOCUMENTO, NOMEPAI , NOMEMAE, DATA_CADASTRO, CIDADE ,
                            UF, CHAVE_CONJUGE, SEXO  , CEP, EMAIL, ENDERECO , DATA_NASCIMENTO, DATA_EXPEDICAO , NATURALIDADE, PESSOA_JURIDICA,
                            DATA_ATUALIZACAO, TELEFONE, CHAVE_CATEGORIAS , CHAVE_TIPO_REGIME , CHAVE_DOCUMENTOS, TIPO_PESSOA , NUMEROCONTROLE,
                            NOME_ORIGINAL, ORGAO_EMISSOR, STATUS, DATACASAMENTO, TIPOCASAMENTO
                            FROM PESSOAS
                            ORDER BY CHAVE_PESSOAS ASC
                            ROWS {offset + 1} TO {offset + batch_size}
                        """
                pessoas = db.execute_query(query)

                if not pessoas:
                    break  # Sai do loop se não houver mais dados para processar

                novos_registros = []
                registros_para_atualizar = []

                for pessoa in pessoas:
                    pk = pessoa["CHAVE_PESSOAS"]
                    naturalidade = (
                        pessoa["NATURALIDADE"] if pessoa["NATURALIDADE"] else ""
                    )
                    cidade = pessoa["CIDADE"] if pessoa["CIDADE"] else ""
                    uf = pessoa["UF"] if pessoa["UF"] else ""
                    adicionar_fuso_horario_em_data(pessoa["DATA_CADASTRO"]) if pessoa[
                        "DATA_CADASTRO"
                    ] else MIN_DATE

                    conjuge = (
                        pessoa["CHAVE_CONJUGE"] if pessoa["CHAVE_CONJUGE"] else "0"
                    )
                    estado_civil_id = (
                        pessoa["CHAVE_CATEGORIAS"]
                        if pessoa["CHAVE_CATEGORIAS"]
                        else "0"
                    )
                    tipo_regime_id = (
                        pessoa["CHAVE_TIPO_REGIME"]
                        if pessoa["CHAVE_TIPO_REGIME"]
                        else "0"
                    )
                    tipo_documento_id = (
                        pessoa["CHAVE_DOCUMENTOS"]
                        if pessoa["CHAVE_DOCUMENTOS"]
                        else "0"
                    )

                    obj = Livro05(
                        id=pk,
                        cpf=somente_numeros(pessoa["CPF"]) if pessoa["CPF"] else "0",
                        nome=formatar_nome(pessoa.get("NOME") or "(Não Informado)"),
                        nacionalidade=pessoa["NACIONALIDADE"]
                        if pessoa["NACIONALIDADE"]
                        else "Brasileira",
                        profissao=pessoa["PROFISSAO"]
                        if pessoa["PROFISSAO"]
                        else "Não Informado",
                        documento=pessoa["DOCUMENTO"]
                        if pessoa["DOCUMENTO"]
                        else "Não Informado",
                        nome_pai=pessoa["NOMEPAI"] if pessoa["NOMEPAI"] else "",
                        nome_mae=pessoa["NOMEMAE"] if pessoa["NOMEMAE"] else "",
                        cidade=cidade,
                        uf=str(uf).upper() if uf else "MG",
                        conjuge=conjuge,
                        sexo=pessoa["SEXO"],
                        cep=pessoa["CEP"],
                        email=str(pessoa["EMAIL"]).lower(),
                        endereco=pessoa["ENDERECO"] if pessoa["ENDERECO"] else "",
                        data_nascimento=pessoa["DATA_NASCIMENTO"],
                        data_expedicao=pessoa["DATA_EXPEDICAO"],
                        naturalidade=naturalidade,
                        pessoa_juridica=pessoa["PESSOA_JURIDICA"],
                        data_atualizacao=pessoa["DATA_ATUALIZACAO"]
                        if pessoa["DATA_ATUALIZACAO"]
                        else MIN_DATE,
                        telefone=somente_numeros(pessoa["TELEFONE"]),
                        estado_civil_id=estado_civil_id,
                        tipo_regime_casamento_id=tipo_regime_id,
                        tipo_documento=tipo_documento_id,
                        tipo_pessoa=pessoa["TIPO_PESSOA"],
                        numero_controle=pessoa["NUMEROCONTROLE"],
                        nome_original=pessoa["NOME_ORIGINAL"],
                        orgao_emissor=pessoa["ORGAO_EMISSOR"],
                        situacao=pessoa["STATUS"],
                        data_casamento=pessoa["DATACASAMENTO"],
                        tipo_casamento=pessoa["TIPOCASAMENTO"],
                        temporario_conjuge=conjuge,
                    )

                    if Livro05.objects.filter(id=pk).exists():
                        registros_para_atualizar.append(obj)
                    else:
                        novos_registros.append(obj)

                # Realiza a criação em massa dos novos registros
                if novos_registros:
                    Livro05.objects.bulk_create(novos_registros)

                # Realiza a atualização em massa dos registros existentes
                if registros_para_atualizar:
                    Livro05.objects.bulk_update(
                        registros_para_atualizar,
                        [
                            "cpf",
                            "nome",
                            "nacionalidade",
                            "profissao",
                            "documento",
                            "nome_pai",
                            "nome_mae",
                            "cidade",
                            "uf",
                            "conjuge",
                            "sexo",
                            "cep",
                            "email",
                            "endereco",
                            "data_nascimento",
                            "data_expedicao",
                            "naturalidade",
                            "pessoa_juridica",
                            "data_atualizacao",
                            "telefone",
                            "estado_civil_id",
                            "tipo_regime_casamento_id",
                            "tipo_documento",
                            "tipo_pessoa",
                            "numero_controle",
                            "nome_original",
                            "orgao_emissor",
                            "situacao",
                            "data_casamento",
                            "tipo_casamento",
                            "temporario_conjuge",
                        ],
                    )

                total_processed += len(pessoas)
                offset += batch_size
                logger.info(f"Processados {total_processed} registros até agora")

        # # Mensagem de sucesso
        self.stdout.write(self.style.SUCCESS("Tabelas Livro05 adicionadas!"))

        # Atualizar o campo conjuge
        Livro05.objects.filter(temporario_conjuge__isnull=False).update(
            conjuge=models.F("temporario_conjuge"),
        )

        # Atualizar o CPF ou CNPJ vazio para o codigo zero
        Livro05.objects.filter(Q(cpf__isnull=True) | Q(cpf="")).update(cpf="0")

        # Mensagem de sucesso
        self.stdout.write(self.style.SUCCESS("Conjugue atualizado!"))


### CRIAR METODO PARA GERAR O OBJETO PESSOAS - PELO ID DE QUALQUER PARTE DO SISTEMA
