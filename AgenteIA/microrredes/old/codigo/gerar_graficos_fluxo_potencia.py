"""
Gera gráficos de fluxo de potência para os cenários principais
(Melhor, Médio e Pior Payback)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from caso_ifg import CasoIFG

# Carregar resultados da análise de sensibilidade
df = pd.read_csv('analise_sensibilidade_bess_pv_resultados.csv')
df_cenarios = df[df['tipo'] == 'Cenário'].copy()
df_cenarios = df_cenarios.sort_values('payback_anos')

# Selecionar cenários
melhor = df_cenarios.iloc[0]
pior = df_cenarios.iloc[-1]
idx_medio = len(df_cenarios) // 2
medio = df_cenarios.iloc[idx_medio]

cenarios = [
    ('MELHOR', melhor, '#34C759'),
    ('MÉDIO', medio, '#FFB800'),
    ('PIOR', pior, '#FF3B30')
]

print("="*100)
print(" "*30 + "GERANDO GRÁFICOS DE FLUXO DE POTÊNCIA")
print("="*100)

for nome, cenario, cor in cenarios:
    print(f"\n📊 Gerando gráfico: {nome} CENÁRIO")
    print(f"   PV: {cenario['pv_kwp']:.0f} kWp | BESS: {cenario['bess_kwh']:.0f} kWh | Payback: {cenario['payback_anos']:.1f} anos")
    
    # Criar caso e simular
    caso = CasoIFG(modalidade='verde')
    caso.pv_potencia_kwp = cenario['pv_kwp']
    caso.bess_capacidade_kwh = cenario['bess_kwh']
    caso.bess_potencia_kw = 230
    caso._configurar_pv()
    
    # Simular dia útil
    resultado = caso.simular_dia(dia_semana=0)
    
    # Criar DataFrame
    df_dia = pd.DataFrame(resultado)
    
    # Criar figura com 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Título principal
    titulo = f"ANÁLISE DETALHADA: {nome} Cenário - Payback {cenario['payback_anos']:.1f} anos\n"
    titulo += f"PV {cenario['pv_kwp']:.0f} kWp + BESS {cenario['bess_kwh']:.0f} kWh | "
    titulo += f"Investimento: R$ {cenario['investimento_total']:,.0f} | "
    titulo += f"Economia: R$ {cenario['economia_total_anual']:,.0f}/ano"
    fig.suptitle(titulo, fontsize=14, fontweight='bold')
    
    # ===== GRÁFICO 1: Geração PV vs Demanda =====
    ax1 = axes[0]
    horas = df_dia['hora']
    
    # Plotar PV
    ax1.fill_between(horas, 0, df_dia['geracao_pv_kw'], 
                      alpha=0.6, color='#FF9500', label='Geração PV')
    ax1.plot(horas, df_dia['geracao_pv_kw'], 
             color='#FF9500', linewidth=2)
    
    # Plotar Demanda
    ax1.fill_between(horas, 0, df_dia['demanda_kw'], 
                      alpha=0.4, color='#FF3B30', label='Demanda')
    ax1.plot(horas, df_dia['demanda_kw'], 
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
    ax1.set_ylim(0, max(df_dia['geracao_pv_kw'].max(), df_dia['demanda_kw'].max()) * 1.1)
    
    # ===== GRÁFICO 2: Fluxo BESS =====
    ax2 = axes[1]
    
    # Separar carga e descarga
    bess_descarga = df_dia['potencia_bess_kw'].clip(lower=0)  # Positivo
    bess_carga = df_dia['potencia_bess_kw'].clip(upper=0)     # Negativo
    
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
    
    # Adicionar texto informativo
    ax2.text(0.02, 0.98, f'Descarga (+)', transform=ax2.transAxes,
             verticalalignment='top', fontsize=9, color='#007AFF', fontweight='bold')
    ax2.text(0.02, 0.92, f'Carga (-)', transform=ax2.transAxes,
             verticalalignment='top', fontsize=9, color='#00C7BE', fontweight='bold')
    
    # ===== GRÁFICO 3: Fluxo Rede =====
    ax3 = axes[2]
    
    # Separar importação e exportação
    rede_importa = df_dia['energia_rede_kw'].clip(lower=0)   # Positivo = compra
    rede_exporta = df_dia['energia_rede_kw'].clip(upper=0)   # Negativo = venda
    
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
    
    # Adicionar texto informativo
    ax3.text(0.02, 0.98, f'Importação (+)', transform=ax3.transAxes,
             verticalalignment='top', fontsize=9, color='#FF3B30', fontweight='bold')
    ax3.text(0.02, 0.92, f'Exportação (-)', transform=ax3.transAxes,
             verticalalignment='top', fontsize=9, color='#34C759', fontweight='bold')
    
    # Ajustar layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Salvar
    filename = f'fluxo_potencia_{nome.lower()}_cenario.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"   ✓ Salvo: {filename}")
    plt.close()

# Estatísticas dos cenários
print("\n" + "="*100)
print(" "*30 + "ESTATÍSTICAS DOS CENÁRIOS")
print("="*100)

for nome, cenario, cor in cenarios:
    # Simular para obter dados
    caso = CasoIFG(modalidade='verde')
    caso.pv_potencia_kwp = cenario['pv_kwp']
    caso.bess_capacidade_kwh = cenario['bess_kwh']
    caso.bess_potencia_kw = 230
    caso._configurar_pv()
    resultado = caso.simular_dia(dia_semana=0)
    df_dia = pd.DataFrame(resultado)
    
    # Calcular estatísticas
    energia_comprada = df_dia[df_dia['energia_rede_kw'] > 0]['energia_rede_kw'].sum()
    energia_vendida = -df_dia[df_dia['energia_rede_kw'] < 0]['energia_rede_kw'].sum()
    energia_bess_descarga = df_dia[df_dia['potencia_bess_kw'] > 0]['potencia_bess_kw'].sum()
    energia_bess_carga = -df_dia[df_dia['potencia_bess_kw'] < 0]['potencia_bess_kw'].sum()
    
    # Compra na ponta
    df_ponta = df_dia[(df_dia['hora'] >= 18) & (df_dia['hora'] < 21)]
    compra_ponta = df_ponta[df_ponta['energia_rede_kw'] > 0]['energia_rede_kw'].sum()
    
    print(f"\n{nome} CENÁRIO:")
    print(f"  Energia comprada da rede:     {energia_comprada:>8.1f} kWh/dia")
    print(f"  Energia vendida para rede:    {energia_vendida:>8.1f} kWh/dia")
    print(f"  Compra na PONTA (18h-21h):    {compra_ponta:>8.1f} kWh")
    print(f"  BESS - Descarga:              {energia_bess_descarga:>8.1f} kWh/dia")
    print(f"  BESS - Carga:                 {energia_bess_carga:>8.1f} kWh/dia")
    print(f"  Custo diário:                 R$ {df_dia['custo_hora'].sum():>8.2f}")

print("\n" + "="*100)
print("✅ Gráficos de fluxo de potência gerados com sucesso!")
print("="*100)
