import io
import logging
import os
import tempfile

import fitz  # PyMuPDF
import pytz
from cryptography import x509
from cryptography.hazmat import backends
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    load_key_and_certificates,
)
from django.utils import timezone
from endesive import pdf
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from apps.home.signals import documento_assinado_signal

logger = logging.getLogger(__name__)


def assinar_pdf(pdf_original_file, certificado_instance):
    # Preparar os dados da assinatura
    data = timezone.now()  # Ajuste para timezone UTC
    date = data.strftime("D:%Y%m%d%H%M%S+00'00'")  # Data em formato string para UTC

    # Configurando para o fuso horário de São Paulo
    sp_tz = pytz.timezone("America/Sao_Paulo")
    humanized_date = data.astimezone(sp_tz).strftime("%d/%m/%Y %H:%M:%S")

    dct = {
        # "aligned": 16384,
        "sigflags": 3,
        "sigflagsft": 132,
        "signform": True,
        # "sigfield": "123456789",
        "sigpage": -1,  # pagina que sera assinada
        "sigbutton": True,  # adiciona botao de assinatura
        # "sigfield": f"ASSINADO DIGITALMENTE POR: {certificado_instance.cn} em {date}",
        "auto_sigfield": True,  # adiciona campo de assinatura automaticamente
        # "sigandcertify": True,  # assina e certifica
        # "signaturebox": (2, 2, 100, 100),  # posicao da assinatura x, y, largura, altura
        "signaturebox": (2, 2, 600, 50),
        # "signature": certificado_instance.texto_assinatura        or f"ASSINADO DIGITALMENTE POR: {certificado_instance.cn} em {date}",  # texto da assinatura
        # "signature_img": certificado_instance.imagem_assinatura.path,  # imagem da assinatura
        "signature_appearance": {
            # "background": [0.75, 0.8, 0.95],  # cor de fundo
            "icon": certificado_instance.imagem_assinatura.path,  # icone da assinatura
            # "labels": True,  # exibe os campos
            # "outline": [0.2, 0.3, 0.5],  # cor da borda
            # "border": 2,  # tamanho da borda
            "display": "reason",  # campos a serem exibidos
            # "software": "Assinado Digitalmente por ",
        },
        "contact": certificado_instance.usuario.email,  # email do assinante
        "location": "BR",  # localizacao
        "signingdate": date,  # data da assinatura
        "reason": f"{certificado_instance.motivo_uso or 'Documento Digital Oficial'} do {certificado_instance.usuario.cartorio} | Impresso por {certificado_instance.usuario} | {certificado_instance.texto_assinatura or 'Assinado Digitalmente por:'}: {certificado_instance.cn} em {humanized_date}",  # motivo da assinatura
        # "password": certificado_instance._senha,
    }

    # Carregar os dados do certificado digital
    with open(certificado_instance.certificado.path, "rb") as cert_file:
        p12 = pkcs12.load_key_and_certificates(
            cert_file.read(),
            certificado_instance._senha.encode(),
            backend=backends.default_backend(),
        )

        datau = pdf_original_file.read()

        signed_pdf_bytes = pdf.cms.sign(
            datau,
            dct,
            p12[0],
            p12[1],
            p12[2],
            "sha256",
        )

        fname = pdf_original_file.name.replace(".pdf", "-assinado.pdf")
        with open(fname, "wb") as fp:
            fp.write(datau)
            fp.write(signed_pdf_bytes)

        logger.info(f"PDF assinado salvo em: {fname}")

        # nvia um signal para registrar o log da assinatura
        documento_assinado_signal.send(
            sender=assinar_pdf,
            documento=fname,
            usuario=certificado_instance.usuario,
            certificado=certificado_instance,
        )

        return fname


