import base64

from django.template import Context, Template


def adicionar_head_elements(
    html: str,
    charset="UTF-8",
    inline_style: str = "",
    inline_script: str = "",
) -> str:
    # Cria a tag meta para especificar o charset
    meta_charset = f'<meta charset="{charset}">'
    # Adiciona CSS inline se fornecido
    style_tag = f"<style>{inline_style}</style>" if inline_style else ""
    # Adiciona JavaScript inline se fornecido
    script_tag = f"<script>{inline_script}</script>" if inline_script else ""
    # Compõe o conteúdo do <head>
    head_content = meta_charset + style_tag + script_tag

    if "<head>" in html:
        html = html.replace("<head>", "<head>" + head_content)
    else:
        html = "<html><head>" + head_content + "</head><body>" + html + "</body></html>"

    return html


def adicionar_head_elements_django(
    body: str,
    charset="UTF-8",
    styles: list | None = None,
    scripts: list | None = None,
) -> str:
    # Define a estrutura básica do template
    template_str = """
        {% load static %}
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="{{ charset }}">
            {% for style in styles %}
            <link rel="stylesheet" type="text/css" href="{% static style %}">
            {% endfor %}
            {{ head_extra }}
        </head>
        <body>
            <div class="ck-content">
                {{ body|safe }}
            </div>
            {% for script in scripts %}
            <script src="{{ script }}"></script>
            {% endfor %}
        </body>
        </html>
        """

    # Cria um template a partir da string
    template = Template(template_str)

    # Contexto que será passado para o template
    context = Context(
        {
            "charset": charset,
            "styles": styles or [],
            "scripts": scripts or [],
            "body": body,
            "head_extra": "",  # Espaço reservado para conteúdo extra no <head> se necessário
        },
    )

    # Renderiza o template com o contexto
    saida = template.render(context)
    print(saida)

    return saida


def get_image_base64(image_path):
    """Converte uma imagem em um arquivo para uma string base64."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode("utf-8")


# Usando em seu HTML
def generate_html_with_base64_image() -> str:
    image_base64 = get_image_base64("/caminho/para/sua/imagem.jpg")
    return f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <link rel="stylesheet" type="text/css" href="{{% static 'assets/css/ckeditor5/content-styles.css' %}}">
            <script src="https://cdn.ckeditor.com/ckeditor5/41.3.0/classic/ckeditor.js"></script>
        </head>
        <body>
            <p>Conteúdo da página</p>
            <img src="data:image/jpeg;base64,{image_base64}">
            <p>Mais conteúdo...</p>
        </body>
    </html>
    """
