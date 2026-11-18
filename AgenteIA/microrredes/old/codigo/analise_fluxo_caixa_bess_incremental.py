"""
Análise de Fluxo de Caixa - BESS Incremental
============================================
Compara estratégias de aquisição de BESS:
1. Incremental: 50 kWh no ano 0, incremento de 50 kWh/ano até 300 kWh no ano 5
2. Compra Única: 300 kWh no ano 0

Horizonte: 10 anos
Taxa de desconto: 10% a.a.
Inflação: 5% a.a.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from caso_ifg import CasoIFG
import warnings
warnings.filterwarnings('ignore')

class AnalisadorFluxoCaixaBESS:
    def __init__(self, pv_kwp=400, taxa_desconto=0.10, inflacao=0.05, horizonte=10,
                 estrategia_bess='solar', bess_carregamento_inicio=0, bess_carregamento_fim=5,
                 icms=0.17, pis=0.05, aplicar_impostos_exportacao=True):
        """
        Inicializa analisador de fluxo de caixa
        
        Parâmetros:
        -----------
        pv_kwp : float
            Capacidade PV instalada (kWp)
        taxa_desconto : float
            Taxa de desconto anual (ex: 0.10 = 10%)
        inflacao : float
            Taxa de inflação anual (ex: 0.05 = 5%)
        horizonte : int
            Horizonte de análise em anos
        estrategia_bess : str
            'solar' (carrega com PV durante o dia) ou 'madrugada' (carrega na madrugada)
        bess_carregamento_inicio : int
            Hora inicial do carregamento na madrugada (0-23)
        bess_carregamento_fim : int
            Hora final do carregamento na madrugada (0-23)
        icms : float
            Aliquota de ICMS aplicada sobre energia (ex: 0.17 = 17%)
        pis : float
            Aliquota de PIS aplicada sobre energia (ex: 0.05 = 5%)
        aplicar_impostos_exportacao : bool
            Se True, aplica impostos tambem sobre o valor da exportacao
        """
        self.pv_kwp = pv_kwp
        self.taxa_desconto = taxa_desconto
        self.inflacao = inflacao
        self.horizonte = horizonte
        self.custo_bess_kwh = 1900  # R$/kWh
        self.estrategia_bess = estrategia_bess
        self.bess_carregamento_inicio = bess_carregamento_inicio
        self.bess_carregamento_fim = bess_carregamento_fim
        self.icms = icms
        self.pis = pis
        self.aplicar_impostos_exportacao = aplicar_impostos_exportacao
        
        print("="*100)
        print(" "*25 + "ANÁLISE DE FLUXO DE CAIXA - BESS INCREMENTAL")
        print("="*100)
        print(f"\n⚙️  PARÂMETROS DA ANÁLISE:")
        print(f"  Capacidade PV:        {pv_kwp} kWp")
        print(f"  Taxa de Desconto:     {taxa_desconto*100:.1f}% a.a.")
        print(f"  Inflação:             {inflacao*100:.1f}% a.a.")
        print(f"  Horizonte:            {horizonte} anos")
        print(f"  Custo BESS:           R$ {self.custo_bess_kwh:,.2f}/kWh")
        print(f"  ICMS/PIS:             {self.icms*100:.1f}% / {self.pis*100:.1f}%")
        print(f"  Impostos exportacao:  {'Sim' if self.aplicar_impostos_exportacao else 'Nao'}")
        if self.estrategia_bess == 'madrugada':
            print("  Estrategia BESS:      Carregamento na madrugada (fora ponta)")
            print(f"  Janela madrugada:     {self.bess_carregamento_inicio:02d}h - {self.bess_carregamento_fim:02d}h")
        else:
            print("  Estrategia BESS:      Carregamento com PV (durante o dia)")
        
        # Cenário base (sem BESS)
        print(f"\n🔄 Simulando cenário base (sem BESS)...")
        caso_base = CasoIFG(
            estrategia_bess=self.estrategia_bess,
            bess_carregamento_inicio=self.bess_carregamento_inicio,
            bess_carregamento_fim=self.bess_carregamento_fim,
            icms=self.icms,
            pis=self.pis,
            aplicar_impostos_exportacao=self.aplicar_impostos_exportacao
        )
        caso_base.pv_potencia_kwp = pv_kwp
        caso_base.bess_capacidade_kwh = 0
        caso_base._configurar_pv()
        resultado_base = caso_base.simular_mes()
        self.custo_base_mensal = resultado_base['custo_mensal']
        self.custo_base_anual = self.custo_base_mensal * 12
        
        print(f"  ✓ Custo Base Anual (sem BESS): R$ {self.custo_base_anual:,.2f}")
    
    def simular_custo_anual_com_bess(self, bess_kwh):
        """Simula e retorna custo anual com determinada capacidade BESS"""
        caso = CasoIFG(
            estrategia_bess=self.estrategia_bess,
            bess_carregamento_inicio=self.bess_carregamento_inicio,
            bess_carregamento_fim=self.bess_carregamento_fim,
            icms=self.icms,
            pis=self.pis,
            aplicar_impostos_exportacao=self.aplicar_impostos_exportacao
        )
        caso.pv_potencia_kwp = self.pv_kwp
        caso.bess_capacidade_kwh = bess_kwh
        caso._configurar_pv()
        resultado = caso.simular_mes()
        custo_anual = resultado['custo_mensal'] * 12
        return custo_anual
    
    def estrategia_incremental(self):
        """
        Estratégia de aquisição incremental
        Ano 0: 50 kWh
        Anos 1-5: +50 kWh por ano até atingir 300 kWh
        """
        print("\n" + "="*100)
        print(" "*30 + "ESTRATÉGIA INCREMENTAL")
        print("="*100)
        print("\n📊 Perfil de Aquisição:")
        print("  Ano 0: 50 kWh inicial")
        print("  Anos 1-5: Incremento de 50 kWh/ano")
        print("  Capacidade final (Ano 5): 300 kWh")
        
        fluxo_caixa = []
        
        for ano in range(self.horizonte):
            # Determinar capacidade BESS do ano
            if ano == 0:
                bess_kwh = 50
                investimento = 50 * self.custo_bess_kwh
            elif ano <= 5:
                bess_kwh = 50 + (ano * 50)  # 50, 100, 150, 200, 250, 300
                investimento = 50 * self.custo_bess_kwh  # Incremento de 50 kWh
            else:
                bess_kwh = 300  # Mantém capacidade máxima
                investimento = 0
            
            # Simular custo anual com BESS
            print(f"\n  Ano {ano}: Simulando BESS {bess_kwh} kWh...", end=" ")
            custo_anual = self.simular_custo_anual_com_bess(bess_kwh)
            
            # Calcular economia
            economia_energia = self.custo_base_anual - custo_anual
            
            # Aplicar inflação na economia
            economia_inflacionada = economia_energia * ((1 + self.inflacao) ** ano)
            
            # Fluxo de caixa líquido
            fluxo_liquido = economia_inflacionada - investimento
            
            # Valor presente do fluxo
            vp_fluxo = fluxo_liquido / ((1 + self.taxa_desconto) ** ano)
            
            fluxo_caixa.append({
                'ano': ano,
                'bess_kwh': bess_kwh,
                'investimento': investimento,
                'custo_energia': custo_anual,
                'economia_energia': economia_energia,
                'economia_inflacionada': economia_inflacionada,
                'fluxo_liquido': fluxo_liquido,
                'vp_fluxo': vp_fluxo
            })
            
            print(f"✓ (Custo: R$ {custo_anual:,.0f}, Economia: R$ {economia_energia:,.0f})")
        
        df = pd.DataFrame(fluxo_caixa)
        
        # Calcular métricas
        investimento_total = df['investimento'].sum()
        vpl = df['vp_fluxo'].sum()
        
        # Calcular payback
        df['fluxo_acumulado'] = df['fluxo_liquido'].cumsum()
        payback_idx = df[df['fluxo_acumulado'] >= 0].index
        payback = payback_idx[0] if len(payback_idx) > 0 else None
        
        # Calcular TIR usando scipy
        try:
            from scipy.optimize import newton
            fluxos = [-df.loc[df['ano'] == 0, 'investimento'].values[0]]  # Investimento inicial negativo
            for ano in range(1, self.horizonte):
                fluxos.append(df.loc[df['ano'] == ano, 'fluxo_liquido'].values[0])
            
            def vpl_tir(r):
                return sum([f / ((1 + r) ** i) for i, f in enumerate(fluxos)])
            
            tir = newton(vpl_tir, 0.1)
        except:
            tir = None
        
        return {
            'nome': 'Incremental',
            'df': df,
            'investimento_total': investimento_total,
            'vpl': vpl,
            'payback': payback,
            'tir': tir
        }
    
    def estrategia_compra_unica(self):
        """
        Estratégia de compra única
        Ano 0: 300 kWh de uma vez
        """
        print("\n" + "="*100)
        print(" "*30 + "ESTRATÉGIA COMPRA ÚNICA")
        print("="*100)
        print("\n📊 Perfil de Aquisição:")
        print("  Ano 0: 300 kWh de uma vez")
        
        fluxo_caixa = []
        bess_kwh = 300
        
        for ano in range(self.horizonte):
            # Investimento apenas no ano 0
            investimento = 300 * self.custo_bess_kwh if ano == 0 else 0
            
            # Simular custo anual
            if ano == 0:
                print(f"\n  Ano {ano}: Simulando BESS {bess_kwh} kWh...", end=" ")
                custo_anual = self.simular_custo_anual_com_bess(bess_kwh)
                custo_base = custo_anual
                print(f"✓ (Custo: R$ {custo_anual:,.0f})")
            else:
                custo_anual = custo_base  # Usar mesmo custo base
            
            # Calcular economia
            economia_energia = self.custo_base_anual - custo_anual
            
            # Aplicar inflação
            economia_inflacionada = economia_energia * ((1 + self.inflacao) ** ano)
            
            # Fluxo líquido
            fluxo_liquido = economia_inflacionada - investimento
            
            # Valor presente
            vp_fluxo = fluxo_liquido / ((1 + self.taxa_desconto) ** ano)
            
            fluxo_caixa.append({
                'ano': ano,
                'bess_kwh': bess_kwh,
                'investimento': investimento,
                'custo_energia': custo_anual,
                'economia_energia': economia_energia,
                'economia_inflacionada': economia_inflacionada,
                'fluxo_liquido': fluxo_liquido,
                'vp_fluxo': vp_fluxo
            })
        
        df = pd.DataFrame(fluxo_caixa)
        
        # Calcular métricas
        investimento_total = df['investimento'].sum()
        vpl = df['vp_fluxo'].sum()
        
        # Payback
        df['fluxo_acumulado'] = df['fluxo_liquido'].cumsum()
        payback_idx = df[df['fluxo_acumulado'] >= 0].index
        payback = payback_idx[0] if len(payback_idx) > 0 else None
        
        # TIR
        try:
            from scipy.optimize import newton
            fluxos = [-df.loc[df['ano'] == 0, 'investimento'].values[0]]
            for ano in range(1, self.horizonte):
                fluxos.append(df.loc[df['ano'] == ano, 'fluxo_liquido'].values[0])
            
            def vpl_tir(r):
                return sum([f / ((1 + r) ** i) for i, f in enumerate(fluxos)])
            
            tir = newton(vpl_tir, 0.1)
        except:
            tir = None
        
        return {
            'nome': 'Compra Única',
            'df': df,
            'investimento_total': investimento_total,
            'vpl': vpl,
            'payback': payback,
            'tir': tir
        }
    
    def gerar_relatorio_comparativo(self, incremental, compra_unica):
        """Gera relatório comparativo das estratégias"""
        print("\n" + "="*100)
        print(" "*35 + "COMPARAÇÃO DE ESTRATÉGIAS")
        print("="*100)
        
        print("\n📊 RESUMO FINANCEIRO:")
        print("-"*100)
        print(f"{'Métrica':<35} {'Incremental':>25} {'Compra Única':>25} {'Diferença':>12}")
        print("-"*100)
        
        print(f"{'Investimento Total':<35} R$ {incremental['investimento_total']:>20,.2f}  "
              f"R$ {compra_unica['investimento_total']:>20,.2f}  "
              f"{((incremental['investimento_total'] - compra_unica['investimento_total'])/compra_unica['investimento_total']*100):>9.1f}%")
        
        print(f"{'VPL (10 anos)':<35} R$ {incremental['vpl']:>20,.2f}  "
              f"R$ {compra_unica['vpl']:>20,.2f}  "
              f"{((incremental['vpl'] - compra_unica['vpl'])/abs(compra_unica['vpl'])*100):>9.1f}%")
        
        payback_inc = f"{incremental['payback']:.1f} anos" if incremental['payback'] is not None else "N/A"
        payback_unica = f"{compra_unica['payback']:.1f} anos" if compra_unica['payback'] is not None else "N/A"
        print(f"{'Payback':<35} {payback_inc:>25}  {payback_unica:>25}  {'':>12}")
        
        tir_inc = f"{incremental['tir']*100:.2f}%" if incremental['tir'] is not None else "N/A"
        tir_unica = f"{compra_unica['tir']*100:.2f}%" if compra_unica['tir'] is not None else "N/A"
        print(f"{'TIR':<35} {tir_inc:>25}  {tir_unica:>25}  {'':>12}")
        
        print("-"*100)
        
        # Economia total
        economia_inc = incremental['df']['economia_inflacionada'].sum()
        economia_unica = compra_unica['df']['economia_inflacionada'].sum()
        
        print(f"{'Economia Total (nominal)':<35} R$ {economia_inc:>20,.2f}  "
              f"R$ {economia_unica:>20,.2f}  "
              f"{((economia_inc - economia_unica)/economia_unica*100):>9.1f}%")
        
        print("\n🎯 RECOMENDAÇÃO:")
        if incremental['vpl'] > compra_unica['vpl']:
            print(f"  ✓ Estratégia INCREMENTAL é mais vantajosa")
            print(f"    - VPL superior em R$ {(incremental['vpl'] - compra_unica['vpl']):,.2f}")
        else:
            print(f"  ✓ Estratégia COMPRA ÚNICA é mais vantajosa")
            print(f"    - VPL superior em R$ {(compra_unica['vpl'] - incremental['vpl']):,.2f}")
        
        return {
            'incremental': incremental,
            'compra_unica': compra_unica
        }
    
    def plotar_analise(self, incremental, compra_unica, output_prefix=None):
        """Gera gráficos comparativos"""
        print("\n📊 Gerando visualizações...")
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)
        
        fig.suptitle('ANÁLISE COMPARATIVA: BESS INCREMENTAL vs COMPRA ÚNICA\n' + 
                     f'PV {self.pv_kwp} kWp | Horizonte {self.horizonte} anos | Taxa {self.taxa_desconto*100:.0f}% | Inflação {self.inflacao*100:.0f}%',
                     fontsize=16, fontweight='bold', y=0.98)
        
        df_inc = incremental['df']
        df_unica = compra_unica['df']
        
        # 1. Evolução da Capacidade BESS
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(df_inc['ano'], df_inc['bess_kwh'], marker='o', linewidth=2.5, 
                markersize=8, color='#1976D2', label='Incremental')
        ax1.plot(df_unica['ano'], df_unica['bess_kwh'], marker='s', linewidth=2.5,
                markersize=8, color='#D32F2F', label='Compra Única', linestyle='--')
        ax1.set_xlabel('Ano', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Capacidade BESS (kWh)', fontsize=11, fontweight='bold')
        ax1.set_title('Evolução da Capacidade BESS', fontsize=12, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(-0.5, self.horizonte - 0.5)
        
        # 2. Investimentos Anuais
        ax2 = fig.add_subplot(gs[0, 1])
        x = np.arange(self.horizonte)
        width = 0.35
        ax2.bar(x - width/2, df_inc['investimento'], width, label='Incremental', 
               color='#1976D2', alpha=0.8, edgecolor='black')
        ax2.bar(x + width/2, df_unica['investimento'], width, label='Compra Única',
               color='#D32F2F', alpha=0.8, edgecolor='black')
        ax2.set_xlabel('Ano', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Investimento (R$)', fontsize=11, fontweight='bold')
        ax2.set_title('Investimentos Anuais', fontsize=12, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        
        # 3. Economia de Energia Anual
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.plot(df_inc['ano'], df_inc['economia_inflacionada'], marker='o', linewidth=2.5,
                markersize=8, color='#2E7D32', label='Incremental')
        ax3.plot(df_unica['ano'], df_unica['economia_inflacionada'], marker='s', linewidth=2.5,
                markersize=8, color='#388E3C', label='Compra Única', linestyle='--')
        ax3.set_xlabel('Ano', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Economia (R$)', fontsize=11, fontweight='bold')
        ax3.set_title('Economia de Energia Anual (com inflação)', fontsize=12, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        
        # 4. Fluxo de Caixa Líquido
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.bar(df_inc['ano'], df_inc['fluxo_liquido'], alpha=0.7, 
               color=['red' if x < 0 else 'green' for x in df_inc['fluxo_liquido']],
               edgecolor='black', label='Incremental')
        ax4.axhline(y=0, color='black', linewidth=2)
        ax4.set_xlabel('Ano', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Fluxo de Caixa (R$)', fontsize=11, fontweight='bold')
        ax4.set_title('Fluxo de Caixa Líquido - Incremental', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        
        # 5. Fluxo de Caixa Compra Única
        ax5 = fig.add_subplot(gs[1, 1])
        ax5.bar(df_unica['ano'], df_unica['fluxo_liquido'], alpha=0.7,
               color=['red' if x < 0 else 'green' for x in df_unica['fluxo_liquido']],
               edgecolor='black', label='Compra Única')
        ax5.axhline(y=0, color='black', linewidth=2)
        ax5.set_xlabel('Ano', fontsize=11, fontweight='bold')
        ax5.set_ylabel('Fluxo de Caixa (R$)', fontsize=11, fontweight='bold')
        ax5.set_title('Fluxo de Caixa Líquido - Compra Única', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3, axis='y')
        ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        
        # 6. Fluxo Acumulado
        ax6 = fig.add_subplot(gs[1, 2])
        df_inc['fluxo_acumulado'] = df_inc['fluxo_liquido'].cumsum()
        df_unica['fluxo_acumulado'] = df_unica['fluxo_liquido'].cumsum()
        
        ax6.plot(df_inc['ano'], df_inc['fluxo_acumulado'], marker='o', linewidth=2.5,
                markersize=8, color='#1976D2', label='Incremental')
        ax6.plot(df_unica['ano'], df_unica['fluxo_acumulado'], marker='s', linewidth=2.5,
                markersize=8, color='#D32F2F', label='Compra Única', linestyle='--')
        ax6.axhline(y=0, color='black', linewidth=1.5, linestyle=':')
        ax6.set_xlabel('Ano', fontsize=11, fontweight='bold')
        ax6.set_ylabel('Fluxo Acumulado (R$)', fontsize=11, fontweight='bold')
        ax6.set_title('Fluxo de Caixa Acumulado', fontsize=12, fontweight='bold')
        ax6.legend(fontsize=10)
        ax6.grid(True, alpha=0.3)
        ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        
        # 7. Valor Presente dos Fluxos
        ax7 = fig.add_subplot(gs[2, 0])
        x = np.arange(self.horizonte)
        width = 0.35
        ax7.bar(x - width/2, df_inc['vp_fluxo'], width, label='Incremental',
               color='#1976D2', alpha=0.8, edgecolor='black')
        ax7.bar(x + width/2, df_unica['vp_fluxo'], width, label='Compra Única',
               color='#D32F2F', alpha=0.8, edgecolor='black')
        ax7.axhline(y=0, color='black', linewidth=1.5)
        ax7.set_xlabel('Ano', fontsize=11, fontweight='bold')
        ax7.set_ylabel('Valor Presente (R$)', fontsize=11, fontweight='bold')
        ax7.set_title('Valor Presente dos Fluxos Anuais', fontsize=12, fontweight='bold')
        ax7.legend(fontsize=10)
        ax7.grid(True, alpha=0.3, axis='y')
        ax7.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        
        # 8. Comparação de Métricas
        ax8 = fig.add_subplot(gs[2, 1])
        metricas = ['Invest.\nTotal', 'VPL\n(10 anos)', 'Economia\nTotal']
        inc_values = [incremental['investimento_total'], incremental['vpl'], 
                     df_inc['economia_inflacionada'].sum()]
        unica_values = [compra_unica['investimento_total'], compra_unica['vpl'],
                       df_unica['economia_inflacionada'].sum()]
        
        x = np.arange(len(metricas))
        width = 0.35
        ax8.bar(x - width/2, inc_values, width, label='Incremental',
               color='#1976D2', alpha=0.8, edgecolor='black')
        ax8.bar(x + width/2, unica_values, width, label='Compra Única',
               color='#D32F2F', alpha=0.8, edgecolor='black')
        ax8.set_ylabel('Valor (R$)', fontsize=11, fontweight='bold')
        ax8.set_title('Comparação de Métricas Financeiras', fontsize=12, fontweight='bold')
        ax8.set_xticks(x)
        ax8.set_xticklabels(metricas, fontsize=10)
        ax8.legend(fontsize=10)
        ax8.grid(True, alpha=0.3, axis='y')
        ax8.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        
        # 9. Tabela Resumo
        ax9 = fig.add_subplot(gs[2, 2])
        ax9.axis('tight')
        ax9.axis('off')
        
        table_data = [
            ['Métrica', 'Incremental', 'Compra Única'],
            ['Invest. Total', f"R$ {incremental['investimento_total']:,.0f}", 
             f"R$ {compra_unica['investimento_total']:,.0f}"],
            ['VPL (10a)', f"R$ {incremental['vpl']:,.0f}", 
             f"R$ {compra_unica['vpl']:,.0f}"],
            ['Payback', f"{incremental['payback']:.1f} anos" if incremental['payback'] else 'N/A',
             f"{compra_unica['payback']:.1f} anos" if compra_unica['payback'] else 'N/A'],
            ['TIR', f"{incremental['tir']*100:.2f}%" if incremental['tir'] else 'N/A',
             f"{compra_unica['tir']*100:.2f}%" if compra_unica['tir'] else 'N/A'],
            ['Economia Total', f"R$ {df_inc['economia_inflacionada'].sum():,.0f}",
             f"R$ {df_unica['economia_inflacionada'].sum():,.0f}"]
        ]
        
        table = ax9.table(cellText=table_data, cellLoc='center', loc='center',
                         colWidths=[0.35, 0.325, 0.325])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2.5)
        
        # Estilizar header
        for i in range(3):
            table[(0, i)].set_facecolor('#4472C4')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Alternar cores das linhas
        for i in range(1, len(table_data)):
            for j in range(3):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#E7E6E6')
        
        ax9.set_title('Resumo Comparativo', fontsize=12, fontweight='bold', pad=20)
        
        # Salvar figura
        if output_prefix is None:
            output_prefix = 'analise_fluxo_caixa_bess_incremental'
        figura_path = f"{output_prefix}.png"
        plt.savefig(figura_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Gráfico salvo: {figura_path}")
        
        # Salvar dados em CSV
        df_comparacao = pd.DataFrame({
            'Ano': df_inc['ano'],
            'BESS_Inc_kWh': df_inc['bess_kwh'],
            'Invest_Inc': df_inc['investimento'],
            'Economia_Inc': df_inc['economia_inflacionada'],
            'Fluxo_Inc': df_inc['fluxo_liquido'],
            'VP_Inc': df_inc['vp_fluxo'],
            'BESS_Unica_kWh': df_unica['bess_kwh'],
            'Invest_Unica': df_unica['investimento'],
            'Economia_Unica': df_unica['economia_inflacionada'],
            'Fluxo_Unica': df_unica['fluxo_liquido'],
            'VP_Unica': df_unica['vp_fluxo']
        })
        dados_path = f"{output_prefix}.csv"
        df_comparacao.to_csv(dados_path, index=False, encoding='utf-8-sig')
        print(f"  ✓ Dados salvos: {dados_path}")
    
    def executar_analise(self, output_prefix=None):
        """Executa análise completa"""
        # Estratégia incremental
        incremental = self.estrategia_incremental()
        
        # Estratégia compra única
        compra_unica = self.estrategia_compra_unica()
        
        # Relatório comparativo
        self.gerar_relatorio_comparativo(incremental, compra_unica)
        
        # Gráficos
        self.plotar_analise(incremental, compra_unica, output_prefix=output_prefix)
        
        print("\n" + "="*100)
        print(" "*35 + "✅ ANÁLISE CONCLUÍDA")
        print("="*100 + "\n")

        return {
            'incremental': incremental,
            'compra_unica': compra_unica
        }


def _montar_prefixo_saida(estrategia_bess, inicio, fim):
    if estrategia_bess == 'madrugada':
        return f"analise_fluxo_caixa_bess_incremental_madrugada_{inicio:02d}-{fim:02d}"
    return "analise_fluxo_caixa_bess_incremental_solar"


def executar_comparacao_estrategias(pv_kwp=400, taxa_desconto=0.10, inflacao=0.05, horizonte=10,
                                    madrugada_inicio=0, madrugada_fim=6):
    """Executa as duas estratégias (solar e madrugada) e gera comparação consolidada."""
    configuracoes = [
        {
            'nome': 'Solar',
            'estrategia_bess': 'solar',
            'inicio': None,
            'fim': None
        },
        {
            'nome': f"Madrugada {madrugada_inicio:02d}-{madrugada_fim:02d}",
            'estrategia_bess': 'madrugada',
            'inicio': madrugada_inicio,
            'fim': madrugada_fim
        }
    ]

    resumo = []

    for conf in configuracoes:
        analisador = AnalisadorFluxoCaixaBESS(
            pv_kwp=pv_kwp,
            taxa_desconto=taxa_desconto,
            inflacao=inflacao,
            horizonte=horizonte,
            estrategia_bess=conf['estrategia_bess'],
            bess_carregamento_inicio=conf['inicio'] if conf['inicio'] is not None else 0,
            bess_carregamento_fim=conf['fim'] if conf['fim'] is not None else 0
        )

        prefixo = _montar_prefixo_saida(conf['estrategia_bess'],
                                        conf['inicio'] or 0,
                                        conf['fim'] or 0)

        resultados = analisador.executar_analise(output_prefix=prefixo)
        incremental = resultados['incremental']
        compra_unica = resultados['compra_unica']

        resumo.append({
            'estrategia_operacao': conf['nome'],
            'tipo_aquisicao': 'Incremental',
            'investimento_total': incremental['investimento_total'],
            'vpl': incremental['vpl'],
            'payback': incremental['payback'],
            'tir': incremental['tir'],
            'economia_total_nominal': incremental['df']['economia_inflacionada'].sum()
        })
        resumo.append({
            'estrategia_operacao': conf['nome'],
            'tipo_aquisicao': 'Compra Unica',
            'investimento_total': compra_unica['investimento_total'],
            'vpl': compra_unica['vpl'],
            'payback': compra_unica['payback'],
            'tir': compra_unica['tir'],
            'economia_total_nominal': compra_unica['df']['economia_inflacionada'].sum()
        })

    df_resumo = pd.DataFrame(resumo)
    df_resumo.to_csv('comparacao_estrategias_bess.csv', index=False, encoding='utf-8-sig')
    print("\n  ✓ Comparativo salvo: comparacao_estrategias_bess.csv")

    _plotar_comparacao_estrategias(df_resumo)

    return df_resumo


def _plotar_comparacao_estrategias(df_resumo):
    """Gera gráfico comparativo entre estratégias de operação."""
    print("\n📊 Gerando gráfico comparativo entre estratégias...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('COMPARAÇÃO: SOLAR vs MADRUGADA (Incremental e Compra Única)',
                 fontsize=14, fontweight='bold', y=0.98)

    metricas = [
        ('vpl', 'VPL (10 anos)', axes[0, 0]),
        ('economia_total_nominal', 'Economia Total (nominal)', axes[0, 1]),
        ('payback', 'Payback (anos)', axes[1, 0]),
        ('tir', 'TIR', axes[1, 1])
    ]

    for (col, titulo, ax) in metricas:
        for tipo in ['Incremental', 'Compra Unica']:
            dados = df_resumo[df_resumo['tipo_aquisicao'] == tipo]
            valores = dados[col].fillna(0).values
            labels = dados['estrategia_operacao'].values
            x = np.arange(len(labels)) + (-0.15 if tipo == 'Incremental' else 0.15)
            ax.bar(x, valores, width=0.3, label=tipo)

        ax.set_title(titulo, fontsize=11, fontweight='bold')
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, rotation=10, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        if col in ['vpl', 'economia_total_nominal']:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'R$ {y/1000:.0f}k'))
        if col == 'tir':
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{y*100:.0f}%'))

    axes[0, 0].legend(fontsize=9)
    plt.tight_layout()
    plt.savefig('comparacao_estrategias_bess.png', dpi=200, bbox_inches='tight')
    print("  ✓ Gráfico salvo: comparacao_estrategias_bess.png")


if __name__ == "__main__":
    executar_comparacao_estrategias(
        pv_kwp=400,
        taxa_desconto=0.10,
        inflacao=0.05,
        horizonte=10,
        madrugada_inicio=0,
        madrugada_fim=6
    )
