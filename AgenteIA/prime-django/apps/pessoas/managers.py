import uuid
from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Model

from core.utils.formatacoes import formatar_nome


class VersaoPessoaManager(models.Manager):
    def get_ultima_versao(self, pessoa_id: uuid.UUID):
        return self.filter(pessoa_id=pessoa_id).order_by("-criado_em").first()

    @transaction.atomic
    def criar_versao_pessoa_obtida_do_pessoas_em_home(self, pessoa_em_home: Model):
        from apps.pessoas.models import Pessoa

        try:
            conjuge_em_home = pessoa_em_home.get_conjuge()
        except AttributeError:
            conjuge_em_home = None

        if conjuge_em_home:
            conjuge, created = Pessoa.objects.get_or_create(
                documento=conjuge_em_home.cpf or "",
                pessoa_home_id=conjuge_em_home.id,
            )

        # ATUALIZAR O EMAIL DO CONJUGE
        if conjuge_em_home:
            if conjuge_em_home.email:
                email_conjuge = conjuge_em_home.email.lower()
            else:
                conjuge_em_home = ""

        versao_pessoa_conjuge = (
            self.create(
                pessoa=conjuge,
                nome=formatar_nome(conjuge_em_home.nome) or "",
                data_nascimento=conjuge_em_home.data_nascimento,
                email=email_conjuge,
                telefone=(
                    conjuge_em_home.telefone[:20] if conjuge_em_home.telefone else ""
                ),
                logradouro=conjuge_em_home.endereco or "",
                cidade=conjuge_em_home.cidade or "",
                estado=conjuge_em_home.uf or "",
                cep=conjuge_em_home.cep or "",
                estado_civil=(
                    conjuge_em_home.estado_civil.descricao_estado_civil[:20]
                    if conjuge_em_home.estado_civil
                    else ""
                ),
                sexo=conjuge_em_home.sexo or "",
            )
            if conjuge_em_home
            else None
        )

        if pessoa_em_home:
            pessoa, created = Pessoa.objects.get_or_create(
                documento=pessoa_em_home.cpf,
                pessoa_home_id=pessoa_em_home.id,
            )

            versao_pessoa = self.create(
                pessoa=pessoa,
                nome=formatar_nome(pessoa_em_home.nome) or "",
                data_nascimento=pessoa_em_home.data_nascimento,
                email=pessoa_em_home.email.lower() if pessoa_em_home.email else "",
                telefone=pessoa_em_home.telefone[:20]
                if pessoa_em_home.telefone
                else "",
                logradouro=pessoa_em_home.endereco or "",
                # bairro=pessoa_em_home.bairro,
                cidade=pessoa_em_home.cidade or "",
                estado=pessoa_em_home.uf or "",
                cep=pessoa_em_home.cep or "",
                estado_civil=(
                    pessoa_em_home.estado_civil.descricao_estado_civil[:20]
                    if pessoa_em_home.estado_civil
                    else ""
                ),
                sexo=pessoa_em_home.sexo or "",
                conjuge=versao_pessoa_conjuge if conjuge_em_home else None,
            )

            versao_pessoa.save()

        if versao_pessoa_conjuge:
            versao_pessoa_conjuge.conjuge = versao_pessoa
            versao_pessoa_conjuge.save()

        try:
            return versao_pessoa
        except UnboundLocalError:
            return None


class PessoaManager(models.Manager):
    def get_pessoa(self, pessoa_id):
        from apps.pessoas.models import VersaoPessoa

        return VersaoPessoa.filter(pessoa_id=pessoa_id).last()

    def criar_pessoa(
        self,
        nome: str,
        documento: str,
        data_nascimento: date,
        email: str,
        telefone: str,
        logradouro: str,
        bairro: str,
        cidade: str,
        estado: str,
        cep: str,
        estado_civil: str,
        sexo: str,
        conjuge,
        observacoes: str,
        tipo_vinculo,
        model: type[Model],
        object_id,
    ):
        from apps.pessoas.models import VersaoPessoa, Vinculo

        if not model or not object_id:
            msg = "Model e object_id são obrigatórios"
            raise ValueError(msg)

        pessoa = self.create(nome=nome, documento=documento)

        VersaoPessoa.create(
            pessoa=pessoa,
            email=email,
            telefone=telefone,
            logradouro=logradouro,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            cep=cep,
            estado_civil=estado_civil,
            sexo=sexo,
            conjuge=conjuge,
            observacoes=observacoes,
            data_nascimento=data_nascimento,
        )

        Vinculo.create(
            pessoa=pessoa,
            tipo_vinculo=tipo_vinculo,
            content_type=ContentType.objects.get_for_model(model),
            object_id=object_id,
        )

        return VersaoPessoa

    def get_pessoa_por_documento(self, documento: str):
        from apps.pessoas.models import VersaoPessoa

        return VersaoPessoa.filter(pessoa__documento=documento).last()

    def get_queryset(self):
        return super().get_queryset()


class AnexoManager(models.Manager):
    def get_anexos_da_pessoa(self, pessoa_id: uuid.UUID):
        return self.filter(pessoa_id=pessoa_id)


class VinculoManager(models.Manager):
    # criar vinculo obtendo o model e o registro

    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)
