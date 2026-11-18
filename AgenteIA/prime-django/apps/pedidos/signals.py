# pedidos/signals.py
import asyncio
import logging
import threading

from django.core.mail import send_mail
from django.db.models import F, Max
from django.db.models.signals import post_migrate, post_save, pre_save
from django.db.utils import ProgrammingError
from django.dispatch import receiver

from apps.comum.models import PrazoLegal
from apps.home.padroes import CODIGO_PRENOTACAO_MG, PRENOTACAO, PROVISORIO
from apps.home.views import verificar_protocolos_nao_importado
from apps.pedidos.models import (
    Ato,
    AtoPraticavel,
    OrgaoEmissor,
    Pedido,
    Tabela,
    TipoEmolumento,
    TipoTitulo,
)
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")

SIGNALS_IMPORTED = True


# @receiver(pre_save)
# def set_audit_fields(sender, instance, **kwargs):
#     if hasattr(instance, "criado_por") or hasattr(instance, "modificado_por"):
#         user = getattr(instance, "audit_user", None)
#         if user:
#             if not instance.pk and hasattr(instance, "criado_por"):
#                 instance.criado_por = user
#             if hasattr(instance, "modificado_por"):
#                 instance.modificado_por = user


# @receiver(pre_save, sender=Pedido)
# def increment_numero_pedido(sender, instance, **kwargs) -> None:
#     """
#     Incrementa o número do pedido antes de salvar.

#     Se o número do pedido não estiver definido, ele será atribuído como o maior número de pedido existente + 1.
#     """
#     try:
#         if not instance.numero_pedido:
#             # Obtém o maior número de pedido existente
#             max_numero_pedido = sender.objects.aggregate(
#                 max_numero=Max("numero_pedido"),
#             )["max_numero"]
#             if max_numero_pedido is not None:
#                 instance.numero_pedido = max_numero_pedido + 1
#                 logger.info(
#                     f"Novo número de pedido atribuído: {instance.numero_pedido}",
#                 )
#             else:
#                 instance.numero_pedido = 1
#                 logger.info(
#                     "Nenhum pedido existente encontrado. Iniciando numeração do pedido em 1.",
#                 )
#     except Exception as e:
#         logger.exception(f"Erro ao incrementar o número do pedido: {e}")
#         # Relevante em casos onde falhas podem exigir ações adicionais ou notificações
#         raise


@receiver(post_save, sender=Pedido)
def add_prenotacao_ato(sender, instance, created, **kwargs) -> None:
    """
    Adiciona o Ato Prenotação em todos os novos pedidos.

    Args:
    ----
        sender: O modelo que enviou o sinal.
        instance: A instância do modelo que foi salva.
        created: Um booleano indicando se a instância foi criada ou atualizada.
        **kwargs: Argumentos adicionais.

    """
    if created:
        from apps.pedidos import models as pedidos_models

        try:
            ato_praticavel_prenotacao = pedidos_models.get_ato_praticavel_prenotacao()
            tipo_emolumento = pedidos_models.get_tipo_emolumento_prenotacao()
            tipo_tributacao = pedidos_models.get_default_tipo_tributacao()
            tipo_titulo = pedidos_models.get_tipo_titulo_prenotacao()

            ato = pedidos_models.create_ato(
                ato_praticavel=ato_praticavel_prenotacao,
                pedido=instance,
                tipo_emolumento=tipo_emolumento,
                data=instance.data_entrada,
                tipo_tributacao=tipo_tributacao,
                tipo_titulo=tipo_titulo,
            )
            ato.save()
            logger.info(f"Ato de Prenotação criado para o pedido {instance.id}")
        except Exception as e:
            logger.exception(
                f"Erro ao criar o Ato de Prenotação para o pedido {instance.id}: {e}",
            )


# @receiver(post_save, sender=Pedido)
# async def notificar_apresentante_por_email(sender, instance, created, **kwargs):
#     if created:
#         apresentante = instance.get_apresentante()
#         if apresentante and apresentante.email:
#             logger.info(f"Enviando email para {apresentante.email}...")


#             # Envio assíncrono do e-mail
#             await asyncio.to_thread(
#                 send_mail,
#                 "Seu pedido foi recebido",
#                 f"Seu pedido foi recebido e está em análise. O número do pedido é: {instance.numero_pedido!s}. Obrigado por fazer um pedido conosco.",
#                 "Cartório de Projeto CEHTES <contato@primecartorios.com.br>",
#                 [apresentante.email],
#                 fail_silently=False,
#             )


