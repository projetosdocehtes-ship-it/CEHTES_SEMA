# modelos_texto/utils.py

from django.template import Context, Template


def renderizar_modelo_texto(conteudo: str, contexto: str) -> str:
    template = Template(conteudo)
    contexto = Context(contexto)
    return template.render(contexto)
