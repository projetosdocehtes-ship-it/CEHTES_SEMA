import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.http import JsonResponse
from rest_framework import serializers

from apps.comum.models import Municipio as MunicipioUF
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class Representante(models.Model):
    ni: str = models.CharField(max_length=255)


class Parte(models.Model):
    indicador_espolio: bool = models.BooleanField()
    indicador_estrangeiro: bool = models.BooleanField()
    indicador_nao_consta_participacao_operacao: bool = models.BooleanField()
    indicador_ni_identificado: bool = models.BooleanField()
    cpf_conjuge: str = models.CharField(max_length=255)
    cpf_inventariante: str = models.CharField(max_length=255)
    indicador_conjuge: bool = models.BooleanField()
    indicador_conjuge_participa: bool = models.BooleanField()
    indicador_cpf_conjuge_identificado: bool = models.BooleanField()
    indicador_representante: bool = models.BooleanField()
    motivo_nao_identificacao_ni: str = models.CharField(max_length=255)
    ni: str = models.CharField(max_length=255)
    participacao = models.FloatField()
    regime_bens: str = models.CharField(max_length=255)
    representantes = models.ManyToManyField(Representante)


# class MunicipioUF(models.Model):
#     codigo_ibge:str = models.CharField(max_length=255)


class Declaracao(models.Model):
    adquirentes = models.ManyToManyField(Parte, related_name="adquirentes")
    alienantes = models.ManyToManyField(Parte, related_name="alienantes")
    data_lavratura_registro_averbacao: str = models.CharField(max_length=255)
    data_negocio_juridico: str = models.CharField(max_length=255)
    destinacao: str = models.CharField(max_length=255)
    forma_pagamento: str = models.CharField(max_length=255)
    indicador_imovel_publico_uniao: bool = models.BooleanField()
    indicador_pagamento_dinheiro: bool = models.BooleanField()
    indicador_permuta_bens: bool = models.BooleanField()
    tipo_declaracao: str = models.CharField(max_length=255)
    tipo_operacao_imobiliaria: str = models.CharField(max_length=255)
    tipo_parte_transacionada: str = models.CharField(max_length=255)
    tipo_servico: str = models.CharField(max_length=255)
    valor_parte_transacionada = models.FloatField()
    area_construida = models.FloatField()
    area_imovel = models.FloatField()
    bairro: str = models.CharField(max_length=255)
    cep: str = models.CharField(max_length=255)
    certidao_autorizacao_transferencia: str = models.CharField(max_length=255)
    cib: str = models.CharField(max_length=255)
    codigo_ibge: str = models.CharField(max_length=255)
    codigo_incra: str = models.CharField(max_length=255)
    codigo_nacional_matricula: str = models.CharField(max_length=255)
    complemento_endereco: str = models.CharField(max_length=255)
    complemento_numero_imovel: str = models.CharField(max_length=255)
    denominacao: str = models.CharField(max_length=255)
    descricao_outras_operacoes_imobiliarias: str = models.CharField(max_length=255)
    existe_doi_anterior: bool = models.BooleanField()
    folha: str = models.CharField(max_length=255)
    indicador_alienacao_fiduciaria: bool = models.BooleanField()
    indicador_area_construida_nao_consta: bool = models.BooleanField()
    indicador_area_lote_nao_consta: bool = models.BooleanField()
    indicador_nao_consta_valor_base_calculo_itbi_itcmd: bool = models.BooleanField()
    indicador_nao_consta_valor_operacao_imobiliaria: bool = models.BooleanField()
    inscricao_municipal: str = models.CharField(max_length=255)
    localizacao: str = models.CharField(max_length=255)
    matricula: str = models.CharField(max_length=255)
    matricula_notarial_eletronica: str = models.CharField(max_length=255)
    mes_ano_ultima_parcela: str = models.CharField(max_length=255)
    municipios_uf = models.ManyToManyField(MunicipioUF)
    natureza_titulo: str = models.CharField(max_length=255)
    nome_logradouro: str = models.CharField(max_length=255)
    numero_imovel: str = models.CharField(max_length=255)
    numero_livro: str = models.CharField(max_length=255)
    numero_registro: str = models.CharField(max_length=255)
    numero_registro_averbacao: str = models.CharField(max_length=255)
    registro_imobiliario_patrimonial: str = models.CharField(max_length=255)
    retificacao_ato: bool = models.BooleanField()
    tipo_ato: str = models.CharField(max_length=255)
    tipo_imovel: str = models.CharField(max_length=255)
    tipo_livro: str = models.CharField(max_length=255)
    tipo_logradouro: str = models.CharField(max_length=255)
    transcricao = models.IntegerField()
    valor_base_calculo_itbi_itcmd = models.FloatField()
    valor_operacao_imobiliaria = models.FloatField()
    valor_pago_ate_data_ato = models.FloatField()
    valor_pago_moeda_corrente_data_ato = models.FloatField()


class RepresentanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Representante
        fields = ["ni"]


class ParteSerializer(serializers.ModelSerializer):
    representantes = RepresentanteSerializer(many=True)

    class Meta:
        model = Parte
        fields = [
            "indicador_espolio",
            "indicador_estrangeiro",
            "indicador_nao_consta_participacao_operacao",
            "indicador_ni_identificado",
            "cpf_conjuge",
            "cpf_inventariante",
            "indicador_conjuge",
            "indicador_conjuge_participa",
            "indicador_cpf_conjuge_identificado",
            "indicador_representante",
            "motivo_nao_identificacao_ni",
            "ni",
            "participacao",
            "regime_bens",
            "representantes",
        ]


class MunicipioUFSerializer(serializers.ModelSerializer):
    class Meta:
        model = MunicipioUF
        fields = ["codigo_ibge"]


class DeclaracaoSerializer(serializers.ModelSerializer):
    adquirentes = ParteSerializer(many=True)
    alienantes = ParteSerializer(many=True)
    municipios_uf = MunicipioUFSerializer(many=True)

    class Meta:
        model = Declaracao
        fields = [
            "adquirentes",
            "alienantes",
            "data_lavratura_registro_averbacao",
            "data_negocio_juridico",
            "destinacao",
            "forma_pagamento",
            "indicador_imovel_publico_uniao",
            "indicador_pagamento_dinheiro",
            "indicador_permuta_bens",
            "tipo_declaracao",
            "tipo_operacao_imobiliaria",
            "tipo_parte_transacionada",
            "tipo_servico",
            "valor_parte_transacionada",
            "area_construida",
            "area_imovel",
            "bairro",
            "cep",
            "certidao_autorizacao_transferencia",
            "cib",
            "codigo_ibge",
            "codigo_incra",
            "codigo_nacional_matricula",
            "complemento_endereco",
            "complemento_numero_imovel",
            "denominacao",
            "descricao_outras_operacoes_imobiliarias",
            "existe_doi_anterior",
            "folha",
            "indicador_alienacao_fiduciaria",
            "indicador_area_construida_nao_consta",
            "indicador_area_lote_nao_consta",
            "indicador_nao_consta_valor_base_calculo_itbi_itcmd",
            "indicador_nao_consta_valor_operacao_imobiliaria",
            "inscricao_municipal",
            "localizacao",
            "matricula",
            "matricula_notarial_eletronica",
            "mes_ano_ultima_parcela",
            "municipios_uf",
            "natureza_titulo",
            "nome_logradouro",
            "numero_imovel",
            "numero_livro",
            "numero_registro",
            "numero_registro_averbacao",
            "registro_imobiliario_patrimonial",
            "retificacao_ato",
            "tipo_ato",
            "tipo_imovel",
            "tipo_livro",
            "tipo_logradouro",
            "transcricao",
            "valor_base_calculo_itbi_itcmd",
            "valor_operacao_imobiliaria",
            "valor_pago_ate_data_ato",
            "valor_pago_moeda_corrente_data_ato",
        ]


def gerar_declaracoes_json(request):
    declaracoes = Declaracao.objects.all()
    serializer = DeclaracaoSerializer(declaracoes, many=True)
    return JsonResponse(
        {"declaracoes": serializer.data},
        encoder=DjangoJSONEncoder,
        safe=False,
    )


