import glob
import re

# Ajuste a expressão regular para cobrir os novos casos
regex = r"if\s+str\((\w+(\.\w+)?)\)\.upper\(\)\s+==\s+\"NONE\":"
substituicao = r"if \1 is None:"


def substituir_codigo_em_arquivo(caminho_arquivo):
    with open(caminho_arquivo, "r+", encoding="utf-8") as arquivo:
        conteudo = arquivo.read()
        conteudo_modificado = re.sub(regex, substituicao, conteudo)
        # Volta ao início do arquivo para sobrescrever
        arquivo.seek(0)
        arquivo.write(conteudo_modificado)
        arquivo.truncate()  # Remova o que estiver após o novo fim, se o arquivo encurtar


def percorrer_diretorios_e_substituir(diretorio_base):
    # Percorre todos os arquivos .py no diretório base e subdiretórios
    for caminho_arquivo in glob.glob(diretorio_base + "/**/*.py", recursive=True):
        substituir_codigo_em_arquivo(caminho_arquivo)


# Substitua '/caminho/para/seu/projeto' pelo caminho real do seu projeto
caminho_do_projeto = "C:/Users/paulo/OneDrive/Dev/prime-RI/apps/home"

# Substitua 'seu_diretorio_base_aqui' pelo caminho do diretório base dos seus arquivos .py
percorrer_diretorios_e_substituir(caminho_do_projeto)
