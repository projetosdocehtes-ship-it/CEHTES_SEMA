import inspect
import os


class Style:
    SUCCESS = "\033[92m"  # Verde
    WARNING = "\033[93m"  # Amarelo
    ERROR = "\033[91m"  # Vermelho
    INFO = "\033[94m"  # Azul
    END = "\033[0m"  # Resetar a cor


def print_success(*messages):
    # Obter a stack frame atual
    frame = inspect.currentframe()
    # Obter a stack frame anterior (a função que chamou print_error)
    caller_frame = frame.f_back
    # Obter informações sobre a linha onde a função foi chamada
    caller_line = caller_frame.f_lineno
    # Obter informações sobre o arquivo onde a função foi chamada
    caller_filepath = caller_frame.f_globals["__file__"]
    # Extrair apenas o nome do arquivo
    caller_filename = os.path.basename(caller_filepath)

    for message in messages:
        print(f"{Style.SUCCESS}SUCCESS: {message}{Style.END} ({caller_filename}:{caller_line})")


def print_warning(*messages):
    # Obter a stack frame atual
    frame = inspect.currentframe()
    # Obter a stack frame anterior (a função que chamou print_error)
    caller_frame = frame.f_back
    # Obter informações sobre a linha onde a função foi chamada
    caller_line = caller_frame.f_lineno
    # Obter informações sobre o arquivo onde a função foi chamada
    caller_filepath = caller_frame.f_globals["__file__"]
    # Extrair apenas o nome do arquivo
    caller_filename = os.path.basename(caller_filepath)

    for message in messages:
        print(f"\n{Style.ERROR}WARNING: {message}\nLOCAL: {caller_filepath}, Linha: {caller_line}){Style.END}\n")


def print_error(*messages):
    # Obter a stack frame atual
    frame = inspect.currentframe()
    # Obter a stack frame anterior (a função que chamou print_error)
    caller_frame = frame.f_back
    # Obter informações sobre a linha onde a função foi chamada
    caller_line = caller_frame.f_lineno
    # Obter informações sobre o arquivo onde a função foi chamada
    caller_filename = caller_frame.f_globals["__file__"]

    for message in messages:
        print(f"\n{Style.ERROR}ERROR: {message}\nLOCAL: {caller_filename}, Linha: {caller_line}){Style.END}\n")


def print_info(*messages):
    # Obter a stack frame atual
    frame = inspect.currentframe()
    # Obter a stack frame anterior (a função que chamou print_error)
    caller_frame = frame.f_back
    # Obter informações sobre a linha onde a função foi chamada
    caller_line = caller_frame.f_lineno
    # Obter informações sobre o arquivo onde a função foi chamada
    caller_filepath = caller_frame.f_globals["__file__"]
    # Extrair apenas o nome do arquivo
    caller_filename = os.path.basename(caller_filepath)

    for message in messages:
        print(f"{Style.INFO}[INFO]: {message}{Style.END} ({caller_filename}:{caller_line})")
