import requests


def baixar_url(file_url, arquivo) -> None:
    r = requests.get(file_url, stream=True)

    with open(arquivo, "wb") as pdf:
        print("Baixando o arquivo: ", file_url)
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                pdf.write(chunk)


# print("Encerrado Baixar Arquivo")
