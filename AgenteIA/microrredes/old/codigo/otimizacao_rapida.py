"""
Otimização Rápida de Microrrede
Versão simplificada com menos avaliações para resultados rápidos
"""

from otimizador_microrrede import OtimizadorMicrorrede
import numpy as np


def otimizacao_rapida():
    """
    Executa otimização rápida com parâmetros reduzidos
    Ideal para testes e demonstrações
    """
    print("\n" + "=" * 80)
    print(" " * 20 + "OTIMIZAÇÃO RÁPIDA DE MICRORREDE")
    print("=" * 80)
    print("\nModo: RÁPIDO (menos avaliações, convergência aproximada)")
    print("Para otimização completa, use: python otimizador_microrrede.py")
    print("=" * 80)
    
    # Criar otimizador com parâmetros típicos
    otimizador = OtimizadorMicrorrede(
        tarifa_energia_kwh=0.85,      # R$/kWh (tarifa Grupo A)
        tarifa_demanda_kw=25.0,        # R$/kW/mês
        vida_util=20,
        taxa_desconto=0.08,
        custo_pv_kw=3200,              # R$/kW instalado
        custo_bess_kwh=2200,           # R$/kWh
        custo_diesel_kw=1200,          # R$/kW
        custo_diesel_litro=6.50        # R$/litro
    )
    
    # Limites de busca ajustados
    limites = [
        (600, 2000),    # PV: 600-2000 kW (faixa mais estreita)
        (250, 550),     # BESS potência: 250-550 kW
        (3, 5),         # BESS horas: 3-5h (faixa reduzida)
        (150, 350)      # Diesel: 150-350 kW
    ]
    
    print("\n📋 Parâmetros da otimização:")
    print("-" * 80)
    print(f"   Tarifa energia:     R$ {otimizador.tarifa_energia_kwh:.2f}/kWh")
    print(f"   Tarifa demanda:     R$ {otimizador.tarifa_demanda_kw:.2f}/kW/mês")
    print(f"   Custo PV:           R$ {otimizador.custo_pv_kw:,.0f}/kW")
    print(f"   Custo BESS:         R$ {otimizador.custo_bess_kwh:,.0f}/kWh")
    print(f"   Vida útil:          {otimizador.vida_util} anos")
    print(f"   Taxa desconto:      {otimizador.taxa_desconto*100:.1f}%")
    
    print("\n🔍 Espaço de busca:")
    print("-" * 80)
    print(f"   PV:                 {limites[0][0]:.0f} - {limites[0][1]:.0f} kW")
    print(f"   BESS potência:      {limites[1][0]:.0f} - {limites[1][1]:.0f} kW")
    print(f"   BESS duração:       {limites[2][0]:.1f} - {limites[2][1]:.1f} horas")
    print(f"   Diesel:             {limites[3][0]:.0f} - {limites[3][1]:.0f} kW")
    
    input("\nPressione ENTER para iniciar otimização...")
    
    # Executar otimização (parâmetros reduzidos para rapidez)
    resultado = otimizador.otimizar_evolucao_diferencial(
        bounds=limites,
        maxiter=30,        # Menos iterações (padrão seria 100)
        popsize=10,        # População menor (padrão seria 15)
        workers=1
    )
    
    # Gerar relatório
    otimizador.gerar_relatorio_otimizacao()
    
    # Plotar resultados
    otimizador.plotar_resultados_otimizacao()
    
    # Salvar histórico
    otimizador.salvar_historico_csv('otimizacao_rapida.csv')
    
    # Análise detalhada da solução ótima
    print("\n" + "=" * 80)
    print("ANÁLISE DETALHADA DA SOLUÇÃO ÓTIMA")
    print("=" * 80)
    
    melhor = otimizador.melhor_config
    
    # Breakdown de CAPEX
    capex_pv = melhor['pv_kw'] * otimizador.custo_pv_kw
    capex_bess = melhor['bess_kwh'] * otimizador.custo_bess_kwh
    capex_diesel = melhor['diesel_kw'] * otimizador.custo_diesel_kw
    capex_adicional = (capex_pv + capex_bess + capex_diesel) * 0.15
    
    print("\n💵 BREAKDOWN DE CAPEX:")
    print("-" * 80)
    print(f"   Sistema PV:         R$ {capex_pv:>15,.2f}  "
          f"({capex_pv/melhor['capex']*100:>5.1f}%)")
    print(f"   Sistema BESS:       R$ {capex_bess:>15,.2f}  "
          f"({capex_bess/melhor['capex']*100:>5.1f}%)")
    print(f"   Gerador Diesel:     R$ {capex_diesel:>15,.2f}  "
          f"({capex_diesel/melhor['capex']*100:>5.1f}%)")
    print(f"   Instalação/Projeto: R$ {capex_adicional:>15,.2f}  "
          f"({capex_adicional/melhor['capex']*100:>5.1f}%)")
    print(f"   " + "-" * 50)
    print(f"   TOTAL:              R$ {melhor['capex']:>15,.2f}")
    
    # Análise de custos operacionais
    custos_micro = melhor['custos_micro']
    
    print("\n⚙️  CUSTOS OPERACIONAIS ANUAIS:")
    print("-" * 80)
    print(f"   Energia comprada:   R$ {custos_micro['custo_energia_comprada']:>15,.2f}")
    print(f"   Energia vendida:    R$ {custos_micro['receita_energia_vendida']:>15,.2f} (receita)")
    print(f"   Demanda:            R$ {custos_micro['custo_demanda']:>15,.2f}")
    print(f"   Diesel:             R$ {custos_micro['custo_diesel']:>15,.2f}")
    print(f"   O&M (2% CAPEX):     R$ {melhor['capex'] * 0.02:>15,.2f}")
    
    # Comparação com cenário base
    from analise_financeira import AnaliseFinanceiraMicrorrede
    analise_temp = AnaliseFinanceiraMicrorrede()
    custos_base = analise_temp.calcular_custos_sem_microrrede()
    
    print("\n📊 COMPARAÇÃO COM CENÁRIO SEM MICRORREDE:")
    print("-" * 80)
    print(f"   Custo sem microrrede:      R$ {custos_base['custo_total']:>15,.2f}/ano")
    print(f"   Custo com microrrede ótima: R$ {custos_micro['custo_total']:>15,.2f}/ano")
    print(f"   ECONOMIA ANUAL:             R$ {melhor['economia_anual']:>15,.2f}/ano")
    reducao_percentual = (melhor['economia_anual'] / custos_base['custo_total']) * 100
    print(f"   Redução percentual:         {reducao_percentual:>15.1f}%")
    
    # ROI simplificado
    roi_simples = (melhor['economia_anual'] / melhor['capex']) * 100
    payback_simples = melhor['capex'] / melhor['economia_anual']
    
    print("\n💡 MÉTRICAS SIMPLIFICADAS:")
    print("-" * 80)
    print(f"   ROI anual:                  {roi_simples:>15.1f}%")
    print(f"   Payback simples:            {payback_simples:>15.1f} anos")
    
    # Recomendações
    print("\n✅ RECOMENDAÇÕES:")
    print("-" * 80)
    
    if melhor['vpl'] > 0:
        print("   ✓ PROJETO VIÁVEL - VPL positivo indica retorno financeiro atrativo")
    else:
        print("   ✗ PROJETO NÃO VIÁVEL - VPL negativo indica retorno insuficiente")
    
    if melhor['economia_anual'] > melhor['capex'] * 0.1:
        print("   ✓ BOA ECONOMIA ANUAL - Retorno > 10% do CAPEX")
    
    percentual_diesel = (custos_micro['energia_diesel_kwh'] / (500*24*365)) * 100
    if percentual_diesel < 10:
        print(f"   ✓ USO DE DIESEL BAIXO - Apenas {percentual_diesel:.1f}% da energia")
    elif percentual_diesel < 30:
        print(f"   ⚠ USO DE DIESEL MODERADO - {percentual_diesel:.1f}% da energia")
    else:
        print(f"   ✗ USO DE DIESEL ALTO - {percentual_diesel:.1f}% da energia")
        print("     Considere aumentar capacidade PV ou BESS")
    
    print("\n" + "=" * 80)
    print("✅ OTIMIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
    print("\nArquivos gerados:")
    print("  • otimizacao_microrrede.png - Gráficos de convergência e análises")
    print("  • otimizacao_rapida.csv - Histórico de todas as avaliações")
    print("=" * 80)
    
    return otimizador


def analise_sensibilidade_custos():
    """
    Analisa sensibilidade do ótimo a variações de custos
    """
    print("\n" + "=" * 80)
    print("ANÁLISE DE SENSIBILIDADE - VARIAÇÃO DE CUSTOS")
    print("=" * 80)
    
    import matplotlib.pyplot as plt
    
    # Cenário base
    custo_pv_base = 3200
    custo_bess_base = 2200
    
    # Variações
    variacoes = np.linspace(0.7, 1.3, 7)  # -30% a +30%
    
    resultados = {
        'variacao_pv': {'multiplic': [], 'vpl': [], 'pv_opt': [], 'bess_opt': []},
        'variacao_bess': {'multiplic': [], 'vpl': [], 'pv_opt': [], 'bess_opt': []}
    }
    
    print("\nTestando sensibilidade ao custo do PV...")
    for mult in variacoes:
        otim = OtimizadorMicrorrede(
            custo_pv_kw=custo_pv_base * mult,
            custo_bess_kwh=custo_bess_base
        )
        
        otim.otimizar_evolucao_diferencial(
            bounds=[(600, 2000), (250, 550), (3, 5), (150, 350)],
            maxiter=20,
            popsize=8
        )
        
        resultados['variacao_pv']['multiplic'].append(mult)
        resultados['variacao_pv']['vpl'].append(otim.melhor_vpl)
        resultados['variacao_pv']['pv_opt'].append(otim.melhor_config['pv_kw'])
        resultados['variacao_pv']['bess_opt'].append(otim.melhor_config['bess_kwh'])
        
        print(f"  Custo PV x{mult:.2f}: VPL = R$ {otim.melhor_vpl/1e6:.2f}M, "
              f"PV = {otim.melhor_config['pv_kw']:.0f}kW")
    
    print("\nTestando sensibilidade ao custo do BESS...")
    for mult in variacoes:
        otim = OtimizadorMicrorrede(
            custo_pv_kw=custo_pv_base,
            custo_bess_kwh=custo_bess_base * mult
        )
        
        otim.otimizar_evolucao_diferencial(
            bounds=[(600, 2000), (250, 550), (3, 5), (150, 350)],
            maxiter=20,
            popsize=8
        )
        
        resultados['variacao_bess']['multiplic'].append(mult)
        resultados['variacao_bess']['vpl'].append(otim.melhor_vpl)
        resultados['variacao_bess']['pv_opt'].append(otim.melhor_config['pv_kw'])
        resultados['variacao_bess']['bess_opt'].append(otim.melhor_config['bess_kwh'])
        
        print(f"  Custo BESS x{mult:.2f}: VPL = R$ {otim.melhor_vpl/1e6:.2f}M, "
              f"BESS = {otim.melhor_config['bess_kwh']:.0f}kWh")
    
    # Plotar
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # VPL vs Custo PV
    ax1 = axes[0, 0]
    ax1.plot(np.array(resultados['variacao_pv']['multiplic']) * custo_pv_base,
            np.array(resultados['variacao_pv']['vpl']) / 1e6, 'o-', linewidth=2)
    ax1.set_xlabel('Custo PV (R$/kW)', fontsize=11)
    ax1.set_ylabel('VPL Ótimo (R$ M)', fontsize=11)
    ax1.set_title('Sensibilidade: VPL vs Custo PV', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Capacidade PV ótima vs Custo PV
    ax2 = axes[0, 1]
    ax2.plot(np.array(resultados['variacao_pv']['multiplic']) * custo_pv_base,
            resultados['variacao_pv']['pv_opt'], 'o-', linewidth=2, color='orange')
    ax2.set_xlabel('Custo PV (R$/kW)', fontsize=11)
    ax2.set_ylabel('Capacidade PV Ótima (kW)', fontsize=11)
    ax2.set_title('Sensibilidade: Capacidade PV Ótima vs Custo PV', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # VPL vs Custo BESS
    ax3 = axes[1, 0]
    ax3.plot(np.array(resultados['variacao_bess']['multiplic']) * custo_bess_base,
            np.array(resultados['variacao_bess']['vpl']) / 1e6, 'o-', linewidth=2, color='green')
    ax3.set_xlabel('Custo BESS (R$/kWh)', fontsize=11)
    ax3.set_ylabel('VPL Ótimo (R$ M)', fontsize=11)
    ax3.set_title('Sensibilidade: VPL vs Custo BESS', fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # Capacidade BESS ótima vs Custo BESS
    ax4 = axes[1, 1]
    ax4.plot(np.array(resultados['variacao_bess']['multiplic']) * custo_bess_base,
            resultados['variacao_bess']['bess_opt'], 'o-', linewidth=2, color='purple')
    ax4.set_xlabel('Custo BESS (R$/kWh)', fontsize=11)
    ax4.set_ylabel('Capacidade BESS Ótima (kWh)', fontsize=11)
    ax4.set_title('Sensibilidade: Capacidade BESS Ótima vs Custo BESS', fontweight='bold')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('sensibilidade_custos.png', dpi=150, bbox_inches='tight')
    print("\n📊 Gráfico salvo: 'sensibilidade_custos.png'")
    plt.show()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--sensibilidade':
        analise_sensibilidade_custos()
    else:
        otimizacao_rapida()
