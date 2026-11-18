import logging
import os
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.home.models import Livro05, Lri, LriDocumento, LriPartesEnvolvidas
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)
path_dir = os.path.split(os.path.abspath(__file__))[0]
MIN_DATE = datetime.min.date()


# Classe do comando
class Command(BaseCommand):
    help = "Iniciar LRI"

    # Método que será executado ao rodar o comandoc
    def handle(self, *args, **kwargs) -> None:
        # Loop para criar ou atualizar o LRI
        query = """
            SELECT      CHAVE_CGI_OFICIOS,
                        OFICIO,
                        PROCESSO,
                        ORIGEM,
                        DATA,
                        TEXTO,
                        NUMINTEIRO,
                        OBSERVACAO,
                        OFICIOESTADO,
                        DATADF,
                        OFICIODF,
                        DATAESTADO,
                        SUBSCRITOPOR,
                        ESTADO,
                        SUBSCRITOPORESTADO,
                        SUBSCRITOPORDF,
                        NROMATRICULA,
                        TIPO,
                        USOINTERNO,
                        DATA_ENVIO,
                        CAB_FICHA,
                        ROD_FICHA
            FROM       CGI_OFICIOS


        """

        print("Selecionando o LRI")
        with FbConnection() as db:
            lri_indisponibilidade = db.execute_query(query)

        maior_numero_id = len(lri_indisponibilidade)
        print("#####", maior_numero_id)

        # Loop para criar ou atualizar os funcionarios
        for x, lri in enumerate(lri_indisponibilidade):
            # Converte a string para um objeto UUID
            lri_id = lri["CHAVE_CGI_OFICIOS"]
            protocolo_indisponibilidade = lri["PROCESSO"]
            numero_do_processo = lri["OFICIO"]
            nome_instituicao = lri["ORIGEM"]
            data_pedido = lri["DATA"]
            observacao = lri["OBSERVACAO"]
            forum_vara = lri["SUBSCRITOPOR"]
            usuario = lri["ESTADO"]
            telefone = lri["SUBSCRITOPORESTADO"]
            email = lri["SUBSCRITOPORDF"]
            uso_origem = lri["USOINTERNO"]
            descricao_cpf_cnpj = lri["OFICIOESTADO"]
            descricao_detalhes = lri["OFICIODF"]
            data = lri["DATA"]

            logger.info(f"Adicionando Lri: ID:{lri_id!s} - {x!s}/{maior_numero_id!s}")

            Lri.objects.update_or_create(
                id=lri_id,
                defaults={
                    "protocolo_indisponibilidade": protocolo_indisponibilidade,
                    "numero_do_processo": numero_do_processo,
                    "nome_instituicao": nome_instituicao,
                    "data_pedido": data_pedido,
                    "forum_vara": forum_vara,
                    "observacao": observacao,
                    "usuario": usuario,
                    "telefone": telefone,
                    "email": email,
                    "uso_origem": uso_origem,
                    "descricao_cpf_cnpj": descricao_cpf_cnpj,
                    "descricao_detalhes": descricao_detalhes,
                    "data": data,
                },
            )

            # GRAVAR PESSOAS ENVOLVIDAS
            # Loop para criar ou atualizar as pessoas
            query = """
                SELECT CHAVE_CGI_PESSOAS,
                CHAVE_CGI_OFICIOS,
                TIPO_ATO,
                NUMERO_ATO,
                VINCULO,
                SITUACAO,
                DATA,
                DATA_CANCELAMENTO,
                CHAVE_PESSOAS,
                NUMERO_ATOINT,
                MATRICULA,
                NUMERO_IMOVEL,
                TIPO_IMOVEL,
                DATA_ENVIO,
                NUMERO,
                TIPO,
                CARTORIO,
                DATAIMPORTACAO,
                PROTOCOLOCANCELADO,
                DATA_ATUALIZACAO,
                CPF_CNPJ,
                USO_INTERNO
            FROM CGI_PESSOAS
            WHERE CHAVE_CGI_OFICIOS = :CHAVE_CGI_OFICIOS
            """
            query = str(query).replace(":CHAVE_CGI_OFICIOS", str(lri_id))

            print("Selecionando o LRI PESSOAS")
            with FbConnection() as db:
                resultados = db.execute_query(query)
            with transaction.atomic():
                # Loop para criar ou atualizar os funcionarios
                for _y, lri_pessoa in enumerate(resultados):
                    lri_pessoa_id = lri_pessoa["CHAVE_CGI_PESSOAS"]
                    pessoa_id = lri_pessoa["CHAVE_PESSOAS"]
                    tipo_ato = lri_pessoa["TIPO_ATO"]
                    numero_ato = lri_pessoa["NUMERO_ATO"]
                    vinculo = lri_pessoa["VINCULO"]
                    situacao = lri_pessoa["SITUACAO"]
                    data = lri_pessoa["DATA"]
                    numero_imovel = (
                        lri_pessoa["NUMERO_IMOVEL"]
                        if lri_pessoa["NUMERO_IMOVEL"]
                        else None
                    )
                    tipo_imovel = lri_pessoa["TIPO_IMOVEL"]
                    data_envio = lri_pessoa["DATA_ENVIO"]
                    numero = lri_pessoa["NUMERO"]
                    tipo = lri_pessoa["TIPO"]
                    cartorio = lri_pessoa["CARTORIO"]
                    data_importacao = lri_pessoa["DATAIMPORTACAO"]
                    cancelado_em = lri_pessoa["DATA_CANCELAMENTO"]
                    data_atualizacao = lri_pessoa["DATA_ATUALIZACAO"]
                    descricao_cpf_cnpj = lri_pessoa["CPF_CNPJ"]
                    uso_origem = lri_pessoa["USO_INTERNO"]
                    matricula = lri_pessoa["MATRICULA"]
                    cancelamento_indisponibilidade = lri_pessoa["PROTOCOLOCANCELADO"]

                    LriPartesEnvolvidas.objects.update_or_create(
                        id=lri_pessoa_id,
                        defaults={
                            "lri_id": lri_id,
                            "pessoa_id": pessoa_id,
                            "tipo_ato": tipo_ato,
                            "numero_ato": numero_ato,
                            "vinculo": vinculo,
                            "situacao": situacao,
                            "data": data,
                            "numero_imovel": numero_imovel,
                            "tipo_imovel": tipo_imovel,
                            "data_envio": data_envio,
                            "numero": numero,
                            "tipo": tipo,
                            "cartorio": cartorio,
                            "data_importacao": data_importacao,
                            "cancelado_em": cancelado_em,
                            "data_atualizacao": data_atualizacao,
                            "descricao_cpf_cnpj": descricao_cpf_cnpj,
                            "uso_origem": uso_origem,
                            "matricula": matricula,
                            "cancelamento_indisponibilidade": cancelamento_indisponibilidade,
                        },
                    )

                    livro05 = Livro05.objects.filter(id=pessoa_id).first()
                    if livro05:
                        LriDocumento.objects.update_or_create(
                            cpf_cnpj=livro05.cpf,
                            defaults={
                                "nome": livro05.nome,
                            },
                        )

        # # Mensagem de sucesso
        self.stdout.write(self.style.SUCCESS("Tabelas LRI adicionadas!"))
