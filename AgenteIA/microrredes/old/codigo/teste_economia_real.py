from caso_ifg import CasoIFG

# Simular SEM PV nem BESS
print("="*80)
print("TESTE: ECONOMIA REAL DO SISTEMA")
print("="*80)

caso_sem = CasoIFG('EQUATORIAL GO', 'verde')
caso_sem.pv_potencia_kwp = 0
caso_sem.bess_capacidade_kwh = 0
caso_sem.usar_diesel = False
r_sem = caso_sem.simular_mes()

print(f"\n📊 CENÁRIO SEM PV NEM BESS:")
print(f"  Custo mensal: R$ {r_sem['custo_mensal']:,.2f}")
print(f"  Custo anual:  R$ {r_sem['custo_mensal']*12:,.2f}")
print(f"  Energia comprada: {r_sem['energia_comprada_kwh']:,.0f} kWh/mês")

# Simular COM 300 kWp PV
caso_300 = CasoIFG('EQUATORIAL GO', 'verde')
caso_300.pv_potencia_kwp = 300
caso_300.bess_capacidade_kwh = 0
caso_300.usar_diesel = False
caso_300._configurar_pv()
r_300 = caso_300.simular_mes()

print(f"\n📊 CENÁRIO COM 300 kWp PV (BASE):")
print(f"  Custo mensal: R$ {r_300['custo_mensal']:,.2f}")
print(f"  Custo anual:  R$ {r_300['custo_mensal']*12:,.2f}")
print(f"  Energia comprada: {r_300['energia_comprada_kwh']:,.0f} kWh/mês")
print(f"  Energia vendida: {r_300['energia_vendida_kwh']:,.0f} kWh/mês")

economia_mensal_pv = r_sem['custo_mensal'] - r_300['custo_mensal']
print(f"\n💰 ECONOMIA DO PV BASE (300 kWp):")
print(f"  Economia mensal: R$ {economia_mensal_pv:,.2f}")
print(f"  Economia anual:  R$ {economia_mensal_pv*12:,.2f}")

# Simular COM 300 kWp PV + 200 kWh BESS
caso_combo = CasoIFG('EQUATORIAL GO', 'verde')
caso_combo.pv_potencia_kwp = 300
caso_combo.bess_capacidade_kwh = 200
caso_combo.usar_diesel = False
caso_combo._configurar_pv()
r_combo = caso_combo.simular_mes()

print(f"\n📊 CENÁRIO COM 300 kWp PV + 200 kWh BESS:")
print(f"  Custo mensal: R$ {r_combo['custo_mensal']:,.2f}")
print(f"  Custo anual:  R$ {r_combo['custo_mensal']*12:,.2f}")
print(f"  Energia comprada: {r_combo['energia_comprada_kwh']:,.0f} kWh/mês")
print(f"  Energia vendida: {r_combo['energia_vendida_kwh']:,.0f} kWh/mês")

economia_mensal_bess = r_300['custo_mensal'] - r_combo['custo_mensal']
economia_total_vs_sem = r_sem['custo_mensal'] - r_combo['custo_mensal']

print(f"\n💰 ECONOMIA ADICIONAL DO BESS (200 kWh):")
print(f"  Economia mensal vs base: R$ {economia_mensal_bess:,.2f}")
print(f"  Economia anual vs base:  R$ {economia_mensal_bess*12:,.2f}")
print(f"  Investimento BESS: R$ {200*1900:,.2f}")
print(f"  Payback: {200*1900/(economia_mensal_bess*12):.1f} anos")

print(f"\n💰 ECONOMIA TOTAL DO SISTEMA COMPLETO (vs sem nada):")
print(f"  Economia mensal: R$ {economia_total_vs_sem:,.2f}")
print(f"  Economia anual:  R$ {economia_total_vs_sem*12:,.2f}")

print("\n" + "="*80)
