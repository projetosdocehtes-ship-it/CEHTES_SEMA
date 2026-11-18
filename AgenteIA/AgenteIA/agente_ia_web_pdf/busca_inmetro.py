import requests

def pesquisar_inmetro(termo):
    url = f"https://servicos.inmetro.gov.br/internet/consumidor/produtos_compulsorios.asp?q={termo}"
    response = requests.get(url)
    if response.status_code == 200:
        return f"Resultados disponíveis no site do INMETRO para '{termo}':\n{url}"
    else:
        return "Erro ao acessar o site do INMETRO."