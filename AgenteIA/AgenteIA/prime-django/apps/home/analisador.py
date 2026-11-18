# apps/relatorios/services/analisador.py

import math
import pandas as pd
from datetime import datetime
from django.db import connection
from decimal import Decimal

DEFAULT_GASTO_KWH = 500
AREA_POR_PAINEL = 2
PRECO_KW = 1800


def parse_float(val):
    try:
        return float(str(val).replace(",", "."))
    except:
        return 0.0

def horas_sol(inicio, fim):
    try:
        h1 = int(inicio.split(":")[0])
        h2 = int(fim.split(":")[0])
        return max(1, h2 - h1)
    except:
        return 5

def gerar_relatorio_projetos():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, nome_projeto, area_disponível_instalacao, horario_inicio_sol_pleno, horario_fim_sol_pleno
            FROM home_projeto
            WHERE fotovoltaico = TRUE AND area_disponível_instalacao IS NOT NULL
        """)
        projetos = dictfetchall(cursor)

        cursor.execute("""
            SELECT id, modelo, pontencial_nominal, eficiencia
            FROM home_painelsolar
            WHERE is_active = TRUE
        """)
        paineis = dictfetchall(cursor)

    resultados = []

    for projeto in projetos:
        area_m2 = parse_float(projeto["area_disponível_instalacao"])
        horas = horas_sol(str(projeto["horario_inicio_sol_pleno"]), str(projeto["horario_fim_sol_pleno"]))
        max_paineis = int(area_m2 // AREA_POR_PAINEL)

        for painel in paineis:
            potencia = parse_float(painel["pontencial_nominal"])
            eficiencia = parse_float(painel["eficiencia"]) or 18
            if potencia <= 0:
                continue

            potencia_kw = potencia / 1000
            producao = potencia_kw * horas * 30 * (eficiencia / 100)
            if producao == 0:
                continue

            qtde = math.ceil(DEFAULT_GASTO_KWH / producao)
            if qtde > max_paineis:
                continue

            custo_unit = potencia_kw * PRECO_KW
            custo_total = custo_unit * qtde
            producao_total = producao * qtde * 12 * 25
            custo_por_kwh = custo_total / producao_total

            resultados.append({
                "Projeto": projeto["nome_projeto"],
                "Painel": painel["modelo"],
                "Potência (W)": potencia,
                "Eficiência (%)": eficiencia,
                "Qtd Painéis": qtde,
                "Produção Mensal (kWh)": round(producao * qtde, 2),
                "Custo Total (R$)": round(custo_total, 2),
                "Custo por kWh (R$)": round(custo_por_kwh, 4),
            })

    return pd.DataFrame(resultados)

def dictfetchall(cursor):
    "Converte resultado em lista de dicionários"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
