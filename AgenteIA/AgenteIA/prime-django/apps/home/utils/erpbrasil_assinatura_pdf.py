import os
from datetime import datetime

# from erpbrasil.assinatura.assinatura import Assinatura
# from erpbrasil.assinatura.certificado import Certificado

# from apps.home.utils.erpbrasil.assinatura.assinatura import Assinatura
# from apps.home.utils.erpbrasil.assinatura.certificado import Certificado


"""
#certificado_nfe_caminho = os.environ.get('certificado_nfe_caminho', 'tests/teste.pfx')
#certificado_nfe_senha = os.environ.get('certificado_nfe_senha', 'teste')
#certificado_nfe_caminho = os.environ.get('certificado_nfe_caminho', '26360022869.pfx')
#certificado_nfe_senha = os.environ.get('certificado_nfe_senha', '651100')

"""
# certificado_nfe_caminho = os.environ.get('certificado_nfe_caminho', 'bierley.pfx')
# certificado_nfe_senha = os.environ.get('certificado_nfe_senha', '6511')

"""
#certificado_nfe_caminho = os.environ.get('certificado_nfe_caminho', 'certificadoemilio.pfx')
#certificado_nfe_senha = os.environ.get('certificado_nfe_senha', '141167')

#certificado_ecpf_caminho = os.environ.get('certificado_ecpf_caminho', 'tests/teste.pfx')
#certificado_ecpf_senha = os.environ.get('certificado_ecpf_senha', 'teste')
certificado_ecpf_caminho = os.environ.get('certificado_ecpf_caminho', '26360022869.pfx')
certificado_ecpf_senha = os.environ.get('certificado_ecpf_senha', '651100')

test_path = os.environ.get('test_path', 'tests/')



import logging
logger = logging.getLogger(__name__)
"""
Certificado = None
Assinatura = None


def gerar_arquivo_assinado_a1() -> None:
    certificado_nfe_caminho = os.environ.get("CERTIFICADO_NFE_CAMINHO", "bierley.pfx")
    certificado_nfe_senha = os.environ.get("CERTIFICADO_NFE_SENHA", "6511")

    certificado = Certificado(
        certificado_nfe_caminho,
        certificado_nfe_senha,
        raise_expirado=False,
    )

    assinador = Assinatura(certificado)

    # nome_arquivo_pdf = test_path + 'files/google.pdf'
    nome_arquivo_pdf = "D:\\ERP\\erpbrasil.assinatura-master\\tests\\files\\google.pdf"

    with open(nome_arquivo_pdf, "rb") as f:
        arquivo = f.read()

    assinatura = {
        "sigflags": 3,
        "contact": "KMEE INFORMATICA LTDA",
        "location": "BR",
        "signingdate": str.encode(datetime.utcnow().strftime("%Y%M%d%H%M%S%Z")),
        "reason": "Teste assinatura",
    }

    try:
        from endesive import pdf  # noqa: F401
    except ImportError:
        print(
            "skipping test because https://github.com/m32/endesive"
            "package but it is not installed. It is not bundled by default"
            "to avoid depending on pyopenssl which is deprecated.",
        )
    # return False

    assinatura = assinador.assina_pdf(
        arquivo=arquivo,
        assinatura=assinatura,
    )

    # file_temp = tempfile.gettempdir() + '/google-signed-nfe.pdf'
    file_temp = (
        "D:\\ERP\\erpbrasil.assinatura-master\\tests\\files\\google-signed-nfe.pdf"
    )

    with open(file_temp, "wb") as fp:
        fp.write(arquivo)
        fp.write(assinatura)

    print("Salvo em: ", file_temp)


"""
def test_assinatura_multipla_pdf():
    ecpf = Certificado(certificado_ecpf_caminho, certificado_ecpf_senha, raise_expirado=False)
    assinador_ecpf = Assinatura(ecpf)

    #nome_arquivo = test_path + 'files/google.pdf'
    nome_arquivo = 'C:\\ERP\\erpbrasil.assinatura-master\\tests\\files\\google.pdf'
    arquivo = open(nome_arquivo, 'rb').read()
    print("Abriu", nome_arquivo)

    assinatura = {
        'sigflags': 3,
        'contact': 'Luis Felipe Mileo',
        'location': 'BR',
        'signingdate': str.encode(
            datetime.utcnow().strftime("%Y%M%d%H%M%S%Z")),
        'reason': 'Teste Assinatura CPF',
    }

    try:
        from endesive import pdf  # noqa: F401

        print("Try", nome_arquivo)
    except ImportError:
        print("Erro", nome_arquivo)

        _print(
            "skipping test because https://github.com/m32/endesive"
            "package but it is not installed. It is not bundled by default"
            "to avoid depending on pyopenssl which is deprecated."
        )

        print("Erro", nome_arquivo)

    #return False

    assinatura1 = assinador_ecpf.assina_pdf(
        arquivo=arquivo,
        assinatura=assinatura,
    )


    #file_temp = tempfile.gettempdir() + '/google-signed-multiple-1.pdf'
    file_temp = 'C:\\ERP\\erpbrasil.assinatura-master\\tests\\files\\google-signed-multiple-1.pdf'

    with open(file_temp, 'wb') as fp:
        fp.write(arquivo)
        fp.write(assinatura1)

    print("AAA", nome_arquivo)

    arquivo2 = open(nome_arquivo, 'rb').read()

    nfe = Certificado(certificado_nfe_caminho, certificado_nfe_senha, raise_expirado=False)
    assinador_nfe = Assinatura(nfe)

    print("BBB", nome_arquivo)

    assinatura = {
        'sigflags': 3,
        'contact': 'KMEE INFORMATICA LTDA',
        'location': 'BR',
        'signingdate': str.encode(
            datetime.utcnow().strftime("%Y%M%d%H%M%S%Z")),
        'reason': 'Teste Assinatura CNPJ',
    }

    print("CCC", nome_arquivo)

    assinatura2 = assinador_nfe.assina_pdf(
        arquivo=arquivo2,
        assinatura=assinatura,
    )

    #file_temp = tempfile.gettempdir() + '/google-signed-multiple-1.pdf'
    file_temp = 'C:\\ERP\\erpbrasil.assinatura-master\\tests\\files\\google-signed-multiple-1.pdf'

    print("DDD", nome_arquivo)

    with open(file_temp, 'wb') as fp:
        fp.write(arquivo2)
        fp.write(assinatura2)

#test_assinatura_multipla_pdf()
"""

# test_assinatura_nfe_pdf()