@receiver(post_save, sender=Pedido)
async def notificar_apresentante_por_email(sender, instance, created, **kwargs):
    try:
        if created:
            apresentante = (
                await instance.get_apresentante()
            )  # Aguarde a execução da coroutine
            if apresentante and apresentante.email:
                logger.info(f"Enviando email para {apresentante.email}...")

                # Envio assíncrono do e-mail
                await asyncio.to_thread(
                    send_mail,
                    "Seu pedido foi recebido",
                    f"Seu pedido foi recebido e está em análise. O número do pedido é: {instance.numero_pedido}. Obrigado por fazer um pedido conosco.",
                    "Cartório de Projeto CEHTES <contato@primecartorios.com.br>",
                    [apresentante.email],
                    fail_silently=False,
                )
    except Exception as e:
        logger.exception(f"Erro ao enviar e-mail para o apresentante: {e}")


@receiver(post_save, sender=Ato)
def informar_ato_salvo(sender, instance, created, **kwargs) -> None:
    if created:
        logger.info(f"Ato {instance} adicionado  ao pedido {instance.pedido}!")


@receiver(post_migrate)
def pupular_emolumento_provisorio_nas_tabelas_existentes(sender, **kwargs) -> None:
    if sender.name == "apps.pedidos":
        try:
            logger.info("Populando emolumento provisório nas tabelas existentes...")
            tabelas = Tabela.objects.all()
            for tabela in tabelas:
                tabela.criar_emolumento_provisorio()
        except ProgrammingError:
            logger.info("ERRO ao acessar a tabela TABELA no banco de dados: {e}")


