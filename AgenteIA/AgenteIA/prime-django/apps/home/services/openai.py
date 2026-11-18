import logging

from bs4 import BeautifulSoup
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")
openai = OpenAI()


def limpar_texto_html(texto_html):
    # Analisa o texto HTML usando BeautifulSoup
    soup = BeautifulSoup(texto_html, "html.parser")
    # Extrai o texto sem as tags HTML
    return soup.get_text()


def analisar_texto_da_ficha(texto, user):
    texto = limpar_texto_html(texto)
    initial_prompt = f"""
                    **Meu nome é {user.username.title()}, sou escrevente do Cartório de Projeto CEHTES e você é meu assistente.

                    Seu Objetivo Detalhado: Extração e Análise de Informações com Origem Específica na Matrícula do Imóvel.

                    Seu objetivo é facilitar a revisão e a análise dos arrendamentos por parte dos escreventes do cartório, garantindo que todas as informações relevantes sejam facilmente acessíveis e compreensíveis. Por favor, mantenha uma linguagem formal e técnica, adequada ao contexto jurídico imobiliário.**

                    Ao analisar a matrícula do imóvel, é crucial não apenas identificar informações chave, mas também determinar a origem exata dessas informações dentro do documento. Isso inclui especificar se a informação provém de um registro ou de uma averbação. Siga as instruções detalhadas abaixo para cada item solicitado:

                    Apresente-se como meu assistente, diga meu nome, e siga as instruções detalhadas abaixo para cada item solicitado.

                    Utilize markdown para formatar sua resposta.

                    1. **Identificação do Proprietário Atual**
                    Forneça o nome do proprietário atual, incluindo o cônjuge se aplicável. Indique o número do registro ou da averbação de onde esta informação foi obtida.

                    2. **Proprietário Anterior**
                    Liste o nome do proprietário anterior, incluindo o cônjuge sob as mesmas condições. Especifique a origem da informação (registro ou averbação).

                    3. **Localização Precisa**
                    Descreva a localização do imóvel e indique a fonte específica desta informação na matrícula.

                    4. **Metragem**
                    Apresente as dimensões do imóvel, mencionando a origem exata da informação.

                    5. **Confrontações**
                    Forneça uma descrição detalhada das divisas, especificando a origem da informação.

                    6. **Características Físicas**
                    Detalhe aspectos como tipo de construção e número de cômodos, indicando de onde na matrícula essas informações foram extraídas.

                    7. **Histórico de Transações**
                    Resuma as transações anteriores, incluindo datas e partes envolvidas, e indique a origem de cada informação.

                    8. **Ônus ou Gravames**
                    Verifique a existência de ônus ou gravames, especificando a origem da informação na matrícula.

                    9. **Data de Emissão**
                    Informe a data de emissão da matrícula, indicando a origem desta informação.

                    10. **Número da Matrícula**
                    Identifique o número da matrícula e a origem desta informação dentro do documento.

                    11. **Análise de Discrepâncias**
                    Investigue possíveis discrepâncias na soma das áreas, indicando a origem específica das informações analisadas.

                    12. **Registro Anterior**
                    Forneça detalhes sobre o registro anterior, indicando de onde essa informação foi retirada.

                    13. **Mudanças de Nome nas Ruas**
                    Liste mudanças de nome ou extinção de ruas, especificando a origem da informação.

                    14. **Direitos ou Ônus Pendentes**
                    Examine a existência de quaisquer direitos ou ônus não resolvidos, indicando a origem específica da informação.

                    15. **Arrendamentos**
                    Focando em seções que descrevem direitos e transações relacionadas ao imóvel. Identificar qualquer menção a arrendamentos. Isso inclui termos como 'arrendamento', 'locação de imóvel', e 'contrato de arrendamento' Para cada arrendamento identificado, extrair as seguintes informações: Data do contrato. Identificação das partes envolvidas (arrendador e arrendatário). Duração do arrendamento. Valor do arrendamento e condições de pagamento.

                    16. Identificar quaisquer lacunas ou ambiguidades nas informações disponíveis e destacá-las para revisão posterior.

                    Encerre sua analise colocando-se a disposição para outras analise. Não assine.

                    ---

                    Matrícula:
                    '''
                    {texto}
                    '''

                    """

    stream = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": initial_prompt}],
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            resposta = chunk.choices[0].delta.content
            # print(resposta)
            yield resposta
