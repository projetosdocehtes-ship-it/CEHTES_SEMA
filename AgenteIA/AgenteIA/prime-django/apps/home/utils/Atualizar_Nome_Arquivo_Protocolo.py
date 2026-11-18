import contextlib
import glob
import logging
from pathlib import Path

from django.utils import timezone

from apps.cartorios.models import Usuario
from apps.home.models import Configuracao, FaseAgenda, PedidoItem, TipoAndamento
from apps.home.templatetags.home_formatos import (
    protocolo_formatado,
)

# Importar os protocolos


logger = logging.getLogger(__name__)


# SELECIONAR O TITULO A ENCERRAR
def encerrar_evento(eventos, protocolo_id, data) -> None:
    from apps.home.models import Event

    titulo = FaseAgenda.objects.filter(id=eventos).values_list("nome", flat=True)
    titulo_baixar = titulo[0] + " " + protocolo_formatado(str(protocolo_id))

    # ENCERRANDO OS EVENTOS DA AGENDA
    Event.objects.encerrar_evento_pelo_titulo(
        titulo=titulo_baixar,
        data=data,
        exibir_agenda_protocolo="S",
    )


def processar_importar_titulo() -> None:
    from apps.home.utils.importacao_de_protocolo_firebird import criar_andamento_fb

    base_scanner = Configuracao.obter("diretorio_scanner_protocolo")
    base_destino = Configuracao.obter("diretorio_ged_protocolos")
    tipo_andamento_id = TipoAndamento.objects.get_ids_de_tipo_digitalizar()
    colaboradores = Usuario.get_usuarios_com_protocolos_prontos_digitalizar()

    tipo_andamento_id = int(tipo_andamento_id[0])
    colaborador_id = colaboradores.last().id

    print("Buscar base das imagens do Titulo ")

    # Criar pastas de destino se não existirem
    try:
        Path(base_destino).mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("ERRO ao criar pasta de destino: ")

    # Contadores de arquivos por pasta

    # Listar e processar os arquivos PDF
    for filepath in glob.glob(base_scanner + "*.pdf"):
        try:
            filename = Path(filepath).name
            arquivo_sem_extensao = filename.split(".pdf")[0].replace(".", "")[:6]
            pedido_item_id = arquivo_sem_extensao

            # VERIFICAR SE E UM INTEIRO
            processar = arquivo_sem_extensao.isdigit()

            if processar:
                caminho_original = base_scanner + filename
                # caminho_da_pasta = base_destino + arquivo_sem_extensao

                # # Criar pasta se necessário
                # if not os.path.exists(caminho_da_pasta):
                #     os.makedirs(caminho_da_pasta, exist_ok=True)
                #     contador_arquivos[caminho_da_pasta] = 0

                # # Incrementar contador de arquivo
                # try:
                #     contador_arquivos[caminho_da_pasta] += 1
                # except KeyError:
                #     contador_arquivos[caminho_da_pasta] = 1

                # total_arquivos = contador_arquivos[caminho_da_pasta]

                # caminho_destino = (
                #     f"{caminho_da_pasta}\\{arquivo_sem_extensao}.{str(total_arquivos).zfill(5)}.pdf"
                # )

                # # Copia o arquivo
                # shutil.copy(caminho_original, caminho_destino)
                # from apps.home.models import Anexo
                # content_type = ContentType.objects.get_for_model(protocolo)
                # anexo = Anexo.objects.create()
                # anexo.content_type = content_type
                # anexo.object_id = protocolo.pk
                # anexo.save()

                # Remove o arquivo original
                Path(caminho_original).unlink()

                # Salvado no banco de dados - FIREBIRD
                try:
                    pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()
                    criar_andamento_fb(
                        pedido_id=pedido_item.pedido_id,
                        colaborador_id=colaborador_id,
                        tipo_andamento_id=tipo_andamento_id,
                        arquivo_docx=None,
                    )
                except Exception:
                    logging.exception("Error while saving to the database: ")

                # Encerrar Evento - DIGITALIZAR
                with contextlib.suppress(Exception):
                    encerrar_evento(2, str(pedido_item_id), timezone.now().date())

                # print("Gerando: ", caminho_destino)

        except Exception:
            logger.info(f"ERRO ao processar arquivo {filepath}: ")

    print("Encerrado")
