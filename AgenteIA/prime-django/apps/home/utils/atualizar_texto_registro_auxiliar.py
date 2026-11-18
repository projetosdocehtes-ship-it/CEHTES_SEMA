import logging
from typing import TYPE_CHECKING

from core.utils.firebird_utils import FbConnection

if TYPE_CHECKING:
    from apps.home.models import Livro03


logger = logging.getLogger(__name__)


def get_livro03_do_fb(registro_auxiliar_id: int, db: FbConnection):
    try:
        query = f""" SELECT FICHA, DATA_ABERTURA
                FROM REG_AUXILIARES
                WHERE CHAVE_REG_AUXILIARES = {registro_auxiliar_id!s}
                """

        db = FbConnection() if db is None else db
        resultado = db.execute_query(query)

        if resultado:
            return resultado

        return None
    except Exception:
        logger.exception("ERRO ao obter RTF do Registro Auxiliar: ")


def conveter_texto_livro03_do_fb(blob_rtf: str) -> str:
    from apps.home.utils.libreoffice import converter_rtf_para_html

    html_content = None

    try:
        if blob_rtf is None or not blob_rtf.strip(b"\x00"):
            print("Não há texto para converter.")
            return None
        html_content = converter_rtf_para_html(blob_rtf)
        print("RTF: Importação bem-sucedida do texto do LIVRO 3: ")
    except Exception:
        logger.exception("ERRO ao importar RTF do Registro Auxiliar: ")

    return html_content


def atualizar_texto_livro03(
    texto: str,
    data_abertura: str,
    registro_auxiliar_id: int,
) -> "Livro03":
    from apps.home.models import Livro03

    # Cria ou atualiza o documento no modelo Document
    registro_auxiliar, created = Livro03.objects.update_or_create(
        id=registro_auxiliar_id,
        defaults={"data_abertura": data_abertura, "texto": texto},
    )
    print("RTF: Importação bem-sucedida do texto do LIVRO 3: ")

    return registro_auxiliar
