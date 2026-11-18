# from mailmerge import MailMerge

# # Iniciar um arquivo global
# document = []


# # Leio o arquivo origem da minuta
# def ler_minuta_origem(documento_minuta):
#     # Ler a minuta que sera usada como modelo
#     return MailMerge(documento_minuta)


# # Imprimir todas as variavies da minuta
# def imprimir_variaveis_minuta() -> None:
#     global document

#     # Imprimir todos os campos que podem ser alterados
#     print(document.get_merge_fields())


# # Processar as substituicoes - LV3
# def get_protocolo(
#     data_protocolo="",
#     nome_titulo="",
#     nome_solicitante="",
#     data_prevista="",
#     numero_protocolo="",
#     data_atual_extenso="",
#     valor_pagar="",
#     document=None,
# ) -> None:
#     # global document

#     if document is None:
#         document = []
#     document.merge(
#         DATA_PROTOCOLO=data_protocolo,
#         NUMERO_PROTOCOLO=numero_protocolo,
#         NOME_TITULO=nome_titulo,
#         NOME_APRESENTANTE=nome_solicitante,
#         DATA_PREVISTA=data_prevista,
#         DATA_ATUAL_EXTENSO=data_atual_extenso,
#         VALOR_PAGAR=valor_pagar,
#     )


# # Leio o arquivo origem da minuta
# def salvar_documento_alterado(document, novo_documento_minuta) -> None:
#     # global document

#     # Salvar o arquivo
#     document.write(novo_documento_minuta)