@receiver(post_migrate)
def populate_initial_data(sender, **kwargs) -> None:
    if sender.name == "apps.pedidos":
        try:
            if not TipoTitulo.objects.exists():
                # Se não houver registros, executa alguma lógica, como criar registros iniciais
                TipoTitulo.objects.create(
                    nome=PROVISORIO,
                    descricao="Aguardando a conclusão de processos ou documentação.",
                )
                TipoTitulo.objects.create(
                    nome="Escritura Pública",
                    descricao="Documento formal para a transferência de propriedade imobiliária, como compra e venda, doação, permuta, entre outros.",
                )
                TipoTitulo.objects.create(
                    nome="Contrato Particular",
                    descricao="Utilizado em casos como promessa de compra e venda, cessão de direitos, e outros contratos que envolvam transações imobiliárias.",
                )
                TipoTitulo.objects.create(
                    nome="Formal de Partilha",
                    descricao="Documento expedido em inventários ou divórcios, que define a divisão de bens, incluindo imóveis.",
                )
                TipoTitulo.objects.create(
                    nome="Cédula de Crédito Imobiliário",
                    descricao="Título de crédito vinculado a financiamentos imobiliários.",
                )
                TipoTitulo.objects.create(
                    nome="Carta de Arrematação",
                    descricao="Documento emitido após um leilão judicial ou extrajudicial que transfere a propriedade do imóvel arrematado.",
                )
                TipoTitulo.objects.create(
                    nome="Certidão de Matrícula",
                    descricao="Documento que comprova a existência e estado atual de um registro imobiliário, contendo informações como evento de propriedade e existência de ônus.",
                )
                TipoTitulo.objects.create(
                    nome="Termo de Quitação",
                    descricao="Documento que comprova a liquidação de uma dívida relacionada a um imóvel, como empréstimos ou financiamentos.",
                )
                TipoTitulo.objects.create(
                    nome="Mandado Judicial",
                    descricao="Ordem emitida por um tribunal, como para transferência de propriedade em casos de partilha ou execução.",
                )
                TipoTitulo.objects.create(
                    nome="Certidão Negativa de Ônus",
                    descricao="Documento que atesta a inexistência de ônus ou gravames sobre um determinado imóvel.",
                )
                TipoTitulo.objects.create(
                    nome="Laudo de Avaliação",
                    descricao="Documento técnico que estabelece o valor de mercado de um imóvel, geralmente utilizado em processos de arrematação ou alienação.",
                )
                TipoTitulo.objects.create(
                    nome="Auto de Demarcação Urbanística",
                    descricao="Documento que define os limites e características de um imóvel urbano, utilizado em processos de regularização fundiária.",
                )
                TipoTitulo.objects.create(
                    nome="Decisão Administrativa",
                    descricao="Documento que representa uma decisão de órgãos públicos relacionada a imóveis, como aprovação de projetos de construção ou desmembramento.",
                )
                TipoTitulo.objects.create(
                    nome="Contrato de Locação",
                    descricao="Documento que formaliza o acordo de aluguel de um imóvel, importante para registro de garantias locatícias.",
                )
        except ProgrammingError as e:
            logger.info(f"ERRO ao acessar a tabela TIPO_TITULO no banco de dados: {e} ")

        try:
            prazo_legal = PrazoLegal.get_default_prazo_legal()
            if not AtoPraticavel.objects.exists():
                AtoPraticavel.objects.create(
                    nome=PRENOTACAO,
                    prazo_legal=prazo_legal,
                    descricao="Ato jurídico que visa assegurar a prioridade e a reserva de um direito em relação a um registro imobiliário.",
                )
                AtoPraticavel.objects.create(
                    nome=PROVISORIO,
                    prazo_legal=prazo_legal,
                    descricao="Aguardando a conclusão de processos ou documentação.",
                )
                AtoPraticavel.objects.create(
                    nome="Abertura de Matrícula",
                    prazo_legal=prazo_legal,
                    descricao="Criação de um novo registro para propriedade sem matrícula anterior.",
                )
                AtoPraticavel.objects.create(
                    nome="Alienação Fiduciária",
                    prazo_legal=prazo_legal,
                    descricao="Registro de propriedade sob alienação fiduciária, transferindo a posse ao credor.",
                )
                AtoPraticavel.objects.create(
                    nome="Averbação de Ofício",
                    prazo_legal=prazo_legal,
                    descricao="Atualizações no registro do imóvel feitas oficialmente pelo cartório.",
                )
                AtoPraticavel.objects.create(
                    nome="Averbação de Penhora",
                    prazo_legal=prazo_legal,
                    descricao="Registro da penhora de um imóvel por ordem judicial devido a dívidas.",
                )
                AtoPraticavel.objects.create(
                    nome="Cancelamento de Hipoteca",
                    prazo_legal=prazo_legal,
                    descricao="Remoção da hipoteca do registro, indicando quitação ou anulação da dívida.",
                )
                AtoPraticavel.objects.create(
                    nome="Cancelamento de Registro",
                    prazo_legal=prazo_legal,
                    descricao="Anulação de um registro anterior, como desconstituição de propriedade.",
                )
                AtoPraticavel.objects.create(
                    nome="Transferência de Titularidade",
                    prazo_legal=prazo_legal,
                    descricao="Mudança de proprietário do imóvel por venda, doação, herança, etc.",
                )
                AtoPraticavel.objects.create(
                    nome="Registro de Hipoteca",
                    prazo_legal=prazo_legal,
                    descricao="Formalização do direito de garantia sobre um imóvel.",
                )
                AtoPraticavel.objects.create(
                    nome="Usucapião",
                    prazo_legal=prazo_legal,
                    descricao="Reconhecimento do direito de propriedade por posse prolongada.",
                )
                AtoPraticavel.objects.create(
                    nome="Servidão de Passagem",
                    prazo_legal=prazo_legal,
                    descricao="Concessão de direito de passagem sobre um terreno.",
                )
                AtoPraticavel.objects.create(
                    nome="Constituição de Condomínio",
                    prazo_legal=prazo_legal,
                    descricao="Divisão de imóvel em unidades autônomas.",
                )
                AtoPraticavel.objects.create(
                    nome="Incorporação Imobiliária",
                    prazo_legal=prazo_legal,
                    descricao="Registro de incorporações de empreendimentos imobiliários.",
                )
                AtoPraticavel.objects.create(
                    nome="Cessão de Direitos",
                    prazo_legal=prazo_legal,
                    descricao="Transferência de direitos sobre um imóvel.",
                )
                AtoPraticavel.objects.create(
                    nome="Hipoteca Reversa",
                    prazo_legal=prazo_legal,
                    descricao="Conversão do valor do imóvel em renda para o proprietário.",
                )
                AtoPraticavel.objects.create(
                    nome="Retificação de Registro",
                    prazo_legal=prazo_legal,
                    descricao="Correção de erros nos registros de imóveis.",
                )
                AtoPraticavel.objects.create(
                    nome="Desmembramento de Imóvel",
                    prazo_legal=prazo_legal,
                    descricao="Divisão de um imóvel em partes independentes.",
                )
                AtoPraticavel.objects.create(
                    nome="Unificação de Imóveis",
                    prazo_legal=prazo_legal,
                    descricao="Unificação de dois ou mais imóveis adjacentes.",
                )
                AtoPraticavel.objects.create(
                    nome="Averbação de Construção",
                    prazo_legal=prazo_legal,
                    descricao="Registro de nova construção em um terreno.",
                )
                AtoPraticavel.objects.create(
                    nome="Indisponibilidade de Bens",
                    prazo_legal=prazo_legal,
                    descricao="Restrição de venda do imóvel por ordem judicial.",
                )
                AtoPraticavel.objects.create(
                    nome="Averbação de Alteração de Nome",
                    prazo_legal=prazo_legal,
                    descricao="Registro da mudança de nome do proprietário do imóvel.",
                )
                AtoPraticavel.objects.create(
                    nome="Penhora Online",
                    prazo_legal=prazo_legal,
                    descricao="Registro de penhoras realizadas eletronicamente.",
                )
                AtoPraticavel.objects.create(
                    nome="Arquivamento",
                    prazo_legal=prazo_legal,
                    descricao="Catalogação e guarda de documentos legais referentes a propriedades imobiliárias.",
                )
                AtoPraticavel.objects.create(
                    nome="Compra e Venda",
                    prazo_legal=prazo_legal,
                    descricao="Registro de contrato de compra e venda de imóvel.",
                )
        except ProgrammingError:
            print("ERRO ao acessar a tabela NATUREZA_ATO no banco de dados: ")

        try:
            # Tabela = apps.get_model("pedidos", "Tabela")
            if not Tabela.objects.exists():
                Tabela.objects.create(data_inicio_validade="2001-01-01")
        except ProgrammingError:
            print("ERRO ao acessar a tabela TABELA no banco de dados: ")

        try:
            # TipoEmolumento = apps.get_model("pedidos", "TipoEmolumento")

            if not TipoEmolumento.objects.exists():
                TipoEmolumento.objects.create(
                    nome="Arquivamento",
                    codigo="8101-8",
                    descricao="Taxa para o registro de um novo imóvel, baseada em uma porcentagem do valor do imóvel.",
                )

                TipoEmolumento.objects.create(
                    nome="Registro de Imóvel",
                    descricao="Taxa para o registro de um novo imóvel, baseada em uma porcentagem do valor do imóvel.",
                )

                TipoEmolumento.objects.create(
                    nome="Averbação",
                    codigo="4143-4",
                    descricao="Taxa para adicionar uma construção ao registro de um imóvel, calculada como uma porcentagem do custo da construção.",
                )

                TipoEmolumento.objects.create(
                    nome="Indicação de registro ou averbação, com os números do livro e da folha ou da matrícula...",
                    codigo="4301",
                    descricao="Taxa para adicionar uma construção ao registro de um imóvel, calculada como uma porcentagem do custo da construção.",
                )

                TipoEmolumento.objects.create(
                    nome="Busca",
                    codigo="4301-4",
                    descricao="taxa cobrada pelo cartório para realizar a pesquisa e fornecer informações sobre a existência ou não de registros e averbações.",
                )

                TipoEmolumento.objects.create(
                    nome=PRENOTACAO,
                    codigo=CODIGO_PRENOTACAO_MG,
                    descricao="Taxa para adicionar uma construção ao registro de um imóvel, calculada como uma porcentagem do custo da construção.",
                )

                TipoEmolumento.objects.create(
                    nome="Certidão de Matrícula",
                    descricao="Emissão de uma certidão que comprova a existência e o estado atual de um registro imobiliário.",
                )

                TipoEmolumento.objects.create(
                    nome="Registro de Hipoteca",
                    descricao="Taxa para o registro de uma hipoteca sobre um imóvel, baseada no valor hipotecado.",
                )

                TipoEmolumento.objects.create(
                    nome="Cancelamento de Hipoteca",
                    descricao="Taxa para o cancelamento de uma hipoteca já registrada sobre um imóvel.",
                )

                TipoEmolumento.objects.create(
                    nome="Registro de Usucapião",
                    descricao="Taxa para o registro de usucapião, reconhecendo o direito de propriedade por posse prolongada.",
                )

                TipoEmolumento.objects.create(
                    nome="Registro de Contrato de Locação",
                    descricao="Taxa para o registro formal de um contrato de locação de um imóvel.",
                )
        except ProgrammingError:
            print("ERRO ao acessar a tabela TABELA no banco de dados: ")


