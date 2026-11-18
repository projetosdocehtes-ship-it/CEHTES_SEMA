import os
import sys

# Adiciona caminho para importar sim.py
sys.path.append(os.path.join(os.path.dirname(__file__), "02.Version_Agent"))

import streamlit as st
from agente_ia import perguntar_ia
from busca_inmetro import pesquisar_inmetro
from pdf_handler import extrair_texto_pdf, perguntar_para_pdf
from sim import executar_simulacao  # Importar função adaptada
import psycopg2
from psycopg2.extras import RealDictCursor
import re
import urllib.parse

def extrair_nome_equipamento(texto):
    # tentativa simples: primeira linha ou nome com números
    linhas = texto.split("\n")
    for linha in linhas:
        if re.search(r"\d", linha):  # Ex: "Inversor XW5000" ou "Growatt 5KW"
            return linha.strip()
    return linhas[0].strip() if linhas else "Equipamento solar"

def salvar_sugestao(pergunta, resposta):
    try:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            dbname="cehtes",
            user="postgres",
            password="CONFIGURAR_LOCALMENTE"
        )
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO home_sugestaoequipamento (pergunta, resposta, criado_em)
            VALUES (%s, %s, NOW());
            """,
            (pergunta, resposta),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao salvar sugestão no banco: {e}")


@st.cache_data
def buscar_valor():
    try:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            dbname="cehtes",
            user="postgres",
            password="CONFIGURAR_LOCALMENTE"
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM public.home_dadossimulacao LIMIT 1;")
        resultado = cur.fetchone()

        cur.close()
        conn.close()

        return resultado if resultado else {}
    except Exception as e:
        st.error(f"Erro ao buscar dados no banco de dados: {e}")
        return {}
            
st.set_page_config(page_title="CEHTES - Agente Solar IA", layout="wide")

st.markdown(
    """
    <style>
      /* 1) Variáveis de tema para manter tudo claro */
      :root {
        --primaryBackgroundColor: #FFFFFF;
        --secondaryBackgroundColor: #FFFFFF;
        --tertiaryBackgroundColor: #FFFFFF;
        --textColor: #000000;
        --font: 16px sans-serif;
      }

      /* 2) Fundo geral branco */
      [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
      }

      /* 3) Texto geral preto */
      [data-testid="stAppViewContainer"] * {
        color: #000000 !important;
      }

      /* 4) Força labels de formulário em preto */
      label {
        color: #000000 !important;
      }

      /* 5) Se quiser ser ainda mais específico (Streamlit wrapping), inclua também: */
      .stRadio label,
      .stTextInput label,
      .stNumberInput label,
      .stFileUploader label,
      .stSelectbox label {
        color: #000000 !important;
      }

      /* 6) Texto dos botões em branco, incluindo todos os filhos */
      .stButton button,
      .stButton button * {
        color: #FFFFFF !important;
      }

      /* 7) Fundo de todos os <input type="number"> em branco */
      input[type="number"] {
      background-color: #FFFFFF !important;
      }

      /* 8) Fundo dos text_input em branco e texto preto */
      .stTextInput input,
      [data-testid="stTextInput"] input,
      input[type="text"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
      }

      /* 9) Fundo e texto do file_uploader em branco/preto via BaseWeb */
        [data-baseweb="file-uploader"] {
        background-color: #FFFFFF !important;   /* fundo branco */
        border-color: #CCCCCC !important;       /* opcional: borda cinza clara */
        }

        /* garante que todo texto e ícones dentro fiquem escuros */
        [data-baseweb="file-uploader"] * {
        color: #FFFFFF !important;
        }

        /* ajusta o botão interno de seleção de arquivo, se existir */
        [data-baseweb="file-uploader"] button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        }

      /* 10) Fundo e texto do selectbox em branco/preto via BaseWeb */
        [data-baseweb="select"] {
        background-color: #FFFFFF !important;  /* fundo branco */
        color: #000000 !important;             /* texto preto */
        }

        /* Para o elemento <select> interno */
        [data-baseweb="select"] select {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        }

        /* Para as opções que aparecem no dropdown */
        [data-baseweb="select"] li[role="option"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        }

        /* Fallback genérico para o wrapper Streamlit */
        .stSelectbox > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        }

     /* 11) Fundo branco para os botões + e – do number_input */
        .stNumberInput button,
        .stNumberInput button *,
        [data-baseweb="number-input"] button,
        [data-baseweb="number-input"] button * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-color: #CCCCCC !important;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


