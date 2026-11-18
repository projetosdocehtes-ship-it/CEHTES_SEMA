import os

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def extrair_texto_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto

def perguntar_para_pdf(texto_pdf, pergunta):
    prompt = f"""O texto a seguir foi extraído de um PDF técnico:

    {texto_pdf[:3000]}

    Agora responda à pergunta: {pergunta}"""

    response = client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
