import time

from selenium import webdriver
from selenium.webdriver.common.by import By

# Inicialize o driver do navegador (neste exemplo, Chrome)
driver = webdriver.Chrome()

try:
    # Abra o site
    driver.get("https://www.oficioeletronico.com.br/")

    # Espere um pouco para garantir que a página foi carregada
    time.sleep(5)

    # Localize o botão "AUTENTICAR COM CERTIFICADO DIGITAL" e clique nele
    autenticar_btn = driver.find_element(By.ID, "btnCallLogin")
    autenticar_btn.click()

    # Opcional: Aguarde mais alguns segundos para visualizar o resultado
    time.sleep(5)

finally:
    # Feche o navegador
    driver.quit()
