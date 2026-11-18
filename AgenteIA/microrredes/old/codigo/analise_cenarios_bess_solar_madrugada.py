"""
Analise comparativa de dois cenarios de operacao do BESS (PV 325 kWp):
1) Solar com exportacao: carrega com PV e exporta excedente.
2) Madrugada com exportacao: exporta excedente PV e carrega na madrugada.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from caso_ifg import CasoIFG
from tarifas_aneel import TarifasANEEL


def _calcular_custo_rede(caso, energia_rede_kw, tarifa, is_ponta):
    if energia_rede_kw > 0:
        return energia_rede_kw * tarifa

    fator_compensacao = 0.90
    scee = caso.tarifas_aneel.dados_tarifa.get('scee', {})
    scee_modalidade = scee.get(caso.modalidade.lower(), {})

    if scee_modalidade:
        if is_ponta:
            tarifa_base = scee_modalidade.get('te_ponta', 0) + scee_modalidade.get('tusd_ponta', 0)
        else:
            tarifa_base = scee_modalidade.get('te_fora_ponta', 0) + scee_modalidade.get('tusd_fora_ponta', 0)
        tarifa_venda = (tarifa_base if tarifa_base > 0 else tarifa) * fator_compensacao
    else:
        tarifa_venda = tarifa * fator_compensacao

    return energia_rede_kw * tarifa_venda


def _simular_dia_custom(caso, dia_semana, estrategia, madrugada_inicio=0, madrugada_fim=6):
    horas = np.arange(24)

    soc_bess = caso.bess_capacidade_kwh * 0.1
    soc_min = caso.bess_capacidade_kwh * 0.1
    soc_max = caso.bess_capacidade_kwh * 0.95

    resultados = {
        'hora': [],
        'demanda_kw': [],
        'geracao_pv_kw': [],
        'potencia_bess_kw': [],
        'soc_bess_kwh': [],
        'energia_rede_kw': [],
        'tarifa_kwh': [],
        'custo_hora': [],
        'is_ponta': [],
        'energia_curtail_kw': []
    }

    for hora in horas:
        demanda_kw = caso.perfil.get_demanda(hora, dia_semana)
        temperatura = 25 + 10 * np.sin((hora - 6) * np.pi / 12)
        temperatura = np.clip(temperatura, 15, 35)
        geracao_pv_kw = caso.calcular_potencia_pv(hora, temperatura)

        is_ponta = TarifasANEEL.is_horario_ponta(hora, dia_semana)
        tarifa_atual = caso.calcular_tarifa_horaria(hora, dia_semana)

        saldo = geracao_pv_kw - demanda_kw
        potencia_bess_kw = 0
        energia_rede_kw = 0
        energia_curtail_kw = 0

        periodo_preparacao_ponta = (hora >= 14 and hora <= 17)
        periodo_carregamento = (hora >= 8 and hora <= 17)
        if madrugada_inicio <= madrugada_fim:
            periodo_madrugada = (madrugada_inicio <= hora <= madrugada_fim)
        else:
            periodo_madrugada = (hora >= madrugada_inicio or hora <= madrugada_fim)

        if estrategia == 'solar_exportacao':
            if saldo > 0:
                if soc_bess < soc_max:
                    espaco_disponivel = soc_max - soc_bess
                    horas_ate_ponta = max(18 - hora, 1)
                    taxa_carregamento = espaco_disponivel / horas_ate_ponta

                    if periodo_preparacao_ponta:
                        taxa_carregamento = min(taxa_carregamento * 1.5, caso.bess_potencia_kw * 0.8)
                    else:
                        taxa_carregamento = min(taxa_carregamento, caso.bess_potencia_kw * 0.4)

                    energia_carregar = min(saldo, taxa_carregamento, espaco_disponivel)

                    if energia_carregar > 0:
                        potencia_bess_kw = -energia_carregar
                        soc_bess += energia_carregar * 0.95
                        saldo -= energia_carregar

                if saldo > 0:
                    energia_rede_kw = -saldo

            else:
                deficit = abs(saldo)

                if is_ponta:
                    energia_descarregar = min(deficit, caso.bess_potencia_kw)
                    energia_descarregar = min(energia_descarregar, (soc_bess - soc_min))

                    if energia_descarregar > 0:
                        potencia_bess_kw = energia_descarregar
                        soc_bess -= energia_descarregar / 0.95
                        deficit -= energia_descarregar

                    if deficit > 0:
                        energia_rede_kw = deficit

                elif periodo_carregamento and not is_ponta:
                    energia_rede_kw = deficit

                    espaco_disponivel = soc_max - soc_bess
                    energia_necessaria_ponta = 410

                    if (periodo_preparacao_ponta and
                        soc_bess < energia_necessaria_ponta and
                        espaco_disponivel > 20):

                        energia_alvo = energia_necessaria_ponta - soc_bess
                        energia_alvo = min(energia_alvo, espaco_disponivel)
                        horas_ate_ponta = max(18 - hora, 1)

                        taxa_carregamento = energia_alvo / horas_ate_ponta
                        taxa_carregamento = min(taxa_carregamento, caso.bess_potencia_kw * 0.6)
                        energia_carregar = min(taxa_carregamento, espaco_disponivel)

                        if energia_carregar > 0:
                            potencia_bess_kw = -energia_carregar
                            soc_bess += energia_carregar * 0.95
                            energia_rede_kw += energia_carregar

                else:
                    energia_rede_kw = deficit

        elif estrategia == 'madrugada_exportacao':
            if saldo > 0:
                energia_rede_kw = -saldo
            else:
                deficit = abs(saldo)

                if is_ponta:
                    energia_descarregar = min(deficit, caso.bess_potencia_kw)
                    energia_descarregar = min(energia_descarregar, (soc_bess - soc_min))

                    if energia_descarregar > 0:
                        potencia_bess_kw = energia_descarregar
                        soc_bess -= energia_descarregar / 0.95
                        deficit -= energia_descarregar

                    if deficit > 0:
                        energia_rede_kw = deficit

                else:
                    energia_rede_kw = deficit

                    if periodo_madrugada:
                        espaco_disponivel = soc_max - soc_bess
                        energia_necessaria_ponta = 410

                        if espaco_disponivel > 0 and soc_bess < energia_necessaria_ponta:
                            energia_alvo = energia_necessaria_ponta - soc_bess
                            energia_alvo = min(energia_alvo, espaco_disponivel)

                            if madrugada_inicio <= madrugada_fim:
                                horas_janela = max(madrugada_fim - madrugada_inicio + 1, 1)
                                horas_restantes = max(madrugada_fim - hora + 1, 1)
                            else:
                                horas_janela = max((24 - madrugada_inicio) + (madrugada_fim + 1), 1)
                                if hora >= madrugada_inicio:
                                    horas_restantes = (24 - hora) + (madrugada_fim + 1)
                                else:
                                    horas_restantes = madrugada_fim - hora + 1

                            taxa_base = energia_alvo / horas_janela
                            taxa_carregamento = max(taxa_base, energia_alvo / horas_restantes)
                            taxa_carregamento = min(taxa_carregamento, caso.bess_potencia_kw * 0.6)
                            energia_carregar = min(taxa_carregamento, espaco_disponivel)

                            if energia_carregar > 0:
                                potencia_bess_kw = -energia_carregar
                                soc_bess += energia_carregar * 0.95
                                energia_rede_kw += energia_carregar
        else:
            raise ValueError(f"Estrategia desconhecida: {estrategia}")

        custo_hora = _calcular_custo_rede(caso, energia_rede_kw, tarifa_atual, is_ponta)

        resultados['hora'].append(hora)
        resultados['demanda_kw'].append(demanda_kw)
        resultados['geracao_pv_kw'].append(geracao_pv_kw)
        resultados['potencia_bess_kw'].append(potencia_bess_kw)
        resultados['soc_bess_kwh'].append(soc_bess)
        resultados['energia_rede_kw'].append(energia_rede_kw)
        resultados['tarifa_kwh'].append(tarifa_atual)
        resultados['custo_hora'].append(custo_hora)
        resultados['is_ponta'].append(is_ponta)
        resultados['energia_curtail_kw'].append(energia_curtail_kw)

    return resultados


def simular_mes_custom(caso, estrategia, madrugada_inicio=0, madrugada_fim=6):
    dias_uteis = 22
    fins_semana = 8

    resultado_util = _simular_dia_custom(caso, 0, estrategia, madrugada_inicio, madrugada_fim)
    resultado_fds = _simular_dia_custom(caso, 6, estrategia, madrugada_inicio, madrugada_fim)

    energia_demanda_mes = (sum(resultado_util['demanda_kw']) * dias_uteis +
                           sum(resultado_fds['demanda_kw']) * fins_semana)

    energia_pv_mes = (sum(resultado_util['geracao_pv_kw']) * dias_uteis +
                      sum(resultado_fds['geracao_pv_kw']) * fins_semana)

    energia_comprada_mes = (sum([e for e in resultado_util['energia_rede_kw'] if e > 0]) * dias_uteis +
                            sum([e for e in resultado_fds['energia_rede_kw'] if e > 0]) * fins_semana)

    energia_vendida_mes = (sum([abs(e) for e in resultado_util['energia_rede_kw'] if e < 0]) * dias_uteis +
                           sum([abs(e) for e in resultado_fds['energia_rede_kw'] if e < 0]) * fins_semana)

    energia_curtail_mes = (sum(resultado_util['energia_curtail_kw']) * dias_uteis +
                           sum(resultado_fds['energia_curtail_kw']) * fins_semana)

    custo_mes = (sum(resultado_util['custo_hora']) * dias_uteis +
                 sum(resultado_fds['custo_hora']) * fins_semana)

    return {
        'energia_demanda_kwh': energia_demanda_mes,
        'energia_pv_kwh': energia_pv_mes,
        'energia_comprada_kwh': energia_comprada_mes,
        'energia_vendida_kwh': energia_vendida_mes,
        'energia_curtail_kwh': energia_curtail_mes,
        'custo_mensal': custo_mes
    }


def calcular_metricas_financeiras(custo_base_anual, custo_anual_cenario, investimento_inicial,
                                  taxa_desconto=0.10, inflacao=0.05, horizonte=10):
    economia_anual = custo_base_anual - custo_anual_cenario
    fluxos = []

    for ano in range(horizonte):
        economia_inflacionada = economia_anual * ((1 + inflacao) ** ano)
        fluxo_liquido = economia_inflacionada - (investimento_inicial if ano == 0 else 0)
        fluxos.append(fluxo_liquido)

    vpl = sum([f / ((1 + taxa_desconto) ** i) for i, f in enumerate(fluxos)])

    fluxo_acumulado = np.cumsum(fluxos)
    payback_idx = np.where(fluxo_acumulado >= 0)[0]
    payback = float(payback_idx[0]) if len(payback_idx) > 0 else None

    try:
        from scipy.optimize import newton

        def vpl_tir(r):
            return sum([f / ((1 + r) ** i) for i, f in enumerate(fluxos)])

        tir = newton(vpl_tir, 0.1)
    except Exception:
        tir = None

    return {
        'economia_anual': economia_anual,
        'economia_total_nominal': sum([economia_anual * ((1 + inflacao) ** ano) for ano in range(horizonte)]),
        'vpl': vpl,
        'payback': payback,
        'tir': tir
    }


def gerar_grafico_comparativo(df):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('COMPARACAO DE CENARIOS BESS - PV 325 kWp', fontsize=14, fontweight='bold', y=0.98)

    metricas = [
        ('custo_anual', 'Custo Anual (R$)', axes[0, 0]),
        ('energia_vendida_kwh', 'Energia Vendida (kWh/mes)', axes[0, 1]),
        ('energia_comprada_kwh', 'Energia Comprada (kWh/mes)', axes[1, 0]),
        ('energia_curtail_kwh', 'Energia Cortada (kWh/mes)', axes[1, 1])
    ]

    for coluna, titulo, ax in metricas:
        ax.bar(df['cenario'], df[coluna], color=['#1B5E20', '#283593'])
        ax.set_title(titulo, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.tick_params(axis='x', rotation=10)
        if coluna == 'custo_anual':
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))

    plt.tight_layout()
    plt.savefig('comparacao_cenarios_bess_325kwp.png', dpi=200, bbox_inches='tight')
    print("\n  ✓ Grafico salvo: comparacao_cenarios_bess_325kwp.png")


def gerar_grafico_financeiro(df):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('COMPARACAO FINANCEIRA - PV 325 kWp', fontsize=14, fontweight='bold', y=0.98)

    metricas = [
        ('vpl', 'VPL (10 anos)', axes[0, 0], True),
        ('economia_total_nominal', 'Economia Total (nominal)', axes[0, 1], True),
        ('payback', 'Payback (anos)', axes[1, 0], False),
        ('tir', 'TIR', axes[1, 1], False)
    ]

    for coluna, titulo, ax, is_moeda in metricas:
        valores = df[coluna].fillna(0).values
        ax.bar(df['cenario'], valores, color=['#00695C', '#5E35B1'])
        ax.set_title(titulo, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.tick_params(axis='x', rotation=10)
        if is_moeda:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        if coluna == 'tir':
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{y*100:.0f}%'))

    plt.tight_layout()
    plt.savefig('comparacao_cenarios_bess_325kwp_financeiro.png', dpi=200, bbox_inches='tight')
    print("  ✓ Grafico salvo: comparacao_cenarios_bess_325kwp_financeiro.png")


def gerar_grafico_fluxo_potencia(caso, estrategia, dia_semana=0, madrugada_inicio=22, madrugada_fim=4):
    resultado = _simular_dia_custom(caso, dia_semana, estrategia, madrugada_inicio, madrugada_fim)

    horas = resultado['hora']
    demanda = np.array(resultado['demanda_kw'])
    pv = np.array(resultado['geracao_pv_kw'])
    bess = np.array(resultado['potencia_bess_kw'])
    injecao = np.array([-e if e < 0 else 0 for e in resultado['energia_rede_kw']])
    compra_rede = np.array([e if e > 0 else 0 for e in resultado['energia_rede_kw']])

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.plot(horas, demanda, label='Demanda (kW)', color='#C62828', linewidth=2)
    ax.plot(horas, pv, label='Geracao PV (kW)', color='#F9A825', linewidth=2)
    ax.plot(horas, bess, label='BESS (+descarga / -carga)', color='#2E7D32', linewidth=2)
    ax.bar(horas, injecao, label='Energia injetada (kW)', color='#1565C0', alpha=0.4)
    ax.bar(horas, compra_rede, label='Energia comprada (kW)', color='#6D4C41', alpha=0.35)

    ax.set_title(f'Fluxo de Potencia - {estrategia.replace("_", " ").title()}')
    ax.set_xlabel('Hora do dia')
    ax.set_ylabel('Potencia (kW)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_xticks(range(0, 24, 2))

    plt.tight_layout()
    nome_arquivo = f"fluxo_potencia_{estrategia}.png"
    plt.savefig(nome_arquivo, dpi=200, bbox_inches='tight')
    print(f"  ✓ Grafico salvo: {nome_arquivo}")


def calcular_energia_carregamento_bess(resultado_util, resultado_fds):
    carga_util = sum([abs(p) for p in resultado_util['potencia_bess_kw'] if p < 0])
    carga_fds = sum([abs(p) for p in resultado_fds['potencia_bess_kw'] if p < 0])
    return carga_util, carga_fds


def gerar_grafico_energia_carregamento(df_sumario):
    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax.bar(df_sumario['cenario'], df_sumario['energia_carregamento_kwh_mes'],
           color=['#2E7D32', '#1565C0'])
    ax.set_title('Energia Total para Carregamento do BESS (kWh/mes)')
    ax.set_xlabel('Cenario')
    ax.set_ylabel('Energia (kWh/mes)')
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(axis='x', rotation=10)
    plt.tight_layout()
    plt.savefig('energia_carregamento_bess.png', dpi=200, bbox_inches='tight')
    print("  ✓ Grafico salvo: energia_carregamento_bess.png")


def gerar_grafico_energia_rede(df_sumario):
    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax.bar(df_sumario['cenario'], df_sumario['energia_rede_kwh_mes'],
           color=['#7B1FA2', '#EF6C00'])
    ax.set_title('Energia Requerida da Rede (kWh/mes)')
    ax.set_xlabel('Cenario')
    ax.set_ylabel('Energia (kWh/mes)')
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(axis='x', rotation=10)
    plt.tight_layout()
    plt.savefig('energia_rede_cenarios.png', dpi=200, bbox_inches='tight')
    print("  ✓ Grafico salvo: energia_rede_cenarios.png")


def executar_cenarios():
    caso = CasoIFG(distribuidora='EQUATORIAL GO', modalidade='verde')
    caso.bess_capacidade_kwh = 300
    caso.bess_potencia_kw = 230
    caso.pv_potencia_kwp = 325
    caso._configurar_pv()

    print(f"\nBESS configurado para este cenario: {caso.bess_capacidade_kwh} kWh / {caso.bess_potencia_kw} kW")

    investimento_bess = caso.bess_capacidade_kwh *  310*1000.0/138 # R$ 1.900

    resultados = []

    # Cenário base sem BESS (permite exportacao)
    bess_cap_original = caso.bess_capacidade_kwh
    bess_pot_original = caso.bess_potencia_kw
    caso.bess_capacidade_kwh = 0
    caso.bess_potencia_kw = 0
    res_base = simular_mes_custom(caso, 'madrugada_exportacao', madrugada_inicio=0, madrugada_fim=6)
    custo_base_anual = res_base['custo_mensal'] * 12
    caso.bess_capacidade_kwh = bess_cap_original
    caso.bess_potencia_kw = bess_pot_original

    res_solar_export = simular_mes_custom(caso, 'solar_exportacao')
    custo_solar_anual = res_solar_export['custo_mensal'] * 12
    met_solar = calcular_metricas_financeiras(
        custo_base_anual,
        custo_solar_anual,
        investimento_bess
    )
    resultados.append({
        'cenario': 'Solar com exportacao',
        **res_solar_export,
        'custo_anual': custo_solar_anual,
        **met_solar
    })

    res_madrugada = simular_mes_custom(caso, 'madrugada_exportacao', madrugada_inicio=22, madrugada_fim=4)
    custo_madrugada_anual = res_madrugada['custo_mensal'] * 12
    met_madrugada = calcular_metricas_financeiras(
        custo_base_anual,
        custo_madrugada_anual,
        investimento_bess
    )
    resultados.append({
        'cenario': 'Madrugada com exportacao',
        **res_madrugada,
        'custo_anual': custo_madrugada_anual,
        **met_madrugada
    })

    df = pd.DataFrame(resultados)
    df.to_csv('comparacao_cenarios_bess_325kwp.csv', index=False, encoding='utf-8-sig')
    print("\n  ✓ Comparativo salvo: comparacao_cenarios_bess_325kwp.csv")

    gerar_grafico_comparativo(df)
    gerar_grafico_financeiro(df)

    # Energia total de carregamento do BESS (mes)
    resumo_carregamento = []

    resultado_util_solar = _simular_dia_custom(caso, 0, 'solar_exportacao', 22, 4)
    resultado_fds_solar = _simular_dia_custom(caso, 6, 'solar_exportacao', 22, 4)
    carga_util, carga_fds = calcular_energia_carregamento_bess(resultado_util_solar, resultado_fds_solar)
    energia_mes = carga_util * 22 + carga_fds * 8
    resumo_carregamento.append({'cenario': 'Solar com exportacao', 'energia_carregamento_kwh_mes': energia_mes})

    resultado_util_mad = _simular_dia_custom(caso, 0, 'madrugada_exportacao', 22, 4)
    resultado_fds_mad = _simular_dia_custom(caso, 6, 'madrugada_exportacao', 22, 4)
    carga_util, carga_fds = calcular_energia_carregamento_bess(resultado_util_mad, resultado_fds_mad)
    energia_mes = carga_util * 22 + carga_fds * 8
    resumo_carregamento.append({'cenario': 'Madrugada com exportacao', 'energia_carregamento_kwh_mes': energia_mes})

    df_carregamento = pd.DataFrame(resumo_carregamento)
    df_carregamento.to_csv('energia_carregamento_bess.csv', index=False, encoding='utf-8-sig')
    print("  ✓ Dados salvos: energia_carregamento_bess.csv")
    gerar_grafico_energia_carregamento(df_carregamento)

    df_rede = df[['cenario', 'energia_comprada_kwh']].copy()
    df_rede.rename(columns={'energia_comprada_kwh': 'energia_rede_kwh_mes'}, inplace=True)
    df_rede.to_csv('energia_rede_cenarios.csv', index=False, encoding='utf-8-sig')
    print("  ✓ Dados salvos: energia_rede_cenarios.csv")
    gerar_grafico_energia_rede(df_rede)

    gerar_grafico_fluxo_potencia(caso, 'solar_exportacao')
    gerar_grafico_fluxo_potencia(caso, 'madrugada_exportacao', madrugada_inicio=22, madrugada_fim=4)

    print("\nResumo:")
    print(df[[
        'cenario',
        'custo_anual',
        'economia_anual',
        'vpl',
        'payback',
        'tir',
        'energia_comprada_kwh',
        'energia_vendida_kwh',
        'energia_curtail_kwh'
    ]])


if __name__ == '__main__':
    executar_cenarios()
