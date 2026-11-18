"""
Análise Detalhada de Fluxo de Potência para Cenários VPL
=========================================================
Gera gráficos detalhados do fluxo de potência horário para:
- Cenário de Maior VPL
- Cenário de Médio VPL
- Cenário de Menor VPL
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from caso_ifg import CasoIFG
import warnings
warnings.filterwarnings('ignore')

class VisualizadorFluxoPotenciaVPL:
    def __init__(self):
        """Inicializa o visualizador"""
        self.caso = CasoIFG()
        
        # Definir os 3 cenários de VPL
        self.cenarios = {
            'Maior VPL': {
                'pv_kwp': 600,
                'bess_kwh': 500,
                'vpl': 694876,
                'payback_anos': 5.3,
                'economia_anual': 332384,
                'investimento': 1778000,
                'cor': '#2E7D32'
            },
            'Médio VPL': {
                'pv_kwp': 400,
                'bess_kwh': 300,
                'vpl': 410476,
                'payback_anos': 4.9,
                'economia_anual': 162434,
                'investimento': 798000,
                'cor': '#1976D2'
            },
            'Menor VPL': {
                'pv_kwp': 324,
                'bess_kwh': 100,
                'vpl': 185549,  # Aproximado
                'payback_anos': 5.7,
                'economia_anual': 33128,
                'investimento': 190000,
                'cor': '#C62828'
            }
        }
        
    def simular_cenario(self, pv_kwp, bess_kwh):
        """Simula um cenário e retorna os dados horários"""
        print(f"    Simulando PV {pv_kwp} kWp + BESS {bess_kwh} kWh...")
        
        # Configura o sistema
        self.caso.pv_potencia_kwp = pv_kwp
        self.caso.bess_capacidade_kwh = bess_kwh
        
        # Reconfigura o PV com nova potência
        self.caso._configurar_pv()
        
        # Simula um dia útil (retorna dados horários)
        resultado_dia = self.caso.simular_dia(dia_semana=0)
        
        # Converte para DataFrame
        df = pd.DataFrame({
            'hora': range(24),
            'demanda_kw': resultado_dia['demanda_kw'],
            'pv_geracao_kw': resultado_dia['geracao_pv_kw'],
            'bess_fluxo_kw': resultado_dia['potencia_bess_kw'],
            'bess_soc_kwh': resultado_dia['soc_bess_kwh'],
            'rede_fluxo_kw': resultado_dia['energia_rede_kw'],
            'custo_hora': resultado_dia['custo_hora']
        })
        
        # Calcular SOC em porcentagem
        df['bess_soc_pct'] = (df['bess_soc_kwh'] / bess_kwh * 100)
        
        return df
    
    def plotar_analise_completa(self, nome_cenario, df, info):
        """Plota análise completa de um cenário em uma figura"""
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Título principal
        titulo_principal = f'ANÁLISE DETALHADA: {nome_cenario}\n'
        titulo_principal += f'PV {info["pv_kwp"]} kWp + BESS {info["bess_kwh"]} kWh | '
        titulo_principal += f'VPL: R$ {info["vpl"]:,.0f} | '
        titulo_principal += f'Payback: {info["payback_anos"]:.1f} anos | '
        titulo_principal += f'Economia: R$ {info["economia_anual"]:,.0f}/ano | '
        titulo_principal += f'Investimento: R$ {info["investimento"]:,.0f}'
        
        fig.suptitle(titulo_principal, fontsize=15, fontweight='bold', y=0.98)
        
        horas = df['hora'].values
        
        # === GRÁFICO 1: Geração PV vs Demanda (Grande - ocupa 2 colunas) ===
        ax1 = fig.add_subplot(gs[0, :2])
        
        pv_gen = df['pv_geracao_kw'].values
        demanda = df['demanda_kw'].values
        
        ax1.fill_between(horas, 0, pv_gen, alpha=0.4, color='gold', label='Geração PV')
        ax1.plot(horas, pv_gen, color='orange', linewidth=2.5)
        
        ax1.fill_between(horas, 0, demanda, alpha=0.2, color='red', label='Demanda')
        ax1.plot(horas, demanda, color='red', linewidth=2.5, linestyle='--')
        
        # Destacar horário de ponta (18-21h)
        ax1.axvspan(18, 21, alpha=0.15, color='red', label='Horário Ponta')
        
        ax1.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Potência (kW)', fontsize=11, fontweight='bold')
        ax1.set_title('Geração Fotovoltaica vs Demanda', fontsize=12, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_xlim(-0.5, 23.5)
        
        # Estatísticas
        stats = f"PV Máx: {pv_gen.max():.0f} kW\n"
        stats += f"PV Total: {pv_gen.sum():.0f} kWh/dia\n"
        stats += f"Demanda Máx: {demanda.max():.0f} kW\n"
        stats += f"Demanda Total: {demanda.sum():.0f} kWh/dia"
        ax1.text(0.98, 0.97, stats, transform=ax1.transAxes,
                fontsize=9, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
        
        # === GRÁFICO 2: Estado de Carga BESS ===
        ax2 = fig.add_subplot(gs[0, 2])
        
        soc_pct = df['bess_soc_pct'].values
        
        ax2.fill_between(horas, 0, soc_pct, alpha=0.4, color='dodgerblue')
        ax2.plot(horas, soc_pct, color='darkblue', linewidth=2.5, marker='o', markersize=4)
        
        ax2.axhline(y=95, color='green', linewidth=1.5, linestyle='--', alpha=0.6, label='SOC Máx (95%)')
        ax2.axhline(y=10, color='red', linewidth=1.5, linestyle='--', alpha=0.6, label='SOC Mín (10%)')
        
        ax2.set_xlabel('Hora', fontsize=10, fontweight='bold')
        ax2.set_ylabel('SOC (%)', fontsize=10, fontweight='bold')
        ax2.set_title('Estado de Carga BESS', fontsize=11, fontweight='bold')
        ax2.set_ylim([0, 105])
        ax2.legend(fontsize=8, loc='best')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(-0.5, 23.5)
        
        # Estatísticas SOC
        stats_soc = f"Médio: {soc_pct.mean():.1f}%\n"
        stats_soc += f"Mín: {soc_pct.min():.1f}%\n"
        stats_soc += f"Máx: {soc_pct.max():.1f}%"
        ax2.text(0.98, 0.02, stats_soc, transform=ax2.transAxes,
                fontsize=8, verticalalignment='bottom', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        
        # === GRÁFICO 3: Fluxo BESS (Carga/Descarga) ===
        ax3 = fig.add_subplot(gs[1, 0])
        
        bess_fluxo = df['bess_fluxo_kw'].values
        colors = ['cyan' if x < 0 else 'blue' for x in bess_fluxo]
        
        ax3.bar(horas, bess_fluxo, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
        ax3.axhline(y=0, color='black', linewidth=2)
        
        ax3.set_xlabel('Hora', fontsize=10, fontweight='bold')
        ax3.set_ylabel('Potência (kW)', fontsize=10, fontweight='bold')
        ax3.set_title('Fluxo BESS', fontsize=11, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.set_xlim(-0.5, 23.5)
        
        # Anotações
        ax3.text(0.5, 0.95, '+ Descarga', transform=ax3.transAxes, 
                ha='center', va='top', color='blue', fontweight='bold', fontsize=9)
        ax3.text(0.5, 0.05, '- Carga', transform=ax3.transAxes, 
                ha='center', va='bottom', color='cyan', fontweight='bold', fontsize=9)
        
        # Estatísticas BESS
        descarga_total = bess_fluxo[bess_fluxo > 0].sum()
        carga_total = abs(bess_fluxo[bess_fluxo < 0].sum())
        stats_bess = f"Descarga: {descarga_total:.1f} kWh\n"
        stats_bess += f"Carga: {carga_total:.1f} kWh\n"
        stats_bess += f"Eficiência: {(descarga_total/carga_total*100):.1f}%" if carga_total > 0 else "N/A"
        ax3.text(0.02, 0.98, stats_bess, transform=ax3.transAxes,
                fontsize=8, verticalalignment='top', horizontalalignment='left',
                bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.7))
        
        # === GRÁFICO 4: Fluxo com a Rede ===
        ax4 = fig.add_subplot(gs[1, 1])
        
        rede_fluxo = df['rede_fluxo_kw'].values
        colors = ['darkred' if x > 0 else 'green' for x in rede_fluxo]
        
        ax4.bar(horas, rede_fluxo, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
        ax4.axhline(y=0, color='black', linewidth=2)
        
        ax4.set_xlabel('Hora', fontsize=10, fontweight='bold')
        ax4.set_ylabel('Potência (kW)', fontsize=10, fontweight='bold')
        ax4.set_title('Fluxo Rede Elétrica', fontsize=11, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.set_xlim(-0.5, 23.5)
        
        # Anotações
        ax4.text(0.5, 0.95, '+ Importação', transform=ax4.transAxes, 
                ha='center', va='top', color='darkred', fontweight='bold', fontsize=9)
        ax4.text(0.5, 0.05, '- Exportação', transform=ax4.transAxes, 
                ha='center', va='bottom', color='green', fontweight='bold', fontsize=9)
        
        # Estatísticas Rede
        import_total = rede_fluxo[rede_fluxo > 0].sum()
        export_total = abs(rede_fluxo[rede_fluxo < 0].sum())
        stats_rede = f"Importação: {import_total:.1f} kWh\n"
        stats_rede += f"Exportação: {export_total:.1f} kWh\n"
        stats_rede += f"Líquido: {(import_total - export_total):.1f} kWh"
        ax4.text(0.02, 0.98, stats_rede, transform=ax4.transAxes,
                fontsize=8, verticalalignment='top', horizontalalignment='left',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
        
        # === GRÁFICO 5: Custo Horário ===
        ax5 = fig.add_subplot(gs[1, 2])
        
        custo_hora = df['custo_hora'].values
        cores_custo = ['red' if h >= 18 and h < 21 else 'blue' for h in horas]
        
        ax5.bar(horas, custo_hora, color=cores_custo, alpha=0.7, edgecolor='black', linewidth=0.5)
        
        ax5.set_xlabel('Hora', fontsize=10, fontweight='bold')
        ax5.set_ylabel('Custo (R$)', fontsize=10, fontweight='bold')
        ax5.set_title('Custo Horário', fontsize=11, fontweight='bold')
        ax5.grid(True, alpha=0.3, axis='y')
        ax5.set_xlim(-0.5, 23.5)
        
        # Estatísticas Custo
        custo_total_dia = custo_hora.sum()
        custo_ponta = custo_hora[18:21].sum()
        stats_custo = f"Total Dia: R$ {custo_total_dia:.2f}\n"
        stats_custo += f"Ponta (18-21h): R$ {custo_ponta:.2f}\n"
        stats_custo += f"Fora Ponta: R$ {(custo_total_dia - custo_ponta):.2f}\n"
        stats_custo += f"Custo Mensal: R$ {custo_total_dia * 30:.0f}"
        ax5.text(0.98, 0.97, stats_custo, transform=ax5.transAxes,
                fontsize=8, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
        
        # === GRÁFICO 6: Balanço Energético Completo (Grande - ocupa 3 colunas) ===
        ax6 = fig.add_subplot(gs[2, :])
        
        # Empilhar fluxos de energia
        y_pos = np.zeros(24)
        
        # PV Generation (base)
        ax6.fill_between(horas, y_pos, pv_gen, alpha=0.5, color='gold', label='Geração PV', step='mid')
        
        # Demanda (negativo)
        ax6.fill_between(horas, -demanda, 0, alpha=0.4, color='red', label='Demanda', step='mid')
        
        # BESS carga (adicional à demanda)
        bess_carga = np.minimum(0, bess_fluxo)
        ax6.fill_between(horas, -demanda, -demanda + bess_carga, alpha=0.6, color='cyan', 
                        label='BESS Carga', step='mid')
        
        # Exportação para rede
        ax6.fill_between(horas, 0, -np.minimum(0, rede_fluxo), alpha=0.5, color='green', 
                        label='Exportação', step='mid', where=(rede_fluxo < 0))
        
        # Importação da rede (adicional quando PV insuficiente)
        rede_import = np.maximum(0, rede_fluxo)
        ax6.fill_between(horas, 0, rede_import, alpha=0.5, color='darkred', 
                        label='Importação', step='mid', where=(rede_fluxo > 0))
        
        # BESS descarga (reduz importação)
        bess_descarga = np.maximum(0, bess_fluxo)
        
        ax6.axhline(y=0, color='black', linewidth=2)
        ax6.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
        ax6.set_ylabel('Potência (kW)', fontsize=11, fontweight='bold')
        ax6.set_title('Balanço Energético Completo (Acima=Geração, Abaixo=Consumo)', 
                     fontsize=12, fontweight='bold')
        ax6.legend(loc='upper left', fontsize=10, ncol=5)
        ax6.grid(True, alpha=0.3)
        ax6.set_xlim(-0.5, 23.5)
        
        # Destacar ponta
        ax6.axvspan(18, 21, alpha=0.1, color='red')
        
        return fig
    
    def gerar_visualizacoes(self):
        """Gera todas as visualizações dos cenários VPL"""
        print("\n" + "="*100)
        print(" "*25 + "ANÁLISE DETALHADA DE FLUXO DE POTÊNCIA - CENÁRIOS VPL")
        print("="*100)
        
        print("\n📋 Cenários definidos:")
        for nome, info in self.cenarios.items():
            print(f"\n  {nome}:")
            print(f"    PV: {info['pv_kwp']} kWp | BESS: {info['bess_kwh']} kWh")
            print(f"    VPL (10a): R$ {info['vpl']:,.0f}")
            print(f"    Payback: {info['payback_anos']:.1f} anos")
            print(f"    Economia Anual: R$ {info['economia_anual']:,.0f}")
            print(f"    Investimento: R$ {info['investimento']:,.0f}")
        
        print("\n🔄 Simulando cenários...")
        dados_simulados = {}
        
        for nome, info in self.cenarios.items():
            print(f"\n  {nome}:")
            df = self.simular_cenario(info['pv_kwp'], info['bess_kwh'])
            dados_simulados[nome] = df
        
        print("\n📊 Gerando gráficos detalhados...")
        
        arquivos_gerados = []
        
        for nome, df in dados_simulados.items():
            print(f"\n  Gerando análise completa: {nome}...")
            info = self.cenarios[nome]
            
            fig = self.plotar_analise_completa(nome, df, info)
            
            # Salvar figura
            nome_arquivo = f'analise_detalhada_{nome.lower().replace(" ", "_")}.png'
            fig.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
            arquivos_gerados.append(nome_arquivo)
            print(f"    ✓ Salvo: {nome_arquivo}")
            plt.close(fig)
        
        print("\n" + "="*100)
        print(" "*35 + "✅ ANÁLISE CONCLUÍDA")
        print("="*100)
        print(f"\n📁 Arquivos gerados ({len(arquivos_gerados)}):")
        for i, arquivo in enumerate(arquivos_gerados, 1):
            print(f"  {i}. {arquivo}")
        print()


if __name__ == "__main__":
    visualizador = VisualizadorFluxoPotenciaVPL()
    visualizador.gerar_visualizacoes()