st.title("🔆 CEHTES - Agente Microgrid")

modo = st.radio(
    "Escolha o modo de operação:",
    ["Conversar com IA", "Conversar com PDF", "Simular Sistema Fotovoltaico"],
    index=2,
)

if modo == "Conversar com IA":
    entrada = st.text_input(
        "Pergunte algo sobre energia solar ou digite 'pesquisar <termo>'", ""
    )
    if st.button("Enviar") and entrada:
        with st.spinner("Processando..."):
            if entrada.lower().startswith("pesquisar "):
                termo = entrada.replace("pesquisar ", "")
                resultado = pesquisar_inmetro(termo)
                st.markdown("### 🔍 Resultado da Pesquisa:")
                st.write(resultado)
            else:
                resposta = perguntar_ia(entrada)
                st.markdown("### 🤖 Resposta da IA:")
                st.write(resposta)

elif modo == "Conversar com PDF":
    uploaded_file = st.file_uploader(
        "Faça upload de um manual técnico (PDF)", type="pdf"
    )
    pergunta_pdf = st.text_input("Pergunte algo com base no PDF:")

    if uploaded_file and pergunta_pdf and st.button("Perguntar ao PDF"):
        with st.spinner("Extraindo texto do PDF..."):
            texto_pdf = extrair_texto_pdf(uploaded_file)
        with st.spinner("Consultando a IA..."):
            resposta = perguntar_para_pdf(texto_pdf, pergunta_pdf)
        st.markdown("### 📄 Resposta baseada no PDF:")
        st.write(resposta)

