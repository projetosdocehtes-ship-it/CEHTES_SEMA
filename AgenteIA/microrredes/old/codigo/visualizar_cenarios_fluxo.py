"""
Visualização de Fluxo de Potência para Cenários Selecionados
============================================================
Gera gráficos detalhados do fluxo de potência horário para:
- Cenário de menor payback
- Cenário de payback médio
- Cenário de maior payback
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from caso_ifg import CasoIFG
import warnings
warnings.filterwarnings('ignore')

class VisualizadorFluxoPotencia:
    def __init__(self, icms=0.17, pis=0.05, aplicar_impostos_exportacao=True):
        self.caso = CasoIFG(
            icms=icms,
            pis=pis,
            aplicar_impostos_exportacao=aplicar_impostos_exportacao
        )
        self.resultados_df = pd.read_csv('analise_sensibilidade_bess_pv_resultados.csv')
        
    def identificar_cenarios(self):
        """Identifica os 3 cenários principais: menor, médio e maior payback"""
        # Remove o cenário base (BESS = 0)
        cenarios = self.resultados_df[self.resultados_df['bess_kwh'] > 0].copy()
        
        # Ordena por payback
        cenarios_ordenados = cenarios.sort_values('payback_anos')
        
        # Seleciona os cenários
        menor_payback = cenarios_ordenados.iloc[0]
        maior_payback = cenarios_ordenados.iloc[-1]
        
        # Payback médio (cenário do meio)
        idx_medio = len(cenarios_ordenados) // 2
        payback_medio = cenarios_ordenados.iloc[idx_medio]
        
        cenarios_selecionados = {
            'Menor Payback': menor_payback,
            'Payback Médio': payback_medio,
            'Maior Payback': maior_payback
        }
        
        print("\n" + "="*100)
        print("CENÁRIOS SELECIONADOS PARA ANÁLISE DE FLUXO DE POTÊNCIA")
        print("="*100)
        
        for nome, cenario in cenarios_selecionados.items():
            print(f"\n{nome}:")
            print(f"  PV: {cenario['pv_kwp']:.0f} kWp | BESS: {cenario['bess_kwh']:.0f} kWh")
            print(f"  Payback: {cenario['payback_anos']:.1f} anos")
            print(f"  Economia: R$ {cenario['economia_anual']:,.2f}/ano")
            print(f"  Investimento: R$ {cenario['investimento']:,.2f}")
        
        return cenarios_selecionados
    
    def simular_cenario(self, pv_kwp, bess_kwh):
        """Simula um cenário e retorna os dados horários"""
        # Configura o sistema
        self.caso.pv_potencia_kwp = pv_kwp
        self.caso.bess_capacidade_kwh = bess_kwh
        
        # Reconfigura o PV com nova potência
        self.caso._configurar_pv()
        
        # Simula um dia útil (retorna dados horários)
        resultado_dia = self.caso.simular_dia(dia_semana=0)
        
        # Converte para DataFrame
        df = pd.DataFrame({
            'demanda_kw': resultado_dia['demanda_kw'],
            'pv_geracao_kw': resultado_dia['geracao_pv_kw'],
            'bess_fluxo_kw': resultado_dia['potencia_bess_kw'],
            'bess_soc': [soc / bess_kwh * 100 for soc in resultado_dia['soc_bess_kwh']],  # Converter para %
            'rede_fluxo_kw': resultado_dia['energia_rede_kw'],
        })
        
        df['hora'] = range(len(df))
        
        return df
    
    def plotar_fluxo_potencia(self, df, titulo, ax):
        """Plota o fluxo de potência em um subplot"""
        horas = df['hora'].values
        
        # Dados de fluxo
        pv_geracao = df['pv_geracao_kw'].values
        carga = df['demanda_kw'].values
        bess_carga = np.maximum(0, df['bess_fluxo_kw'].values)  # Positivo = carregando
        bess_descarga = np.maximum(0, -df['bess_fluxo_kw'].values)  # Negativo = descarregando
        rede_importa = np.maximum(0, df['rede_fluxo_kw'].values)  # Positivo = importando
        rede_exporta = np.maximum(0, -df['rede_fluxo_kw'].values)  # Negativo = exportando
        
        # Plot
        ax.fill_between(horas, 0, carga, alpha=0.3, color='red', label='Carga')
        ax.plot(horas, carga, color='red', linewidth=2, label='Demanda')
        
        ax.fill_between(horas, 0, pv_geracao, alpha=0.5, color='gold', label='Geração PV')
        ax.plot(horas, pv_geracao, color='orange', linewidth=1.5)
        
        # BESS
        ax.plot(horas, bess_carga, color='blue', linewidth=1.5, linestyle='--', label='BESS Carregando')
        ax.plot(horas, bess_descarga, color='cyan', linewidth=1.5, linestyle='--', label='BESS Descarregando')
        
        # Rede
        ax.plot(horas, rede_importa, color='darkred', linewidth=1.5, linestyle=':', label='Importação Rede')
        ax.plot(horas, rede_exporta, color='green', linewidth=1.5, linestyle=':', label='Exportação Rede')
        
        # Linha zero
        ax.axhline(y=0, color='black', linewidth=0.5, linestyle='-', alpha=0.3)
        
        # Formatação
        ax.set_xlabel('Hora', fontsize=10)
        ax.set_ylabel('Potência (kW)', fontsize=10)
        ax.set_title(titulo, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper left', fontsize=8, ncol=2)
        
        # Estatísticas
        stats_text = f"PV Máx: {pv_geracao.max():.0f} kW\n"
        stats_text += f"Carga Máx: {carga.max():.0f} kW\n"
        stats_text += f"Import Máx: {rede_importa.max():.0f} kW\n"
        stats_text += f"Export Máx: {rede_exporta.max():.0f} kW"
        
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
                fontsize=8, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    def plotar_soc_bess(self, df, titulo, ax):
        """Plota o estado de carga do BESS"""
        horas = df['hora'].values
        soc = df['bess_soc'].values
        
        ax.fill_between(horas, 0, soc, alpha=0.4, color='blue')
        ax.plot(horas, soc, color='darkblue', linewidth=2, label='SOC BESS')
        
        # Linha de 100%
        ax.axhline(y=100, color='green', linewidth=1, linestyle='--', alpha=0.5, label='100%')
        ax.axhline(y=20, color='red', linewidth=1, linestyle='--', alpha=0.5, label='20% (mínimo)')
        
        ax.set_xlabel('Hora', fontsize=10)
        ax.set_ylabel('Estado de Carga (%)', fontsize=10)
        ax.set_title(f'{titulo} - Estado de Carga BESS', fontsize=11, fontweight='bold')
        ax.set_ylim([0, 105])
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=8)
        
        # Estatísticas
        stats_text = f"SOC Médio: {soc.mean():.1f}%\n"
        stats_text += f"SOC Mín: {soc.min():.1f}%\n"
        stats_text += f"SOC Máx: {soc.max():.1f}%"
        
        ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
                fontsize=8, verticalalignment='bottom', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    
    def gerar_visualizacoes(self):
        """Gera todas as visualizações"""
        print("\n🔍 Identificando cenários...")
        cenarios = self.identificar_cenarios()
        
        print("\n🔄 Simulando cenários...")
        dados_simulados = {}
        for nome, info in cenarios.items():
            pv = info['pv_kwp']
            bess = info['bess_kwh']
            print(f"  Simulando: {nome} (PV {pv:.0f} kWp + BESS {bess:.0f} kWh)...")
            dados_simulados[nome] = self.simular_cenario(pv, bess)
        
        # === GRÁFICO 1: Fluxo de Potência ===
        print("\n📊 Gerando gráficos de fluxo de potência...")
        fig1, axes = plt.subplots(3, 1, figsize=(16, 12))
        fig1.suptitle('ANÁLISE DE FLUXO DE POTÊNCIA - COMPARAÇÃO DE CENÁRIOS', 
                      fontsize=16, fontweight='bold', y=0.995)
        
        for idx, (nome, df) in enumerate(dados_simulados.items()):
            info = cenarios[nome]
            titulo = f"{nome}: PV {info['pv_kwp']:.0f} kWp + BESS {info['bess_kwh']:.0f} kWh (Payback: {info['payback_anos']:.1f} anos)"
            self.plotar_fluxo_potencia(df, titulo, axes[idx])
        
        plt.tight_layout()
        filename1 = 'fluxo_potencia_comparacao_cenarios.png'
        plt.savefig(filename1, dpi=300, bbox_inches='tight')
        print(f"✓ Gráfico salvo: {filename1}")
        
        # === GRÁFICO 2: Estado de Carga BESS ===
        print("\n🔋 Gerando gráficos de estado de carga BESS...")
        fig2, axes = plt.subplots(3, 1, figsize=(16, 10))
        fig2.suptitle('ESTADO DE CARGA DO BESS - COMPARAÇÃO DE CENÁRIOS', 
                      fontsize=16, fontweight='bold', y=0.995)
        
        for idx, (nome, df) in enumerate(dados_simulados.items()):
            info = cenarios[nome]
            titulo = f"{nome}: BESS {info['bess_kwh']:.0f} kWh"
            self.plotar_soc_bess(df, titulo, axes[idx])
        
        plt.tight_layout()
        filename2 = 'soc_bess_comparacao_cenarios.png'
        plt.savefig(filename2, dpi=300, bbox_inches='tight')
        print(f"✓ Gráfico salvo: {filename2}")
        
        # === GRÁFICO 3: Detalhes por Cenário (3 subplots lado a lado) ===
        print("\n📈 Gerando análise detalhada individual...")
        
        for nome, df in dados_simulados.items():
            info = cenarios[nome]
            
            fig3, axes = plt.subplots(1, 3, figsize=(20, 6))
            fig3.suptitle(f'ANÁLISE DETALHADA: {nome}\n' + 
                         f'PV {info["pv_kwp"]:.0f} kWp + BESS {info["bess_kwh"]:.0f} kWh | ' +
                         f'Payback: {info["payback_anos"]:.1f} anos | ' +
                         f'Economia: R$ {info["economia_anual"]:,.2f}/ano',
                         fontsize=14, fontweight='bold')
            
            # Subplot 1: Fluxo de potência
            horas = df['hora'].values
            pv_gen = pd.to_numeric(df['pv_geracao_kw'], errors='coerce').fillna(0).values
            demanda = pd.to_numeric(df['demanda_kw'], errors='coerce').fillna(0).values
            
            axes[0].plot(horas, pv_gen, color='orange', linewidth=2, label='Geração PV')
            axes[0].plot(horas, demanda, color='red', linewidth=2, label='Demanda')
            axes[0].fill_between(horas, 0, pv_gen, alpha=0.3, color='gold')
            axes[0].fill_between(horas, 0, demanda, alpha=0.2, color='red')
            axes[0].set_xlabel('Hora')
            axes[0].set_ylabel('Potência (kW)')
            axes[0].set_title('Geração PV vs Demanda')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # Subplot 2: Fluxo BESS
            bess_fluxo = pd.to_numeric(df['bess_fluxo_kw'], errors='coerce').fillna(0).values
            colors = ['blue' if x > 0 else 'cyan' for x in bess_fluxo]
            axes[1].bar(horas, bess_fluxo, color=colors, alpha=0.6, label='Fluxo BESS')
            axes[1].axhline(y=0, color='black', linewidth=1)
            axes[1].set_xlabel('Hora')
            axes[1].set_ylabel('Potência (kW)')
            axes[1].set_title('Fluxo BESS (+ = Descarga, - = Carga)')
            axes[1].grid(True, alpha=0.3)
            axes[1].text(0.5, 0.95, 'Descarga (+)', transform=axes[1].transAxes, 
                        ha='center', color='blue', fontweight='bold')
            axes[1].text(0.5, 0.05, 'Carga (-)', transform=axes[1].transAxes, 
                        ha='center', color='cyan', fontweight='bold')
            
            # Subplot 3: Fluxo com a rede
            rede_fluxo = pd.to_numeric(df['rede_fluxo_kw'], errors='coerce').fillna(0).values
            colors = ['darkred' if x > 0 else 'green' for x in rede_fluxo]
            axes[2].bar(horas, rede_fluxo, color=colors, alpha=0.6)
            axes[2].axhline(y=0, color='black', linewidth=1)
            axes[2].set_xlabel('Hora')
            axes[2].set_ylabel('Potência (kW)')
            axes[2].set_title('Fluxo Rede (+ = Importa, - = Exporta)')
            axes[2].grid(True, alpha=0.3)
            axes[2].text(0.5, 0.95, 'Importação (+)', transform=axes[2].transAxes, 
                        ha='center', color='darkred', fontweight='bold')
            axes[2].text(0.5, 0.05, 'Exportação (-)', transform=axes[2].transAxes, 
                        ha='center', color='green', fontweight='bold')
            
            plt.tight_layout()
            filename3 = f'analise_detalhada_{nome.lower().replace(" ", "_")}.png'
            plt.savefig(filename3, dpi=300, bbox_inches='tight')
            print(f"✓ Gráfico detalhado salvo: {filename3}")
        
        print("\n" + "="*100)
        print("✅ VISUALIZAÇÕES CONCLUÍDAS")
        print("="*100)
        print(f"\nArquivos gerados:")
        print(f"  1. fluxo_potencia_comparacao_cenarios.png - Comparação de fluxo de potência")
        print(f"  2. soc_bess_comparacao_cenarios.png - Estados de carga BESS")
        print(f"  3. analise_detalhada_menor_payback.png - Análise detalhada menor payback")
        print(f"  4. analise_detalhada_payback_médio.png - Análise detalhada payback médio")
        print(f"  5. analise_detalhada_maior_payback.png - Análise detalhada maior payback")
        print("\n")


if __name__ == "__main__":
    visualizador = VisualizadorFluxoPotencia()
    visualizador.gerar_visualizacoes()
