"""
Análise de Sensibilidade: BESS vs PV para o IFG
Simula fluxo de potência para diferentes configurações
Métricas: Payback e Economia Anual vs Cenário Base
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from caso_ifg import CasoIFG
import itertools
from tqdm import tqdm

class AnalisadorSensibilidadeBESSPV:
    """Analisa impacto de diferentes tamanhos de BESS e PV"""
    
    def __init__(self):
        self.distribuidora = 'EQUATORIAL GO'
        self.modalidade = 'verde'
        self.resultados = []
        
        # Cenário base
        self.pv_base_kwp = 324  # PV existente (real do IFG)
        self.bess_base_kwh = 0   # Sem BESS
        self.custo_base = None
        
        # Custos de investimento (R$/unidade)
        self.custo_pv_kwp = 3000         # R$ 3.000/kWp instalado
        self.custo_bess_kwh = 310*1000.0/138       # R$ 1.900/kWh (sistema completo)
        
        # Tarifa de demanda
        self.tarifa_demanda_kw = 26.08   # R$/kW/mês
        
        # Parâmetros para análise de VPL
        self.taxa_desconto = 0.10        # 10% a.a. (SELIC média histórica)
        self.horizonte_anos = 10         # Horizonte de análise
        self.taxa_inflacao = 0.05        # 5% a.a. (inflação esperada)
        
    def simular_cenario_base(self):
        """Simula cenário base (PV 324 kWp, sem BESS)"""
        print("\n" + "="*100)
        print(" "*30 + "SIMULANDO CENÁRIO BASE")
        print("="*100)
        print(f"  PV: {self.pv_base_kwp} kWp (existente)")
        print(f"  BESS: {self.bess_base_kwh} kWh (sem bateria)")
        
        caso_base = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso_base.pv_potencia_kwp = self.pv_base_kwp
        caso_base.bess_capacidade_kwh = self.bess_base_kwh
        caso_base.usar_diesel = False
        caso_base._configurar_pv()
        
        resultado_base = caso_base.simular_mes()
        self.custo_base = resultado_base['custo_mensal']
        self.energia_comprada_base = resultado_base['energia_comprada_kwh']
        self.energia_vendida_base = resultado_base['energia_vendida_kwh']
        
        # Calcular demanda máxima do cenário base
        self.demanda_base_kw = self._calcular_demanda_maxima(resultado_base)
        
        print(f"\n📊 RESULTADO BASE:")
        print(f"  Custo mensal:          R$ {self.custo_base:,.2f}")
        print(f"  Custo anual:           R$ {self.custo_base * 12:,.2f}")
        print(f"  Demanda máxima:        {self.demanda_base_kw:.0f} kW")
        print(f"  Energia comprada:      {resultado_base['energia_comprada_kwh']:,.0f} kWh/mês")
        print(f"  Energia vendida:       {resultado_base['energia_vendida_kwh']:,.0f} kWh/mês")
        
        return {
            'pv_kwp': self.pv_base_kwp,
            'bess_kwh': self.bess_base_kwh,
            'custo_mensal': self.custo_base,
            'custo_anual': self.custo_base * 12,
            'demanda_max_kw': self.demanda_base_kw,
            'energia_comprada': resultado_base['energia_comprada_kwh'],
            'energia_vendida': resultado_base['energia_vendida_kwh'],
            'investimento': 0,
            'economia_anual': 0,
            'payback_anos': 0,
            'vpl_10anos': 0,
            'tir': 0,
            'tipo': 'Base'
        }
    
    def _calcular_demanda_maxima(self, resultado_simulacao):
        """Extrai demanda máxima do resultado da simulação"""
        # A demanda máxima já vem no resultado da simulação do CasoIFG
        return resultado_simulacao.get('demanda_maxima_kw', 0)
    
    def _calcular_vpl(self, investimento_inicial, economia_anual):
        """Calcula o Valor Presente Líquido (VPL) para o horizonte de análise"""
        vpl = -investimento_inicial  # Investimento inicial é negativo
        
        for ano in range(1, self.horizonte_anos + 1):
            # Economia crescendo com a inflação
            economia_ano = economia_anual * ((1 + self.taxa_inflacao) ** (ano - 1))
            
            # Valor presente da economia do ano
            valor_presente = economia_ano / ((1 + self.taxa_desconto) ** ano)
            vpl += valor_presente
        
        return vpl
    
    def _calcular_tir(self, investimento_inicial, economia_anual):
        """Calcula a Taxa Interna de Retorno (TIR) aproximada"""
        if investimento_inicial <= 0:
            return 0
        
        # Fluxo de caixa simplificado
        fluxos = [-investimento_inicial]
        for ano in range(1, self.horizonte_anos + 1):
            economia_ano = economia_anual * ((1 + self.taxa_inflacao) ** (ano - 1))
            fluxos.append(economia_ano)
        
        # Usar numpy para calcular TIR
        try:
            tir = np.irr(fluxos)
            return tir if not np.isnan(tir) else 0
        except:
            return 0
    
    def simular_cenario(self, pv_kwp, bess_kwh, descricao=""):
        """Simula um cenário específico e calcula métricas"""
        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = pv_kwp
        caso.bess_capacidade_kwh = bess_kwh
        caso.usar_diesel = False
        caso._configurar_pv()
        
        resultado = caso.simular_mes()
        custo_mensal = resultado['custo_mensal']
        
        # Calcular demanda máxima
        demanda_max_kw = self._calcular_demanda_maxima(resultado)
        
        # Economia com redução de demanda contratada
        reducao_demanda_kw = max(0, self.demanda_base_kw - demanda_max_kw)
        economia_demanda_mensal = reducao_demanda_kw * self.tarifa_demanda_kw
        economia_demanda_anual = economia_demanda_mensal * 12
        
        # Economia de energia - calculada pela diferença de custo mensal
        energia_comprada = resultado['energia_comprada_kwh']
        energia_vendida = resultado['energia_vendida_kwh']
        
        # Variação na exportação (apenas para informação)
        variacao_exportacao_kwh = energia_vendida - self.energia_vendida_base
        
        # Economia total na energia = diferença de custo mensal
        # IMPORTANTE: custo_mensal JÁ inclui receita de exportação calculada hora a hora
        # com as tarifas SCEE corretas (ponta/fora ponta), então NÃO precisamos
        # fazer nenhum cálculo adicional com tarifa média
        economia_energia_mensal = self.custo_base - custo_mensal
        economia_energia_anual = economia_energia_mensal * 12
        
        # Economia total
        economia_total_anual = economia_energia_anual + economia_demanda_anual
        
        # Investimento incremental
        investimento_pv = max(0, pv_kwp - self.pv_base_kwp) * self.custo_pv_kwp
        investimento_bess = bess_kwh * self.custo_bess_kwh
        investimento_total = investimento_pv + investimento_bess
        
        # Payback
        if economia_total_anual > 0:
            payback_anos = investimento_total / economia_total_anual
        else:
            payback_anos = 999
        
        # Cálculo do VPL (Valor Presente Líquido)
        vpl = self._calcular_vpl(investimento_total, economia_total_anual)
        tir = self._calcular_tir(investimento_total, economia_total_anual)
        
        return {
            'pv_kwp': pv_kwp,
            'bess_kwh': bess_kwh,
            'descricao': descricao,
            'custo_mensal': custo_mensal,
            'custo_anual': custo_mensal * 12,
            'demanda_max_kw': demanda_max_kw,
            'reducao_demanda_kw': reducao_demanda_kw,
            'economia_demanda_anual': economia_demanda_anual,
            'economia_energia_anual': economia_energia_anual,
            'economia_total_anual': economia_total_anual,
            'energia_comprada': energia_comprada,
            'energia_vendida': energia_vendida,
            'variacao_exportacao_kwh': variacao_exportacao_kwh,
            'investimento_pv': investimento_pv,
            'investimento_bess': investimento_bess,
            'investimento_total': investimento_total,
            'payback_anos': payback_anos,
            'vpl_10anos': vpl,
            'tir': tir,
            'tipo': 'Cenário'
        }
    
    def executar_analise_completa(self):
        """Executa análise de sensibilidade completa"""
        print("\n" + "="*100)
        print(" "*20 + "ANÁLISE DE SENSIBILIDADE: BESS E FOTOVOLTAICO - CASO IFG")
        print("="*100)
        
        # Simular cenário base
        resultado_base = self.simular_cenario_base()
        self.resultados.append(resultado_base)
        
        # Definir variações
        # BESS: 30, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500 kWh
        tamanhos_bess = [30, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
        
        # PV: 324 (base - existente), 400, 450, 500, 550, 600 kWp
        tamanhos_pv = [324, 400, 450, 500, 550, 600]
        
        print(f"\n🔬 CONFIGURAÇÃO DA ANÁLISE:")
        print(f"  Tamanhos de BESS: {tamanhos_bess}")
        print(f"  Capacidades PV: {tamanhos_pv}")
        print(f"  Total de cenários: {len(tamanhos_bess) * len(tamanhos_pv)}")
        
        # Simular todas as combinações
        total_cenarios = len(tamanhos_bess) * len(tamanhos_pv)
        print(f"\n⚙️  Simulando {total_cenarios} cenários...")
        
        contador = 0
        for pv_kwp in tamanhos_pv:
            for bess_kwh in tamanhos_bess:
                contador += 1
                descricao = f"PV {pv_kwp} kWp + BESS {bess_kwh} kWh"
                
                print(f"  [{contador:>3}/{total_cenarios}] Simulando: PV={pv_kwp:>4} kWp | BESS={bess_kwh:>4} kWh  ...", end=' ', flush=True)
                
                resultado = self.simular_cenario(pv_kwp, bess_kwh, descricao)
                self.resultados.append(resultado)
                
                print(f"OK  | Custo: R$ {resultado['custo_mensal']:>8,.0f}/mês | "
                      f"Economia: R$ {resultado['economia_total_anual']:>8,.0f}/ano | "
                      f"Payback: {resultado['payback_anos']:>5.1f} a")
        
        print(f"\n✓ Simulações concluídas!")
        
        # Converter para DataFrame
        self.df_resultados = pd.DataFrame(self.resultados)
        
        # Salvar resultados
        self.df_resultados.to_csv('analise_sensibilidade_bess_pv_resultados.csv', index=False)
        print(f"\n💾 Resultados salvos em: analise_sensibilidade_bess_pv_resultados.csv")
    
    def gerar_relatorio(self):
        """Gera relatório com melhores cenários"""
        print("\n\n" + "="*100)
        print(" "*30 + "ANÁLISE DE RESULTADOS")
        print("="*100)
        
        # Filtrar apenas cenários (excluir base)
        df_cenarios = self.df_resultados[self.df_resultados['tipo'] == 'Cenário'].copy()
        
        # Top 10 melhores paybacks
        print(f"\n🏆 TOP 10 CENÁRIOS - MENOR PAYBACK:")
        print("-"*120)
        print(f"{'Rank':<5} {'PV (kWp)':<10} {'BESS (kWh)':<12} {'Investimento':<15} {'Economia/ano':<15} {'Payback':<12} {'VPL (10a)':<15}")
        print("-"*120)
        
        top_payback = df_cenarios.nsmallest(10, 'payback_anos')
        for idx, (i, row) in enumerate(top_payback.iterrows(), 1):
            print(f"{idx:<5} {row['pv_kwp']:<10.0f} {row['bess_kwh']:<12.0f} "
                  f"R$ {row['investimento_total']:>10,.0f}  "
                  f"R$ {row['economia_total_anual']:>11,.0f}  "
                  f"{row['payback_anos']:>7.1f} a  "
                  f"R$ {row['vpl_10anos']:>11,.0f}")
        
        # Top 10 maiores economias anuais
        print(f"\n\n💰 TOP 10 CENÁRIOS - MAIOR ECONOMIA ANUAL:")
        print("-"*120)
        print(f"{'Rank':<5} {'PV (kWp)':<10} {'BESS (kWh)':<12} {'Investimento':<15} {'Economia/ano':<15} {'Payback':<12} {'VPL (10a)':<15}")
        print("-"*120)
        
        top_economia = df_cenarios.nsmallest(10, 'payback_anos')  # Melhores paybacks geralmente = maiores economias
        top_economia = df_cenarios.nlargest(10, 'economia_total_anual')
        for idx, (i, row) in enumerate(top_economia.iterrows(), 1):
            print(f"{idx:<5} {row['pv_kwp']:<10.0f} {row['bess_kwh']:<12.0f} "
                  f"R$ {row['investimento_total']:>10,.0f}  "
                  f"R$ {row['economia_total_anual']:>11,.0f}  "
                  f"{row['payback_anos']:>7.1f} a  "
                  f"R$ {row['vpl_10anos']:>11,.0f}")
        
        # Top 10 maiores VPLs
        print(f"\n\n💎 TOP 10 CENÁRIOS - MAIOR VPL (10 ANOS):")
        print("-"*120)
        print(f"{'Rank':<5} {'PV (kWp)':<10} {'BESS (kWh)':<12} {'Investimento':<15} {'VPL (10a)':<15} {'TIR':<10} {'Payback':<12}")
        print("-"*120)
        
        top_vpl = df_cenarios.nlargest(10, 'vpl_10anos')
        for idx, (i, row) in enumerate(top_vpl.iterrows(), 1):
            print(f"{idx:<5} {row['pv_kwp']:<10.0f} {row['bess_kwh']:<12.0f} "
                  f"R$ {row['investimento_total']:>10,.0f}  "
                  f"R$ {row['vpl_10anos']:>11,.0f}  "
                  f"{row['tir']*100:>6.1f}%  "
                  f"{row['payback_anos']:>7.1f} a")
        
        # Análise por capacidade de BESS (fixando PV = 324)
        print(f"\n\n🔋 IMPACTO DO TAMANHO DO BESS (PV fixo em 324 kWp - BASE EXISTENTE):")
        print("-"*100)
        print(f"{'BESS (kWh)':<12} {'Investimento':<15} {'Economia/ano':<15} {'Payback':<12} {'Redução Demanda':<18}")
        print("-"*100)
        
        df_bess_324 = df_cenarios[df_cenarios['pv_kwp'] == 324].sort_values('bess_kwh')
        for i, row in df_bess_324.iterrows():
            print(f"{row['bess_kwh']:<12.0f} "
                  f"R$ {row['investimento_total']:>10,.0f}  "
                  f"R$ {row['economia_total_anual']:>11,.0f}  "
                  f"{row['payback_anos']:>7.1f} anos  "
                  f"{row['reducao_demanda_kw']:>6.0f} kW")
        
        # Análise por capacidade de PV (fixando BESS = 0 - sem bateria)
        print(f"\n\n☀️  IMPACTO DA EXPANSÃO PV (sem BESS):")
        print("-"*100)
        print(f"{'PV (kWp)':<10} {'Investimento':<15} {'Economia/ano':<15} {'Payback':<12} {'Redução Demanda':<18}")
        print("-"*100)
        
        df_pv_0 = df_cenarios[df_cenarios['bess_kwh'] == 0].sort_values('pv_kwp')
        for i, row in df_pv_0.iterrows():
            print(f"{row['pv_kwp']:<10.0f} "
                  f"R$ {row['investimento_total']:>10,.0f}  "
                  f"R$ {row['economia_total_anual']:>11,.0f}  "
                  f"{row['payback_anos']:>7.1f} anos  "
                  f"{row['reducao_demanda_kw']:>6.0f} kW")
        
        # Análise por capacidade de PV (fixando BESS = 200)
        print(f"\n\n☀️  IMPACTO DA EXPANSÃO PV (BESS fixo em 200 kWh):")
        print("-"*100)
        print(f"{'PV (kWp)':<10} {'Investimento':<15} {'Economia/ano':<15} {'Payback':<12} {'Redução Demanda':<18}")
        print("-"*100)
        
        df_pv_200 = df_cenarios[df_cenarios['bess_kwh'] == 200].sort_values('pv_kwp')
        for i, row in df_pv_200.iterrows():
            print(f"{row['pv_kwp']:<10.0f} "
                  f"R$ {row['investimento_total']:>10,.0f}  "
                  f"R$ {row['economia_total_anual']:>11,.0f}  "
                  f"{row['payback_anos']:>7.1f} anos  "
                  f"{row['reducao_demanda_kw']:>6.0f} kW")
        
        # Recomendação final
        melhor_cenario = df_cenarios.loc[df_cenarios['payback_anos'].idxmin()]
        
        print(f"\n\n⭐ RECOMENDAÇÃO FINAL:")
        print("-"*100)
        print(f"\n  Melhor configuração (menor payback):")
        print(f"    PV:                    {melhor_cenario['pv_kwp']:.0f} kWp")
        print(f"    BESS:                  {melhor_cenario['bess_kwh']:.0f} kWh")
        print(f"    Investimento:          R$ {melhor_cenario['investimento_total']:,.2f}")
        print(f"    Economia anual:        R$ {melhor_cenario['economia_total_anual']:,.2f}")
        print(f"      - Energia:           R$ {melhor_cenario['economia_energia_anual']:,.2f}")
        print(f"      - Demanda:           R$ {melhor_cenario['economia_demanda_anual']:,.2f}")
        print(f"    Payback:               {melhor_cenario['payback_anos']:.1f} anos")
        print(f"    VPL (10 anos):         R$ {melhor_cenario['vpl_10anos']:,.2f}")
        print(f"    TIR:                   {melhor_cenario['tir']*100:.2f}%")
        print(f"    Redução de demanda:    {melhor_cenario['reducao_demanda_kw']:.0f} kW")
        
        # Melhor cenário por VPL
        melhor_vpl = df_cenarios.loc[df_cenarios['vpl_10anos'].idxmax()]
        print(f"\n  Melhor configuração (maior VPL):")
        print(f"    PV:                    {melhor_vpl['pv_kwp']:.0f} kWp")
        print(f"    BESS:                  {melhor_vpl['bess_kwh']:.0f} kWh")
        print(f"    Investimento:          R$ {melhor_vpl['investimento_total']:,.2f}")
        print(f"    VPL (10 anos):         R$ {melhor_vpl['vpl_10anos']:,.2f}")
        print(f"    TIR:                   {melhor_vpl['tir']*100:.2f}%")
        print(f"    Economia anual:        R$ {melhor_vpl['economia_total_anual']:,.2f}")
        print(f"    Payback:               {melhor_vpl['payback_anos']:.1f} anos")
    
    def gerar_graficos(self):
        """Gera gráficos de análise de sensibilidade"""
        df_cenarios = self.df_resultados[self.df_resultados['tipo'] == 'Cenário'].copy()
        
        fig = plt.figure(figsize=(20, 16))
        
        # Gráfico 1: Payback vs Tamanho BESS (para cada PV)
        ax1 = plt.subplot(3, 3, 1)
        
        for pv in sorted(df_cenarios['pv_kwp'].unique()):
            df_pv = df_cenarios[df_cenarios['pv_kwp'] == pv].sort_values('bess_kwh')
            ax1.plot(df_pv['bess_kwh'], df_pv['payback_anos'], 
                    'o-', label=f'PV {pv:.0f} kWp', linewidth=2, markersize=6)
        
        ax1.set_xlabel('Capacidade BESS (kWh)', fontsize=11)
        ax1.set_ylabel('Payback (anos)', fontsize=11)
        ax1.set_title('Payback vs Tamanho do BESS', fontweight='bold', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(bottom=0)
        
        # Gráfico 2: Economia Anual vs BESS
        ax2 = plt.subplot(3, 3, 2)
        
        for pv in sorted(df_cenarios['pv_kwp'].unique()):
            df_pv = df_cenarios[df_cenarios['pv_kwp'] == pv].sort_values('bess_kwh')
            ax2.plot(df_pv['bess_kwh'], df_pv['economia_total_anual']/1000, 
                    'o-', label=f'PV {pv:.0f} kWp', linewidth=2, markersize=6)
        
        ax2.set_xlabel('Capacidade BESS (kWh)', fontsize=11)
        ax2.set_ylabel('Economia Anual (R$ mil)', fontsize=11)
        ax2.set_title('Economia Anual vs Tamanho do BESS', fontweight='bold', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Gráfico 3: Mapa de calor - Payback
        ax3 = plt.subplot(3, 3, 3)
        
        pivot_payback = df_cenarios.pivot(index='bess_kwh', columns='pv_kwp', values='payback_anos')
        im3 = ax3.imshow(pivot_payback.values, cmap='RdYlGn_r', aspect='auto')
        
        ax3.set_xticks(range(len(pivot_payback.columns)))
        ax3.set_xticklabels([f'{int(x)}' for x in pivot_payback.columns])
        ax3.set_yticks(range(len(pivot_payback.index)))
        ax3.set_yticklabels([f'{int(x)}' for x in pivot_payback.index])
        
        ax3.set_xlabel('Capacidade PV (kWp)', fontsize=11)
        ax3.set_ylabel('Capacidade BESS (kWh)', fontsize=11)
        ax3.set_title('Mapa de Calor: Payback (anos)', fontweight='bold', fontsize=12)
        
        plt.colorbar(im3, ax=ax3, label='Payback (anos)')
        
        # Adicionar valores nas células
        for i in range(len(pivot_payback.index)):
            for j in range(len(pivot_payback.columns)):
                val = pivot_payback.values[i, j]
                if not np.isnan(val):
                    ax3.text(j, i, f'{val:.1f}', ha='center', va='center', 
                           color='white' if val > 10 else 'black', fontsize=8)
        
        # Gráfico 4: Investimento vs Economia
        ax4 = plt.subplot(3, 3, 4)
        
        scatter = ax4.scatter(df_cenarios['investimento_total']/1000, 
                             df_cenarios['economia_total_anual']/1000,
                             c=df_cenarios['payback_anos'], 
                             s=df_cenarios['bess_kwh']*0.5,
                             cmap='viridis', alpha=0.6, edgecolors='black')
        
        ax4.set_xlabel('Investimento (R$ mil)', fontsize=11)
        ax4.set_ylabel('Economia Anual (R$ mil)', fontsize=11)
        ax4.set_title('Investimento vs Economia (tamanho = BESS)', fontweight='bold', fontsize=12)
        ax4.grid(True, alpha=0.3)
        
        plt.colorbar(scatter, ax=ax4, label='Payback (anos)')
        
        # Gráfico 5: Redução de Demanda vs BESS
        ax5 = plt.subplot(3, 3, 5)
        
        for pv in sorted(df_cenarios['pv_kwp'].unique()):
            df_pv = df_cenarios[df_cenarios['pv_kwp'] == pv].sort_values('bess_kwh')
            ax5.plot(df_pv['bess_kwh'], df_pv['reducao_demanda_kw'], 
                    'o-', label=f'PV {pv:.0f} kWp', linewidth=2, markersize=6)
        
        ax5.set_xlabel('Capacidade BESS (kWh)', fontsize=11)
        ax5.set_ylabel('Redução de Demanda (kW)', fontsize=11)
        ax5.set_title('Redução de Demanda Contratada vs BESS', fontweight='bold', fontsize=12)
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # Gráfico 6: Economia de Energia vs Demanda
        ax6 = plt.subplot(3, 3, 6)
        
        ax6.scatter(df_cenarios['economia_energia_anual']/1000, 
                   df_cenarios['economia_demanda_anual']/1000,
                   c=df_cenarios['payback_anos'],
                   s=100, cmap='plasma', alpha=0.7, edgecolors='black')
        
        ax6.set_xlabel('Economia de Energia (R$ mil/ano)', fontsize=11)
        ax6.set_ylabel('Economia de Demanda (R$ mil/ano)', fontsize=11)
        ax6.set_title('Decomposição da Economia', fontweight='bold', fontsize=12)
        ax6.grid(True, alpha=0.3)
        
        # Linha diagonal
        max_val = max(df_cenarios['economia_energia_anual'].max(), 
                     df_cenarios['economia_demanda_anual'].max()) / 1000
        ax6.plot([0, max_val], [0, max_val], 'k--', alpha=0.3)
        
        # Gráfico 7: VPL vs Tamanho BESS
        ax7 = plt.subplot(3, 3, 7)
        
        for pv in sorted(df_cenarios['pv_kwp'].unique()):
            df_pv = df_cenarios[df_cenarios['pv_kwp'] == pv].sort_values('bess_kwh')
            ax7.plot(df_pv['bess_kwh'], df_pv['vpl_10anos']/1000, 
                    'o-', label=f'PV {pv:.0f} kWp', linewidth=2, markersize=6)
        
        ax7.set_xlabel('Capacidade BESS (kWh)', fontsize=11)
        ax7.set_ylabel('VPL 10 anos (R$ mil)', fontsize=11)
        ax7.set_title('VPL vs Tamanho do BESS', fontweight='bold', fontsize=12)
        ax7.legend(fontsize=8)
        ax7.grid(True, alpha=0.3)
        ax7.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        
        # Gráfico 8: Mapa de calor - VPL
        ax8 = plt.subplot(3, 3, 8)
        
        pivot_vpl = df_cenarios.pivot(index='bess_kwh', columns='pv_kwp', values='vpl_10anos')
        im8 = ax8.imshow(pivot_vpl.values/1000, cmap='RdYlGn', aspect='auto')
        
        ax8.set_xticks(range(len(pivot_vpl.columns)))
        ax8.set_xticklabels([f'{int(x)}' for x in pivot_vpl.columns])
        ax8.set_yticks(range(len(pivot_vpl.index)))
        ax8.set_yticklabels([f'{int(x)}' for x in pivot_vpl.index])
        
        ax8.set_xlabel('Capacidade PV (kWp)', fontsize=11)
        ax8.set_ylabel('Capacidade BESS (kWh)', fontsize=11)
        ax8.set_title('Mapa de Calor: VPL (R$ mil)', fontweight='bold', fontsize=12)
        
        plt.colorbar(im8, ax=ax8, label='VPL (R$ mil)')
        
        # Adicionar valores nas células
        for i in range(len(pivot_vpl.index)):
            for j in range(len(pivot_vpl.columns)):
                val = pivot_vpl.values[i, j] / 1000
                if not np.isnan(val):
                    color = 'white' if abs(val) > pivot_vpl.values.max()/2000 else 'black'
                    ax8.text(j, i, f'{val:.0f}', ha='center', va='center', 
                           color=color, fontsize=7)
        
        # Gráfico 9: VPL vs Investimento
        ax9 = plt.subplot(3, 3, 9)
        
        scatter9 = ax9.scatter(df_cenarios['investimento_total']/1000, 
                              df_cenarios['vpl_10anos']/1000,
                              c=df_cenarios['tir']*100, 
                              s=df_cenarios['bess_kwh']*0.5,
                              cmap='coolwarm', alpha=0.6, edgecolors='black')
        
        ax9.set_xlabel('Investimento (R$ mil)', fontsize=11)
        ax9.set_ylabel('VPL 10 anos (R$ mil)', fontsize=11)
        ax9.set_title('VPL vs Investimento (cor = TIR)', fontweight='bold', fontsize=12)
        ax9.grid(True, alpha=0.3)
        ax9.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        
        cbar9 = plt.colorbar(scatter9, ax=ax9, label='TIR (%)')
        
        plt.tight_layout()
        
        filename = 'analise_sensibilidade_bess_pv_graficos.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráficos salvos em: {filename}")
        plt.close()
        
        # Gráfico adicional: Curvas 3D
        self._gerar_grafico_3d()
    
    def _gerar_grafico_3d(self):
        """Gera gráfico 3D de superfície"""
        from mpl_toolkits.mplot3d import Axes3D
        
        df_cenarios = self.df_resultados[self.df_resultados['tipo'] == 'Cenário'].copy()
        
        fig = plt.figure(figsize=(16, 6))
        
        # Superfície 3D - Payback
        ax1 = fig.add_subplot(121, projection='3d')
        
        pivot_payback = df_cenarios.pivot(index='bess_kwh', columns='pv_kwp', values='payback_anos')
        X, Y = np.meshgrid(pivot_payback.columns, pivot_payback.index)
        Z = pivot_payback.values
        
        surf1 = ax1.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)
        ax1.set_xlabel('PV (kWp)', fontsize=10)
        ax1.set_ylabel('BESS (kWh)', fontsize=10)
        ax1.set_zlabel('Payback (anos)', fontsize=10)
        ax1.set_title('Superfície de Payback', fontweight='bold', fontsize=12)
        fig.colorbar(surf1, ax=ax1, shrink=0.5)
        
        # Superfície 3D - Economia
        ax2 = fig.add_subplot(122, projection='3d')
        
        pivot_economia = df_cenarios.pivot(index='bess_kwh', columns='pv_kwp', values='economia_total_anual')
        Z2 = pivot_economia.values / 1000
        
        surf2 = ax2.plot_surface(X, Y, Z2, cmap='plasma', alpha=0.8)
        ax2.set_xlabel('PV (kWp)', fontsize=10)
        ax2.set_ylabel('BESS (kWh)', fontsize=10)
        ax2.set_zlabel('Economia (R$ mil/ano)', fontsize=10)
        ax2.set_title('Superfície de Economia Anual', fontweight='bold', fontsize=12)
        fig.colorbar(surf2, ax=ax2, shrink=0.5)
        
        plt.tight_layout()
        
        filename = 'analise_sensibilidade_bess_pv_3d.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"📊 Gráficos 3D salvos em: {filename}")
        plt.close()


def main():
    """Executa análise completa"""
    analisador = AnalisadorSensibilidadeBESSPV()
    
    # Executar análise
    analisador.executar_analise_completa()
    
    # Gerar relatório
    analisador.gerar_relatorio()
    
    # Gerar gráficos
    analisador.gerar_graficos()
    
    print("\n" + "="*100)
    print(" "*35 + "ANÁLISE CONCLUÍDA")
    print("="*100)


if __name__ == '__main__':
    main()
