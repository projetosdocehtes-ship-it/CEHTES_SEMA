"""
Script de execução: Comparação IFG (PV vs PV+BESS)
"""
from comparador_generico import ComparadorGenerico, Cenario

def main():
    print("Iniciando comparação para o caso IFG...")
    
    comparador = ComparadorGenerico()
    
    # 1. Caso Base: Somente PV (254 kWp)
    base = Cenario(
        nome="Base (PV 254 kWp)",
        pv_kwp=254,
        bess_kwh=0, # Sem BESS
        bess_kw=0,
        usar_diesel=False,
        cor='orange'
    )
    comparador.adicionar_cenario(base)
    
    # 2. Caso Alternativo: PV + BESS (500 kWh)
    alt = Cenario(
        nome="PV 254 + BESS 500",
        pv_kwp=254,
        bess_kwh=500,
        bess_kw=230, # Potência default do caso IFG
        usar_diesel=False,
        cor='green'
    )
    comparador.adicionar_cenario(alt)

    # 3. Caso Expandido + BESS: PV 324 kWp + BESS 500 kWh
    exp_bess = Cenario(
        nome="PV 324 + BESS 500",
        pv_kwp=324,
        bess_kwh=500,
        bess_kw=230,
        usar_diesel=False,
        cor='blue'
    )
    comparador.adicionar_cenario(exp_bess)
    
    # Executar
    comparador.executar_simulacoes()
    
    # Gerar relatórios
    print("\n" + "="*80)
    print(" RESULTADOS DETALHADOS")
    print("="*80)
    df = comparador.gerar_tabela_comparativa()
    if df is not None:
        print(df.to_string(index=False))
        
        # Salvar em CSV também para facilitar
        df.to_csv('resultados_comparacao.csv', index=False)
    
    # Gerar gráficos
    comparador.gerar_graficos(output_file='comparacao_ifg_vs_bess.png')

if __name__ == "__main__":
    main()
