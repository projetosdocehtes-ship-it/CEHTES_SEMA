import base64
import logging

import PyKCS11
from zeep import Client

# Configuração do logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


logger.debug(f"Iniciando {__name__}")


class TokenA3Service:
    def __init__(self, lib_path, pin):
        self.lib_path = lib_path
        self.pin = pin
        self.pkcs11 = PyKCS11.PyKCS11Lib()
        self.pkcs11.load(self.lib_path)
        self.session = None

    def list_slots(self):
        slots = self.pkcs11.getSlotList(tokenPresent=True)
        for slot in slots:
            print(f"Slot {slot}: {self.pkcs11.getSlotInfo(slot)}")
        return slots

    def start_session(self):
        slots = self.list_slots()
        if not slots:
            msg = "Nenhum token encontrado"
            raise Exception(msg)

        self.session = self.pkcs11.openSession(slots[0])
        try:
            self.session.login(self.pin)
            print("Sessão iniciada")
        except PyKCS11.PyKCS11Error as e:
            self.session.closeSession()
            self.session = None
            print("Erro ao iniciar sessão:", e)
            raise

    def close_session(self):
        if self.session:
            try:
                self.session.logout()
            except PyKCS11.PyKCS11Error as e:
                print("Erro ao encerrar sessão:", e)
            finally:
                self.session.closeSession()
                self.session = None
                print("Sessão encerrada")

    def get_certificate(self):
        if not self.session:
            msg = "Sessão não iniciada"
            raise Exception(msg)

        try:
            for obj in self.session.findObjects():
                attr = self.session.getAttributeValue(
                    obj,
                    [PyKCS11.CKA_CLASS, PyKCS11.CKA_LABEL],
                )
                if attr[0] == PyKCS11.CKO_CERTIFICATE:
                    cert_der = self.session.getAttributeValue(obj, [PyKCS11.CKA_VALUE])[
                        0
                    ]

                    if isinstance(cert_der, tuple):
                        if all(isinstance(x, int) for x in cert_der):
                            cert_der = bytes(cert_der)
                        else:
                            msg = "A tupla contém valores que não são inteiros"
                            raise Exception(msg)

                    if isinstance(cert_der, bytes):
                        return base64.b64encode(cert_der).decode("utf-8")
                    else:
                        msg = "O valor do certificado não é um objeto de bytes nem uma lista de inteiros válida"
                        raise Exception(
                            msg,
                        )
        except Exception as e:
            print("Erro ao obter certificado:", e)
            raise

    def sign_data(self, data):
        if not self.session:
            msg = "Sessão não iniciada"
            raise Exception(msg)

        try:
            print("Desafio (bytes):", data)

            priv_key = None
            for obj in self.session.findObjects():
                attr = self.session.getAttributeValue(obj, [PyKCS11.CKA_CLASS])
                if attr[0] == PyKCS11.CKO_PRIVATE_KEY:
                    priv_key = obj
                    break

            if priv_key is None:
                msg = "Chave privada não encontrada"
                raise Exception(msg)

            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)
            signature = bytes(self.session.sign(priv_key, data, mechanism))
            print("Assinatura (bytes):", signature)

            return signature
        except Exception as e:
            print("Erro ao assinar dados:", e)
            raise

    def get_token(self):
        token = "LilH4NDK9NY93d/zHbhdDpOy2GiXs3jbqvMKHf+M/vZ8ZuURDvmG8k4agwWftufqDf5VWSPUq2Q176oyxzh87OOPdq3sKgkynP5Zd4JnjHqkNg2gaxTSqkYVv5oHOsQHJx2LunMwTK0aOTMbEVpeROZTF7/TagMk3rBBNo7uUPI="
        print("Token obtido:", token)
        return token


