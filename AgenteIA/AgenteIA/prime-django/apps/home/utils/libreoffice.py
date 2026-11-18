import logging
import os
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def converter_rtf_para_html(rtf_blob: str) -> str:
    print("Convertendo texto...")
    html_content = None

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".rtf",
        mode="wb",
    ) as temp_rtf_file:
        # Ensure rtf_blob is bytes before writing
        if isinstance(rtf_blob, str):
            rtf_blob = rtf_blob.encode()
        temp_rtf_file.write(rtf_blob)
        temp_rtf_file_path = temp_rtf_file.name  # Store the full path

        libre_path = get_caminho_office()
        infile = temp_rtf_file_path
        outdir = str(Path(temp_rtf_file_path).parent)

        try:
            result = subprocess.run(
                [
                    libre_path,
                    "--headless",
                    "--convert-to",
                    "html:HTML",
                    infile,
                    "--outdir",
                    outdir,
                ],
                check=True,
                capture_output=True,
            )

            if result.returncode != 0:
                logger.error(
                    f"LibreOffice failed to convert file. stderr:\n{result.stderr.decode()}",
                )
                return None

            # The output HTML file might have a name derived from the input RTF filename minus its .rtf extension
            rtf_file_path = Path(temp_rtf_file_path)
            html_file_path = rtf_file_path.with_suffix(".html")
            html_path = Path(Path(temp_rtf_file_path).parent / html_file_path.name)
            html_content = None

            if Path(html_path).exists():
                with html_path.open(encoding="utf-8") as html_file:
                    html_content = html_file.read()

            else:
                logger.error(f"O arquivo HTML esperado não foi encontrado: {html_path}")
                return None
        except subprocess.CalledProcessError as e:
            logger.exception(
                f"Error converting RTF to HTML with LibreOffice: {e.stderr.decode()}",
            )
            return None
        except Exception:
            logger.exception("Error converting RTF to HTML with LibreOffice: ")
            return None
    print("Conversão bem-sucedida do texto RTF para HTML!")
    return html_content


# def adicionar_meta_charset(html: str, charset="UTF-8") -> str:
#     # Adiciona a tag meta para especificar o charset se ainda não existir
#     header = f'<meta charset="{charset}">'
#     if "<head>" in html:
#         html = html.replace("<head>", "<head>" + header)
#     else:
#         html = "<html><head>" + header + "</head><body>" + html + "</body></html>"
#     return html


def converter_html_para_rtf(html: str) -> str:
    from apps.home.utils.html_utils import adicionar_head_elements

    rtf_content = None
    rtf_file_path = None
    fd, temp_html_file_path = tempfile.mkstemp(suffix=".html")

    html = adicionar_head_elements(
        html,
        charset="UTF-8",
    )  # Adiciona a tag meta para especificar o charset se ainda não existir

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_html_file:
            temp_html_file.write(html)

        libre_path = get_caminho_office()
        infile = temp_html_file_path
        outdir = str(Path(temp_html_file_path).parent)

        try:
            result = subprocess.run(
                [
                    libre_path,
                    "--headless",
                    "--convert-to",
                    "rtf:Rich Text Format",
                    infile,
                    "--outdir",
                    outdir,
                ],
                check=True,
                capture_output=True,
            )

            if result.returncode == 0:
                # O arquivo RTF de saída tem um nome derivado do nome do arquivo HTML de entrada menos sua extensão .html
                rtf_file_path = Path(infile).with_suffix(
                    ".rtf",
                )  # Ajuste para .rtf se for o formato desejado
                if rtf_file_path.exists():
                    with open(rtf_file_path, "rb") as rtf_file:
                        rtf_content = rtf_file.read().decode("utf-8")
                else:
                    logger.info(f"The expected RTF file was not found: {rtf_file_path}")
            else:
                print(
                    f"LibreOffice failed to convert file. stderr:\n{result.stderr.decode('utf-8')}",
                )
        except subprocess.CalledProcessError as e:
            print(
                f"Error converting HTML to RTF with LibreOffice: {e.stderr.decode('utf-8')}",
            )
        except Exception:
            print("Error converting HTML to RTF with LibreOffice: ")

    finally:
        Path(temp_html_file_path).unlink(
            missing_ok=True,
        )  # Limpa o arquivo temporário HTML
        if rtf_file_path:
            rtf_file_path.unlink(
                missing_ok=True,
            )  # Limpa o arquivo RTF gerado, se necessário

    return rtf_content


def get_caminho_office() -> str:
    caminho_windows = settings.DEFAULT_DIRETORIO_LIBRE_OFFICE_WINDOWS
    caminho_unix = settings.DEFAULT_DIRETORIO_LIBRE_OFFICE_UNIX

    diretorio_padrao = (
        None  # Inicialize com None para evitar referência antes da atribuição
    )

    if Path(caminho_windows).exists():
        diretorio_padrao = caminho_windows
    elif Path(caminho_unix).exists():
        diretorio_padrao = caminho_unix
    elif "soffice" in os.getenv(
        "PATH",
        "",
    ):  # Verifica somente o nome do executável no PATH
        diretorio_padrao = "soffice"

    # Se nenhum caminho padrão foi encontrado, o retorno será DEFAULT_CAMINHO_OFFICE.
    return diretorio_padrao or settings.DEFAULT_CAMINHO_OFFICE
