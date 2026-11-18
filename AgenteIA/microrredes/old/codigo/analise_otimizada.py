"""
Análise Financeira Otimizada - Microrrede Dimensionada Corretamente
Sistema PV dimensionado para atender a maior parte da demanda
"""

from analise_financeira import AnaliseFinanceiraMicrorrede
from microrrede_powerflow import MicrorrredePowerFlow
import numpy as np


class MicrorrredeOtimizada(MicrorrredePowerFlow):
    """Versão otimizada da microrrede com dimensionamento adequado"""
    
    def setup_pv_system(self):
        """
        Sistema PV otimizado para atender ~70% da demanda diária
        Demanda: 500 kW x 24h = 12.000 kWh/dia
        Meta PV: ~8.400 kWh/dia (70%)
        Considerando 5 horas úteis de sol: 1.680 kW nominal
        """
        from fotovoltaico import Painel_Fotovoltaico
        
        self.pv_painel = Painel_Fotovoltaico(
            fabricante_painel="Canadian Solar",
            modelo_painel="CS6.2-66TB-610",
            Pmp=610,
            Isc=15.97,
            Voc=48,
            Imp=14.96,
            Vmp=40.8,
            Uisc=0.05,
            Uvoc=-0.25,
            Upmp=-0.29,
            material_painel="Silicio",
            eficiencia=22.6
        )
        
        # Número de painéis otimizado: ~1.700 kW
        self.num_paineis = 2787  # 2787 painéis x 610W = 1.700 kW
        self.pv_potencia_nominal_kw = self.num_paineis * 0.610
        
        print(f"\n🔆 Sistema PV Otimizado: {self.pv_potencia_nominal_kw:.1f} kW "
              f"({self.num_paineis} painéis)")
    
    def controle_bess_diesel(self, p_pv_mw, p_carga_mw):
        """
        Controle otimizado com BESS maior
        - BESS ampliado para 500 kW / 2.000 kWh
        - Diesel reduzido para backup de emergência
        """
        diferenca = p_carga_mw - p_pv_mw
        
        # Capacidades otimizadas
        bess_max_mw = 0.5      # 500 kW (aumentado de 200 kW)
        diesel_max_mw = 0.2    # 200 kW (reduzido de 300 kW - apenas backup)
        
        if diferenca <= 0:
            # Excesso de geração PV - carrega BESS
            p_bess = max(-bess_max_mw, diferenca)
            p_diesel = 0.0
        else:
            # Déficit de geração
            if diferenca <= bess_max_mw:
                # BESS consegue suprir
                p_bess = diferenca
                p_diesel = 0.0
            else:
                # BESS no máximo + diesel se necessário
                p_bess = bess_max_mw
                p_diesel = min(diesel_max_mw, diferenca - bess_max_mw)
        
        return p_bess, p_diesel


