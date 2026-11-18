import logging
from threading import Lock, Thread
from typing import TYPE_CHECKING

from django.apps import apps
from django.db.models import CharField, F, Value
from django.db.models.functions import Concat
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from apps.home import models, views
from apps.home.models import PedidoCertidao
from core import settings

SIGNALS_IMPORTED = True

if TYPE_CHECKING:
    from apps.cartorios.models import Usuario as User

lock_onr = Lock()
lock_correcoes = Lock()

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def get_current_username():
    from core.middlewares import get_current_user

    user = get_current_user()
    if user:
        return user.username
    return "Sistema"


@receiver(post_save, sender=models.Livro01Andamento)
def post_save_exportar_andamento_para_firebird(
    sender,
    instance,
    created,
    **kwargs,
) -> None:
    logger.debug(f"Post-save signal recebido para {sender.__name__}.")
    from apps.home.utils.importacao_de_protocolo_firebird import (
        exportar_andamento_para_firebird,
    )

    if created and not instance.data_importacao:
        print("SIGNAL: Exportar andamento para firebird")
        exportar_andamento_para_firebird(instance)


# @receiver(post_save, sender=Livro02)
# def post_save_revincular_anexos_orfaos(sender, instance, created, **kwargs):
#     print("SIGNAL: Procurando anexos orfãos do registro")
#     # Busca por anexos que possam estar associados ao imóvel atualizado/criado
#     anexos = Anexo.objects.filter(
#         Q(nome__contains=instance.numero_formatado) | Q(nome__contains=instance.numero),
#     )

#     # Para cada anexo encontrado, tenta atualizar o vinculo ao imóvel
#     for anexo in anexos:
#         anexo.vincular_imovel()


# @receiver(post_save, sender=SeloEletronico)
# def servicos_realizados_sender(sender, instance, created, **kwargs):
#     if created:
#         descricao = instance.pedidos.nome_solicitante_formatado
#         valor = instance.pedidos_itens.valor_total
#         data_servico = instance.utilizado_em
#         # usuario_id = instancia

#     servico_realizado_signal.send(
#         sender=sender,
#         descricao=descricao,
#         valor=valor,
#         data_servico=data_servico,
#         # usuario_id=usuario_id,
#         tipo_servico="DepositoPrevio",
#     )


# CRIANDO UM SIGNAL
@receiver(post_save, sender=models.Livro01Andamento)
def atualizar_evento_protocolo(sender, instance, created, **kwargs) -> None:
    logger.debug(f"Post-save signal recebido para {sender.__name__}.")
    print(
        f"SIGNAL: Pós Atualização de Andamento no Protocolo. \n  Acionado por: {instance}, \n  Criado: {created}",
    )


@receiver(post_save, sender=models.PedidoCertidao)
def criar_andamento_novo_pedido(
    sender: "PedidoCertidao",
    instance: "PedidoCertidao",
    created,
    **kwargs,
) -> None:
    logger.debug(f"Post-save signal recebido para {sender.__name__}.")
    if created:
        instance.registrar_andamento_recepcao()


# @receiver(post_save, sender=PedidoCertidaoAndamento)
# def enviar_pedido_certida_para_caixa(sender, instance, created, **kwargs):
#     instance.enviar_para_caixa()


@receiver(pre_save, sender=models.Financeiro)
def pre_save_financeiro(sender, instance: models.Financeiro, **kwargs):
    logger.debug(f"Post-save signal recebido para {sender.__name__}.")
    from apps.home.models import TipoCategoriaFinanceira

    if instance.pedido_certidao_id:
        instance.tipo_categoria_financeira = (
            TipoCategoriaFinanceira.get_pedido_certidao()
        )
    elif instance.pedido_id:
        instance.tipo_categoria_financeira = TipoCategoriaFinanceira.get_protocolo()
    else:
        instance.tipo_categoria_financeira = TipoCategoriaFinanceira.get_geral()


