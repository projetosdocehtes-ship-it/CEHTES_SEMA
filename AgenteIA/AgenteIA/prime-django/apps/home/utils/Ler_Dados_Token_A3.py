import configparser
import os

from cryptography import x509
from cryptography.hazmat.backends import default_backend

# Diretorio aplicacao
path_dir = os.path.split(os.path.abspath(__file__))[0]


# LER ARQUIVO INI DO TOKEN
def read_token():
    config = configparser.ConfigParser()
    config.read(path_dir + "\\Token.ini", encoding="utf-8")
    arquivo_pem = str(config["TOKEN"]["CAMINHO_TOKEN_PEM"])
    arquivo_pfx = str(config["TOKEN"]["CAMINHO_TOKEN_PFX"])
    senha = str(config["TOKEN"]["SENHA"])

    return str(arquivo_pem).strip(), str(arquivo_pfx).strip(), str(senha).strip()


# RETORNA O NOME DO ARQUIVO TOKEN
def get_nome_token():
    # Certificaod de origem
    arquivo_pem, arquivo_pfx, senha = read_token()

    with open(arquivo_pem, "rb") as f:
        cert_data = f.read()

    # Lendo o certificado
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())

    # Obtém o nome do emissor do certificado
    cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value

    # Obtém o nome do proprietário do certificado
    owner = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value

    return str(owner).split(":")[0]

    # Outros paramatros TOKEN

    # return str(owner)

    # serial_number = cert.serial_number
    # algorithm = cert.signature_hash_algorithm
    # not_valid_after = cert.not_valid_after
    # signature = cert.signature
    # version = cert.version
    # public_key = cert.public_key
    # extensions = cert.extensions
    # tbs_certificate_bytes    = cert.tbs_certificate_bytes
    # signature_hash_algorithm = cert.signature_hash_algorithm
    # signature_algorithm_oid  = cert.signature_algorithm_oid

    # print("")
    # print("Emissor:",       issuer)
    # print("Proprietário:",  owner)
    # print("Serial Number:", serial_number)
    # print("Algoritmo:",     algorithm)
    # print("Validade:",      not_valid_after)

    # print("Assinatura:",    signature)
    # print("Versao:",        version)
    # print(public_key)
    # print("tbs_certificate_bytes:",    tbs_certificate_bytes)
    # print("signature_hash_algorithm:", signature_hash_algorithm)
    # print("signature_algorithm_oid:",  signature_algorithm_oid)
    # print(help(cert))
