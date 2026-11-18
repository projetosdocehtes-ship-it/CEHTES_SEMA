# # https://pypi.org/project/docxcompose/

# # Importing the required packages
# import os

# from docx import Document as Document_compose
# from docxcompose.composer import Composer


# def combine_all_docx(filename_master, files_list, diretorio_modelo, nome_salvar_arquivo):
#     # Constrói o caminho completo para o diretório do modelo
#     modelo_dir = os.path.join(diretorio_modelo, "Modelo")

#     # Constrói o caminho completo para o arquivo master
#     master_path = os.path.join(modelo_dir, filename_master)

#     # Inicializa o documento mestre e o compositor
#     master_doc = Document_compose(master_path)
#     composer = Composer(master_doc)

#     # Imprime uma mensagem inicial com a lista de arquivos a serem combinados
#     logger.info(f"Combinando os seguintes arquivos: {files_list}")

#     # Itera sobre a lista de arquivos, combinando-os ao documento mestre
#     for file in files_list:
#         file_path = os.path.join(modelo_dir, file)  # Constrói o caminho completo para cada arquivo
#         doc_temp = Document_compose(file_path)
#         composer.append(doc_temp)
#         logger.info(f"Unificado {file}")

#     # Define o caminho completo para salvar o arquivo final
#     final_path = os.path.join(diretorio_modelo, nome_salvar_arquivo)

#     # Salva o documento unificado
#     composer.save(final_path)
#     logger.info(f"Unificado FINAL {nome_salvar_arquivo}")

#     return final_path


# def unificar_arquivos(filename_master, filename_second_docx, arquivo_saida) -> None:
#     # filename_master is name of the file you want to merge the docx file into

#     # pedido_item_id = 0

#     # print("Passo 12 - Nota de devolucao para: pedido_item_id")

#     master = Document_compose(filename_master)

#     # print("Passo 13 - Nota de devolucao para: pedido_item_id")

#     composer = Composer(master)

#     # print("Passo 14 - Nota de devolucao para: pedido_item_id")

#     # filename_second_docx is the name of the second docx file
#     doc2 = Document_compose(filename_second_docx)

#     # print("Passo 15 - Nota de devolucao para: pedido_item_id")

#     # append the doc2 into the master using composer.append function
#     composer.append(doc2)

#     # print("Passo 16 - Nota de devolucao para: pedido_item_id")

#     # Save the combined docx with a name
#     composer.save(arquivo_saida)
#     # print('SAIDA', arquivo_saida)
