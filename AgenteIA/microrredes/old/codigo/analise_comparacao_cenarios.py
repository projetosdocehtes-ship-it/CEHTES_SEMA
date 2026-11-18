"""
Análise Detalhada dos Cenários: Melhor, Pior e Médio Payback
"""

import pandas as pd
import matplotlib.pyplot as plt

# Carregar resultados
df = pd.read_csv('analise_sensibilidade_bess_pv_resultados.csv')

# Filtrar apenas cenários (excluir base)
df_cenarios = df[df['tipo'] == 'Cenário'].copy()

# Ordenar por payback
df_cenarios = df_cenarios.sort_values('payback_anos')

print("\n" + "="*100)
print(" "*25 + "ANÁLISE COMPARATIVA DE CENÁRIOS - PAYBACK")
print("="*100)

# MELHOR CENÁRIO (Menor Payback)
melhor = df_cenarios.iloc[0]
print(f"\n🏆 MELHOR CENÁRIO (Menor Payback = {melhor['payback_anos']:.1f} anos)")
print("-"*100)
print(f"  Configuração:")
print(f"    PV:                        {melhor['pv_kwp']:.0f} kWp")
print(f"    BESS:                      {melhor['bess_kwh']:.0f} kWh")
print(f"\n  Investimento:")
print(f"    Investimento Total:        R$ {melhor['investimento_total']:,.2f}")
print(f"    Custo específico PV:       R$ {melhor['investimento_total'] / melhor['pv_kwp']:,.2f}/kWp")
if melhor['bess_kwh'] > 0:
    print(f"    Custo específico BESS:     R$ {(melhor['investimento_total']) / melhor['bess_kwh']:,.2f}/kWh")
print(f"\n  Economia Anual:")
print(f"    Economia Total:            R$ {melhor['economia_total_anual']:,.2f}/ano")
print(f"    Economia Energia:          R$ {melhor['economia_energia_anual']:,.2f}/ano")
print(f"    Economia Demanda:          R$ {melhor['economia_demanda_anual']:,.2f}/ano")
print(f"\n  Retorno Financeiro:")
print(f"    Payback:                   {melhor['payback_anos']:.1f} anos")
print(f"    Economia em 10 anos:       R$ {melhor['economia_total_anual'] * 10:,.2f}")
print(f"    Lucro líquido (10 anos):   R$ {(melhor['economia_total_anual'] * 10) - melhor['investimento_total']:,.2f}")
print(f"    ROI (10 anos):             {((melhor['economia_total_anual'] * 10) / melhor['investimento_total'] - 1) * 100:.1f}%")
print(f"\n  Operação:")
print(f"    Custo anual COM sistema:   R$ {melhor['custo_anual']:,.2f}")
print(f"    Redução de demanda:        {melhor['reducao_demanda_kw']:.0f} kW")

# PIOR CENÁRIO (Maior Payback)
pior = df_cenarios.iloc[-1]
print(f"\n\n❌ PIOR CENÁRIO (Maior Payback = {pior['payback_anos']:.1f} anos)")
print("-"*100)
print(f"  Configuração:")
print(f"    PV:                        {pior['pv_kwp']:.0f} kWp")
print(f"    BESS:                      {pior['bess_kwh']:.0f} kWh")
print(f"\n  Investimento:")
print(f"    Investimento Total:        R$ {pior['investimento_total']:,.2f}")
print(f"    Custo específico PV:       R$ {pior['investimento_total'] / pior['pv_kwp']:,.2f}/kWp")
if pior['bess_kwh'] > 0:
    print(f"    Custo específico BESS:     R$ {(pior['investimento_total']) / pior['bess_kwh']:,.2f}/kWh")
print(f"\n  Economia Anual:")
print(f"    Economia Total:            R$ {pior['economia_total_anual']:,.2f}/ano")
print(f"    Economia Energia:          R$ {pior['economia_energia_anual']:,.2f}/ano")
print(f"    Economia Demanda:          R$ {pior['economia_demanda_anual']:,.2f}/ano")
print(f"\n  Retorno Financeiro:")
print(f"    Payback:                   {pior['payback_anos']:.1f} anos")
print(f"    Economia em 10 anos:       R$ {pior['economia_total_anual'] * 10:,.2f}")
print(f"    Lucro líquido (10 anos):   R$ {(pior['economia_total_anual'] * 10) - pior['investimento_total']:,.2f}")
print(f"    ROI (10 anos):             {((pior['economia_total_anual'] * 10) / pior['investimento_total'] - 1) * 100:.1f}%")
print(f"\n  Operação:")
print(f"    Custo anual COM sistema:   R$ {pior['custo_anual']:,.2f}")
print(f"    Redução de demanda:        {pior['reducao_demanda_kw']:.0f} kW")

