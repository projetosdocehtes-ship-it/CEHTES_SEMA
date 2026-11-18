from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def perguntar_ia(pergunta):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um especialista em energia solar fotovoltaica."},
            {"role": "user", "content": pergunta}
        ]
    )
    return response.choices[0].message.content