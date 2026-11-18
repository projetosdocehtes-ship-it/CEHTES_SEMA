"""
Compara perfis de carga IFG atual vs Fevereiro
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Ler ambos os perfis
perfil_atual = pd.read_csv('perfil_carga_ifg.csv')
perfil_fev = pd.read_csv('perfil_carga_horaria_fev.csv')

# Criar figura com 2 subplots
fig, axes = plt.subplots(2, 1, figsize=(14, 10))
fig.suptitle('Comparação de Perfis de Carga - IFG', fontsize=16, fontweight='bold')

# Cores
cor_util = '#2E86AB'
cor_fds = '#A23B72'

# --- GRÁFICO 1: Dias Úteis ---
ax1 = axes[0]
atual_util = perfil_atual[perfil_atual['dia_semana'] == 'util']
fev_util = perfil_fev[perfil_fev['dia_semana'] == 'util']

x = np.arange(24)
width = 0.35

bars1 = ax1.bar(x - width/2, atual_util['demanda_kw'], width, 
                label='Perfil Atual', color=cor_util, alpha=0.8)
bars2 = ax1.bar(x + width/2, fev_util['demanda_kw'], width,
                label='Perfil Fev/2025', color='#F77F00', alpha=0.8)

# Destacar horário de ponta (18h-21h)
ax1.axvspan(17.5, 20.5, alpha=0.2, color='red', label='Horário de Ponta')

ax1.set_xlabel('Hora do Dia', fontsize=12)
ax1.set_ylabel('Demanda (kW)', fontsize=12)
ax1.set_title('Dias Úteis', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels([f'{h}h' for h in range(24)], rotation=45, ha='right')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3, axis='y')

# Adicionar estatísticas
stats_text = f'Atual - Média: {atual_util["demanda_kw"].mean():.0f} kW | Máx: {atual_util["demanda_kw"].max():.0f} kW\n'
stats_text += f'Fev/25 - Média: {fev_util["demanda_kw"].mean():.0f} kW | Máx: {fev_util["demanda_kw"].max():.0f} kW'
ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
         fontsize=10, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# --- GRÁFICO 2: Fins de Semana ---
ax2 = axes[1]
atual_fds = perfil_atual[perfil_atual['dia_semana'] == 'fim_semana']
fev_fds = perfil_fev[perfil_fev['dia_semana'] == 'fim_semana']

bars3 = ax2.bar(x - width/2, atual_fds['demanda_kw'], width,
                label='Perfil Atual', color=cor_fds, alpha=0.8)
bars4 = ax2.bar(x + width/2, fev_fds['demanda_kw'], width,
                label='Perfil Fev/2025', color='#06FFA5', alpha=0.8)

# Destacar horário de ponta (18h-21h) - não se aplica em fins de semana, mas mostrar para referência
ax2.axvspan(17.5, 20.5, alpha=0.1, color='red')

ax2.set_xlabel('Hora do Dia', fontsize=12)
ax2.set_ylabel('Demanda (kW)', fontsize=12)
ax2.set_title('Fins de Semana', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([f'{h}h' for h in range(24)], rotation=45, ha='right')
ax2.legend(loc='upper left')
ax2.grid(True, alpha=0.3, axis='y')

# Adicionar estatísticas
stats_text2 = f'Atual - Média: {atual_fds["demanda_kw"].mean():.0f} kW | Máx: {atual_fds["demanda_kw"].max():.0f} kW\n'
stats_text2 += f'Fev/25 - Média: {fev_fds["demanda_kw"].mean():.0f} kW | Máx: {fev_fds["demanda_kw"].max():.0f} kW'
ax2.text(0.02, 0.98, stats_text2, transform=ax2.transAxes,
         fontsize=10, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('comparacao_perfis_carga.png', dpi=150, bbox_inches='tight')
print("\n✓ Gráfico salvo: comparacao_perfis_carga.png")

# Calcular diferenças
print("\n" + "="*80)
print("ANÁLISE COMPARATIVA DOS PERFIS")
print("="*80)

print("\n📊 DIAS ÚTEIS:")
print(f"  Demanda Média - Atual:  {atual_util['demanda_kw'].mean():>6.1f} kW")
print(f"  Demanda Média - Fev/25: {fev_util['demanda_kw'].mean():>6.1f} kW")
print(f"  Variação:               {((fev_util['demanda_kw'].mean()/atual_util['demanda_kw'].mean())-1)*100:>+6.1f}%")

print(f"\n  Demanda Máxima - Atual:  {atual_util['demanda_kw'].max():>5.0f} kW (hora {atual_util.loc[atual_util['demanda_kw'].idxmax(), 'hora']:.0f}h)")
print(f"  Demanda Máxima - Fev/25: {fev_util['demanda_kw'].max():>5.0f} kW (hora {fev_util.loc[fev_util['demanda_kw'].idxmax(), 'hora']:.0f}h)")
print(f"  Variação:                {((fev_util['demanda_kw'].max()/atual_util['demanda_kw'].max())-1)*100:>+5.1f}%")

# Ponta (18h-21h)
ponta_atual = atual_util[atual_util['hora'].isin([18, 19, 20])]['demanda_kw'].mean()
ponta_fev = fev_util[fev_util['hora'].isin([18, 19, 20])]['demanda_kw'].mean()

print(f"\n  Demanda Ponta (18-20h) - Atual:  {ponta_atual:>6.1f} kW")
print(f"  Demanda Ponta (18-20h) - Fev/25: {ponta_fev:>6.1f} kW")
print(f"  Variação:                        {((ponta_fev/ponta_atual)-1)*100:>+6.1f}%")

print("\n📊 FINS DE SEMANA:")
print(f"  Demanda Média - Atual:  {atual_fds['demanda_kw'].mean():>6.1f} kW")
print(f"  Demanda Média - Fev/25: {fev_fds['demanda_kw'].mean():>6.1f} kW")
print(f"  Variação:               {((fev_fds['demanda_kw'].mean()/atual_fds['demanda_kw'].mean())-1)*100:>+6.1f}%")

print(f"\n  Demanda Máxima - Atual:  {atual_fds['demanda_kw'].max():>5.0f} kW")
print(f"  Demanda Máxima - Fev/25: {fev_fds['demanda_kw'].max():>5.0f} kW")
print(f"  Variação:                {((fev_fds['demanda_kw'].max()/atual_fds['demanda_kw'].max())-1)*100:>+5.1f}%")

print("\n" + "="*80)