class CNIBService:
    def __init__(self, wsdl, token_service):
        self.client = Client(wsdl=wsdl)
        self.token_service = token_service

    def challenge_generator(self):
        response = self.client.service.challenge_generator()
        if response.success:
            return response.info.challenge
        else:
            msg = f"Erro ao gerar desafio: {response.info.faultMessage}"
            raise Exception(msg)

    def auth(self, challenge):
        try:
            # Decodifica o desafio de base64 para bytes
            challenge_bytes = base64.b64decode(challenge)

            self.token_service.start_session()
            certificate = self.token_service.get_certificate()

            # Assina os dados decodificados do desafio
            assinatura = self.token_service.sign_data(challenge_bytes)

            # Codifica a assinatura de volta para base64
            assinatura_base64 = base64.b64encode(assinatura).decode("utf-8")

            token = self.token_service.get_token()

            auth_data = {
                "token": token,
                "challenge": challenge,
                "signature": assinatura_base64,
                "certificate": certificate,
            }

            print("Dados de autenticação:", auth_data)

            response = self.client.service.auth(**auth_data)
            if response.success:
                return response.info.session_id
            else:
                msg = f"Erro na autenticação: {response.info.faultMessage}"
                raise Exception(msg)
        except Exception as e:
            logger.exception("Erro em auth: %s", e)
            raise
        finally:
            self.token_service.close_session()

    def get_user_data(self, session_id):
        get_user_data = {"session_id": session_id}
        response = self.client.service.get_user_data(get_user_data)
        if response.success:
            return response.info.user_data
        else:
            msg = f"Erro ao obter dados do usuário: {response.info.faultMessage}"
            raise Exception(msg)

    def get_xml(self, session_id, visualizado, data_inicial, data_final):
        get_xml_data = {
            "session_id": session_id,
            "visualizado": visualizado,
            "data_inicial": data_inicial,
            "data_final": data_final,
        }
        response = self.client.service.get_xml(get_xml_data)
        if response.success:
            return response.info.xml_content
        else:
            msg = f"Erro ao obter XML: {response.info.faultMessage}"
            raise Exception(msg)

    def responde_indisponibilidade(self, session_id, xml_content):
        responde_indisponibilidade_data = {
            "session_id": session_id,
            "xml_content": xml_content,
        }
        response = self.client.service.responde_indisponibilidade(
            responde_indisponibilidade_data,
        )
        if response.success:
            return response.info.matriculas
        else:
            msg = f"Erro ao responder indisponibilidade: {response.info.faultMessage}"
            raise Exception(msg)

    def pesquisa(self, session_id, documento):
        pesquisa_data = {"session_id": session_id, "documento": documento}
        response = self.client.service.pesquisa(pesquisa_data)
        if response.success:
            return response.info.documentos, response.info.hash
        else:
            msg = f"Erro na pesquisa: {response.info.faultMessage}"
            raise Exception(msg)


# Exemplo de uso:
if __name__ == "__main__":
    wsdl = "http://www.indisponibilidade.org.br/wsdl/"
    lib_path = "C:\\Program Files (x86)\\Gemalto\\IDGo 800 PKCS#11\\IDPrimePKCS1164.dll"
    pin = "915338"  # Substitua pelo PIN do seu token
    token_service = TokenA3Service(lib_path, pin)
    service = CNIBService(wsdl, token_service)

    try:
        slots = token_service.list_slots()
        print("Slots disponíveis:", slots)
    except Exception as e:
        print("Erro ao listar slots disponíveis:", e)
        raise

    try:
        challenge = service.challenge_generator()
        print("Challenge:", challenge)
    except Exception as e:
        print("Erro ao gerar challenge:", e)
        raise

    try:
        session_id = service.auth(challenge)
        print("Session ID:", session_id)
    except Exception as e:
        print("Erro ao obter Session ID:", e)
        raise

    try:
        user_data = service.get_user_data(session_id)
        print("User Data:", user_data)
    except Exception as e:
        print("Erro ao obter User Data:", e)
        raise

    try:
        xml_content = service.get_xml(session_id, "sim", "10/10/2014", "20/10/2014")
        print("XML Content:", xml_content)
    except Exception as e:
        print("Erro ao obter XML Content:", e)
        raise

    try:
        matriculas = service.responde_indisponibilidade(session_id, "<?xml...?>...")
        print("Matriculas:", matriculas)
    except Exception as e:
        print("Erro ao responder indisponibilidade: ", e)
        raise

    try:
        documentos, hash_value = service.pesquisa(session_id, "12345678901")
        print("Documentos:", documentos)
        print("Hash:", hash_value)
    except Exception as e:
        print("Erro ao realizar pesquisa de documentos:", e)
        raise
