"""
Comparador Genérico de Cenários
Permite comparar uma lista arbitrária de cenários de microrrede.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from caso_ifg import CasoIFG

class Cenario:
    def __init__(self, nome, pv_kwp, bess_kwh, bess_kw, usar_diesel=False, cor='blue'):
        self.nome = nome
        self.pv_kwp = pv_kwp
        self.bess_kwh = bess_kwh
        self.bess_kw = bess_kw
        self.usar_diesel = usar_diesel
        self.cor = cor
        
        # Resultados serão preenchidos após simulação
        self.resultado = None

class ComparadorGenerico:
    def __init__(self, cenarios=None):
        self.cenarios = cenarios if cenarios else []
        self.base_compare_index = 0 # Índice do cenário base para comparações relativas

    def adicionar_cenario(self, cenario):
        self.cenarios.append(cenario)

    def executar_simulacoes(self):
        print("\n" + "="*80)
        print(" INICIANDO SIMULAÇÕES DOS CENÁRIOS")
        print("="*80)
        
        for i, c in enumerate(self.cenarios):
            print(f"\n⚡ Simulando Cenário {i+1}: {c.nome}")
            print(f"   PV: {c.pv_kwp} kWp | BESS: {c.bess_kwh} kWh | Diesel: {c.usar_diesel}")
            
            # Instanciar caso padrão
            # TODO: Permitir configurar distribuidora/modalidade se necessário
            caso = CasoIFG()
            
            # Injetar parâmetros do cenário
            caso.pv_potencia_kwp = c.pv_kwp
            caso.bess_capacidade_kwh = c.bess_kwh
            caso.bess_potencia_kw = c.bess_kw
            caso.usar_diesel = c.usar_diesel
            
            # Reconfigurar PV pois __init__ já o configurou com valores padrão
            caso._configurar_pv()
            
            # Rodar simulação
            c.resultado = caso.simular_mes()
            
            print(f"   => Custo Mensal: R$ {c.resultado['custo_mensal']:,.2f}")

    def gerar_tabela_comparativa(self):
        if not self.cenarios or self.cenarios[0].resultado is None:
            print("Erro: Execute simulações primeiro.")
            return None
            
        base_scenario = self.cenarios[self.base_compare_index]
        base_cost = base_scenario.resultado['custo_mensal']
        
        dados = []
        for c in self.cenarios:
            res = c.resultado
            custo = res['custo_mensal']
            economia = base_cost - custo
            
            # Investimento estimado (Baseado em valores do script original)
            invest_pv = (c.pv_kwp) * 3500 # R$/kWp 
            invest_bess = c.bess_kwh * 1900 # R$/kWh
            investimento = invest_pv + invest_bess 
            
            payback = investimento / (economia * 12) if economia > 0 else float('inf')
            
            dados.append({
                'Cenário': c.nome,
                'PV (kWp)': c.pv_kwp,
                'BESS (kWh)': c.bess_kwh,
                'Custo Mensal (R$)': custo,
                'Economia Mensal (R$)': economia,
                'Economia Anual (R$)': economia * 12,
                'Investimento (R$)': investimento,
                'Payback (anos)': payback
            })
            
        df = pd.DataFrame(dados)
        return df

    def gerar_graficos(self, output_file='comparacao_generica.png'):
        if not self.cenarios or self.cenarios[0].resultado is None:
            return
            
        # Extrair dados
        nomes = [c.nome for c in self.cenarios]
        custos = [c.resultado['custo_mensal'] for c in self.cenarios]
        economias = [(self.cenarios[self.base_compare_index].resultado['custo_mensal'] - c.resultado['custo_mensal']) * 12 for c in self.cenarios]
        cores = [c.cor for c in self.cenarios]
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('Comparativo de Cenários', fontsize=16)
        
        # Gráfico Custo Mensal
        ax1 = axes[0]
        bars1 = ax1.bar(nomes, custos, color=cores)
        ax1.set_title("Custo Mensal de Energia")
        ax1.set_ylabel("R$")
        ax1.grid(True, axis='y', alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=15, ha='right')
        
        # Labels
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                     f'R$ {height/1000:.1f}k', ha='center', va='bottom')
                     
        # Gráfico Economia Anual
        ax2 = axes[1]
        bars2 = ax2.bar(nomes, economias, color=cores)
        ax2.set_title(f"Economia Anual vs {self.cenarios[self.base_compare_index].nome}")
        ax2.set_ylabel("R$ / ano")
        ax2.grid(True, axis='y', alpha=0.3)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=15, ha='right')
        
        for bar in bars2:
            height = bar.get_height()
            if height != 0:
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                         f'R$ {height/1000:.1f}k', ha='center', va='bottom')
                     
        plt.tight_layout()
        plt.savefig(output_file)
        print(f"\nGráfico salvo em: {output_file}")
