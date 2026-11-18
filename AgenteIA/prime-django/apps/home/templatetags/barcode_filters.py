import base64
from io import BytesIO

import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from django import template

register = template.Library()


@register.filter
def gerar_codigo_barras(value) -> str:
    # Preenche com zeros à esquerda até ter 12 dígitos e pega apenas os primeiros 12 dígitos.
    value = str(value).zfill(12)[:12]
    barcode = Code128(str(value), writer=ImageWriter())
    image = barcode.render()

    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{img_str}"


@register.filter
def gerar_qr_code(value) -> str:
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=2,
        border=2,
    )
    qr.add_data(value)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{img_str}"
