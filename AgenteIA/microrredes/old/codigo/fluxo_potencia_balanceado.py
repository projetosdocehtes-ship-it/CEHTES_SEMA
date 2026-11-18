"""
Gera gráfico de fluxo de potência para o cenário BALANCEADO
Balanço entre Investimento (peso 2) e Payback (peso 1)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from caso_ifg import CasoIFG

# Carregar resultados da análise de sensibilidade
df = pd.read_csv('analise_sensibilidade_bess_pv_resultados.csv')
df_cenarios = df[df['tipo'] == 'Cenário'].copy()

print("="*100)
print(" "*25 + "SELEÇÃO DO CENÁRIO BALANCEADO")
print(" "*20 + "Investimento (peso 2) vs Payback (peso 1)")
print("="*100)

# Normalizar valores (min-max normalization)
# Quanto menor, melhor -> vamos normalizar para que 0 = melhor, 1 = pior
inv_min = df_cenarios['investimento_total'].min()
inv_max = df_cenarios['investimento_total'].max()
df_cenarios['inv_norm'] = (df_cenarios['investimento_total'] - inv_min) / (inv_max - inv_min)

pay_min = df_cenarios['payback_anos'].min()
pay_max = df_cenarios['payback_anos'].max()
df_cenarios['pay_norm'] = (df_cenarios['payback_anos'] - pay_min) / (pay_max - pay_min)

# Calcular score combinado (quanto MAIOR, melhor)
# Score = peso_inv × (1 - inv_norm) + peso_pay × (1 - pay_norm)
# Queremos maximizar o inverso das normalizações (menor investimento e menor payback)
peso_investimento = 2
peso_payback = 1
df_cenarios['score'] = (peso_investimento * (1 - df_cenarios['inv_norm']) + 
                        peso_payback * (1 - df_cenarios['pay_norm']))

# Ordenar por score e selecionar o melhor
df_cenarios = df_cenarios.sort_values('score', ascending=False)
cenario_balanceado = df_cenarios.iloc[0]

print(f"\n📊 ANÁLISE DOS CENÁRIOS:")
print(f"   Total de cenários analisados: {len(df_cenarios)}")
print(f"   Faixa de investimento: R$ {inv_min:,.0f} - R$ {inv_max:,.0f}")
print(f"   Faixa de payback: {pay_min:.1f} - {pay_max:.1f} anos")

print(f"\n🎯 CENÁRIO SELECIONADO (Melhor Score):")
print(f"   PV: {cenario_balanceado['pv_kwp']:.0f} kWp")
print(f"   BESS: {cenario_balanceado['bess_kwh']:.0f} kWh")
print(f"   Investimento: R$ {cenario_balanceado['investimento_total']:,.2f}")
print(f"   Payback: {cenario_balanceado['payback_anos']:.1f} anos")
print(f"   Economia anual: R$ {cenario_balanceado['economia_total_anual']:,.2f}")
print(f"   Score balanceado: {cenario_balanceado['score']:.3f}")
print(f"   Inv normalizado: {cenario_balanceado['inv_norm']:.3f}")
print(f"   Pay normalizado: {cenario_balanceado['pay_norm']:.3f}")

# Comparação com extremos
melhor_payback = df_cenarios.iloc[-1]  # Último após sort por score = menor payback
melhor_inv = df_cenarios[df_cenarios['investimento_total'] == inv_min].iloc[0]

print(f"\n📈 COMPARAÇÃO:")
print(f"\n   Melhor Payback isolado:")
print(f"      PV: {melhor_payback['pv_kwp']:.0f} kWp, BESS: {melhor_payback['bess_kwh']:.0f} kWh")
print(f"      Investimento: R$ {melhor_payback['investimento_total']:,.0f}, Payback: {melhor_payback['payback_anos']:.1f} anos")
print(f"\n   Menor Investimento isolado:")
print(f"      PV: {melhor_inv['pv_kwp']:.0f} kWp, BESS: {melhor_inv['bess_kwh']:.0f} kWh")
print(f"      Investimento: R$ {melhor_inv['investimento_total']:,.0f}, Payback: {melhor_inv['payback_anos']:.1f} anos")
print(f"\n   Cenário BALANCEADO (peso 2:1):")
print(f"      PV: {cenario_balanceado['pv_kwp']:.0f} kWp, BESS: {cenario_balanceado['bess_kwh']:.0f} kWh")
print(f"      Investimento: R$ {cenario_balanceado['investimento_total']:,.0f}, Payback: {cenario_balanceado['payback_anos']:.1f} anos")

# Gerar gráfico de fluxo de potência
print(f"\n" + "="*100)
print(" "*30 + "GERANDO GRÁFICO DE FLUXO DE POTÊNCIA")
print("="*100)

# Criar caso e simular
caso = CasoIFG(modalidade='verde')
caso.pv_potencia_kwp = cenario_balanceado['pv_kwp']
caso.bess_capacidade_kwh = cenario_balanceado['bess_kwh']
caso.bess_potencia_kw = 230
caso._configurar_pv()

# Simular dia útil
resultado = caso.simular_dia(dia_semana=0)

# Criar DataFrame
df_dia = pd.DataFrame({
    'hora': resultado['hora'],
    'geracao_pv_kw': resultado['geracao_pv_kw'],
    'demanda_kw': resultado['demanda_kw'],
    'potencia_bess_kw': resultado['potencia_bess_kw'],
    'energia_rede_kw': resultado['energia_rede_kw'],
    'custo_hora': resultado['custo_hora'],
    'soc_bess': resultado['soc_bess_kwh']
})

# Criar figura com 3 subplots
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Título principal
titulo = f"CENÁRIO BALANCEADO (Investimento peso 2, Payback peso 1)\n"
titulo += f"PV {cenario_balanceado['pv_kwp']:.0f} kWp + BESS {cenario_balanceado['bess_kwh']:.0f} kWh | "
titulo += f"Investimento: R$ {cenario_balanceado['investimento_total']:,.0f} | "
titulo += f"Payback: {cenario_balanceado['payback_anos']:.1f} anos | "
titulo += f"Economia: R$ {cenario_balanceado['economia_total_anual']:,.0f}/ano"
fig.suptitle(titulo, fontsize=13, fontweight='bold')

# ===== GRÁFICO 1: Geração PV vs Demanda =====
ax1 = axes[0]
horas = df_dia['hora'].values

# Plotar PV
ax1.fill_between(horas, 0, df_dia['geracao_pv_kw'].values, 
                  alpha=0.6, color='#FF9500', label='Geração PV')
ax1.plot(horas, df_dia['geracao_pv_kw'].values, 
         color='#FF9500', linewidth=2)

# Plotar Demanda
ax1.fill_between(horas, 0, df_dia['demanda_kw'].values, 
                  alpha=0.4, color='#FF3B30', label='Demanda')
ax1.plot(horas, df_dia['demanda_kw'].values, 
         color='#FF3B30', linewidth=2)

# Destacar horário de ponta
for hora in range(18, 21):
    ax1.axvspan(hora-0.5, hora+0.5, alpha=0.1, color='red')

ax1.set_xlabel('Hora', fontsize=11)
ax1.set_ylabel('Potência (kW)', fontsize=11)
ax1.set_title('Geração PV vs Demanda', fontweight='bold', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(alpha=0.3)
ax1.set_xlim(0, 23)

# ===== GRÁFICO 2: Fluxo BESS =====
ax2 = axes[1]

# Separar carga e descarga
bess_descarga = df_dia['potencia_bess_kw'].clip(lower=0).values
bess_carga = df_dia['potencia_bess_kw'].clip(upper=0).values

# Plotar descarga (positivo = azul)
ax2.bar(horas, bess_descarga, color='#007AFF', alpha=0.7, 
        label='Descarga (+)', width=0.8)

# Plotar carga (negativo = ciano)
ax2.bar(horas, bess_carga, color='#00C7BE', alpha=0.7, 
        label='Carga (-)', width=0.8)

# Linha zero
ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='-')

# Destacar horário de ponta
for hora in range(18, 21):
    ax2.axvspan(hora-0.5, hora+0.5, alpha=0.1, color='red')

ax2.set_xlabel('Hora', fontsize=11)
ax2.set_ylabel('Potência (kW)', fontsize=11)
ax2.set_title('Fluxo BESS (+ = Descarga, - = Carga)', fontweight='bold', fontsize=12)
ax2.legend(loc='upper left')
ax2.grid(alpha=0.3)
ax2.set_xlim(-0.5, 23.5)

# Adicionar SOC no eixo secundário
ax2_twin = ax2.twinx()
ax2_twin.plot(horas, df_dia['soc_bess'].values, color='purple', 
              linewidth=2, linestyle='--', alpha=0.7, label='SOC')
ax2_twin.set_ylabel('SOC (%)', fontsize=10, color='purple')
ax2_twin.tick_params(axis='y', labelcolor='purple')
ax2_twin.set_ylim(0, 100)
ax2_twin.legend(loc='upper right')

# ===== GRÁFICO 3: Fluxo Rede =====
ax3 = axes[2]

# Separar importação e exportação
rede_importa = df_dia['energia_rede_kw'].clip(lower=0).values
rede_exporta = df_dia['energia_rede_kw'].clip(upper=0).values

# Plotar importação (positivo = vermelho)
ax3.bar(horas, rede_importa, color='#FF3B30', alpha=0.7, 
        label='Importação (+)', width=0.8)

# Plotar exportação (negativo = verde)
ax3.bar(horas, rede_exporta, color='#34C759', alpha=0.7, 
        label='Exportação (-)', width=0.8)

# Linha zero
ax3.axhline(y=0, color='black', linewidth=0.8, linestyle='-')

# Destacar horário de ponta
for hora in range(18, 21):
    ax3.axvspan(hora-0.5, hora+0.5, alpha=0.1, color='red')

ax3.set_xlabel('Hora', fontsize=11)
ax3.set_ylabel('Potência (kW)', fontsize=11)
ax3.set_title('Fluxo Rede (+ = Importa, - = Exporta)', fontweight='bold', fontsize=12)
ax3.legend(loc='upper left')
ax3.grid(alpha=0.3)
ax3.set_xlim(-0.5, 23.5)

# Ajustar layout
plt.tight_layout(rect=[0, 0, 1, 0.96])

# Salvar
filename = 'fluxo_potencia_balanceado.png'
plt.savefig(filename, dpi=300, bbox_inches='tight')
print(f"\n✓ Gráfico salvo: {filename}")
plt.close()

# Estatísticas do cenário
print("\n" + "="*100)
print(" "*30 + "ESTATÍSTICAS DO CENÁRIO BALANCEADO")
print("="*100)

# Calcular estatísticas
energia_comprada = df_dia[df_dia['energia_rede_kw'] > 0]['energia_rede_kw'].sum()
energia_vendida = -df_dia[df_dia['energia_rede_kw'] < 0]['energia_rede_kw'].sum()
energia_bess_descarga = df_dia[df_dia['potencia_bess_kw'] > 0]['potencia_bess_kw'].sum()
energia_bess_carga = -df_dia[df_dia['potencia_bess_kw'] < 0]['potencia_bess_kw'].sum()

# Compra na ponta
df_ponta = df_dia[(df_dia['hora'] >= 18) & (df_dia['hora'] < 21)]
compra_ponta = df_ponta[df_ponta['energia_rede_kw'] > 0]['energia_rede_kw'].sum()

print(f"\n  Energia comprada da rede:     {energia_comprada:>8.1f} kWh/dia")
print(f"  Energia vendida para rede:    {energia_vendida:>8.1f} kWh/dia")
print(f"  Compra na PONTA (18h-21h):    {compra_ponta:>8.1f} kWh")
print(f"  BESS - Descarga:              {energia_bess_descarga:>8.1f} kWh/dia")
print(f"  BESS - Carga:                 {energia_bess_carga:>8.1f} kWh/dia")
print(f"  Eficiência BESS:              {(energia_bess_descarga/energia_bess_carga*100) if energia_bess_carga > 0 else 0:>8.1f}%")
print(f"  Custo diário:                 R$ {df_dia['custo_hora'].sum():>8.2f}")

# Análise de custo-benefício
roi_10anos = ((cenario_balanceado['economia_total_anual'] * 10) / cenario_balanceado['investimento_total'] - 1) * 100
lucro_10anos = cenario_balanceado['economia_total_anual'] * 10 - cenario_balanceado['investimento_total']

print(f"\n📊 ANÁLISE FINANCEIRA (10 anos):")
print(f"  ROI (10 anos):                {roi_10anos:>8.1f}%")
print(f"  Lucro líquido (10 anos):      R$ {lucro_10anos:>10,.2f}")
print(f"  VPL (considerando inflação):  Em análise")

print("\n" + "="*100)
print("✅ Análise do cenário balanceado concluída!")
print("="*100)
