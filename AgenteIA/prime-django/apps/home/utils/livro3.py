# import logging
# import os
# import re
# import shutil

# from docx import Document

# from apps.home.helpers import (
#     formatar_variavel,
#     retonar_nome_e_extensao,
#     verificar_item_vazio,
# )

# # Configurar logging
# from apps.home.utils.ajustar_negrito_italico import Gerar_Negrito, criar_dicionario
# from apps.home.utils.finalizar_texto_word import gerar_Negrito

# logger = logging.getLogger(__name__)

# listVariaveis, listValor, listFormato = [], [], []
# listPalavrasDestacar = [verificar_item_vazio("", "0"), "  "]
# listPalavrasDestacarObrigatorio = [verificar_item_vazio("", "1")]

# arqOrigem, arqCredor = "", "Credor.docx"

# # Diretorio aplicacao
# path_dir = os.path.split(os.path.abspath(__file__))[0]


# # Atualizando a Minuta usada
# def set_Minuta_Escolhida(nome) -> None:
#     global arqOrigem

#     arqOrigem = nome


# # Limpar todos os dados das variaveis
# def limpar_listVariaveis() -> None:
#     global listVariaveis, listValor, listFormato

#     listVariaveis, listValor, listFormato = [], [], []


# # Criando as variaveis a serem atualizadas
# def atualizar_listVariaveis(variavel, valor, formato) -> None:
#     global listVariaveis, listValor, listFormato

#     # print(variavel, valor)

#     listVariaveis.append(variavel)
#     listValor.append(valor)
#     listFormato.append(formato)


# # Pegando o texto do arquivo
# def get_Texto(arquivo):
#     input = Document(arquivo)

#     paragraphs = ""
#     for para in input.paragraphs:
#         p = para.text
#         paragraphs = paragraphs + p

#     return paragraphs


# # Pegando os dados do PROPRIETARIO
# def getProprietario():
#     input = Document(arqCredor)

#     paragraphs = []
#     for para in input.paragraphs:
#         p = para.text
#         paragraphs.append(p)

#     return paragraphs[0]


# def replace_string(filename, dir_atual):
#     import PySimpleGUI as sg

#     global listVariaveis, listValor, listFormato

#     doc = Document(filename)
#     # print("Modelo Escolhido:", filename)
#     # print("Dir Atual:", dir_atual)

#     # Alterar os dados que estao no TEXTO
#     for p in doc.paragraphs:
#         for variavel, valor, mascara in zip(listVariaveis, listValor, listFormato, strict=False):
#             # print("Processando no texto:", variavel, valor, mascara, p)

#             try:
#                 # print("VARIAVEL ALTERAR: variavel ", variavel, " valor ", valor, " maskara ", str(mascara))

#                 Atualizar_variavel(variavel, valor, str(mascara), p)
#             except Exception:
#                 logger.exception("ERRO")
#                 print("Erro", variavel, valor, mascara)

#     arqNovo = dir_atual + "/" + retonar_nome_e_extensao(arqOrigem)[1] + "_Alterado.docx"
#     # print("Modelo salvo como:", dir_atual + "/" + arqNovo)
#     # print("Modelo salvo como:", arqNovo)

#     try:
#         doc.save(arqNovo)
#     except Exception:
#         logger.exception("ERRO")
#         temp = "Arquivo não pode ser salvo:" + str(arqNovo) + "Verificar se o arquivo não esta aberto."
#         sg.popup_error(temp)

#     return arqNovo


# # Retirar o INICIO e FIM das variaves temporarias
# def replace_string_arquivo_final(filename, listVariaveis, listValor, listFormato) -> None:
#     # print("")
#     # print("Alteracao final no arquivo:", filename)
#     # print("lista: ", listVariaveis)

#     # lista_atualizada = []
#     doc = Document(filename)

#     # Alterar os dados que estao no TEXTO
#     for p in doc.paragraphs:
#         # print("  ")
#         # print("Checando: ", doc.paragraphs)

#         for variavel, valor, mascara in zip(listVariaveis, listValor, listFormato, strict=False):
#             try:
#                 # if variavel not in set(lista_atualizada):
#                 # print("VARIAVEL ALTERAR: variavel ", variavel, " valor ", valor, " maskara ", str(mascara), " p = ", p)
#                 Atualizar_variavel(variavel, valor, str(mascara), p)
#                 # lista_atualizada.append(variavel)
#             except Exception:
#                 logger.exception("ERRO")

