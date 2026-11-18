import logging
from typing import TYPE_CHECKING

from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection, models
from django.db.utils import IntegrityError
from django.utils import timezone

from core.utils.firebird_utils import FbConnection

if TYPE_CHECKING:
    from apps.cartorios.models import Cartorio, Funcao

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


class CartorioManager(models.Manager):
    def get_or_create_cartorio_padrao(self: "CartorioManager") -> "Cartorio":
        cartorio_model: Cartorio = apps.get_model("cartorios", "Cartorio")
        apps.get_model("comum", "TipoCartorio")
        if cartorio_model:
            if cartorio_model.objects.exists():
                cartorios = cartorio_model.objects.all()
                if cartorios.count() > 1:
                    logger.warning("Há mais de um cartório cadastrado!")
                for cartorio in cartorios:
                    logger.info(
                        f"Cadastrado: {cartorio.id} - {cartorio.nome} - {cartorio.cnpj_formatado}",
                    )
                return None
            cartorio_ri, created = cartorio_model.objects.get_or_create(
                defaults={
                    "nome": "Cartório de Projeto CEHTES",
                    "cnpj": "12345678901234",
                    "cns": "123456",
                    "email": "cartorio@email.com",
                    "telefone": "1234567890",
                    "telefone_2": "1234567891",
                },
            )

            # if created:
            # tipo = TipoCartorio.get_cartorio_registro_imoveis()
            # cartorio_ri.tipo_cartorio.set(tipos)

            # Cria uma função padrão se ela não existir
            funcao_model: Funcao = apps.get_model("cartorios", "Funcao")

            funcao_admin, funcao_created = funcao_model.objects.update_or_create(
                nome="Administrador",
                defaults={"titulo": "Administrador do Sistema"},
            )
            funcao, funcao_created = funcao_model.objects.update_or_create(
                nome="Usuário",
                defaults={"titulo": "Usuário do Sistema"},
            )
            funcao, funcao_created = funcao_model.objects.update_or_create(
                nome="Responsável",
                defaults={"titulo": "Oficial"},
            )

            cartorio_ri.criar_usuario_admin()

            logger.info(
                "Cartório, Função e Usuário Admin criados ou atualizados!",
            )

            return cartorio_ri
        return None

    def criar_usuario_no_cartorio(
        self: models.Manager,
        username: str,
        **extra_fields: dict,
    ) -> models.Model:
        # Campos específicos para usuários de cartório
        cartorio_fields = {
            "cartorio_id": extra_fields.get("cartorio_id", 2),
            "funcao_id": extra_fields.get("funcao_id", 1),
            "status": extra_fields.get("status", 1),
            "avisar_protocolo_vencendo": extra_fields.get(
                "avisar_protocolo_vencendo",
                "N",
            ),
            # Inclui outros campos específicos do cartório aqui
            **extra_fields,
        }

        # pdb.set_trace()

        return UsuarioManager().criar_ou_get_usuario(
            username,
            **cartorio_fields,
        )


class UsuarioManager(models.Manager):
    def normalize_email(self: models.Manager, email: str) -> str:
        """
        Normaliza o email fazendo a parte do domínio ser passada para minúscula.

        Este é um método simples que pode ser expandido conforme necessário.
        """
        try:
            validate_email(email)
            name, domain = email.rsplit("@", 1)
            return f"{name}@{domain.lower()}"
        except ValidationError:
            return email  # ou levante uma exceção, dependendo da sua necessidade

    def get_ou_criar_usuario(self: models.Manager, username: str) -> models.Model:
        # Chave de cache baseada no username
        # sanitized_username = str(username).replace(" ", "_")
        # cache_key = f"user_{sanitized_username}"
        # user = cache.get(cache_key)

        # pdb.set_trace()

        # if user is None:
        # Define os valores padrão para criar um novo usuário, se necessário
        defaults = {
            "password": make_password(
                "CONFIGURAR_LOCALMENTE",
            ),  # Gera uma senha segura
            "is_superuser": False,
            "first_name": username or "Indefinido",
            "is_staff": False,
            "is_active": True,
            "date_joined": timezone.now(),
            "cartorio_id": 1,
            "funcao_id": 1,
            "status": 1,
            "avisar_protocolo_vencendo": "N",
            "avisar_protocolo_nota_devolucao_anexada": "N",
            "assinar_nota_devolucao_digital": "N",
            "assinar_qualificar_titulo": "N",
            "avisar_pronto_registrar": "N",
        }
        try:
            user = self.filter(username=username or "Indefinido").first()
            # pdb.set_trace()

            if not user:
                user = self.create(username=username, **defaults)
            # cache.set(cache_key, user, timeout=3600)
        except IntegrityError:
            # Corrige a sequência de IDs se houver um erro de integridade
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT setval('cartorios_usuario_id_seq', (SELECT MAX(id) FROM cartorios_usuario)+1)",
                )

        return user

    def importar_do_fb(self):
        # from constance import config

        # if not config.FIREBIRD_ENABLED:
        #     logger.error("Firebird não habilitado!")
        #     return

        query = """
                SELECT CHAVE_FUNCIONARIOS, NOME, INATIVO
                FROM FUNCIONARIOS"""
        with FbConnection() as db:
            funcionarios = db.execute_query(query)

        colaborador_model = apps.get_model("home", "Colaborador")
        cartorio_model = apps.get_model("cartorios", "Cartorio")

        # with transaction.atomic():
        for funcionario in funcionarios:
            try:
                nome = colaborador_model.get_nome_mapeado(funcionario["NOME"])

                # pdb.set_trace()
                print(
                    "Salvando Usuario: ",
                    nome,
                    " ID: ",
                    funcionario["CHAVE_FUNCIONARIOS"],
                )
                obj, created = self.update_or_create(
                    pk=funcionario["CHAVE_FUNCIONARIOS"],
                    defaults={
                        "username": nome,
                        "first_name": nome,
                        #"fullname": nome,
                        "cartorio_id": cartorio_model.objects.first().pk,
                    },
                )

                print("Salvando Colaborador: ", funcionario["CHAVE_FUNCIONARIOS"])
                colaborador_model.objects.update_or_create(
                    pk=funcionario["CHAVE_FUNCIONARIOS"],
                    defaults={
                        "usuario": obj,
                    },
                )
            except IntegrityError:
                # logger.exception(f"Erro ao criar funcionario {nome} ID: {funcionario['CHAVE_FUNCIONARIOS']}")
                continue

        # # Mensagem de sucesso
        logger.info("Tabela Funcionarios adicionada!")
