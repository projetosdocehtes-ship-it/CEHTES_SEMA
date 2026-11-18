import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


def inicializar_navegador():
    # Configura o driver do Selenium
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()))


def login_reverso(driver):
    # Abre a URL
    driver.get("https://reverso.---.com.br/")

    # Aguarda o carregamento da página
    time.sleep(2)

    # Entra com o usuário e senha
    campo_usuario = driver.find_element(By.ID, "username")
    campo_usuario.send_keys("rodrigo")
    campo_senha = driver.find_element(By.ID, "password")
    campo_senha.send_keys("senhas12399")
    campo_senha.send_keys(Keys.RETURN)

    # Aguarda o login ser efetuado
    time.sleep(2)


def descriptografar_lista(criptografados):
    driver = inicializar_navegador()
    login_reverso(driver)

    resultados = []

    for criptografado in criptografados:
        # Encontra o primeiro textarea e insere o valor criptografado
        textarea_criptografado = driver.find_element(By.ID, "criptografado")
        textarea_criptografado.send_keys(criptografado)

        # Aguarda a descriptografia (assumindo que ocorre automaticamente)
        time.sleep(2)

        # Recupera o valor descriptografado do segundo textarea
        textarea_descriptografado = driver.find_element(By.ID, "descriptografado")
        valor_descriptografado = textarea_descriptografado.get_attribute("value")

        # Adiciona o valor descriptografado à lista de resultados
        resultados.append(valor_descriptografado)

        # Limpa o campo de entrada para o próximo valor
        textarea_criptografado.clear()

    # Fecha o navegador
    driver.quit()

    return resultados


# Exemplo de uso
lista_criptografados = ["valor1", "valor2", "valor3"]
resultados = descriptografar_lista(lista_criptografados)
print(resultados)


# # Teste da função
# criptografado = "29342529132d"
# descriptografado = descriptografar_valor(criptografado)
# print("Valor descriptografado:", descriptografado)
