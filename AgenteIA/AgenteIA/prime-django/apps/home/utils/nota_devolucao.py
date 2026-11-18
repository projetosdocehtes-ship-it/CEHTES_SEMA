import os
import subprocess

from apps.home.helpers import apenas_numeros
from apps.home.models import NotaDevolucaoTexto

# from apps.home.utils.converter_html_docx import converter_docx_para_html_e_voltar

# from apps.home.utils.mala_direta_nota_devolucao import Get_Protocolo, Salvar_Documento_Alterado, ler_minuta_origem

# from tomlkit import document


# GRAVAR HTML NO BANCO DE DADOS
def gravar_html_bd_nota_devolucao(
    pedido_item_id,
    pedidos_atual_id,
    numero_ato,
    arquivo_gerado_final_html,
) -> None:
    # Gerar apenas numero inteiro
    pedido_item_id = str(pedido_item_id).split(".")[0]
    numero_ato = int(apenas_numeros(numero_ato))

    # Leitura do arquivo HTML
    with open(arquivo_gerado_final_html, encoding="utf_8") as file:
        html_content = file.read()

    b = NotaDevolucaoTexto(
        id=pedido_item_id,
        # imovel=None,
        pedido_item_id=pedido_item_id,
        pedido_id=pedidos_atual_id,
        numero_ato=numero_ato,
        texto=html_content,
    )
    b.save()


# LIBRARY OFFICE
def criar_nota_de_devolucao_em_pdf(origem):
    # Separar o arquivo e jogar na mesma pasta
    destino_arquivo = os.path.abspath(os.path.dirname(origem))
    arquivo_com_extensao = os.path.split(os.path.abspath(origem))[1]

    # print("Hora Exportar PDF 4", Data.now())
    # Mudando para o dir do
    proc = subprocess.Popen(
        r' "C:\Program Files\LibreOffice\program\soffice.exe" -headless -convert-to pdf '
        + str(origem)
        + " --outdir "
        + destino_arquivo,
        shell=True,
    )

    # print("Hora Exportar PDF 5", Data.now())
    proc.wait()

    # print("Hora Exportar PDF 6", Data.now())
    # Formatar arquivo
    arquivo_com_extensao = str(arquivo_com_extensao).replace("docx", "pdf")
    return destino_arquivo + "/" + arquivo_com_extensao


# # Atualizar os dados da nota de devolucao
# def atualizando_nota_devolucao(
#     numero_protocolo,
#     pedido_item_atual,
#     data_protocolo,
#     data_prevista,
#     nome_solicitante,
#     nome_titulo,
#     tipo_registro,
#     numero_matricula,
#     caminho_nota_devolucao_criar,
#     valor_pagar,
#     pedido_atual,
#     numero_ato,
# ):
#     # Salvando e substituindo o temporario
#     data_atual_extenso = get_data_e_hora_por_opcao("1")

#     # Formatando numero do protocolo
#     numero_protocolo = protocolo_formatado(str(numero_protocolo).split(".")[0])

#     # Salvando e Substituindo o Temporario
#     Salvar_Documento = os.path.dirname(caminho_nota_devolucao_criar) + "/" + numero_protocolo + ".docx"

#     document = ler_minuta_origem(caminho_nota_devolucao_criar)

#     # Ler a Minuta Original
#     # document = ler_minuta_origem(caminho_nota_devolucao_criar)

#     # Formatando o titulo
#     nome_titulo = nome_titulo + " - " + tipo_registro + "." + numero_matricula

#     # Formatando a data prevista
#     data_prevista = converter_data_para_formato_de_modelo(data_prevista)

#     # Formatando a data do protocolo
#     data_protocolo = converter_data_para_formato_de_modelo(data_protocolo)

#     # valor_pagar = str(3000)

#     # Substituir Variaveis
#     Get_Protocolo(
#         data_protocolo,
#         nome_titulo,
#         nome_solicitante,
#         data_prevista,
#         numero_protocolo,
#         data_atual_extenso,
#         valor_pagar,
#         document,
#     )

#     Salvar_Documento_Alterado(document, Salvar_Documento)

#     # GRAVAR HTML NO BANCO DE DADOS
#     # Processar os ajustes de paragrafos e caracteres - Nome_Arquivo_Minuta
#     _, arquivo_gerado_final_html = converter_docx_para_html_e_voltar(caminho_nota_devolucao_criar)

#     # GRAVAR HTML NO BANCO DE DADOS
#     try:
#         gravar_html_bd_nota_devolucao(
#             pedido_item_atual,
#             pedido_atual,
#             numero_ato,
#             arquivo_gerado_final_html,
#         )

#         # criar_pedido_item_no_fb(pedido_id, funcionario_id, tipo_andamento_id): exigencia
#         from apps.home.models import Colaborador

#         criar_andamento_fb(
#             pedido_id=pedido_atual,
#             colaborador_id=Colaborador.objects.filtrar_por_default_id(),
#             tipo_andamento_id="23",
#             arquivo_docx=Salvar_Documento,
#         )

#         """
#         views.gravar_html_bd_livro02(
#             str(pedido_item_atual), str(arquivo_gerado_final_html), "1"
#         )
#         """
#     except Exception as error:
#         print(error)

#     # Formatando a Nota de Devolucao e limpando os arquivo temporarios
#     return Salvar_Documento