@receiver(post_save, sender=models.Financeiro)
def enviar_pdf_fechamento_caixa(sender, instance, **kwargs):
    pass

    # if instance.colaborador_confirmado and instance.data_transacao_colaborador_confirmado:
    #     # Obter o colaborador e outras informações necessárias
    #     colaborador = get_object_or_404(User, pk=instance.colaborador_confirmado.pk)
    #     timezone.now().strftime("%Y-%m-%d")

    #     # Renderizar o PDF
    #     context = {"financeiro": instance}

    #     try:
    #         pdf = render_to_pdf("modelo_detail.html", context)
    #     except :
    #         pdf = None
    #         print("Erro enviar email caixa.")

    #     # Enviar o PDF por e-mail
    #     if pdf:
    #         to_email = colaborador.email
    #         subject = "Fechamento de Caixa"
    #         message = "Segue em anexo o PDF do fechamento de caixa."
    #         email = EmailMessage(subject, message, "from@example.com", [to_email])
    #         email
    #         email.send()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(
    sender: type["User"],
    instance: "User",
    created: bool,
    **kwargs,
) -> None:
    """Cria ou atualiza o colaborador sempre que um User for salvo."""
    logger.debug(f"Post-save signal recebido para {sender.__name__}.")
    logger.debug(f"Iniciando sinal para o usuário: {instance.id}")

    if created:
        logger.debug(
            "Novo usuário criado, tentando criar ou obter colaborador correspondente.",
        )
        colaborador, colaborador_created = models.Colaborador.objects.get_or_create(
            id=instance.id,
            defaults={"usuario": instance},
        )
        logger.debug(
            f"Colaborador {'criado' if colaborador_created else 'obtido'}: {colaborador.id}",
        )

        if not colaborador_created:
            logger.debug("Colaborador já existia, vinculando usuário ao colaborador.")
            colaborador.usuario = instance
            colaborador.save()
            logger.debug(f"Colaborador atualizado: {colaborador.id}")
        else:
            logger.debug("Colaborador criado e vinculado ao usuário.")
    else:
        logger.debug("Usuário existente salvo, nenhuma ação necessária.")


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs) -> None:
    logger.debug(
        f"Post-save signal recebido para {sender.__name__}.",
    )
    """Salva (atualiza) o colaborador sempre que um User for salvo."""
    from apps.home.models import Colaborador

    # Usar get_or_create para garantir que o colaborador será encontrado ou criado
    logger.info(f"Salvando o colaborador: {instance} devido a alterações em {sender}")

    # Tentar obter o colaborador relacionado ou criá-lo
    colaborador, created = Colaborador.objects.get_or_create(
        usuario=instance,
        defaults={"nome": instance.username},
    )


@receiver(pre_delete)
def log_pre_delete(sender, instance, **kwargs):
    if sender.__name__ == "LogEntry":
        return
    username = get_current_username()
    logger.warning(
        f"Tentando excluir - Modelo: {sender.__name__}, ID: {instance.pk}, Usuário: {username}",
    )


@receiver(post_delete)
def log_post_delete(sender, instance, **kwargs):
    if sender.__name__ == "LogEntry":
        return
    username = get_current_username()
    logger.warning(
        f"Exclusão realizada - Modelo: {sender.__name__}, ID: {instance.pk}, Usuário: {username}",
    )


@receiver(pre_save)
def log_pre_save(sender, instance, **kwargs):
    if sender.__name__ in settings.MODELS_TO_IGNORE_IN_LOG_PRE_SAVE:
        return
    username = get_current_username()
    logger.debug(
        f"Tentando salvar - Modelo: {sender.__name__}, ID: {instance.pk}, Usuário: {username}",
    )


@receiver(post_save)
def log_post_save(sender, instance, created, **kwargs):
    if sender.__name__ in settings.MODELS_TO_IGNORE_IN_LOG_PRE_SAVE:
        return
    username = get_current_username()
    action = "criado" if created else "atualizado"
    logger.debug(
        f"Registro {action} - Modelo: {sender.__name__}, ID: {instance.pk}, Usuário: {username}",
    )


