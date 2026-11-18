# models.py
import datetime
import logging
from datetime import date, timedelta
from functools import cached_property

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.db import DatabaseError, IntegrityError, models
from django.utils import timezone
from django_tenants.models import DomainMixin, TenantMixin

from apps import COMMON
from apps.cartorios.managers import CartorioManager, UsuarioManager
from apps.comum.mixins import EnderecoMixin
from apps.comum.models import Expediente, TipoCartorio
from core.middlewares import get_current_user
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_nome

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def avatar_with_id(instance, filename):
    return "{}/avatar/{}".format(f"{instance.user.id}", filename)


def assinatura_with_id(instance, filename):
    return "{}/assinatura/{}".format(f"{instance.id}", filename)


def trinta_dias_futuros() -> date:
    return timezone.now() + timedelta(days=30)


# class TipoCartorio(models.Model):
#     nome:str = models.CharField(max_length=200, null=True, blank=True)

#     class Meta:
#         verbose_name = "Tipo de Cartório"
#         verbose_name_plural = "Tipos de Cartórios"

#     def __str__(self):
#         return self.nome


class Cartorio(EnderecoMixin, TenantMixin, models.Model):
    """
    Modelo representando um cartório  multitenant.

    Cada cartório é um tenant, possuindo um esquema de banco de dados separado,
        permitindo a segregação de dados entre diferentes cartórios. Isso é
        gerenciado pela biblioteca django-tenants através da herança do TenantMixin.

    Campos:
        nome (CharField): Nome do cartório.
        pago_ate (DateField): Data até a qual o serviço está pago pelo cartório.
        em_teste (BooleanField): Indica se o cartório está em um período de teste.
        criado_em (DateField): Data de criação do registro do cartório .
        auto_create_schema (bool): Controla a criação automática de schemas no Postgres.
            Se True, um novo schema será criado automaticamente no banco de dados ao salvar um novo
            objeto Tenant. Além disso, todas as migrações relacionadas aos apps listados em TENANT_APPS serão executadas para
            o novo schema. Isso facilita o provisionamento de novos tenants, eliminando a necessidade de gerenciamento manual
            de schemas e migrações para cada tenant.

    Campos Herdados (de TenantMixin):
        schema_name (CharField): Nome do esquema de banco de dados específico para este cartório.
        domain_url (CharField): URL do domínio através da qual este cartório pode ser acessado.
        id (AutoField): ID único do cartório (tenant).

    O método __str__ retorna o nome do cartório, facilitando a identificação em
        interfaces administrativas ou logs.

    O sistema multitenant permite que cada cartório tenha seu próprio subdomínio,
        proporcionando um ambiente isolado e pessoalizado para cada cartório, onde
        eles podem gerenciar seus próprios dados de forma independente.

    Este modelo, junto com a configuração do django-tenants, permite a criação
        e gestão de múltiplos tenants (cartórios) de forma eficaz e organizada.
    """

    nome: str = models.CharField(max_length=100, verbose_name="Nome do Cartório")
    pago_ate = models.DateField(
        verbose_name="Pago Até",
        default=date(2099, 12, 31),
        null=True,
        blank=True,
    )
    em_teste: bool = models.BooleanField(
        default=True,
        verbose_name="Em Teste",
        null=True,
        blank=True,
    )
    criado_em = models.DateField(
        auto_now_add=True,
        verbose_name="Criado Em",
        null=True,
        blank=True,
    )
    cnpj: str = models.CharField(
        max_length=14,
        verbose_name="CNPJ",
        default="",
        null=True,
    )
    cns: str = models.CharField(
        max_length=14,
        verbose_name="CNS",
        default="",
        null=True,
    )
    email: str = models.CharField(verbose_name="E-mail", null=True)
    site: str = models.CharField(verbose_name="Site", null=True)
    telefone: str = models.CharField(
        max_length=40,
        verbose_name="Telefone",
        default="",
        null=True,
        blank=True,
    )
    telefone_2: str = models.CharField(
        max_length=40,
        verbose_name="Telefone 2",
        default="",
        null=True,
        blank=True,
    )
    whatsapp: str = models.CharField(
        max_length=40,
        verbose_name="WhatsApp",
        default="",
        null=True,
        blank=True,
    )
    tipo_cartorio = models.ManyToManyField(
        TipoCartorio,
        verbose_name="Tipo de Cartório",
        help_text="Tipo de cartório. Ex.: Projeto CEHTES, Tabelionato de Notas, etc.",
        blank=True,
    )

    expediente = models.ManyToManyField(
        Expediente,
        blank=True,
        # default=Expediente.get_default_expediente,
        related_name="cartorio_expediente",
    )

    numero_cartorio = models.BigIntegerField(default=0)

    data_hora_sincronismo: datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data do Sincronismo",
        null=True,
        blank=True,
    )

    atualizar_somente_caixa: str = models.CharField(
        max_length=1,
        verbose_name="Atualizar o cartorio pelo caixa",
        default="N",
        null=True,
        blank=True,
    )

    usar_selo_sql_server: str = models.CharField(
        max_length=1,
        verbose_name="Usar o Selo de SQL SERVER",
        default="N",
        null=True,
        blank=True,
    )

    codigo_uf = models.BigIntegerField(default=10)

    logo = models.ImageField(
        upload_to="logo/",
        null=True,
        blank=True,
        verbose_name="Logo",
    )

    # Criação automática de schemas no Postgres para Tenants.
    auto_create_schema = False

    objects: CartorioManager = CartorioManager()

    class Meta:
        verbose_name = "Cartório"
        verbose_name_plural = "Cartórios"

    def __str__(self: "Cartorio") -> str:
        return f"{self.nome} - Id: {self.id}"

    def get_absolute_url(self: "Cartorio") -> str:
        return f"/admin/cartorios/cartorio/{self.id}/change/"

    def __init__(self: "Cartorio", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.debug(f"Sistema instanciado: {self}")

    @cached_property
    def usuarios(self: "Cartorio") -> models.QuerySet:
        user_model = get_user_model()

        return user_model.objects.filter(cartorio=self)

    @cached_property
    def telefones(self: "Cartorio") -> str:
        from apps.comum.utils import formatar_telefone

        telefones_list = [self.telefone, self.telefone_2]
        # Filtra os números de telefone que não são None ou vazios
        valores_validos = [formatar_telefone(t) for t in telefones_list if t]

        # Se não houver telefones válidos, retorna a mensagem padrão
        if not valores_validos:
            return "Não disponível"

        return ", ".join(valores_validos)

    @cached_property
    def email_formatado(self: "Cartorio") -> str:
        if not self.email:
            return "Email não informado"

        return self.email.lower()

    @cached_property
    def site_formatado(self):
        from apps.home.models import Configuracao as ConfiguracaoHome

        if (
            ConfiguracaoHome.obter(chave="exibir_site_cartorio", fallback="S").exists()
            and self.site
        ):
            return self.site.lower()

        return ""

    @staticmethod
    def get_cartorio() -> "Cartorio":
        cartorio = apps.get_model("cartorios", "Cartorio")
        return cartorio.objects.first()

    @cached_property
    def responsavel(self):
        """Retorna o usuário responsável pelo cartório, se existir, ou uma mensagem padrão."""
        try:
            funcao_responsavel = Funcao.objects.filter(nome="Responsável").first()
            usuario_responsavel = Usuario.objects.filter(
                cartorio=self,
                funcao=funcao_responsavel,
            ).first()
            return usuario_responsavel or "Responsável não definido"
        except (Funcao.DoesNotExist, Usuario.DoesNotExist):
            return "Responsável não definido"

    def atualizar_sincronismo(self) -> None:
        """Atualiza a data e hora do sincronismo do cartório para o momento atual."""
        self.data_hora_sincronismo = timezone.now()
        self.save()

    def ultimo_sincronismo(self) -> str:
        """Retorna a data e hora do último sincronismo do cartório no formato definido em settings.DATETIME_FORMAT_STR."""
        return self.data_hora_sincronismo.strftime(settings.DATETIME_FORMAT_STR)

    @cached_property
    def cnpj_formatado(self) -> str:
        """Retorna o CNPJ formatado do cartório."""
        from apps.home.helpers import formatar_cnpj

        return formatar_cnpj(self.cnpj) if self.cnpj else "CNPJ não informado"

    @cached_property
    def cns_formatado(self) -> str:
        """Retorna o CNS formatado do cartório."""
        from apps.home.helpers import formatar_cns

        return formatar_cns(self.cns) if self.cns else ""

    def criar_usuario_admin(self: "Cartorio") -> "Usuario":
        """Cria um usuário administrador para o cartório."""
        Funcao = apps.get_model("cartorios", "Funcao")
        Colaborador = apps.get_model("home", "Colaborador")

        funcao_admin, funcao_created = Funcao.objects.update_or_create(
            nome="Administrador",
            defaults={"titulo": "Administrador do Sistema"},
        )

        admin, admin_created = Usuario.objects.update_or_create(
            username="admin",
            defaults={
                "email": "admin@email.com",
                "is_staff": True,
                "is_superuser": True,
                "cartorio": self,
                "funcao": funcao_admin,
                "colaborador": Colaborador.objects.get_or_create(
                    id=999,
                    nome="Administrador",
                )[0],
                "password": make_password("CONFIGURAR_LOCALMENTE"),
            },
        )

        return admin


class Funcao(models.Model):
    nome: str = models.CharField(
        max_length=50,
        default="Funcionário",
        help_text="Nome da função",
        verbose_name="Nome",
    )
    titulo: str = models.CharField(
        max_length=50,
        default="Colaborador",
        help_text="Título da função",
        verbose_name="Título",
    )

    class Meta:
        verbose_name = "Função"
        verbose_name_plural = "Funções"

    def __str__(self) -> str:
        return self.nome or "Colaborador"


class Usuario(AbstractUser):
    id = models.BigIntegerField(primary_key=True)

    cartorio = models.ForeignKey(
        "cartorios.Cartorio",
        on_delete=models.CASCADE,
        default=1,
    )
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE, null=True, blank=True)
    is_online = models.BooleanField(default=False)
    failed_logins = models.BigIntegerField(default=0)
    status = models.BigIntegerField(default=COMMON.USER_ACTIVE, verbose_name="Status")
    website = models.URLField(default="", blank=True, null=True, verbose_name="Website")
    default = models.BooleanField(default=False, verbose_name="Padrão")
    paginate_by = models.IntegerField(default=10)
    phone = models.CharField(
        max_length=20,
        default="",
        blank=True,
        null=True,
        verbose_name="Telefone",
    )
    registration_date = models.DateField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="Data de Registro",
    )

    # fullname = models.CharField(
    #     max_length=50,
    #     default="",
    #     blank=True,
    #     null=True,
    #     verbose_name="Nome Completo user",
    # )

    address = models.TextField(
        default="",
        blank=True,
        null=True,
        verbose_name="Endereço",
    )
    zipcode = models.CharField(
        max_length=10,
        default="",
        blank=True,
        null=True,
        verbose_name="CEP",
    )
    bio = models.TextField(default="", blank=True, null=True, verbose_name="Biografia")
    image = models.URLField(default="", blank=True, null=True, verbose_name="Imagem")
    avisar_protocolo_vencendo = models.CharField(
        max_length=1,
        default="N",
        blank=True,
        null=True,
        verbose_name="Alertar quando houver Protocolos vencendo",
        help_text="Define se o usuário deve ser alertado quando houver protocolos vencendo.",
        choices=(("S", "Sim"), ("N", "Não")),
    )
    last_activity = models.DateTimeField(null=True, blank=True)
    avisar_protocolo_nota_devolucao_anexada = models.CharField(
        max_length=1,
        default="N",
        blank=True,
        null=True,
        verbose_name="Alertar Protocolo com Nota de Devolução Anexada",
        help_text="Define se o usuário deve ser alertado quando um protocolo tiver uma nota de devolução anexada.",
        choices=(("S", "Sim"), ("N", "Não")),
    )
    assinar_nota_devolucao_digital = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default="N",
        verbose_name="Assinar Digitalmente Notas de Devolução",
        help_text="Define se o usuário pode assinar digitalmente notas de devolução.",
        choices=(("S", "Sim"), ("N", "Não")),
    )
    assinar_qualificar_titulo = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default="N",
        verbose_name="Assinar e Qualificar Títulos",
        help_text="Define se o usuário pode assinar e qualificar títulos.",
        choices=(("S", "Sim"), ("N", "Não")),
    )

    avisar_pronto_registrar = models.CharField(
        max_length=1,
        default="N",
        blank=True,
        null=True,
        verbose_name="Alertar quando Protocolo estiver Pronto para Registrar",
        help_text="Define se o usuário deve ser alertado quando um protocolo estiver pronto para registrar.",
        choices=(("S", "Sim"), ("N", "Não")),
    )

    avisar_digitalizar = models.CharField(
        max_length=1,
        default="N",
        blank=True,
        null=True,
        verbose_name="Alertar quando Protocolo estiver Pronto para Digitalizar",
        help_text="Define se o usuário deve ser alertado quando um protocolo estiver pronto para digitalizar.",
        choices=(("S", "Sim"), ("N", "Não")),
    )

    last_password_change = models.DateTimeField(auto_now_add=True)

    imagem_assinatura = models.ImageField(
        upload_to=assinatura_with_id,
        null=True,
        blank=True,
        verbose_name="Imagem da Assinatura",
    )

    nome = models.CharField(max_length=200, null=True, blank=True)

    visualizar_caixa_completo = models.BooleanField(
        default=False,
        verbose_name="Pode visualizar o caixa completo",
        help_text="Marque se o colaborador pode visualizar o caixa completo.",
    )

    visualizar_caixa_previo = models.BooleanField(
        default=False,
        verbose_name="Pode visualizar o caixa previo",
        help_text="Marque se o colaborador pode visualizar o caixa previo.",
    )

    gerar_selo_certidao = models.BooleanField(
        default=False,
        verbose_name="Pode gerar selo de pedido de certidão",
        help_text="Marque se o colaborador pode gerar selo de pedido de certidão.",
    )

    usuario_caixa_certidao_onr = models.BooleanField(
        default=False,
        verbose_name="Usuário do caixa do pedido de certidão ONR",
        help_text="Marque se o colaborador e caixa da certidão ONR.",
    )

    avisar_certidao_onr = models.BooleanField(
        default=False,
        verbose_name="Usuário avisado de certidão ONR",
        help_text="Marque se o colaborador avisado certidão ONR.",
    )

    assina_digitalmente = models.BooleanField(
        default=False,
        verbose_name="Assina digitalmentent",
        help_text="Marque se o colaborador deve assinar digitalmente",
    )

    # Removido pois já tem o is_active que é nativo do usuario do django...
    # ativo:bool = models.BooleanField(
    #     default=True,
    #     verbose_name="Ativo",
    #     help_text="Define se o usuário está ativo.",
    # )

    objects: UsuarioManager = UsuarioManager()

    def __str__(self) -> str:
        return self.get_nome_mapeado(self.username)

    def get_distribuidos_url(self):
        try:
            if self.colaborador:
                return self.colaborador.get_distribuidos_url()
            return None
        except Exception as e:
            logger.exception(str(e))

    @classmethod
    def reset_or_create_admin_password(cls) -> None:
        try:
            user: Usuario = cls.objects.get(username__iexact="admin")
            user.password = make_password("CONFIGURAR_LOCALMENTE")
            user.last_password_change = timezone.now()
            user.save()
            logger.info("Senha do usuário admin redefinida.")
        except cls.DoesNotExist:
            logger.exception("Usuário admin não encontrado. Criando usuário 'admin'.")
            cartorio = Cartorio.objects.first()
            user = cls.objects.create(
                username="admin",
                is_superuser=True,
                is_staff=True,
                cartorio=cartorio,
            )

    # cria um usuario com o nome sistema e id 1
    @staticmethod
    def criar_usuario_sistema() -> "Usuario":
        logger.info("Criando usuário 'sistema' com id 1")
        usuario, created = Usuario.objects.get_or_create(
            id=1,
            defaults={
                "nome": "Sistema",
                "cartorio": Cartorio.get_cartorio(),
                "default": True,
            },
        )

        from apps.home.models.models_home import Colaborador

        logger.info("Criando colaborador 'sistema' com id 1")
        try:
            if Colaborador.objects.filter(id=1).exists():
                logger.debug("Colaborador 'sistema' já existe, atualizando nome")
                colaborador = Colaborador.objects.get(id=1)
                colaborador.nome = "Sistema"
                colaborador.usuario = usuario
                colaborador.save()
            else:
                logger.debug("Colaborador 'sistema' não existe, criando")
                colaborador = Colaborador.objects.create(
                    id=1,
                    nome="Sistema",
                    usuario=usuario,
                )
                colaborador.save()
        except IntegrityError as e:
            logger.exception(f"Erro ao criar colaborador 'sistema': {e}")
            raise

        try:
            # from constance import config

            # if not config.FIREBIRD_ENABLED:
            #     logger.error("Firebird não habilitado!")
            #     return None

            with FbConnection() as db:
                logger.info("Criando colaborador 'sistema' com id 1 no Firebird")
                # Verifica se o usuário já existe
                result = db.execute_query(
                    "SELECT COUNT(1) FROM FUNCIONARIOS WHERE CHAVE_FUNCIONARIOS = 1",
                )
                if result[0]["COUNT"] == 0:  # Se não existir, cria
                    db.execute_command(
                        """INSERT INTO FUNCIONARIOS
                            (NIVEL,
                            NOME,
                            NOMECOMPLETO,
                            CHAVE_FUNCIONARIOS,
                            SENHA, INICIAIS,
                            CHAVE_PAPEIS,
                            INATIVO,
                            VERIFICARANDAMENTO,
                            CARGOFUNCIONARIO, AVISARRECOLHIMENTO, CHAVE_DOCUMENTOS, NUMERO_DOCUMENTO, NOMERELATORIOS,
                            AVISOSISTEMA,
                            AVISARDISTRIBUICAO, ORDEMDISTRIBUICAO, ULTIMADISTRIBUICAO, CHAVE_GRUPO_SELO, CPF,
                            USAR_ACESSO_CERTIFICADO_DIGITA, ASSINASELODIGITAL, AVISARESTOQUE, DATA_SENHA_ALTERADA,
                            ORDEMDISTRIBUICAOORC, ULTIMADISTRIBUICAOORC, AVISARDISTRIBUICAOORC, HORA_ENTRADA_AM,
                            HORA_SAIDA_AM, HORA_ENTRADA_PM, HORA_SAIDA_PM, HORA_TOLERANCIA)
                            VALUES(NULL, '0B1012163B1C', '0B1012163B1C', 1.00,
                            '5BxT5ys4mbuzwzEnNk2LunWg8voCxNBx1G/KVOXsFJkfO0jP+n5bqOBLubHFn2O3NtoUaRy/U9eV+NXmRYylcrSWCD9AuhBN3wkeLd596ZE=',
                            NULL, NULL, 'N', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                            NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);""",
                    )
        except DatabaseError as e:
            logger.exception(f"Erro ao criar funcionario 'sistema' no Firebird: {e}")

        return usuario

    @cached_property
    def nome_completo(self):
        """Retorna o nome completo do usuário, se disponível, ou o nome de usuário."""
        # return (
        #     self.fullname
        #     if self.fullname
        #     else (
        #         f"{self.first_name} {self.last_name}"
        #         if self.first_name
        #         else self.username
        #         if self.username
        #         else "Usuário sem nome"
        #     )
        # )

        return f"{self.first_name} {self.last_name}"

    @cached_property
    def is_authenticated(self) -> bool:
        return True

    @cached_property
    def expediente_cartorio(self):
        # verificar cartorio e expediente para evitar erros
        if self.cartorio and self.cartorio.expediente:
            return self.cartorio.expediente
        return None

    @staticmethod
    def get_nome_mapeado(nome: str) -> str:
        """
        Mapeia o nome do funcionário usando o dicionário NOME_MAP.
        Retorna o nome original se não houver mapeamento.
        """
        return formatar_nome(Usuario.NOME_MAP.get(nome, nome))

    @classmethod
    def get_usuarios_com_protocolo_vencendo(cls) -> models.QuerySet:
        return cls.objects.filter(avisar_protocolo_vencendo="S")

    @classmethod
    def get_usuarios_com_protocolos_nota_devolucao_anexada(cls) -> models.QuerySet:
        return cls.objects.filter(avisar_protocolo_nota_devolucao_anexada="S")

    @classmethod
    def get_usuarios_com_protocolos_prontos_registrar(cls) -> models.QuerySet:
        return cls.objects.filter(avisar_pronto_registrar="S")

    @classmethod
    def get_usuarios_com_protocolos_prontos_digitalizar(cls) -> models.QuerySet:
        return cls.objects.filter(avisar_digitalizar="S")

    @classmethod
    def get_usuarios_com_assinar_qualificar_titulo(cls) -> models.QuerySet:
        return cls.objects.filter(assinar_qualificar_titulo="S")

    @classmethod
    def get_usuarios_ids_para_notificar_nota_de_devolucao(cls) -> list:
        try:
            return [
                usuario["id"]
                for usuario in cls.get_usuarios_com_protocolos_nota_devolucao_anexada().values(
                    "id",
                )
            ]
        except Exception:
            return []

    @classmethod
    def get_usuarios_ids_para_notificar_protocolo_vencendo(cls) -> list:
        try:
            return [
                usuario["id"]
                for usuario in cls.get_usuarios_com_protocolo_vencendo().values("id")
            ]
        except Exception:
            return []

    @classmethod
    def get_usuarios_para_notificar_protocolo_assinar(cls) -> list:
        try:
            return [
                usuario["id"]
                for usuario in cls.get_usuarios_com_assinar_qualificar_titulo().values(
                    "id",
                )
            ]
        except Exception:
            return []

    @classmethod
    def get_or_create_usuario_sistema(cls) -> "Usuario":
        """Retorna o usuário do sistema, criando-o se não existir."""
        usuario = Usuario.objects.filter(default=True).first()

        if not usuario:
            funcionario_id_sistema_antigo = 1

            if not funcionario_id_sistema_antigo:
                # funcionario_id_sistema_antigo = 999998
                funcionario_id_sistema_antigo = 1

            Cartorio.objects.get_or_create_cartorio_padrao()

            # if not cartorio:
            #     cartorio = Cartorio.objects.criar_padroes()

            usuario, created = Usuario.objects.update_or_create(
                id=funcionario_id_sistema_antigo,
                defaults={
                    "nome": "Sistema",
                    "cartorio_id": 1,
                    "default": True,
                },
            )

        return usuario

    @classmethod
    def get_usuario_sistema(cls) -> "Usuario":
        return cls.get_or_create_usuario_sistema()

    @staticmethod
    def get_current_user() -> "Usuario":
        return get_current_user()

    @classmethod
    def get_usuario_sistema_id(cls) -> int:
        retorno = cls.get_or_create_usuario_sistema()
        return retorno.id if retorno else None

    @classmethod
    def get_usuarios_avisar_certidao_onr(cls) -> models.QuerySet:
        usuarios = cls.objects.filter(avisar_certidao_onr=True)
        return usuarios if usuarios.exists() else cls.objects.filter(id=1)

    @classmethod
    def get_usuario_caixa_certidao_onr_id(cls) -> models.QuerySet:
        return (
            cls.objects.filter(usuario_caixa_certidao_onr=True)
            .values_list(
                "id",
                flat=True,
            )
            .first()
        )

    @classmethod
    def user_assina_digitalmente_default(cls) -> "Usuario":
        return Usuario.objects.filter(assina_digitalmente=True).first()

    @classmethod
    def get_ativos(cls) -> models.QuerySet:
        return cls.objects.filter(status=COMMON.USER_ACTIVE)

    @cached_property
    def configuracoes_globais(self):
        from apps.home.models import Configuracao

        return Configuracao.all()

    @cached_property
    def configuracoes_usuario(self):
        from apps.home.models import Configuracao

        return Configuracao.objects.filter(criado_para=self)

    class Meta:
        ordering = ["username"]
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    # Dicionário para mapear nomes
    from apps.cartorios.constants import NOME_MAP

    NOME_MAP = NOME_MAP


class Dominio(DomainMixin):
    # DomainMixin já inclui os campos necessários

    def __str__(self) -> str:
        return self.domain

    class Meta:
        verbose_name = "Domínio"
        verbose_name_plural = "Domínios"