elif modo == "Simular Sistema Fotovoltaico":
    #### NOVO ITEM
    st.subheader("⚙️ Configurações do Painel Fotovoltaico")
    #pmp = st.number_input("Potência Máxima (Pmp) [W]", value=178.65)
    #isc = st.number_input("Corrente de Curto-Circuito (Isc) [A]", value=8.07)
    #voc = st.number_input("Tensão de Circuito Aberto (Voc) [V]", value=29.35)
    
    # BUSCANDO OS VALORES CADASTRADO NO BANCO DE DADOS
    valor_inicial = buscar_valor()
       
    col1, col2, col3 = st.columns(3)
    with col1: pmp = st.number_input("Potência Máxima (Pmp) [W]", value=valor_inicial["pmp"])
    with col2: isc = st.number_input("Corrente de Curto-Circuito (Isc) [A]", value=8.07)
    with col3: voc = st.number_input("Tensão de Circuito Aberto (Voc) [V]", value=29.35)
    
    col4, col5, col6 = st.columns(3)
    with col4: imp = st.number_input("Corrente de Máxima Potência (Imp) [A]", value=7.57)
    with col5: vmp = st.number_input("Tensão de Máxima Potência (Vmp) [V]", value=23.60)
    with col6: uisc = st.number_input(
        "Coeficiente de Temperatura Corrente (Uisc) [A/°C]", value=0.00222
    )
    
    col7, col8, col9 = st.columns(3)
    with col7: uvoc = st.number_input(
        "Coeficiente de Temperatura Tensão (Uvoc) [V/°C]", value=-0.107
    )
    with col8: upmp = st.number_input(
        "Coeficiente de Temperatura Potência (Upmp) [%/°C]", value=-0.49
    )
    with col9: material_painel = st.selectbox("Material do Painel", ["Silicio", "HIT"])
        
    #### NOVO ITEM
    eficiencia_painel = st.number_input("Eficiência do Painel [%]", value=15)
    st.subheader("⚙️ Configurações do Inversor e Sistema")
    
    col1, col2, col3 = st.columns(3)
    with col1: nm_paineis = st.number_input("Número de Painéis", value=18)
    with col2: nm_mppt = st.number_input("Número de MPPTs", value=2)
    with col3: in_pmax = st.number_input("Potência Máxima Entrada [kW]", value=12.3)
    
    col4, col5, col6 = st.columns(3)
    with col4: imax_mppt = st.number_input("Corrente Máxima MPPT [A]", value=18)
    with col5: in_vnom = st.number_input("Tensão Nominal Entrada [V]", value=420)
    with col6: in_vmin = st.number_input("Tensão Mínima Entrada [V]", value=80)
    
    col7, col8, col9 = st.columns(3)
    with col7: in_vmax = st.number_input("Tensão Máxima Entrada [V]", value=1000)
    with col8: in_mpp_vmin = st.number_input("MPPT Tensão Mínima [V]", value=240)
    with col9: in_mpp_vmax = st.number_input("MPPT Tensão Máxima [V]", value=800)
    
    col10, col11, col12 = st.columns(3)
    with col10: out_pmax = st.number_input("Potência Máxima Saída [kW]", value=8.2)
    with col11: out_imax = st.number_input("Corrente Máxima Saída [A]", value=34.2)
    with col12: out_vnom = st.number_input("Tensão Nominal Saída [V]", value=220)
    
    col13, col14, col15 = st.columns(3)
    with col13: out_freq = st.number_input("Frequência de Saída [Hz]", value=60)
    with col14: eficiencia_inv = st.number_input("Eficiência do Inversor [%]", value=0.98)
    with col15: max_thd = st.number_input("Máximo THD [%]", value=5)
    
    fator_potencia = st.number_input("Fator de Potência", value=0.85)

    # st.markdown('<div class="botao-simulacao">', unsafe_allow_html=True)
    # executar = st.button("Executar Simulação")
    # st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <style>
            /* Força cor preta para texto e todos os elementos internos do botão */
            div[data-testid="stButton"] button,
            div[data-testid="stButton"] button * {
                color: black !important;
            }

            /* Também força cor de fundo branca */
            div[data-testid="stButton"] button {
                background-color: white !important;
                border: 1px solid #999 !important;
                border-radius: 5px !important;
                padding: 0.5rem 1rem !important;
                font-weight: bold !important;
            }

            /* Efeito hover */
            div[data-testid="stButton"] button:hover {
                background-color: #f0f0f0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

       
    col_sim, col_sugestao, col_sugestao_inversor = st.columns([1, 1, 1])
    #col1_btn, col2_btn, col3_btn = st.columns([1, 1, 1])
    
    with col_sim:
        executar = st.button("Executar Simulação")

    with col_sugestao:
        sugerir = st.button("Sugerir Equipamento Painel Fotovoltaico")
        
    with col_sugestao_inversor:
        sugerir_inversor = st.button("Sugerir Equipamento Inversor")    
    
    #if st.button("Executar Simulação"):
    if executar:
        with st.spinner("Executando simulação..."):
            executar_simulacao(
                pmp,
                isc,
                voc,
                imp,
                vmp,
                uisc,
                uvoc,
                upmp,
                material_painel,
                eficiencia_painel,
                nm_paineis,
                nm_mppt,
                in_pmax,
                imax_mppt,
                in_vnom,
                in_vmin,
                in_vmax,
                in_mpp_vmin,
                in_mpp_vmax,
                out_pmax,
                out_imax,
                out_vnom,
                out_freq,
                eficiencia_inv,
                max_thd,
                fator_potencia,
            )

    if sugerir:
        pergunta = (
            f"Com base nos seguintes parâmetros do painel solar:\n"
            f"- Pmp: {pmp} W\n"
            f"- Isc: {isc} A\n"
            f"- Voc: {voc} V\n"
            f"- Imp: {imp} A\n"
            f"- Vmp: {vmp} V\n"
            f"- Uisc: {uisc} A/°C\n"
            f"- Uvoc: {uvoc} V/°C\n"
            f"- Upmp: {upmp} %/°C\n"
            f"- Material: {material_painel}\n"
            f"Qual o equipamento mais adequado e eficiente no mercado?"
        )

        with st.spinner("Consultando a IA para sugerir equipamento..."):
            resposta = perguntar_ia(pergunta)      
    
            # salvar no banco
            salvar_sugestao(pergunta, resposta)

            # link para compra
            nome_produto = extrair_nome_equipamento(resposta)
            nome_codificado = urllib.parse.quote_plus(nome_produto)

            st.markdown("### 🛒 Buscar equipamento sugerido:")
            st.markdown(f"- [🔍 Buscar no Mercado Livre](https://lista.mercadolivre.com.br/{nome_codificado})")
            st.markdown(f"- [🔍 Buscar no Google Shopping](https://www.google.com/search?tbm=shop&q={nome_codificado})")


        st.markdown("### 🔧 Sugestão de Equipamento:")
        st.write(resposta)
        
    if sugerir_inversor:
        pergunta_inv = (
            f"Com base nos seguintes parâmetros do sistema solar:\n"
            f"- Nº de Painéis: {nm_paineis}\n"
            f"- Nº de MPPTs: {nm_mppt}\n"
            f"- Potência Máxima Entrada: {in_pmax} kW\n"
            f"- Corrente Máxima MPPT: {imax_mppt} A\n"
            f"- Tensão Nominal Entrada: {in_vnom} V\n"
            f"- Tensão Mínima Entrada: {in_vmin} V\n"
            f"- Tensão Máxima Entrada: {in_vmax} V\n"
            f"- Faixa MPPT: {in_mpp_vmin} V a {in_mpp_vmax} V\n"
            f"- Potência Máxima Saída: {out_pmax} kW\n"
            f"- Corrente Máxima Saída: {out_imax} A\n"
            f"- Tensão Nominal Saída: {out_vnom} V\n"
            f"- Frequência de Saída: {out_freq} Hz\n"
            f"- Eficiência do Inversor: {eficiencia_inv * 100:.1f}%\n"
            f"- Fator de Potência: {fator_potencia}\n"
            f"- Máximo THD: {max_thd}%\n"
            f"Qual o modelo de inversor mais adequado e eficiente disponível no mercado?"
        )
    
        with st.spinner("Consultando a IA para sugerir inversor..."):
            resposta_inv = perguntar_ia(pergunta_inv)

        st.markdown("### 🔧 Sugestão de Inversor:")
        st.write(resposta_inv)

        # salvar no banco
        salvar_sugestao(pergunta_inv, resposta_inv)

        # gerar links de compra
        nome_inv = extrair_nome_equipamento(resposta_inv)
        nome_inv_url = urllib.parse.quote_plus(nome_inv)

        st.markdown("### 🛒 Buscar inversor sugerido:")
        st.markdown(f"- [🔍 Buscar no Mercado Livre](https://lista.mercadolivre.com.br/{nome_inv_url})")
        st.markdown(f"- [🔍 Buscar no Google Shopping](https://www.google.com/search?tbm=shop&q={nome_inv_url})")
        
    # # CSS para alterar a cor do texto do botão para preto
    # st.markdown("""
    #     <style>
    #         .botao-simulacao button {
    #             color: black !important;
    #         }
    #     </style>
    # """, unsafe_allow_html=True)

    # if st.button("Executar Simulação"):
    #     with st.spinner("Executando simulação..."):
    #         executar_simulacao(
    #             pmp,
    #             isc,
    #             voc,
    #             imp,
    #             vmp,
    #             uisc,
    #             uvoc,
    #             upmp,
    #             material_painel,
    #             eficiencia_painel,
    #             nm_paineis,
    #             nm_mppt,
    #             in_pmax,
    #             imax_mppt,
    #             in_vnom,
    #             in_vmin,
    #             in_vmax,
    #             in_mpp_vmin,
    #             in_mpp_vmax,
    #             out_pmax,
    #             out_imax,
    #             out_vnom,
    #             out_freq,
    #             eficiencia_inv,
    #             max_thd,
    #             fator_potencia,
    #         )


  