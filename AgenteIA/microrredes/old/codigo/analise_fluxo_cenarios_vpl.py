"""
Análise de Fluxo de Potência para Cenários de VPL
Compara 3 cenários: Maior VPL, Médio VPL e Menor VPL
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from caso_ifg import CasoIFG

# Definir os 3 cenários baseados na análise de sensibilidade
cenarios = {
    'Maior VPL': {
        'pv_kwp': 600,
        'bess_kwh': 500,
        'vpl': 694876,
        'cor': '#2E7D32'  # Verde escuro
    },
    'Médio VPL': {
        'pv_kwp': 400,
        'bess_kwh': 300,
        'vpl': 410476,
        'cor': '#1976D2'  # Azul
    },
    'Menor VPL': {
        'pv_kwp': 324,
        'bess_kwh': 100,
        'vpl': None,  # Será calculado
        'cor': '#C62828'  # Vermelho
    }
}

print("\n" + "="*100)
print(" "*30 + "ANÁLISE DE FLUXO DE POTÊNCIA")
print(" "*25 + "Comparação de Cenários por VPL")
print("="*100)

resultados = {}

for nome_cenario, config in cenarios.items():
    print(f"\n{'='*100}")
    print(f"  📊 CENÁRIO: {nome_cenario}")
    print(f"{'='*100}")
    print(f"  PV: {config['pv_kwp']} kWp | BESS: {config['bess_kwh']} kWh")
    if config['vpl']:
        print(f"  VPL (10 anos): R$ {config['vpl']:,.2f}")
    print(f"{'='*100}\n")
    
    # Criar instância e modificar configuração
    caso = CasoIFG()
    
    # Ajustar configuração do sistema
    caso.pv_potencia_kwp = config['pv_kwp']
    caso.bess_capacidade_kwh = config['bess_kwh']
    
    # Reconfigurar sistema PV com nova potência
    caso._configurar_pv()
    
    # Executar simulação mensal
    resultado = caso.simular_mes()
    
    # Calcular valores anuais (12 meses)
    resultado['custo_total_anual'] = resultado['custo_mensal'] * 12
    resultado['custo_energia_anual'] = resultado['custo_mensal'] * 12  # Simplificação
    resultado['custo_demanda_anual'] = 0  # Verde não tem demanda contratada
    resultado['custo_ultrapassagem_anual'] = 0
    
    # Demandas máximas do dia útil
    resultado['demanda_maxima_ponta'] = max([resultado['resultado_dia_util']['demanda_kw'][h] 
                                              for h in range(18, 21)])  # 18-21h
    resultado['demanda_maxima_fora_ponta'] = max([resultado['resultado_dia_util']['demanda_kw'][h] 
                                                    for h in list(range(0, 18)) + list(range(21, 24))])
    
    # Armazenar resultados
    resultados[nome_cenario] = {
        'config': config,
        'resultado': resultado,
        'caso': caso
    }
    
    # Exibir resumo
    print(f"\n📈 RESUMO ENERGÉTICO - {nome_cenario}")
    print("-" * 100)
    print(f"  Custo Total Anual:           R$ {resultado['custo_total_anual']:>12,.2f}")
    print(f"  Custo Energia:               R$ {resultado['custo_energia_anual']:>12,.2f}")
    print(f"  Custo Demanda:               R$ {resultado['custo_demanda_anual']:>12,.2f}")
    print(f"  Custo Ultrapassagem:         R$ {resultado['custo_ultrapassagem_anual']:>12,.2f}")
    print(f"  Demanda Máxima (Ponta):      {resultado['demanda_maxima_ponta']:>12,.2f} kW")
    print(f"  Demanda Máxima (Fora Ponta): {resultado['demanda_maxima_fora_ponta']:>12,.2f} kW")
    print("-" * 100)

print("\n" + "="*100)
print(" "*35 + "ANÁLISE COMPARATIVA")
print("="*100)

# Criar DataFrame comparativo
df_comparacao = pd.DataFrame({
    'Cenário': list(resultados.keys()),
    'PV (kWp)': [r['config']['pv_kwp'] for r in resultados.values()],
    'BESS (kWh)': [r['config']['bess_kwh'] for r in resultados.values()],
    'Custo Total (R$/ano)': [r['resultado']['custo_total_anual'] for r in resultados.values()],
    'Custo Energia (R$/ano)': [r['resultado']['custo_energia_anual'] for r in resultados.values()],
    'Custo Demanda (R$/ano)': [r['resultado']['custo_demanda_anual'] for r in resultados.values()],
    'Demanda Ponta (kW)': [r['resultado']['demanda_maxima_ponta'] for r in resultados.values()],
    'Demanda Fora Ponta (kW)': [r['resultado']['demanda_maxima_fora_ponta'] for r in resultados.values()]
})

print("\n" + df_comparacao.to_string(index=False))
print("\n" + "="*100)

# Criar visualizações comparativas
fig = plt.figure(figsize=(20, 12))

# 1. Comparação de Custos
ax1 = plt.subplot(2, 3, 1)
largura = 0.25
x = np.arange(len(resultados))
for i, (nome, dados) in enumerate(resultados.items()):
    res = dados['resultado']
    custos = [res['custo_energia_anual'], res['custo_demanda_anual'], res['custo_ultrapassagem_anual']]
    labels = ['Energia', 'Demanda', 'Ultrapassagem']
    colors = ['#1976D2', '#388E3C', '#D32F2F']
    
    bottom = 0
    for j, (custo, label, cor) in enumerate(zip(custos, labels, colors)):
        if i == 0:  # Só adicionar label na primeira barra
            ax1.bar(i, custo, largura*3, bottom=bottom, color=cor, label=label, alpha=0.8)
        else:
            ax1.bar(i, custo, largura*3, bottom=bottom, color=cor, alpha=0.8)
        bottom += custo

ax1.set_ylabel('Custo Anual (R$)', fontsize=11, fontweight='bold')
ax1.set_title('Composição de Custos Anuais', fontsize=12, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(list(resultados.keys()), rotation=0, fontsize=10)
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))

# 2. Comparação de Demanda Máxima
ax2 = plt.subplot(2, 3, 2)
largura = 0.35
x = np.arange(len(resultados))
demandas_ponta = [dados['resultado']['demanda_maxima_ponta'] for dados in resultados.values()]
demandas_fora = [dados['resultado']['demanda_maxima_fora_ponta'] for dados in resultados.values()]

ax2.bar(x - largura/2, demandas_ponta, largura, label='Ponta', color='#D32F2F', alpha=0.8)
ax2.bar(x + largura/2, demandas_fora, largura, label='Fora Ponta', color='#1976D2', alpha=0.8)

ax2.set_ylabel('Demanda (kW)', fontsize=11, fontweight='bold')
ax2.set_title('Demanda Máxima por Período', fontsize=12, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(list(resultados.keys()), rotation=0, fontsize=10)
ax2.legend(loc='upper right', fontsize=9)
ax2.grid(True, alpha=0.3, axis='y')

# 3. Configuração dos Sistemas
ax3 = plt.subplot(2, 3, 3)
x = np.arange(len(resultados))
pvs = [dados['config']['pv_kwp'] for dados in resultados.values()]
bess = [dados['config']['bess_kwh'] for dados in resultados.values()]

ax3_twin = ax3.twinx()
bars1 = ax3.bar(x - 0.2, pvs, 0.4, label='PV (kWp)', color='#FFA000', alpha=0.8)
bars2 = ax3_twin.bar(x + 0.2, bess, 0.4, label='BESS (kWh)', color='#7B1FA2', alpha=0.8)

ax3.set_ylabel('Capacidade PV (kWp)', fontsize=11, fontweight='bold', color='#FFA000')
ax3_twin.set_ylabel('Capacidade BESS (kWh)', fontsize=11, fontweight='bold', color='#7B1FA2')
ax3.set_title('Configuração dos Sistemas', fontsize=12, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(list(resultados.keys()), rotation=0, fontsize=10)
ax3.tick_params(axis='y', labelcolor='#FFA000')
ax3_twin.tick_params(axis='y', labelcolor='#7B1FA2')
ax3.grid(True, alpha=0.3, axis='y')

# 4. Perfil de Carga Típico (Dia de Semana)
ax4 = plt.subplot(2, 3, 4)
for nome, dados in resultados.items():
    caso = dados['caso']
    perfil_dia = caso.perfil.perfil_util['demanda_kw'].values[:24]
    ax4.plot(range(24), perfil_dia, marker='o', linewidth=2, 
            label=nome, color=dados['config']['cor'], alpha=0.8)

ax4.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
ax4.set_ylabel('Demanda (kW)', fontsize=11, fontweight='bold')
ax4.set_title('Perfil de Carga - Dia de Semana', fontsize=12, fontweight='bold')
ax4.legend(loc='upper right', fontsize=9)
ax4.grid(True, alpha=0.3)
ax4.set_xlim(-0.5, 23.5)
ax4.axvspan(18, 21, alpha=0.2, color='red', label='Horário Ponta')

# 5. Custo Total Anual
ax5 = plt.subplot(2, 3, 5)
custos_totais = [dados['resultado']['custo_total_anual'] for dados in resultados.values()]
cores = [dados['config']['cor'] for dados in resultados.values()]
bars = ax5.bar(list(resultados.keys()), custos_totais, color=cores, alpha=0.8, edgecolor='black', linewidth=1.5)

# Adicionar valores nas barras
for bar, valor in zip(bars, custos_totais):
    height = bar.get_height()
    ax5.text(bar.get_x() + bar.get_width()/2., height,
            f'R$ {valor:,.0f}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

ax5.set_ylabel('Custo Total Anual (R$)', fontsize=11, fontweight='bold')
ax5.set_title('Custo Total Anual por Cenário', fontsize=12, fontweight='bold')
ax5.grid(True, alpha=0.3, axis='y')
ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))

# 6. Economia Relativa ao Pior Cenário
ax6 = plt.subplot(2, 3, 6)
custo_maximo = max(custos_totais)
economias = [(custo_maximo - custo) for custo in custos_totais]
economias_pct = [(economia / custo_maximo * 100) for economia in economias]

bars = ax6.bar(list(resultados.keys()), economias, color=cores, alpha=0.8, edgecolor='black', linewidth=1.5)

# Adicionar valores nas barras
for bar, valor, pct in zip(bars, economias, economias_pct):
    height = bar.get_height()
    ax6.text(bar.get_x() + bar.get_width()/2., height,
            f'R$ {valor:,.0f}\n({pct:.1f}%)',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

ax6.set_ylabel('Economia Anual (R$)', fontsize=11, fontweight='bold')
ax6.set_title(f'Economia vs. Cenário Base', fontsize=12, fontweight='bold')
ax6.grid(True, alpha=0.3, axis='y')
ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))

plt.suptitle('ANÁLISE COMPARATIVA DE FLUXO DE POTÊNCIA - CENÁRIOS VPL', 
             fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()

# Salvar figura
nome_arquivo = 'analise_fluxo_cenarios_vpl.png'
plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
print(f"\n✅ Gráficos salvos em: {nome_arquivo}")

# Salvar dados em CSV
df_comparacao.to_csv('analise_fluxo_cenarios_vpl.csv', index=False, encoding='utf-8-sig')
print(f"✅ Dados salvos em: analise_fluxo_cenarios_vpl.csv")

print("\n" + "="*100)
print(" "*35 + "ANÁLISE CONCLUÍDA")
print("="*100 + "\n")