@receiver(post_migrate)
def popular_dados_de_orgao_emissor(sender, **kwargs) -> None:
    if sender.name != "apps.pedidos":
        return

    try:
        OrgaoEmissor.criar_orgaos_emissores_padroes()
    except ProgrammingError:
        print("ERRO ao acessar a tabela ORGAO_EMISSOR no banco de dados: ")


@receiver(pre_save, sender=Pedido)
def obter_proximo_numero_do_pedido_no_fb(sender, instance, **kwargs) -> None:
    """Define o número do pedido para um Pedido de Protocolo."""
    logger.debug("Setando número de pedido para Pedido de Protocolo.")
    if instance.numero_pedido:
        return

    try:
        if instance.numero_pedido is None:
            with FbConnection() as db:
                instance.numero_pedido = db.sequence("PEDIDOS_SEQ").proximo
    except:
        logger.debug("Erro ao obter o próximo número do pedido no Firebird.")

    try:
        if not instance.numero_pedido:
            # Obtém o maior número de pedido existente
            max_numero_pedido = sender.objects.aggregate(
                max_numero=Max("numero_pedido"),
            )["max_numero"]
            if max_numero_pedido is not None:
                instance.numero_pedido = max_numero_pedido + 1

                logger.info(
                    f"Novo número de pedido atribuído: {instance.numero_pedido}",
                )
            else:
                instance.numero_pedido = 1

                logger.info(
                    "Nenhum pedido existente encontrado. Iniciando numeração do pedido em 1.",
                )
    except Exception as e:
        logger.exception(f"Erro ao incrementar o número do pedido: {e}")
        # Relevante em casos onde falhas podem exigir ações adicionais ou notificações
        raise

    if not instance.id:
        instance.id = instance.numero_pedido