# CENÁRIO MÉDIO (Payback mediano)
idx_medio = len(df_cenarios) // 2
medio = df_cenarios.iloc[idx_medio]
print(f"\n\n📊 CENÁRIO MÉDIO (Payback mediano = {medio['payback_anos']:.1f} anos)")
print("-"*100)
print(f"  Configuração:")
print(f"    PV:                        {medio['pv_kwp']:.0f} kWp")
print(f"    BESS:                      {medio['bess_kwh']:.0f} kWh")
print(f"\n  Investimento:")
print(f"    Investimento Total:        R$ {medio['investimento_total']:,.2f}")
print(f"    Custo específico PV:       R$ {medio['investimento_total'] / medio['pv_kwp']:,.2f}/kWp")
if medio['bess_kwh'] > 0:
    print(f"    Custo específico BESS:     R$ {(medio['investimento_total']) / medio['bess_kwh']:,.2f}/kWh")
print(f"\n  Economia Anual:")
print(f"    Economia Total:            R$ {medio['economia_total_anual']:,.2f}/ano")
print(f"    Economia Energia:          R$ {medio['economia_energia_anual']:,.2f}/ano")
print(f"    Economia Demanda:          R$ {medio['economia_demanda_anual']:,.2f}/ano")
print(f"\n  Retorno Financeiro:")
print(f"    Payback:                   {medio['payback_anos']:.1f} anos")
print(f"    Economia em 10 anos:       R$ {medio['economia_total_anual'] * 10:,.2f}")
print(f"    Lucro líquido (10 anos):   R$ {(medio['economia_total_anual'] * 10) - medio['investimento_total']:,.2f}")
print(f"    ROI (10 anos):             {((medio['economia_total_anual'] * 10) / medio['investimento_total'] - 1) * 100:.1f}%")
print(f"\n  Operação:")
print(f"    Custo anual COM sistema:   R$ {medio['custo_anual']:,.2f}")
print(f"    Redução de demanda:        {medio['reducao_demanda_kw']:.0f} kW")

# Comparação lado a lado
print("\n\n" + "="*100)
print(" "*35 + "COMPARAÇÃO DIRETA")
print("="*100)
print(f"\n{'Métrica':<35} {'Melhor':<20} {'Médio':<20} {'Pior':<20}")
print("-"*100)
print(f"{'PV (kWp)':<35} {melhor['pv_kwp']:>19.0f} {medio['pv_kwp']:>19.0f} {pior['pv_kwp']:>19.0f}")
print(f"{'BESS (kWh)':<35} {melhor['bess_kwh']:>19.0f} {medio['bess_kwh']:>19.0f} {pior['bess_kwh']:>19.0f}")
print(f"{'Investimento (R$)':<35} {melhor['investimento_total']:>19,.0f} {medio['investimento_total']:>19,.0f} {pior['investimento_total']:>19,.0f}")
print(f"{'Economia anual (R$)':<35} {melhor['economia_total_anual']:>19,.0f} {medio['economia_total_anual']:>19,.0f} {pior['economia_total_anual']:>19,.0f}")
print(f"{'Payback (anos)':<35} {melhor['payback_anos']:>19.1f} {medio['payback_anos']:>19.1f} {pior['payback_anos']:>19.1f}")
print(f"{'Lucro 10 anos (R$)':<35} {(melhor['economia_total_anual'] * 10) - melhor['investimento_total']:>19,.0f} {(medio['economia_total_anual'] * 10) - medio['investimento_total']:>19,.0f} {(pior['economia_total_anual'] * 10) - pior['investimento_total']:>19,.0f}")
print(f"{'ROI 10 anos (%)':<35} {((melhor['economia_total_anual'] * 10) / melhor['investimento_total'] - 1) * 100:>18.1f}% {((medio['economia_total_anual'] * 10) / medio['investimento_total'] - 1) * 100:>18.1f}% {((pior['economia_total_anual'] * 10) / pior['investimento_total'] - 1) * 100:>18.1f}%")

