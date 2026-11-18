import logging
from typing import TYPE_CHECKING

from apps.home.models import models_home as models
from apps.home.utils.libreoffice import converter_rtf_para_html
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from apps.home.models import Livro02


def get_ficha_e_data_de_abertura_do_registro_fb(imovel_id, db: FbConnection) -> dict:
    db = db if db else FbConnection()

    if not imovel_id:
        return None

    resultado = db.execute_query(
        f"""
        SELECT FICHA, DATA_ABERTURA
        FROM IMOVEIS
        WHERE CHAVE_IMOVEIS = {imovel_id}
        """,
    )

    return resultado[0] if resultado else None


def importar_ficha_do_fb_e_gravar_no_livro02(imovel_id: int, db: FbConnection) -> None:
    logger.info(f"RTF: Importando RTF Registro: {imovel_id}")

    ficha_e_data_de_abertura = get_ficha_e_data_de_abertura_do_registro_fb(
        imovel_id,
        db,
    )

    if ficha_e_data_de_abertura:
        ficha_rtf = ficha_e_data_de_abertura["FICHA"]
        data_abertura = ficha_e_data_de_abertura["DATA_ABERTURA"]

        ficha_html = None
        # Converte o BLOB RTF para HTML
        try:
            if ficha_rtf is None or not ficha_rtf.strip(b"\x00"):
                print("Não há texto para converter.")
                return None
            ficha_html = converter_rtf_para_html(ficha_rtf)
        except Exception:
            mensagem = "ERRO converter RTF para HTML usando o LibreOffice"
            logger.exception(mensagem)
            logger.exception(mensagem)
            return None

        if ficha_html:
            livro02_atualizado = gravar_texto_livro02(
                ficha_html,
                data_abertura,
                imovel_id,
            )
            logger.info("RTF: Importação bem-sucedida do texto do LIVRO 2!")
            return livro02_atualizado
    else:
        logger.error("RTF: Não foi possível obter o texto do LIVRO 2.")

    return None


def gravar_texto_livro02(texto: str, data_abertura: str, imovel_id: int) -> "Livro02":
    # Cria ou atualiza o documento no modelo Document
    livro02, created = models.Livro02.objects.update_or_create(
        id=imovel_id,
        defaults={"data_abertura": data_abertura, "texto": texto},
    )
    logger.info("RTF: Importação bem-sucedida do texto do LIVRO 2!")

    return livro02