#     # print("  ")
#     # print("Salvo como:", filename)

#     try:
#         doc.save(filename)
#     except Exception:
#         logger.exception("ERRO")


# # Verificar as variaveis e trocar os valroes
# def Atualizar_variavel(nome_variavel, valor_variavel, mascara, p) -> None:
#     # print("Variavel que vai trocar:", nome_variavel)
#     if nome_variavel in p.text:
#         inline = p.runs

#         # Loop added to work with runs (strings with same style)
#         for i in range(len(inline)):
#             if nome_variavel in inline[i].text:
#                 # Formatar variavel
#                 if mascara is not None:
#                     valor_variavel = formatar_variavel(valor_variavel, str(mascara))

#                 text = inline[i].text.replace(nome_variavel, valor_variavel)
#                 inline[i].text = text


# # Processar alteracoes lista
# def processar_lista_finalizar_arquivo(arqWord, listaModelo, opcao) -> None:
#     # print("lista de NEGRITO, ITALICO, SUBLINHADO, MINUSCULA")

#     list_atual = listaModelo.copy()
#     # ftw.Iniciar_Aplicativo()

#     # Escolher se e lista de NEGRITO, ITALICO, SUBLINHADO
#     for _ in listaModelo:
#         # print("Opcao:", str(opcao), "Lista de modelo:", listaModelo)

#         if opcao == 1:
#             gerar_Negrito(arqWord, list_atual, [], [], [], [])
#         elif opcao == 2:
#             gerar_Negrito(arqWord, [], list_atual, [], [], [])
#         elif opcao == 3:
#             gerar_Negrito(arqWord, [], [], list_atual, [], [])
#         elif opcao == 4:
#             gerar_Negrito(arqWord, [], [], [], list_atual, [])
#         elif opcao == 5:
#             gerar_Negrito(arqWord, [], [], [], [], list_atual)

#         # print(" ")
#         # print("Item da lista:", list_atual)

#         list_atual.pop(0)
#     # ftw.Fechar_Aplicativo()


# # Verificar se existe dentro arquivo
# def Selecionar_Variaveis(inicio, fim, arquivo):
#     # print("")
#     # print("Inicio - Selecionar variaveis:", inicio)

#     # Procurando no modelo a variavel
#     txt = get_Texto(arquivo)
#     lista = []

#     # Retirando o ponto inserido para gerar NEGRITO
#     txt = txt.replace("{{ r ", "{{ ")

#     # Pesquisando na variavel
#     Modelo = re.split(inicio, txt)

#     # print("MODELO", txt)
#     # print("MODELO")
#     # print(txt)

#     # Percorrendo todo o texto
#     for item in Modelo:
#         if re.split(fim, item) and fim in item:
#             # print("NEGRITAR", re.split(fim, item)[0])
#             lista.append(str(inicio) + str(re.split(fim, item)[0]) + str(fim))
#             # temp = str(str(inicio) + str(re.split(fim, item)[0]) + str(fim))
#             # temp = str(temp).replace("", "_")
#             # lista.append(temp)

#     # print("Fim - Selecionar variaveis:", inicio)
#     # print(lista)
#     # print("")

#     # Se encontrar uma variavel retornar True - Para solicitar do usuario
#     return lista


# # Gerando as finalizacoes (NEGRITO, ITALICO, SUBLINHANDO)
# def finalizar_Arquivo_doc(arqWord) -> None:
#     global listPalavrasDestacar, listPalavrasDestacarObrigatorio

#     # print("")
#     # print("Inicio - Modelo Final", arqWord)

#     # lista palavras para Negrito
#     # listPalavrasNegrito     = Selecionar_Variaveis("<w:N>", "</w:N>", arqWord)
#     listPalavrasNegrito = Selecionar_Variaveis("{{ ", " }}", arqWord)

#     # lista palavras para Italico
#     # listPalavrasItalico     = Selecionar_Variaveis("<w:I>", "</w:I>", arqWord)