def adicionar_texto_vertical_centralizado(caminho_pdf_original, texto):
    # Abre o documento PDF original
    doc = fitz.open(caminho_pdf_original)

    for pagina in doc:
        # Define a altura e a largura da página para calcular o posicionamento centralizado
        altura_pagina = pagina.rect.height

        # O tamanho da fonte pode ser ajustado conforme necessário
        tamanho_fonte = 11

        # Calcula a largura do texto (aproximadamente, já que cada letra pode ter uma largura diferente)
        # Ajuste "tamanho_fonte * 0.6" conforme necessário para obter uma estimativa mais precisa
        largura_texto = len(texto) * tamanho_fonte * 0.6

        # Define a posição inicial do texto para que ele fique centralizado verticalmente
        # E ajusta para que o texto comece na borda inferior da página
        posicao_x = 10  # Distância da borda esquerda da página
        posicao_y_inicial = (altura_pagina / 2) - (largura_texto / 2)

        # Adiciona cada caractere do texto verticalmente
        for caractere in texto:
            # Insere o texto na página
            pagina.insert_text(
                (posicao_x, posicao_y_inicial),
                caractere,
                fontsize=tamanho_fonte,
                rotate=90,  # Rotação de cada caractere para que o texto fique vertical
            )
            # Ajusta a posição y para o próximo caractere
            posicao_y_inicial += tamanho_fonte

    # Gera um nome de arquivo temporário para salvar o PDF modificado
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf_file:
        caminho_pdf_modificado = temp_pdf_file.name

    # Salva as modificações no arquivo temporário
    doc.save(caminho_pdf_modificado)
    doc.close()

    # Retorna o caminho para o novo arquivo PDF
    return caminho_pdf_modificado


def extrair_informacoes_certificado(caminho_certificado, senha):
    # Carregar o certificado PFX
    with open(caminho_certificado, "rb") as arquivo_certificado:
        conteudo_certificado = arquivo_certificado.read()

    # O segundo argumento é a senha do arquivo PFX. Se o arquivo não tiver senha, use b"".
    privada_id, certificado, cadeia_certificados = load_key_and_certificates(
        conteudo_certificado,
        senha.encode(),
        default_backend(),
    )

    # Informações básicas
    nome_completo = certificado.subject.rfc4514_string()

    email = None
    localizacao = None

    # Extrair email
    for extensao in certificado.extensions:
        if isinstance(extensao.value, x509.SubjectAlternativeName):
            emails = extensao.value.get_values_for_type(x509.RFC822Name)
            email = emails[0] if emails else None

    # Extrair localização
    pais = (
        certificado.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)[0].value
        if certificado.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)
        else "Desconhecido"
    )
    estado = (
        certificado.subject.get_attributes_for_oid(x509.NameOID.STATE_OR_PROVINCE_NAME)[
            0
        ].value
        if certificado.subject.get_attributes_for_oid(
            x509.NameOID.STATE_OR_PROVINCE_NAME,
        )
        else "Desconhecido"
    )
    cidade = (
        certificado.subject.get_attributes_for_oid(x509.NameOID.LOCALITY_NAME)[0].value
        if certificado.subject.get_attributes_for_oid(x509.NameOID.LOCALITY_NAME)
        else "Desconhecido"
    )

    localizacao = f"País: {pais}, Estado: {estado}, Cidade: {cidade}"

    # Datas de validade
    data_inicio_validade = certificado.not_valid_before_utc
    data_fim_validade = certificado.not_valid_after_utc

    return {
        "nome_completo": nome_completo,
        "email": email,
        "localizacao": localizacao,
        "data_inicio_validade": data_inicio_validade,
        "data_fim_validade": data_fim_validade,
    }


def adicionar_rodape_no_pdf(caminho_pdf_original, texto_rodape) -> None:
    # Primeiro, crie um PDF temporário com o texto do rodapé
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    width, height = letter
    c.drawString(30, 30, texto_rodape)  # Ajuste a posição conforme necessário
    c.save()

    # Mova o ponteiro para o início do StringIO buffer
    packet.seek(0)

    # Ler o PDF original e o PDF do rodapé
    reader_original = PdfReader(caminho_pdf_original)
    reader_rodape = PdfReader(packet)
    writer = PdfWriter()

    # Para cada página do PDF original, adicione o rodapé
    for page_number in range(len(reader_original.pages)):
        page = reader_original.pages[page_number]
        page.merge_page(reader_rodape.pages[0])
        writer.add_page(page)

    # Escreva o PDF resultante em um arquivo temporário
    caminho_temporario = caminho_pdf_original + ".temp"
    with open(caminho_temporario, "wb") as f_temp:
        writer.write(f_temp)

    # Substitua o PDF original pelo temporário modificado
    os.replace(caminho_temporario, caminho_pdf_original)
