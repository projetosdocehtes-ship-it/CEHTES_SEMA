# # https://stackoverflow.com/questions/34353499/find-and-replace-italics-in-word-document-with-python-win32com
# # https://win32com.goermezer.de/microsoft/ms-office/create-and-write-text-to-a-word-document.html
# # https://docs.microsoft.com/en-us/office/vba/api/word.find.execute
# # https://stackoverflow.com/questions/33267002/why-am-i-suddenly-getting-a-no-attribute-clsidtopackagemap-error-with-win32com
# # https://gist.github.com/rdapaz/63590adb94a46039ca4a10994dff9dbe#gistcomment-2918299

# import os

# word = ""


# # bug corrigido ao chamar a aplicacao
# # def dispatch(app_name: str):
# #     #from win32com import client

# #     try:
# #         app = client.gencache.EnsureDispatch(app_name)
# #     except AttributeError:
# #         # Remove cache and try again.
# #         module_list = [m.__name__ for m in sys.modules.values()]
# #         for module in module_list:
# #             if re.match(r"win32com\.gen_py\..+", module):
# #                 del sys.modules[module]
# #         shutil.rmtree(os.path.join(os.environ.get("LOCALAPPDATA"), "Temp", "gen_py"))
# #         app = client.gencache.EnsureDispatch(app_name)
# #     return app


# # Inicio abrir arquivo
# def iniciar_aplicativo() -> None:
#     # global word

#     # word = dispatch("Word.Application")
#     # word.DisplayAlerts = False
#     # word.Visible = False


# def fechar_aplicativo() -> None:
#     # global word

#     word.ActiveWindow.Close()


# # Gerar Listas das Palavras
# def gerar_negrito(
#     arquivo,
#     list_palavras_negrito,
#     list_palavras_italico,
#     list_palavras_sublinhado,
#     list_palavras_destacar,
#     list_palavras_destacar_obrigatorio,
# ) -> None:
#     global word

#     # Inicio
#     iniciar_aplicativo()

#     # Abrir o arquivo do WORD
#     print("     ")
#     print("Arquivo:", os.path.abspath(arquivo))

#     word.Documents.Open(os.path.abspath(arquivo))

#     # Lista das palavras que ficaram em NEGRITO
#     for item in list_palavras_negrito:
#         print(str(len(list_palavras_negrito)) + " - item arquivo NEGRITO:", item)
#         while word.Selection.Find.Execute(item):
#             word.Selection.Range.Font.Bold = True
#         # fechar_aplicativo()

#     # Lista das palavras que ficaram em ITALICO
#     for item in list_palavras_italico:
#         # iniciar_aplicativo()
#         # word.Documents.Open(os.path.abspath(arquivo))
#         print(str(len(list_palavras_italico)) + " - item arquivo ITALICO:", item)
#         while word.Selection.Find.Execute(item):
#             word.Selection.Range.Font.Italic = True

#     # Lista das palavras que ficaram em SUBLINHADO
#     for item in list_palavras_sublinhado:
#         print(str(len(list_palavras_sublinhado)) + " - item arquivo SUBLINHADO:", item)
#         while word.Selection.Find.Execute(item):
#             word.Selection.Range.Font.Underline = True

#     """
#     for item in list_palavras_destacar:
#         print(str(len(list_palavras_destacar)) + " - item arquivo DESTACAR:", item)
#         while word.Selection.Find.Execute(item):
#             word.Selection.Range.HighlightColorIndex = WD_COLOR_INDEX.YELLOW

#     for item in list_palavras_destacar_obrigatorio:
#         print(str(len(list_palavras_destacar_obrigatorio)) + " - item arquivo DESTACAR:", item)
#         while word.Selection.Find.Execute(item):
#             word.Selection.Range.HighlightColorIndex = WD_COLOR_INDEX.RED
#     """

#     # Fechar Word
#     fechar_aplicativo()

#     print("Fim do Word Application")


# # Funcao principal
# if __name__ == "__main__":
#     # Listas
#     # list_palavras_negrito, list_palavras_italico, list_palavras_sublinhado = ['new text'], ['text'], ['x']

#     # Funcao para gerar a lista
#     # gerar_negrito('D:/HelloWorld.docx', list_palavras_negrito, list_palavras_italico, list_palavras_sublinhado)
#     pass

# # print("Fim Finalizar Texto Word")