#     # lista palavras para SUBLINHAR
#     # listPalavrasSublinhado  = Selecionar_Variaveis("<w:S>", "</w:S>", arqWord)
#     # print("Fim - Modelo Final", arqWord)
#     # print("")

#     # Processo a ser feito para atualizar a lista = NEGRITO
#     if len(listPalavrasNegrito) > 0:
#         # print("Inicio = Verificar Negrito")
#         # processar_lista_finalizar_arquivo(arqWord, listPalavrasNegrito, 1)
#         # print("Fim = Verificar Negrito")
#         # for item in listPalavrasNegrito:
#         # print(item)
#         # print(arqWord)
#         # print('Lista em NEGRITO', listPalavrasNegrito)
#         myDict = criar_dicionario(listPalavrasNegrito, "N")
#         Gerar_Negrito(arqWord, arqWord, myDict)
#         # print(myDict)

#     # Processo a ser feito para atualizar a lista = ITALICO
#     # if len(listPalavrasItalico) > 0:
#     #     print("Verificar Italico")
#     # processar_lista_finalizar_arquivo(arqWord, listPalavrasItalico, 2)

#     # Processo a ser feito para atualizar a lista = SUBLINHADO
#     # if len(listPalavrasSublinhado) > 0:
#     #     print("Verificar Sublinhado")
#     #     processar_lista_finalizar_arquivo(arqWord, listPalavrasSublinhado, 3)

#     # Processo a ser feito para atualizar a lista = DESTACADO
#     # if len(listPalavrasDestacar) > 0:
#     #     print("Verificar Destacar")
#     # processar_lista_finalizar_arquivo(arqWord, listPalavrasDestacar, 4)

#     # Processo a ser feito para atualizar a lista = DESTACADO OBRIGATORIO
#     # if len(listPalavrasDestacarObrigatorio) > 0:
#     #     print("Verificar Destacar Obrigatorio")
#     # processar_lista_finalizar_arquivo(arqWord, listPalavrasDestacarObrigatorio, 5)

#     # TODOs ao mesmo tempo
#     # processar_lista_finalizar_arquivo_todos(arqWord, listPalavrasNegrito, 0, listPalavrasItalico, listPalavrasSublinhado, listPalavrasDestacar, listPalavrasDestacarObrigatorio)

#     # Retirar o INICIO e FIM das Variaves
#     # listVariaveis = ["<w:N>", "</w:N>", "<w:I>", "</w:I>", "<w:S>", "</w:S>"]
#     # listValor     = ["", "", "", "", "", "", "", ""]
#     # listFormato   = ["", "", "", "", "", "", "", ""]

#     # Salvar novo sem INI e FIM
#     # print("Inicio = replace")
#     # replace_string_arquivo_final(arqWord, listVariaveis, listValor, listFormato)
#     # print("Fim = replace")


# # Gerando o ato no EDITOR
# def get_Gerar_Ato(dirOrigem) -> None:
#     global arqOrigem

#     # Gerar mudancas e abrir arquivo NOVO
#     if dirOrigem != "":
#         # Arquivo FINAL novo pela minuta escolhida
#         # print('Novo', dirOrigem + arqOrigem, path_dir)
#         Arq_temp = replace_string(dirOrigem + arqOrigem, path_dir)

#         # Finalizar o arquivo com melhorias
#         finalizar_Arquivo_doc(Arq_temp)

#         # Copiar e Apagar Arquivo da pasta
#         Arq_Destino = path_dir + "/Alterados/" + retonar_nome_e_extensao(Arq_temp)[0]
#         # print("Copiando Arquivo:", Arq_Destino)
#         shutil.copyfile(Arq_temp, Arq_Destino)
#         os.remove(Arq_temp)

#         # Abrir o arquivo pelo sistema
#         os.system(Arq_Destino)


# # Processar alteracoes lista
# def processar_lista_finalizar_arquivo_todos(
#     arqWord,
#     listaModelo1,
#     opcao,
#     listaModelo2,
#     listaModelo3,
#     listaModelo4,
#     listaModelo5,
# ) -> None:
#     # print("Todos - lista de NEGRITO, ITALICO, SUBLINHADO, MINUSCULA")
#     gerar_Negrito(arqWord, listaModelo1, listaModelo2, listaModelo3, listaModelo4, listaModelo5)
