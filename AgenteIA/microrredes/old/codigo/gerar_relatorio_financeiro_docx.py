"""
Gera relatório financeiro em DOCX com:
1) Resumo financeiro (tabela)
2) Tabela comparativa de investimentos por cenário de BESS
   com normalização usando BESS 500 kWh como referência
   e normalização para indicadores econômicos.
"""

from datetime import datetime
import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

ARQUIVO_CSV = "analise_sensibilidade_bess_pv_resultados.csv"
ARQUIVO_SAIDA = "RELATORIO_FINANCEIRO_BESS.docx"
PV_REFERENCIA = 400
BESS_REFERENCIA = 500


def format_currency(value):
    if pd.isna(value):
        return "-"
    return f"R$ {value:,.2f}"


def format_number(value, dec=1):
    if pd.isna(value):
        return "-"
    return f"{value:.{dec}f}"


def format_percent(value, dec=1):
    if pd.isna(value):
        return "-"
    return f"{value:.{dec}f}%"


def main():
    df = pd.read_csv(ARQUIVO_CSV)
    df_cenarios = df[df["tipo"] == "Cenário"].copy()

    # ===== TABELA 1: RESUMO FINANCEIRO =====
    df_cenarios = df_cenarios.sort_values("payback_anos")
    melhor = df_cenarios.iloc[0]
    pior = df_cenarios.iloc[-1]

    # Mediano por payback
    med_idx = len(df_cenarios) // 2
    medio = df_cenarios.iloc[med_idx]

    resumo = pd.DataFrame([
        {
            "Cenário": "Melhor (menor payback)",
            "PV (kWp)": melhor["pv_kwp"],
            "BESS (kWh)": melhor["bess_kwh"],
            "Investimento Total": melhor["investimento_total"],
            "Economia Total Anual": melhor["economia_total_anual"],
            "Payback (anos)": melhor["payback_anos"],
            "VPL 10 anos": melhor.get("vpl_10anos", None),
            "TIR": melhor.get("tir", None),
        },
        {
            "Cenário": "Médio (mediano)",
            "PV (kWp)": medio["pv_kwp"],
            "BESS (kWh)": medio["bess_kwh"],
            "Investimento Total": medio["investimento_total"],
            "Economia Total Anual": medio["economia_total_anual"],
            "Payback (anos)": medio["payback_anos"],
            "VPL 10 anos": medio.get("vpl_10anos", None),
            "TIR": medio.get("tir", None),
        },
        {
            "Cenário": "Pior (maior payback)",
            "PV (kWp)": pior["pv_kwp"],
            "BESS (kWh)": pior["bess_kwh"],
            "Investimento Total": pior["investimento_total"],
            "Economia Total Anual": pior["economia_total_anual"],
            "Payback (anos)": pior["payback_anos"],
            "VPL 10 anos": pior.get("vpl_10anos", None),
            "TIR": pior.get("tir", None),
        },
    ])

    # ===== TABELA 2: COMPARATIVA POR BESS (PV fixo) =====
    df_bess = df_cenarios[df_cenarios["pv_kwp"] == PV_REFERENCIA].copy()
    interpolado = False

    if df_bess.empty:
        # Interpolar para PV não existente (ex.: 418 kWp)
        interpolado = True
        pv_values = sorted(df_cenarios["pv_kwp"].unique())
        pv_inf = max([pv for pv in pv_values if pv < PV_REFERENCIA], default=None)
        pv_sup = min([pv for pv in pv_values if pv > PV_REFERENCIA], default=None)

        if pv_inf is None or pv_sup is None:
            raise ValueError(
                f"Não é possível interpolar PV {PV_REFERENCIA} kWp. Valores disponíveis: {pv_values}."
            )

        df_inf = df_cenarios[df_cenarios["pv_kwp"] == pv_inf].copy()
        df_sup = df_cenarios[df_cenarios["pv_kwp"] == pv_sup].copy()

        # Garantir que ambos têm os mesmos BESS
        bess_values = sorted(set(df_inf["bess_kwh"]).intersection(set(df_sup["bess_kwh"])))
        df_inf = df_inf[df_inf["bess_kwh"].isin(bess_values)]
        df_sup = df_sup[df_sup["bess_kwh"].isin(bess_values)]

        # Fator de interpolação
        fator = (PV_REFERENCIA - pv_inf) / (pv_sup - pv_inf)

        # Interpolar colunas numéricas relevantes
        cols_interp = [
            "investimento_total",
            "economia_total_anual",
            "payback_anos",
            "vpl_10anos",
            "tir",
        ]

        df_bess = pd.DataFrame({"bess_kwh": bess_values})
        df_bess["pv_kwp"] = PV_REFERENCIA

        for col in cols_interp:
            inf_vals = df_inf.set_index("bess_kwh")[col]
            sup_vals = df_sup.set_index("bess_kwh")[col]
            df_bess[col] = inf_vals + (sup_vals - inf_vals) * fator

        # Completar colunas usadas no relatório
        df_bess["tipo"] = "Cenário"
        df_bess["descricao"] = f"Interpolado PV {PV_REFERENCIA} kWp"
    else:
        df_bess = df_bess.sort_values("bess_kwh")

    # Referência BESS 500 kWh
    ref_row = df_bess[df_bess["bess_kwh"] == BESS_REFERENCIA]
    if ref_row.empty:
        raise ValueError(
            f"Não encontrado cenário de referência BESS {BESS_REFERENCIA} kWh para PV {PV_REFERENCIA} kWp."
        )

    ref_row = ref_row.iloc[0]

    def norm(value, ref):
        if pd.isna(value) or pd.isna(ref) or ref == 0:
            return None
        return value / ref

    df_bess["investimento_norm"] = df_bess["investimento_total"].apply(lambda v: norm(v, ref_row["investimento_total"]))
    df_bess["economia_norm"] = df_bess["economia_total_anual"].apply(lambda v: norm(v, ref_row["economia_total_anual"]))
    df_bess["payback_norm"] = df_bess["payback_anos"].apply(lambda v: norm(v, ref_row["payback_anos"]))
    df_bess["vpl_norm"] = df_bess["vpl_10anos"].apply(lambda v: norm(v, ref_row["vpl_10anos"]))
    df_bess["tir_norm"] = df_bess["tir"].apply(lambda v: norm(v, ref_row["tir"]))

    # ===== GERAR DOCX =====
    doc = Document()

    # Título
    title = doc.add_paragraph("Relatório Financeiro - BESS")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(16)

    subtitle_text = f"Gerado em: {datetime.now().strftime('%d/%m/%Y')} | Referência: PV {PV_REFERENCIA} kWp, BESS {BESS_REFERENCIA} kWh"
    if interpolado:
        subtitle_text += " | PV interpolado"
    subtitle = doc.add_paragraph(subtitle_text)
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.size = Pt(10)

    doc.add_paragraph("\n1) Resumo Financeiro (Melhor, Médio e Pior Payback)")

    # Tabela resumo financeiro
    cols_resumo = ["Cenário", "PV (kWp)", "BESS (kWh)", "Investimento Total", "Economia Total Anual", "Payback (anos)", "VPL 10 anos", "TIR"]
    table = doc.add_table(rows=1, cols=len(cols_resumo))
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(cols_resumo):
        hdr_cells[i].text = col

    for _, row in resumo.iterrows():
        cells = table.add_row().cells
        cells[0].text = str(row["Cenário"])
        cells[1].text = format_number(row["PV (kWp)"], 0)
        cells[2].text = format_number(row["BESS (kWh)"], 0)
        cells[3].text = format_currency(row["Investimento Total"])
        cells[4].text = format_currency(row["Economia Total Anual"])
        cells[5].text = format_number(row["Payback (anos)"], 1)
        cells[6].text = format_currency(row["VPL 10 anos"])
        tir_val = row["TIR"]
        cells[7].text = format_percent(tir_val * 100 if pd.notna(tir_val) else None, 1)

    doc.add_paragraph("\n2) Comparativo por BESS (PV fixo em 324 kWp)")
    doc.add_paragraph("Normalização: valores divididos pelo cenário de referência BESS 500 kWh.")

    # Tabela comparativa BESS
    cols_bess = [
        "BESS (kWh)",
        "Investimento Total",
        "Investimento (norm)",
        "Economia Total Anual",
        "Economia (norm)",
        "Payback (anos)",
        "Payback (norm)",
        "VPL 10 anos",
        "VPL (norm)",
        "TIR",
        "TIR (norm)",
    ]

    table2 = doc.add_table(rows=1, cols=len(cols_bess))
    hdr_cells2 = table2.rows[0].cells
    for i, col in enumerate(cols_bess):
        hdr_cells2[i].text = col

    for _, row in df_bess.iterrows():
        cells = table2.add_row().cells
        cells[0].text = format_number(row["bess_kwh"], 0)
        cells[1].text = format_currency(row["investimento_total"])
        cells[2].text = format_number(row["investimento_norm"], 3)
        cells[3].text = format_currency(row["economia_total_anual"])
        cells[4].text = format_number(row["economia_norm"], 3)
        cells[5].text = format_number(row["payback_anos"], 1)
        cells[6].text = format_number(row["payback_norm"], 3)
        cells[7].text = format_currency(row["vpl_10anos"])
        cells[8].text = format_number(row["vpl_norm"], 3)
        tir_val = row["tir"]
        cells[9].text = format_percent(tir_val * 100 if pd.notna(tir_val) else None, 1)
        cells[10].text = format_number(row["tir_norm"], 3)

    # ===== TEXTO EXPLICATIVO (2 PÁGINAS) =====
    doc.add_page_break()
    doc.add_paragraph("3) Explicação dos gráficos – Página 1")

    p1 = (
        "Os gráficos de comparação entre BESS incremental e compra única mostram trajetórias diferentes de risco e retorno. "
        "No gráfico de evolução da capacidade, a estratégia incremental cresce em degraus anuais, enquanto a compra única "
        "alcança a capacidade total desde o primeiro ano. Isso impacta diretamente o gráfico de investimentos anuais: "
        "na compra única há um desembolso concentrado no ano 0, enquanto na estratégia incremental o investimento é distribuído "
        "ao longo dos anos."
    )
    doc.add_paragraph(p1)

    p2 = (
        "A curva de economia anual com inflação evidencia que, no modelo incremental, o ganho cresce de forma mais lenta no início, "
        "pois a capacidade do BESS ainda é reduzida. Já na compra única, a economia anual é maior desde o início, refletindo a "
        "capacidade total instalada. Nos gráficos de fluxo de caixa líquido, isso se traduz em um período inicial mais negativo "
        "para compra única (por causa do investimento concentrado), porém com recuperação mais rápida dos fluxos positivos."
    )
    doc.add_paragraph(p2)

    p3 = (
        "O fluxo de caixa acumulado reforça essa leitura: a compra única tende a cruzar o zero mais cedo, enquanto o incremental "
        "tem uma recuperação mais gradual. Já o gráfico de valor presente dos fluxos demonstra o efeito da taxa de desconto: "
        "fluxos mais cedo valem mais. Por isso, estratégias que antecipam economias têm vantagem no valor presente, mesmo com "
        "maior desembolso inicial."
    )
    doc.add_paragraph(p3)

    doc.add_page_break()
    doc.add_paragraph("4) Explicação dos gráficos – Página 2")

    p4 = (
        "Na análise detalhada por cenário (ex.: payback médio), observa-se a interação entre geração PV, demanda e despacho do BESS. "
        "O gráfico de geração vs demanda evidencia o excesso diurno de PV e o déficit noturno. O BESS absorve parte do excesso "
        "durante o dia e devolve na ponta, reduzindo a necessidade de compra em horário caro. O gráfico de fluxo de rede confirma "
        "isso ao mostrar exportação durante o dia e importação reduzida na ponta."
    )
    doc.add_paragraph(p4)

    p5 = (
        "Os mapas de calor e curvas comparativas (payback, VPL, economia anual) mostram tendência consistente: conforme o BESS cresce, "
        "a economia anual aumenta, mas o payback não melhora proporcionalmente. Existe um ponto de equilíbrio onde o ganho marginal "
        "de economia passa a crescer menos que o investimento. Por isso, a seleção ponderada (investimento peso 2 e payback peso 1) "
        "privilegia capacidades intermediárias, evitando superdimensionamento."
    )
    doc.add_paragraph(p5)

    p6 = (
        "Conclusões: (1) compra única maximiza economias antecipadas e melhora VPL, mas exige maior capital inicial; "
        "(2) incremental reduz risco financeiro, porém alonga o payback; (3) cenários com BESS muito pequeno geram pouca economia; "
        "(4) o dimensionamento ótimo depende do objetivo: minimizar payback, reduzir investimento ou balancear ambos. "
        "Neste relatório, o foco foi o equilíbrio entre investimento e retorno, mantendo PV fixo em 400 kWp e normalizando indicadores "
        "com referência em 500 kWh."
    )
    doc.add_paragraph(p6)

    doc.save(ARQUIVO_SAIDA)
    print(f"Arquivo gerado: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
