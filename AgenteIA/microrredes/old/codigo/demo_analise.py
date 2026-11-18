"""
Script de demonstração rápida do módulo de análise financeira
"""

from analise_financeira import AnaliseFinanceiraMicrorrede


def demo_rapida():
    """Executa demonstração rápida da análise financeira"""
    
    print("\n" + "=" * 80)
    print(" " * 20 + "DEMONSTRAÇÃO - ANÁLISE FINANCEIRA DE MICRORREDE")
    print("=" * 80)
    
    print("\n📌 Este módulo calcula a economia de energia baseado em:")
    print("   ✓ Simulação de fluxo de potência AC (PandaPower)")
    print("   ✓ Modelo realista de painéis fotovoltaicos")
    print("   ✓ Perfis de irradiância e temperatura")
    print("   ✓ Tarifas de energia e demanda")
    print("   ✓ Custos operacionais e de manutenção")
    
    print("\n📊 Indicadores calculados:")
    print("   • VPL (Valor Presente Líquido)")
    print("   • TIR (Taxa Interna de Retorno)")
    print("   • Payback Descontado")
    print("   • Economia anual ajustada")
    
    print("\n⚙️  Parâmetros da análise:")
    print("-" * 80)
    
    # Criar análise
    analise = AnaliseFinanceiraMicrorrede(
        tarifa_energia_kwh=0.85,
        tarifa_demanda_kw=25.0,
        vida_util=20,
        taxa_desconto=0.08
    )
    
    print(f"   Tarifa de energia:     R$ {analise.tarifa_energia_kwh:.2f}/kWh")
    print(f"   Tarifa de demanda:     R$ {analise.tarifa_demanda_kw:.2f}/kW/mês")
    print(f"   Vida útil do projeto:  {analise.vida_util} anos")
    print(f"   Taxa de desconto:      {analise.taxa_desconto * 100:.1f}% a.a.")
    print(f"   Custo PV:              R$ {analise.custo_pv_kw:,.0f}/kW instalado")
    print(f"   Custo BESS:            R$ {analise.custo_bess_kwh:,.0f}/kWh")
    print(f"   Custo diesel:          R$ {analise.custo_diesel_litro:.2f}/litro")
    
    print("\n" + "=" * 80)
    print("EXECUTANDO SIMULAÇÃO...")
    print("=" * 80)
    
    # Executar simulação
    analise.executar_simulacao_powerflow()
    
    # Gerar relatório
    analise.gerar_relatorio_completo()
    
    print("\n" + "=" * 80)
    print("💡 DICA: Execute 'python analise_otimizada.py' para ver sistema dimensionado")
    print("         corretamente com PV de ~1.700 kW e análise de viabilidade!")
    print("=" * 80)
    
    return analise


if __name__ == "__main__":
    demo_rapida()
