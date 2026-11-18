from caso_ifg import CasoIFG

print("="*80)
print("INVESTIGAÇÃO: POR QUE PV ESTÁ AUMENTANDO O CUSTO?")
print("="*80)

# Cenário SEM PV
caso_sem = CasoIFG('EQUATORIAL GO', 'verde')
caso_sem.pv_potencia_kwp = 0
caso_sem.bess_capacidade_kwh = 0
caso_sem.usar_diesel = False
r_sem = caso_sem.simular_mes()

print(f"\n📊 SEM PV:")
print(f"  Energia comprada: {r_sem['energia_comprada_kwh']:,.0f} kWh")
print(f"  Energia vendida: {r_sem.get('energia_vendida_kwh', 0):,.0f} kWh")
print(f"  Custo total: R$ {r_sem['custo_mensal']:,.2f}")

# Cenário COM 300 kWp PV
caso_com = CasoIFG('EQUATORIAL GO', 'verde')
caso_com.pv_potencia_kwp = 300
caso_com.bess_capacidade_kwh = 0
caso_com.usar_diesel = False
caso_com._configurar_pv()
r_com = caso_com.simular_mes()

print(f"\n📊 COM 300 kWp PV:")
print(f"  Energia comprada: {r_com['energia_comprada_kwh']:,.0f} kWh")
print(f"  Energia vendida: {r_com.get('energia_vendida_kwh', 0):,.0f} kWh")
print(f"  Custo total: R$ {r_com['custo_mensal']:,.2f}")

# Análise detalhada
print(f"\n🔍 ANÁLISE:")
print(f"  Diferença energia comprada: {r_com['energia_comprada_kwh'] - r_sem['energia_comprada_kwh']:+,.0f} kWh")
print(f"  Diferença custo: R$ {r_com['custo_mensal'] - r_sem['custo_mensal']:+,.2f}")

# Verificar tarifas
from tarifas_aneel import TarifasANEEL
tarifas = TarifasANEEL('EQUATORIAL GO', usar_api=True)
print(f"\n💰 TARIFAS:")
print(f"  TE Ponta: R$ {tarifas.dados_tarifa['te_ponta']:.4f}/kWh")
print(f"  TE Fora Ponta: R$ {tarifas.dados_tarifa['te_fora_ponta']:.4f}/kWh")
print(f"  TUSD Ponta: R$ {tarifas.dados_tarifa['tusd_ponta']:.4f}/kWh")
print(f"  TUSD Fora Ponta: R$ {tarifas.dados_tarifa['tusd_fora_ponta']:.4f}/kWh")

# Verificar SCEE
scee = tarifas.dados_tarifa.get('scee', {})
scee_verde = scee.get('verde', {})
print(f"\n📤 SCEE (Compensação) VERDE:")
print(f"  Ponta: R$ {scee_verde.get('te_ponta', 0) + scee_verde.get('tusd_ponta', 0):.4f}/kWh")
print(f"  Fora Ponta: R$ {scee_verde.get('te_fora_ponta', 0) + scee_verde.get('tusd_fora_ponta', 0):.4f}/kWh")

print("\n" + "="*80)
