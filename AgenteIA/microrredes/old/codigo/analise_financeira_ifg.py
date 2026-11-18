"""
Análise Financeira Detalhada - Caso IFG
Inclui: VPL, TIR, Fluxo de Caixa, Payback Descontado
"""

import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import pandas as pd
from caso_ifg import CasoIFG


class AnaliseFinanceiraIFG:
    """Análise financeira completa para investimento em BESS no IFG"""
    
    def __init__(self, caso_ifg_resultado):
        """
        Inicializa análise financeira
        
        Parâmetros:
        -----------
        caso_ifg_resultado : dict
            Resultado da simulação do CasoIFG
        """
        self.resultado = caso_ifg_resultado
        
        # Parâmetros financeiros
        self.vida_util_anos = 25  # anos
        self.taxa_desconto = 0.05  # 5% ao ano (inflação)
        self.inflacao_tarifa = 0.04  # 4% ao ano (reajuste tarifário)
        self.custo_om_anual = 0.02  # 2% do investimento/ano (O&M)
        self.degradacao_bess = 0.02  # 2% ao ano (degradação capacidade)
        
        # Valores do investimento
        self.investimento_inicial = caso_ifg_resultado['investimento_bess']
        self.economia_anual_ano1 = caso_ifg_resultado['economia_anual']
        
    def calcular_fluxo_caixa(self):
        """Calcula fluxo de caixa projetado"""
        anos = np.arange(0, self.vida_util_anos + 1)
        fluxo_caixa = np.zeros(len(anos))
        
        # Ano 0: Investimento inicial (negativo)
        fluxo_caixa[0] = -self.investimento_inicial
        
        # Anos 1 a 25: Economia menos custos O&M
        economia_base = self.economia_anual_ano1
        custo_om = self.investimento_inicial * self.custo_om_anual
        
        for ano in range(1, len(anos)):
            # Economia cresce com inflação tarifária
            economia_ano = economia_base * ((1 + self.inflacao_tarifa) ** ano)
            
            # Reduzir economia devido à degradação do BESS
            fator_degradacao = (1 - self.degradacao_bess) ** ano
            economia_ano *= fator_degradacao
            
            # Custo O&M também cresce com inflação
            custo_om_ano = custo_om * ((1 + self.inflacao_tarifa) ** ano)
            
            # Fluxo de caixa = Economia - Custo O&M
            fluxo_caixa[ano] = economia_ano - custo_om_ano
        
        return anos, fluxo_caixa
    
    def calcular_vpl(self, fluxo_caixa):
        """Calcula Valor Presente Líquido"""
        return npf.npv(self.taxa_desconto, fluxo_caixa)
    
    def calcular_tir(self, fluxo_caixa):
        """Calcula Taxa Interna de Retorno"""
        try:
            return npf.irr(fluxo_caixa)
        except:
            return None
    
    def calcular_payback_descontado(self, anos, fluxo_caixa):
        """Calcula payback descontado (considerando valor do dinheiro no tempo)"""
        fluxo_descontado_acumulado = np.zeros(len(anos))
        
        for i in range(len(anos)):
            valor_presente = fluxo_caixa[i] / ((1 + self.taxa_desconto) ** anos[i])
            if i == 0:
                fluxo_descontado_acumulado[i] = valor_presente
            else:
                fluxo_descontado_acumulado[i] = fluxo_descontado_acumulado[i-1] + valor_presente
        
        # Encontrar ano onde fluxo acumulado fica positivo
        for i in range(1, len(fluxo_descontado_acumulado)):
            if fluxo_descontado_acumulado[i] >= 0:
                # Interpolação linear para encontrar ponto exato
                x1, y1 = anos[i-1], fluxo_descontado_acumulado[i-1]
                x2, y2 = anos[i], fluxo_descontado_acumulado[i]
                payback = x1 + (0 - y1) * (x2 - x1) / (y2 - y1)
                return payback, fluxo_descontado_acumulado
        
        return None, fluxo_descontado_acumulado
    
    def gerar_relatorio(self):
        """Gera relatório financeiro completo"""
        print("\n" + "=" * 100)
        print(" " * 30 + "ANÁLISE FINANCEIRA DETALHADA - CASO IFG")
        print("=" * 100)
        
        # Calcular indicadores
        anos, fluxo_caixa = self.calcular_fluxo_caixa()
        vpl = self.calcular_vpl(fluxo_caixa)
        tir = self.calcular_tir(fluxo_caixa)
        payback_desc, fluxo_desc_acum = self.calcular_payback_descontado(anos, fluxo_caixa)
        
        # Payback simples
        payback_simples = self.resultado['payback']
        
        print("\n📊 PREMISSAS DA ANÁLISE:")
        print("-" * 100)
        print(f"  Vida Útil do Projeto:              {self.vida_util_anos} anos")
        print(f"  Taxa de Desconto (TMA):            {self.taxa_desconto*100:.1f}% ao ano")
        print(f"  Inflação Tarifária:                {self.inflacao_tarifa*100:.1f}% ao ano")
        print(f"  Custo O&M:                         {self.custo_om_anual*100:.1f}% do investimento/ano")
        print(f"  Degradação Anual BESS:             {self.degradacao_bess*100:.1f}% ao ano")
        
        print("\n💰 INVESTIMENTO:")
        print("-" * 100)
        print(f"  Investimento Inicial (BESS):       R$ {self.investimento_inicial:>15,.2f}")
        print(f"  Economia Anual (Ano 1):            R$ {self.economia_anual_ano1:>15,.2f}")
        print(f"  Custo O&M Anual (Ano 1):           R$ {self.investimento_inicial * self.custo_om_anual:>15,.2f}")
        
        print("\n📈 INDICADORES FINANCEIROS:")
        print("-" * 100)
        print(f"  VPL (Valor Presente Líquido):      R$ {vpl:>15,.2f}")
        
        if tir is not None:
            print(f"  TIR (Taxa Interna de Retorno):     {tir*100:>15.2f}%")
            viabilidade_tir = "✅ VIÁVEL" if tir > self.taxa_desconto else "❌ INVIÁVEL"
            print(f"  Viabilidade (TIR > TMA):           {viabilidade_tir}")
        else:
            print(f"  TIR (Taxa Interna de Retorno):     Não calculável")
        
        print(f"  Payback Simples:                   {payback_simples:>15.1f} anos")
        if payback_desc is not None:
            print(f"  Payback Descontado:                {payback_desc:>15.1f} anos")
        else:
            print(f"  Payback Descontado:                > {self.vida_util_anos} anos")
        
        viabilidade_vpl = "✅ VIÁVEL" if vpl > 0 else "❌ INVIÁVEL"
        print(f"\n  Viabilidade (VPL > 0):             {viabilidade_vpl}")
        
        # Benefício/Custo
        beneficio_total_vp = sum([fluxo_caixa[i] / ((1 + self.taxa_desconto) ** i) 
                                   for i in range(1, len(anos))])
        relacao_bc = beneficio_total_vp / abs(fluxo_caixa[0])
        print(f"  Relação Benefício/Custo:           {relacao_bc:>15.2f}")
        
        # Criar tabela de fluxo de caixa para primeiros 10 anos
        print("\n📋 FLUXO DE CAIXA PROJETADO (Primeiros 10 Anos):")
        print("-" * 100)
        print(f"{'Ano':>5} | {'Economia (R$)':>18} | {'Custo O&M (R$)':>18} | "
              f"{'Fluxo Caixa (R$)':>18} | {'Fluxo Acum. (R$)':>18}")
        print("-" * 100)
        
        fluxo_acumulado = 0
        for i in range(min(11, len(anos))):
            if i == 0:
                print(f"{anos[i]:>5} | {0:>18,.2f} | {0:>18,.2f} | "
                      f"{fluxo_caixa[i]:>18,.2f} | {fluxo_caixa[i]:>18,.2f}")
                fluxo_acumulado = fluxo_caixa[i]
            else:
                economia = fluxo_caixa[i] + (self.investimento_inicial * self.custo_om_anual * 
                                            ((1 + self.inflacao_tarifa) ** i))
                custo_om = self.investimento_inicial * self.custo_om_anual * ((1 + self.inflacao_tarifa) ** i)
                fluxo_acumulado += fluxo_caixa[i]
                print(f"{anos[i]:>5} | {economia:>18,.2f} | {custo_om:>18,.2f} | "
                      f"{fluxo_caixa[i]:>18,.2f} | {fluxo_acumulado:>18,.2f}")
        
        print("\n" + "=" * 100)
        
        # Gerar gráficos
        self.gerar_graficos(anos, fluxo_caixa, fluxo_desc_acum)
        
        return {
            'vpl': vpl,
            'tir': tir,
            'payback_simples': payback_simples,
            'payback_descontado': payback_desc,
            'relacao_bc': relacao_bc,
            'fluxo_caixa': fluxo_caixa,
            'anos': anos
        }
    
    def gerar_graficos(self, anos, fluxo_caixa, fluxo_desc_acum):
        """Gera gráficos da análise financeira"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Análise Financeira - Investimento em BESS - Caso IFG', 
                     fontsize=16, fontweight='bold')
        
        # Gráfico 1: Fluxo de Caixa Anual
        ax1 = axes[0, 0]
        cores = ['red' if fc < 0 else 'green' for fc in fluxo_caixa]
        ax1.bar(anos, fluxo_caixa / 1000, color=cores, alpha=0.7, edgecolor='black')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax1.set_xlabel('Ano', fontsize=12)
        ax1.set_ylabel('Fluxo de Caixa (R$ mil)', fontsize=12)
        ax1.set_title('Fluxo de Caixa Anual', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 2: Fluxo de Caixa Acumulado
        ax2 = axes[0, 1]
        fluxo_acumulado = np.cumsum(fluxo_caixa)
        ax2.plot(anos, fluxo_acumulado / 1000, 'o-', linewidth=2, markersize=4, color='blue')
        ax2.fill_between(anos, 0, fluxo_acumulado / 1000, alpha=0.3, color='blue')
        ax2.axhline(y=0, color='red', linestyle='--', linewidth=2, label='Break-even')
        ax2.set_xlabel('Ano', fontsize=12)
        ax2.set_ylabel('Fluxo Acumulado (R$ mil)', fontsize=12)
        ax2.set_title('Fluxo de Caixa Acumulado (Payback Simples)', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Gráfico 3: Fluxo Descontado Acumulado
        ax3 = axes[1, 0]
        ax3.plot(anos, fluxo_desc_acum / 1000, 's-', linewidth=2, markersize=4, color='purple')
        ax3.fill_between(anos, 0, fluxo_desc_acum / 1000, alpha=0.3, color='purple')
        ax3.axhline(y=0, color='red', linestyle='--', linewidth=2, label='Break-even')
        ax3.set_xlabel('Ano', fontsize=12)
        ax3.set_ylabel('VPL Acumulado (R$ mil)', fontsize=12)
        ax3.set_title('Fluxo Descontado Acumulado (Payback Descontado)', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Gráfico 4: Comparação Fluxos
        ax4 = axes[1, 1]
        ax4.plot(anos, np.cumsum(fluxo_caixa) / 1000, 'o-', linewidth=2, 
                label='Fluxo Simples', color='blue')
        ax4.plot(anos, fluxo_desc_acum / 1000, 's-', linewidth=2, 
                label='Fluxo Descontado (VPL)', color='purple')
        ax4.axhline(y=0, color='red', linestyle='--', linewidth=1)
        ax4.set_xlabel('Ano', fontsize=12)
        ax4.set_ylabel('Valor Acumulado (R$ mil)', fontsize=12)
        ax4.set_title('Comparação: Fluxo Simples vs Descontado', fontsize=14, fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Salvar gráfico
        filename = 'analise_financeira_ifg.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráficos salvos em: {filename}")
        plt.close()


def main():
    """Executa análise financeira completa"""
    print("\n🔋 Executando simulação do Caso IFG...")
    
    # Executar simulação do caso IFG
    caso = CasoIFG(distribuidora='EQUATORIAL GO', modalidade='verde')
    resultado_caso = caso.gerar_relatorio()
    
    # Análise financeira detalhada
    analise = AnaliseFinanceiraIFG(resultado_caso)
    resultado_financeiro = analise.gerar_relatorio()
    
    # Resumo final
    print("\n" + "=" * 100)
    print(" " * 35 + "RESUMO EXECUTIVO")
    print("=" * 100)
    
    print("\n⚡ CONFIGURAÇÃO DO SISTEMA:")
    print(f"  Sistema Fotovoltaico:              254 kWp (existente)")
    print(f"  BESS Proposto:                     {caso.bess_capacidade_kwh} kWh / {caso.bess_potencia_kw} kW")
    
    print("\n💰 RESULTADOS FINANCEIROS:")
    print(f"  Investimento:                      R$ {resultado_caso['investimento_bess']:>15,.2f}")
    print(f"  Economia Anual (Ano 1):            R$ {resultado_caso['economia_anual']:>15,.2f}")
    print(f"  VPL (25 anos):                     R$ {resultado_financeiro['vpl']:>15,.2f}")
    
    if resultado_financeiro['tir'] is not None:
        print(f"  TIR:                               {resultado_financeiro['tir']*100:>15.2f}%")
    
    print(f"  Payback Simples:                   {resultado_financeiro['payback_simples']:>15.1f} anos")
    if resultado_financeiro['payback_descontado'] is not None:
        print(f"  Payback Descontado:                {resultado_financeiro['payback_descontado']:>15.1f} anos")
    
    print(f"  Relação Benefício/Custo:           {resultado_financeiro['relacao_bc']:>15.2f}")
    
    # Recomendação
    print("\n✅ RECOMENDAÇÃO:")
    if resultado_financeiro['vpl'] > 0 and resultado_financeiro['tir'] > 0.05:
        print("  O INVESTIMENTO EM BESS É FINANCEIRAMENTE VIÁVEL!")
        print("  • VPL positivo indica criação de valor")
        print("  • TIR superior à taxa mínima de atratividade (5%)")
        print(f"  • Payback em {resultado_financeiro['payback_simples']:.1f} anos é aceitável")
    else:
        print("  O investimento requer análise adicional de sensibilidade.")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