def executar_analise_otimizada():
    """Executa análise com sistema otimizado"""
    print("=" * 80)
    print("ANÁLISE FINANCEIRA - SISTEMA OTIMIZADO")
    print("=" * 80)
    print("\nMelhorias implementadas:")
    print("  ✓ PV aumentado de 400 kW para ~1.700 kW (4,25x)")
    print("  ✓ BESS aumentado de 200 kW para 500 kW (2,5x)")
    print("  ✓ Capacidade BESS: 2.000 kWh (antes 800 kWh)")
    print("  ✓ Diesel reduzido para 200 kW (backup apenas)")
    print("=" * 80)
    
    # Criar análise com custos ajustados
    analise = AnaliseFinanceiraMicrorrede(
        tarifa_energia_kwh=0.85,
        tarifa_demanda_kw=25.0,
        vida_util=20,
        taxa_desconto=0.08
    )
    
    # Ajustar custos unitários (economia de escala)
    analise.custo_pv_kw = 3200        # R$/kW (redução de escala)
    analise.custo_bess_kwh = 2200     # R$/kWh (redução de escala)
    analise.custo_diesel_kw = 1200    # R$/kW
    
    # Substituir microrrede pela versão otimizada
    print("\nExecutando simulação de fluxo de potência...")
    analise.microrrede = MicrorrredeOtimizada()
    analise.microrrede.simular_24h()
    
    # Gerar relatório
    analise.gerar_relatorio_completo()
    
    # Plotar resultados
    analise.plotar_analise_financeira()
    analise.microrrede.plotar_resultados()
    
    # Comparação com sistema original
    print("\n" + "=" * 80)
    print("COMPARAÇÃO: SISTEMA ORIGINAL vs OTIMIZADO")
    print("=" * 80)
    
    print("\nSistema ORIGINAL:")
    print(f"  - PV: 400 kW")
    print(f"  - BESS: 200 kW / 800 kWh")
    print(f"  - Diesel: 300 kW")
    print(f"  - RESULTADO: VPL negativo, sem retorno")
    
    print("\nSistema OTIMIZADO:")
    print(f"  - PV: {analise.microrrede.pv_potencia_nominal_kw:.1f} kW")
    print(f"  - BESS: 500 kW / 2.000 kWh")
    print(f"  - Diesel: 200 kW (backup)")
    
    custos_micro = analise.calcular_custos_com_microrrede()
    print(f"\n  - Energia do diesel: {custos_micro['energia_diesel_kwh']:,.0f} kWh/ano")
    print(f"  - Custo diesel: R$ {custos_micro['custo_diesel']:,.2f}/ano")
    
    vpl = analise.resultados_economicos['vpl']
    tir = analise.resultados_economicos['tir']
    payback = analise.resultados_economicos['payback']
    
    print(f"\n  INDICADORES:")
    print(f"  - VPL: R$ {vpl:,.2f}")
    print(f"  - TIR: {tir*100:.2f}%")
    if payback != np.inf:
        print(f"  - Payback: {payback} anos")
    else:
        print(f"  - Payback: Não atingido")
    
    print("\n" + "=" * 80)
    
    # Retornar objeto para análises adicionais
    return analise


