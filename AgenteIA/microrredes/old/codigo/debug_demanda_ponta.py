from caso_ifg import CasoIFG
import pandas as pd

caso = CasoIFG(modalidade='verde')
r = caso.simular_dia()
df = pd.DataFrame(r)
ponta = df[(df['hora'] >= 18) & (df['hora'] < 21)]

print('\nDemanda na PONTA (18h-21h):')
print(ponta[['hora', 'demanda_kw', 'soc_bess_kwh', 'potencia_bess_kw', 'energia_rede_kw']])
print(f'\nDemanda total ponta: {ponta["demanda_kw"].sum():.1f} kWh')
print(f'Demanda média ponta: {ponta["demanda_kw"].mean():.1f} kW')
