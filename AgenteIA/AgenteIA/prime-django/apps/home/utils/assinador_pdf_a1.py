# https://github.com/m32/endesive/blob/master/examples/pdf-sign-cms.py
# https://github.com/m32/endesive/blob/master/examples/pdf-sign-fpdf.py

import datetime

from cryptography.hazmat import backends
from cryptography.hazmat.primitives.serialization import pkcs12
from endesive.pdf import cms


def main(token_pfx, senha, pdf_path) -> None:
    date = datetime.datetime.now()
    date = date.strftime("D:%Y%m%d%H%M%S+00'00'")
    dct = {
        "aligned": 8192,
        "sigflags": 3,
        "sigflagsft": 132,
        "sigpage": 0,
        "signature": "Dokument podpisany cyfrowo ąćęłńóśżź",
        "contact": "contact:mak@trisoft.com.pl",
        "location": "Szczecin",
        "signingdate": date,
        "reason": "Dokument podpisany cyfrowo aą cć eę lł nń oó sś zż zź",
        "password": senha,
    }

    # Converter senha em bytes
    bytes_senha = str(senha).encode("utf-8")

    with open(token_pfx, "rb") as fp:
        p12 = pkcs12.load_key_and_certificates(
            fp.read(),
            bytes_senha,
            backends.default_backend(),
        )

    with open(pdf_path, "rb").read() as datau:
        pdf_assinado_bytes = cms.sign(datau, dct, p12[0], p12[1], p12[2], "sha256")
        pdf_path = pdf_path.replace(".pdf", "-assinado.pdf")

    with open(pdf_path, "wb") as fp:
        fp.write(datau)
        fp.write(pdf_assinado_bytes)

    print("Assinado o arquivo digital ")


# passar o TOKEN, SENHA, ARQUIVO
# main("C:\\AssinarA1\\Token\\1001383853.pfx", "marciomoraes66", "C:\\AssinarA1\\AA.pdf")