@receiver(post_save, sender=Ato)
def atualizar_ato_no_firebird(sender, instance: Ato, created, **kwargs) -> None:
    """
    Atualiza um Ato no banco de dados Firebird.

    Args:
    ----
        sender: O modelo que enviou o sinal.
        instance: A instância do modelo que foi salva.
        created: Um booleano indicando se a instância foi criada ou atualizada.
        **kwargs: Argumentos adicionais.

    """
    try:
        if created:
            instance.exportar_para_fb()

    except Exception as e:
        logger.exception(f"Erro ao atualizar o Ato no Firebird: {e}")


@receiver(post_save, sender=Pedido)
def corrigir_erros_de_exportacao_dos_protocolos_no_firebird(
    sender,
    instance,
    created,
    **kwargs,
):
    logger.debug(f"Post-save signal recebido para {sender.__name__}.")
    from apps.pedidos.models import Ato

    logger.debug(
        "Obtendo protocolos cuja Prenotação tem tributação diferente de Normal",
    )
    protocolos = (
        Ato.objects.exclude(tipo_tributacao_id=1)
        .annotate(protocolo=F("pedido__numero_protocolo_firebird"))
        .filter(protocolo__isnull=False)
        .exclude(protocolo="")
        .values_list("protocolo", flat=True)
    )
    logger.debug("Protocolos obtidos: %s", protocolos)

    # thread_onr = Thread(target=corrigir_tributacao_protocolos, args=(protocolos,))
    # thread_onr.start()


@receiver(post_save, sender=Pedido)
def sincronizar_com_firebird(sender, instance, created, **kwargs) -> None:
    """
    Sincroniza os pedidos com o banco de dados Firebird.

    Args:
    ----
        sender: O modelo que enviou o sinal.
        instance: A instância do modelo que foi salva.
        created: Um booleano indicando se a instância foi criada ou atualizada.
        **kwargs: Argumentos adicionais.

    """
    try:
        # Iniciar a função verificar_protocolos_nao_importado em uma nova thread
        thread = threading.Thread(
            target=verificar_protocolos_nao_importado,
            args=(None,),
        )
        thread.start()

    except Exception as e:
        logger.exception(f"Erro ao sincronizar o Pedido no Firebird: {e}")
