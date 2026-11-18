import os
from django.conf import settings
from openai import OpenAI
import json

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# def ask_llm(user_question: str, system_instructions: str = "") -> str:
#     """
#     Retorna texto final (plain/HTML) de um modelo LLM.
#     """
#     OPENAI_MODEL = "gpt-4o"
#     OPENAI_MAX_OUTPUT_TOKENS = 800  # limite de saída
#     OPENAI_TEMPERATURE = 0.2

#     if not settings.OPENAI_API_KEY:
#         return "⚠️ OPENAI_API_KEY não configurada."

#     # Você pode usar system_instructions para “especializar” a resposta
#     # (por exemplo, orientar o modelo a responder com HTML, listas, etc.)
#     response = _client.responses.create(
#         model=OPENAI_MODEL,
#         # 'instructions' vira o "system prompt" nesse endpoint
#         instructions=system_instructions or "Você é um assistente técnico objetivo. Responda em português. Separe cada assunto em uma linha ou item de lista. Responda em HTML conciso.",
#         # input=[{"role": "user", "content": user_question}],
#         input=[{"role": "user", "content": user_question}],
#         temperature=OPENAI_TEMPERATURE,
#         max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
#     )
#     return response.output_text  # texto final “pronto para uso”

def ask_llm(user_question: str, system_instructions: str = "", data: dict | None = None) -> str:
    """
    Retorna texto final (plain/HTML) de um modelo LLM.
    Pode receber um JSON (data) como 'anexo' para análise.
    """
    OPENAI_MODEL = "gpt-4o"
    #OPENAI_MODEL = "gpt-4o-mini"   # mais rápido que o gpt-4o
    #OPENAI_MODEL = "gpt-3.5-turbo"

    OPENAI_MAX_OUTPUT_TOKENS = 800  # limite de saída
    OPENAI_TEMPERATURE = 0.2

    if not settings.OPENAI_API_KEY:
        return "⚠️ OPENAI_API_KEY não configurada."

    # Construir input da requisição
    inputs = [
        {"role": "user", "content": user_question},
    ]

    if data is not None:
        # Passa o JSON formatado como um segundo bloco (como se fosse um arquivo)
        inputs.append({
            "role": "user",
            "content": f"JSON anexado:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        })

    response = _client.responses.create(
        model=OPENAI_MODEL,
        instructions=system_instructions or (
            "Você é um assistente técnico objetivo. "
            "Responda em português. "
            "Separe cada assunto em uma linha ou item de lista. "
            "Responda em HTML conciso."
        ),
        input=inputs,
        temperature=OPENAI_TEMPERATURE,
        max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
    )

    return response.output_text  # texto final “pronto para uso”
