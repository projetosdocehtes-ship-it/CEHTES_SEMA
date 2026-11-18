import os

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv
from openai import OpenAI

""" CONVERSAS COM CHATGPT
https://chatgpt.com/c/67f528f9-58a8-800e-90a5-69f42426c556
https://chatgpt.com/c/67f53335-8480-800e-b81f-7cd7abb58f32

"""

"""
1. Usar ferramentas prontas (sem codar):
Essas plataformas permitem enviar um PDF e conversar com ele diretamente:
ChatPDF (https://www.chatpdf.com)
Humata (https://www.humata.ai)
AskYourPDF (https://www.askyourpdf.com)
PDF.ai (https://www.pdf.ai)
"""

load_dotenv()  # Carrega variáveis do .env

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
caminho_pdf = "C:\\AgenteIA\\ManualCadian\\Installation_Manual_of_Standard_Solar_Modules_en.pdf"

def perguntar_para_pdf(texto_pdf, pergunta):
    prompt = f"O texto a seguir é um conteúdo de um PDF:\n\n{texto_pdf[:3000]}...\n\nAgora responda à pergunta: {pergunta}"

    response = client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def extrair_texto_pdf(caminho_pdf):
    doc = fitz.open(caminho_pdf)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto

def perguntar_ia(pergunta):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "Você é um especialista em energia solar fotovoltaica.",
            },
            {"role": "user", "content": pergunta},
        ],
    )
    return print("IA:", response.choices[0].message.content)

def pesquisar_inmetro(modelo):
    url = f"https://servicos.inmetro.gov.br/internet/consumidor/produtos_compulsorios.asp?q={modelo}"
    response = requests.get(url)
    if response.status_code == 200:
        return f"Resultados do INMETRO para '{modelo}':\n{url}"
    else:
        return "Erro ao buscar no INMETRO."

def main():
    print("Agente IA de Equipamentos Fotovoltaicos ☀️🔌")

    while True:
        entrada = input("\nVocê: ")
        if entrada.lower() in ['sair', 'exit', 'quit']:
            break

        if entrada.startswith("pesquisar "):
            termo = entrada.replace("pesquisar ", "")
            print(pesquisar_inmetro(termo))
        else:
            resposta = perguntar_ia(entrada)
            print("IA:", resposta)

def main_pdf():
    print("PDF - Agente IA de Equipamentos Fotovoltaicos ☀️🔌")

    while True:
        entrada = input("\nVocê: ")
        if entrada.lower() in ['sair', 'exit', 'quit']:
            break

        texto_pdf = extrair_texto_pdf(caminho_pdf)

        resposta = perguntar_para_pdf(texto_pdf=texto_pdf, pergunta=entrada)

        print("IA PDF:", resposta)

if __name__ == "__main__":
    main()
    #main_pdf()