# Estatísticas gerais
print("\n\n" + "="*100)
print(" "*35 + "ESTATÍSTICAS GERAIS")
print("="*100)
print(f"\nTotal de cenários analisados: {len(df_cenarios)}")
print(f"\nPayback:")
print(f"  Mínimo:    {df_cenarios['payback_anos'].min():.1f} anos")
print(f"  Máximo:    {df_cenarios['payback_anos'].max():.1f} anos")
print(f"  Médio:     {df_cenarios['payback_anos'].mean():.1f} anos")
print(f"  Mediano:   {df_cenarios['payback_anos'].median():.1f} anos")
print(f"\nInvestimento:")
print(f"  Mínimo:    R$ {df_cenarios['investimento_total'].min():,.2f}")
print(f"  Máximo:    R$ {df_cenarios['investimento_total'].max():,.2f}")
print(f"  Médio:     R$ {df_cenarios['investimento_total'].mean():,.2f}")
print(f"\nEconomia Anual:")
print(f"  Mínima:    R$ {df_cenarios['economia_total_anual'].min():,.2f}")
print(f"  Máxima:    R$ {df_cenarios['economia_total_anual'].max():,.2f}")
print(f"  Média:     R$ {df_cenarios['economia_total_anual'].mean():,.2f}")

# Gráfico comparativo
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Comparação: Melhor, Médio e Pior Cenário', fontsize=16, fontweight='bold')

cenarios_comp = pd.DataFrame({
    'Cenário': ['Melhor', 'Médio', 'Pior'],
    'PV (kWp)': [melhor['pv_kwp'], medio['pv_kwp'], pior['pv_kwp']],
    'BESS (kWh)': [melhor['bess_kwh'], medio['bess_kwh'], pior['bess_kwh']],
    'Investimento': [melhor['investimento_total'], medio['investimento_total'], pior['investimento_total']],
    'Economia Anual': [melhor['economia_total_anual'], medio['economia_total_anual'], pior['economia_total_anual']],
    'Payback': [melhor['payback_anos'], medio['payback_anos'], pior['payback_anos']]
})

# Gráfico 1: Configuração (PV + BESS)
ax1 = axes[0, 0]
x = range(3)
width = 0.35
ax1.bar([i - width/2 for i in x], cenarios_comp['PV (kWp)'], width, label='PV (kWp)', color='#FF9500')
ax1.bar([i + width/2 for i in x], cenarios_comp['BESS (kWh)'], width, label='BESS (kWh)', color='#34C759')
ax1.set_xticks(x)
ax1.set_xticklabels(cenarios_comp['Cenário'])
ax1.set_ylabel('Capacidade')
ax1.set_title('Configuração do Sistema', fontweight='bold')
ax1.legend()
ax1.grid(axis='y', alpha=0.3)

# Gráfico 2: Investimento
ax2 = axes[0, 1]
bars = ax2.bar(cenarios_comp['Cenário'], cenarios_comp['Investimento'] / 1000, color=['#34C759', '#FFB800', '#FF3B30'])
ax2.set_ylabel('Investimento (R$ mil)')
ax2.set_title('Investimento Total', fontweight='bold')
ax2.grid(axis='y', alpha=0.3)
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'R$ {height:.0f}k',
             ha='center', va='bottom')

# Gráfico 3: Economia Anual
ax3 = axes[1, 0]
bars = ax3.bar(cenarios_comp['Cenário'], cenarios_comp['Economia Anual'] / 1000, color=['#34C759', '#FFB800', '#FF3B30'])
ax3.set_ylabel('Economia Anual (R$ mil)')
ax3.set_title('Economia Anual', fontweight='bold')
ax3.grid(axis='y', alpha=0.3)
for bar in bars:
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'R$ {height:.0f}k',
             ha='center', va='bottom')

# Gráfico 4: Payback
ax4 = axes[1, 1]
bars = ax4.bar(cenarios_comp['Cenário'], cenarios_comp['Payback'], color=['#34C759', '#FFB800', '#FF3B30'])
ax4.set_ylabel('Payback (anos)')
ax4.set_title('Período de Retorno', fontweight='bold')
ax4.axhline(y=5, color='gray', linestyle='--', label='Meta: 5 anos', alpha=0.5)
ax4.grid(axis='y', alpha=0.3)
ax4.legend()
for bar in bars:
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f} anos',
             ha='center', va='bottom')

plt.tight_layout()
plt.savefig('comparacao_cenarios_payback.png', dpi=300, bbox_inches='tight')
print(f"\n\n📊 Gráfico de comparação salvo: comparacao_cenarios_payback.png")
print("\n" + "="*100)
