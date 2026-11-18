import io
import logging
from io import BytesIO

import signxml
import xhtml2pdf.pisa as pisa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.http import HttpResponse
from django.template.loader import get_template
from lxml import etree
from signxml import XMLSigner

# from weasyprint import HTML

try:
    from OpenSSL import crypto
except ImportError:
    msg = "O pacote não está instalado. Execute 'pip install cryptography PyOpenSSL'"
    raise


logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


# RETORNAR O CODIGO DA CERTIDAO POS REGISTRO
def get_cod_certidao_pos_registro() -> str:
    from apps.home.models import ValorCertidao

    return ValorCertidao.objects.filter(certidao_pos_registro=True).first()


def assinar_documento(documento, certificado_path, senha):
    with open(certificado_path, "rb") as cert_file:
        certificado = crypto.load_pkcs12(cert_file.read(), senha)

    privada_id = certificado.get_privatekey()
    cert = certificado.get_certificate()
    store = crypto.X509Store()
    store.add_cert(cert)

    # Assinatura do documento
    return privada_id.sign(
        documento.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def verificar_assinatura(
    documento,
    assinatura,
    certificado_publico_path,
) -> bool | None:
    with open(certificado_publico_path, "rb") as cert_file:
        certificado_publico = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            cert_file.read(),
        )

    # Verificação da assinatura
    try:
        crypto.verify(certificado_publico, assinatura, documento.encode(), "sha256")
        return True
    except crypto.Error:
        return False


def converter_html_para_pdf(html_content: str) -> io.BytesIO:
    # Criar o PDF inicialmente em memória
    pdf_bytes = io.BytesIO()

    # converter o HTML para PDF e salvar em memória
    HTML(string=html_content).write_pdf(target=pdf_bytes)

    # Retorna o PDF em bytes
    pdf_bytes.seek(0)

    # Ler o conteúdo do PDF do buffer de bytes e retornar
    return pdf_bytes


def html_to_pdf(template_src, context_dict=None):
    # defining the function to convert an HTML file to a PDF file
    if context_dict is None:
        context_dict = {}
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type="application/pdf")
    return None


def assinar_xml(xml_path: str, key_path: str, cert_path: str, output_path: str):
    """
    Assina digitalmente um arquivo XML.

    :param xml_path: Caminho para o arquivo XML a ser assinado.
    :param key_path: Caminho para a chave privada.
    :param cert_path: Caminho para o certificado público.
    :param output_path: Caminho para salvar o arquivo XML assinado.
    """
    # Carrega o XML
    with open(xml_path, "rb") as xml_file:
        xml_data = xml_file.read()

    # Carrega a chave privada e o certificado
    with open(key_path, "rb") as key_file:
        key_data = key_file.read()

    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()

    # Parseia o XML
    xml_tree = etree.fromstring(xml_data)

    # Cria o assinador
    signer = XMLSigner(method=signxml.methods.enveloped, digest_algorithm="sha256")

    # Assina o XML
    signed_xml = signer.sign(xml_tree, key=key_data, cert=cert_data)

    # Salva o XML assinado
    with open(output_path, "wb") as output_file:
        output_file.write(etree.tostring(signed_xml))


# # Exemplo de uso
# xml_path = "path/to/input.xml"
# key_path = "path/to/private_key.pem"
# cert_path = "path/to/certificate.pem"
# output_path = "path/to/signed_output.xml"
# assinar_xml(xml_path, key_path, cert_path, output_path)