def analise_sensibilidade_dimensionamento():
    """
    Analisa diferentes configurações de PV para encontrar ótimo
    """
    import matplotlib.pyplot as plt
    
    print("\n" + "=" * 80)
    print("ANÁLISE DE SENSIBILIDADE - DIMENSIONAMENTO PV")
    print("=" * 80)
    
    # Testar diferentes capacidades de PV
    capacidades_pv = np.linspace(400, 3000, 10)  # De 400 a 3000 kW
    
    resultados = {
        'capacidade_kw': [],
        'vpl': [],
        'tir': [],
        'payback': [],
        'economia_anual': [],
        'capex': []
    }
    
    print("\nTestando diferentes configurações...\n")
    print("Capacidade PV (kW) | CAPEX (R$)      | VPL (R$)        | TIR (%)  | Payback (anos)")
    print("-" * 85)
    
    for cap_pv in capacidades_pv:
        # Criar análise
        analise = AnaliseFinanceiraMicrorrede(
            tarifa_energia_kwh=0.85,
            tarifa_demanda_kw=25.0,
            vida_util=20,
            taxa_desconto=0.08
        )
        
        analise.custo_pv_kw = 3200
        analise.custo_bess_kwh = 2200
        
        # Criar microrrede com capacidade específica
        microrrede = MicrorrredeOtimizada()
        num_paineis = int(cap_pv / 0.610)
        microrrede.num_paineis = num_paineis
        microrrede.pv_potencia_nominal_kw = num_paineis * 0.610
        
        # Simular sem imprimir
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        microrrede.simular_24h()
        
        sys.stdout = old_stdout
        
        analise.microrrede = microrrede
        
        # Calcular indicadores
        custos_base = analise.calcular_custos_sem_microrrede()
        custos_micro = analise.calcular_custos_com_microrrede()
        capex_info = analise.calcular_capex()
        economia = custos_base['custo_total'] - custos_micro['custo_total']
        
        vpl, _ = analise.calcular_vpl()
        tir = analise.calcular_tir()
        payback, _ = analise.calcular_payback_descontado()
        
        # Armazenar
        resultados['capacidade_kw'].append(microrrede.pv_potencia_nominal_kw)
        resultados['vpl'].append(vpl)
        resultados['tir'].append(tir * 100 if not np.isnan(tir) else 0)
        resultados['payback'].append(payback if payback != np.inf else 20)
        resultados['economia_anual'].append(economia)
        resultados['capex'].append(capex_info['capex_total'])
        
        # Imprimir
        print(f"{microrrede.pv_potencia_nominal_kw:>15.0f}    | "
              f"{capex_info['capex_total']:>15,.0f} | "
              f"{vpl:>15,.0f} | "
              f"{tir*100:>8.2f} | "
              f"{payback if payback != np.inf else '>20':>14}")
    
    # Plotar resultados
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # VPL vs Capacidade
    ax1 = axes[0, 0]
    ax1.plot(resultados['capacidade_kw'], resultados['vpl'], 'o-', linewidth=2, markersize=8)
    ax1.axhline(y=0, color='red', linestyle='--', linewidth=2, label='VPL = 0')
    ax1.set_xlabel('Capacidade PV (kW)', fontsize=12)
    ax1.set_ylabel('VPL (R$)', fontsize=12)
    ax1.set_title('VPL vs Capacidade PV', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Encontrar ótimo (máximo VPL)
    idx_max = np.argmax(resultados['vpl'])
    ax1.plot(resultados['capacidade_kw'][idx_max], resultados['vpl'][idx_max], 
            'r*', markersize=20, label='Ótimo')
    
    # TIR vs Capacidade
    ax2 = axes[0, 1]
    ax2.plot(resultados['capacidade_kw'], resultados['tir'], 'o-', 
            linewidth=2, markersize=8, color='green')
    ax2.axhline(y=8, color='red', linestyle='--', linewidth=2, 
               label='Taxa de desconto (8%)')
    ax2.set_xlabel('Capacidade PV (kW)', fontsize=12)
    ax2.set_ylabel('TIR (%)', fontsize=12)
    ax2.set_title('TIR vs Capacidade PV', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Payback vs Capacidade
    ax3 = axes[1, 0]
    ax3.plot(resultados['capacidade_kw'], resultados['payback'], 'o-', 
            linewidth=2, markersize=8, color='purple')
    ax3.set_xlabel('Capacidade PV (kW)', fontsize=12)
    ax3.set_ylabel('Payback (anos)', fontsize=12)
    ax3.set_title('Payback vs Capacidade PV', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim([0, 20])
    
    # Economia Anual vs CAPEX
    ax4 = axes[1, 1]
    scatter = ax4.scatter(resultados['capex'], resultados['economia_anual'], 
                         c=resultados['capacidade_kw'], s=100, cmap='viridis')
    ax4.set_xlabel('CAPEX (R$)', fontsize=12)
    ax4.set_ylabel('Economia Anual (R$)', fontsize=12)
    ax4.set_title('Economia Anual vs CAPEX', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax4)
    cbar.set_label('Capacidade PV (kW)', fontsize=11)
    
    plt.tight_layout()
    plt.savefig('sensibilidade_dimensionamento.png', dpi=150, bbox_inches='tight')
    print("\n\nGráfico salvo como 'sensibilidade_dimensionamento.png'")
    plt.show()
    
    # Imprimir recomendação
    print("\n" + "=" * 80)
    print("RECOMENDAÇÃO DE DIMENSIONAMENTO")
    print("=" * 80)
    print(f"\nCapacidade ótima: {resultados['capacidade_kw'][idx_max]:.0f} kW")
    print(f"VPL máximo: R$ {resultados['vpl'][idx_max]:,.2f}")
    print(f"TIR: {resultados['tir'][idx_max]:.2f}%")
    print(f"Payback: {resultados['payback'][idx_max]:.0f} anos")
    print(f"CAPEX: R$ {resultados['capex'][idx_max]:,.2f}")
    print(f"Economia anual: R$ {resultados['economia_anual'][idx_max]:,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    # Executar análise otimizada
    analise_otimizada = executar_analise_otimizada()
    
    # Executar análise de sensibilidade
    resposta = input("\n\nDeseja executar análise de sensibilidade de dimensionamento? (s/n): ")
    if resposta.lower() == 's':
        analise_sensibilidade_dimensionamento()