@receiver(post_save, sender=apps.get_model("home", "Financeiro"))
def historico_financeiro(sender, instance, created, **kwargs):
    tipo_operacao = "criação" if created else "atualização"
    logger.debug(
        f"Post-save signal recebido para Financeiro ID {instance.id}. Tipo de operação: {tipo_operacao}.",
    )
    models.FinanceiroHistorico.atualizar_ou_criar_historico(instance, tipo_operacao)


@receiver(pre_save, sender=models.PedidoCertidao)
def set_numero_pedido_certidao(sender, instance: "PedidoCertidao", **kwargs):
    """
    Define o número de pedido de certidão para um PedidoCertidao.
    Primeira tenta obter a proxima sequence do Firebird para manter os sistemas alinhados.
    Se não encontrar ou tiver erros, tenta obter o max do numero_pedido e incrementar.
    """
    # logger.debug(f"Setando número de pedido de certidão para {instance}")
    logger.debug(f"Pré-save signal recebido para {sender.__name__}.")
    if not instance.senha_site:
        import random

        # Gerar um número aleatório inteiro entre 0 e 999999
        numero_senha_aleatorio = random.randint(0, 999999)
        instance.senha_site = str(numero_senha_aleatorio).zfill(6)

    if not instance.numero_pedido:
        try:
            logger.debug(
                "Tentando setar o número de pedido para Pedido de Certidão com base no Firebird",
            )
            from core.utils.firebird_utils import FbConnection

            with FbConnection() as fb:
                numero_pedido = fb.sequence("PED_CERTIDOES_SEQ").proximo
                while PedidoCertidao.objects.filter(
                    numero_pedido=numero_pedido,
                ).exists():
                    logger.debug(
                        "Número de pedido de certidão retornado pelo Firebird já existe localmente, tentando outro.",
                    )
                    numero_pedido = fb.sequence("PED_CERTIDOES_SEQ").proximo
                instance.numero_pedido = numero_pedido
        except Exception as e:
            logger.exception(
                f"Erro ao obter próximo número de pedido a partir do firebird: {e}",
            )

    if not instance.numero_pedido:
        try:
            logger.debug(
                "Tentando setar o número do Pedido de Certidão para com base no max numero_pedido do Postgres",
            )
            max_numero_pedido = models.PedidoCertidao.objects.aggregate(
                models.Max("numero_pedido"),
            )["numero_pedido__max"]
            instance.numero_pedido = max_numero_pedido + 1

        except Exception as e:
            logger.exception(f"Erro ao obter o max do numero_pedido: {e}")
            raise
    else:
        logger.debug(
            f"Pedido de Certidão [ID: {instance.pk}] já possui o número : {instance.numero_pedido}",
        )

    if not instance.id and instance.numero_pedido:
        instance.id = instance.numero_pedido


@receiver(post_save, sender=models.PedidoCertidao)
def post_save_pedido_certidao(
    sender: "PedidoCertidao",
    instance: "PedidoCertidao",
    created,
    **kwargs,
):
    from core.utils.firebird_utils import FbConnection

    try:
        if instance.apresentante and created:
            with FbConnection() as fb:
                fb.begin_transaction()
                instance.exportar_pedido_para_firebird(db=fb)
                fb.commit()
    except Exception as e:
        logger.exception(
            f"Erro ao exportar pedido de certidão para o Firebird: {e}",
        )


@receiver(post_save, sender=PedidoCertidao)
def resolver_problemas_conhecidos_signal(sender, instance, created, **kwargs):
    """SIGNAL PARA VERIFICAR ONR E CORRIGIR PROTOCOLOS."""

    # Função para executar a verificação ONR de forma controlada
    def executar_verificacao_onr() -> None:
        with lock_onr:
            views.verificar_webservice_onr(None)

    # Função para executar correções de protocolo de forma controlada
    def executar_correcoes_protocolo() -> None:
        with lock_correcoes:
            views.corrigir_protocolo_certidao()

    # Iniciar a thread para verificação ONR, se não criada
    thread_onr = Thread(target=executar_verificacao_onr)
    thread_onr.start()

    # Iniciar a thread para correções de protocolo, se não criada
    thread_correcoes = Thread(target=executar_correcoes_protocolo)
    thread_correcoes.start()