# INICIO DO PREENCHIMENTO DAS CLASSES PARA EXPORTAR O JSON:
def importar_dados_firebird():
    lista_declaracoes = []
    with FbConnection() as db:
        # Exemplo: Importando dados da tabela 'Declaracao'
        declaracoes = db.execute_query(
            "SELECT * FROM ATOSDOI A WHERE A.chave_atosdoi = 25311 ",
        )

        cep_default = "74910000"
        codigo_ibge_default = "74910000"
        cib_default = "74910000"
        codigo_incra_default = "74910000"
        codigo_nacional_matricula = "74910000"
        inscricao_municipal_default = "74910000"
        matricula_default = "10000"
        mes_ano_ultima_parcela_default = "1"
        municipios_uf_default = MunicipioUF.objects.filter(
            codigo_ibge="3101607",
        ).first()
        # municipios_uf_default.codigo_ibge = "3101607"
        natureza_titulo_default = "Compra e Venda"
        numero_livro_default = "2"

        for declaracao in declaracoes:
            declaracao = Declaracao(
                id=declaracao["CHAVE_ATOSDOI"],
                data_lavratura_registro_averbacao=declaracao["DATA_ALIENACAO"],
                data_negocio_juridico=declaracao["DATA_LAVRATURA"],
                destinacao=declaracao["DESCRICAO_OUTROS_ATOS"],
                forma_pagamento=declaracao["FORMA_ALIENACAO"],
                indicador_imovel_publico_uniao=False,
                indicador_pagamento_dinheiro=False,
                indicador_permuta_bens=False,
                tipo_declaracao=declaracao["ATUALIZAR_DATA_ALIENACAO"],
                tipo_operacao_imobiliaria=declaracao["ATUALIZAR_DATA_ALIENACAO"],
                tipo_parte_transacionada=declaracao["ATUALIZAR_DATA_ALIENACAO"],
                tipo_servico=declaracao["ATUALIZAR_DATA_ALIENACAO"],
                valor_parte_transacionada=declaracao["VALOR_ALIENACAO"],
                area_construida=str(declaracao["AREA"]).replace(",", "."),
                area_imovel=str(declaracao["AREA"]).replace(",", "."),
                bairro=declaracao["DESCRICAO_OUTROS_TIPO"],
                cep=cep_default,
                certidao_autorizacao_transferencia=declaracao["DESCRICAO_OUTROS_TIPO"],
                cib=cib_default,
                codigo_ibge=codigo_ibge_default,
                codigo_incra=codigo_incra_default,
                codigo_nacional_matricula=codigo_nacional_matricula,
                complemento_endereco="",
                complemento_numero_imovel="",
                denominacao="",
                descricao_outras_operacoes_imobiliarias="",
                existe_doi_anterior=False,
                folha="",
                indicador_alienacao_fiduciaria=False,
                indicador_area_construida_nao_consta=False,
                indicador_area_lote_nao_consta=False,
                indicador_nao_consta_valor_base_calculo_itbi_itcmd=False,
                indicador_nao_consta_valor_operacao_imobiliaria=False,
                inscricao_municipal=inscricao_municipal_default,
                localizacao="",
                matricula=matricula_default,
                matricula_notarial_eletronica=matricula_default,
                mes_ano_ultima_parcela=mes_ano_ultima_parcela_default,
                natureza_titulo=natureza_titulo_default,
                nome_logradouro="",
                numero_imovel=matricula_default,
                numero_livro=numero_livro_default,
                numero_registro=numero_livro_default,
                numero_registro_averbacao=numero_livro_default,
                registro_imobiliario_patrimonial="",
                retificacao_ato=False,
                tipo_ato="R",
                tipo_imovel="M",
                tipo_livro="2",
                tipo_logradouro="",
                transcricao=0,
                valor_base_calculo_itbi_itcmd=declaracao["VALOR_ALIENACAO"],
                valor_operacao_imobiliaria=declaracao["VALOR_AVALIACAO"],
                valor_pago_ate_data_ato=declaracao["VALOR_AVALIACAO"],
                valor_pago_moeda_corrente_data_ato=declaracao["VALOR_ALIENACAO"],
            )
            declaracao.municipios_uf.add(municipios_uf_default.codigo_ibge)

            # Exemplo para Parte
            partes = db.execute_query(
                "SELECT * FROM vinculos_partes_doi WHERE chave_atosdoi=%s",
                [declaracao[0]],
            )
            for parte_declaracao in partes:
                parte = Parte(
                    indicador_espolio=parte_declaracao[1],
                    indicador_estrangeiro=parte_declaracao[2],
                    indicador_nao_consta_participacao_operacao=parte_declaracao[3],
                    indicador_ni_identificado=parte_declaracao[4],
                    cpf_conjuge=parte_declaracao[5],
                    cpf_inventariante=parte_declaracao[6],
                    indicador_conjuge=parte_declaracao[7],
                    # Continue atribuindo outros campos
                )
                declaracao.adquirentes.add(
                    parte,
                )  # Exemplo de associação com 'Declaracao'

        lista_declaracoes.append(declaracao)

        return lista_declaracoes


def gerar_declaracoes_json(request):
    declaracoes = importar_dados_firebird()
    serializer = DeclaracaoSerializer(declaracoes, many=True)
    return JsonResponse(
        {"declaracoes": serializer.data},
        encoder=DjangoJSONEncoder,
        safe=False,
    )
