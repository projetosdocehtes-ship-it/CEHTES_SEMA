"""
Teste da otimização corrigida - verificar se está evitando compra na ponta
e priorizando exportação PV na ponta
"""

from caso_ifg import CasoIFG
import pandas as pd

# Criar caso IFG com modalidade Verde
caso = CasoIFG(modalidade='verde')

# Simular um dia útil
print("\n" + "="*90)
print("TESTE: OTIMIZAÇÃO CORRIGIDA - Análise Horária")
print("="*90)

resultado = caso.simular_dia(dia_semana=0)  # Segunda-feira

# Converter para DataFrame
df = pd.DataFrame(resultado)

# Verificar tarifas
print("\n💰 TARIFAS:")
print(f"  Ponta (18h-21h):      R$ 2,14/kWh (compra) | R$ 1,70/kWh (venda SCEE)")
print(f"  Fora Ponta:           R$ 0,45/kWh (compra) | R$ 0,19/kWh (venda SCEE)")
print(f"  Diferencial:          4,72x mais caro na ponta")

# Análise por período
print("\n" + "="*90)
print("ANÁLISE POR PERÍODO:")
print("="*90)

periodos = {
    'Madrugada (0h-6h)': (0, 6),
    'Manhã/Sol (6h-14h)': (6, 14),
    'Preparação Ponta (14h-18h)': (14, 18),
    'PONTA (18h-21h)': (18, 21),
    'Noite (21h-24h)': (21, 24)
}

for nome, (inicio, fim) in periodos.items():
    df_periodo = df[(df['hora'] >= inicio) & (df['hora'] < fim)]
    
    energia_comprada = df_periodo[df_periodo['energia_rede_kw'] > 0]['energia_rede_kw'].sum()
    energia_vendida = -df_periodo[df_periodo['energia_rede_kw'] < 0]['energia_rede_kw'].sum()
    energia_pv = df_periodo['geracao_pv_kw'].sum()
    soc_inicial = df_periodo['soc_bess_kwh'].iloc[0] if len(df_periodo) > 0 else 0
    soc_final = df_periodo['soc_bess_kwh'].iloc[-1] if len(df_periodo) > 0 else 0
    carregou_bess = soc_final - soc_inicial
    custo = df_periodo['custo_hora'].sum()
    
    print(f"\n{nome}:")
    print(f"  Energia PV:           {energia_pv:>7.1f} kWh")
    print(f"  Compra da rede:       {energia_comprada:>7.1f} kWh")
    print(f"  Venda para rede:      {energia_vendida:>7.1f} kWh")
    print(f"  Carga BESS:           {carregou_bess:>+7.1f} kWh (SOC: {soc_inicial:.0f} → {soc_final:.0f})")
    print(f"  Custo líquido:        R$ {custo:>7.2f}")

# Verificações críticas
print("\n" + "="*90)
print("VERIFICAÇÕES CRÍTICAS:")
print("="*90)

# 1. Compra na ponta
df_ponta = df[(df['hora'] >= 18) & (df['hora'] < 21)]
compra_ponta = df_ponta[df_ponta['energia_rede_kw'] > 0]['energia_rede_kw'].sum()
venda_ponta = -df_ponta[df_ponta['energia_rede_kw'] < 0]['energia_rede_kw'].sum()

print(f"\n✓ Compra na PONTA:      {compra_ponta:.1f} kWh")
if compra_ponta > 50:
    print(f"  ⚠️  ATENÇÃO: Comprando muita energia na ponta (tarifa cara R$ 2,14/kWh)")
elif compra_ponta > 0:
    print(f"  ⚠️  Comprando energia na ponta (deveria usar BESS)")
else:
    print(f"  ✓ OK: Não está comprando na ponta!")

print(f"\n✓ Venda na PONTA:       {venda_ponta:.1f} kWh")
if venda_ponta > 0:
    print(f"  ✓ ÓTIMO: Exportando PV na ponta (receita R$ 1,70/kWh)")
else:
    print(f"  ⚠️  Não está exportando PV na ponta")

# 2. Compra fora ponta para carregar BESS
df_fp = df[(df['hora'] >= 8) & (df['hora'] < 18)]
compra_fp_carga_bess = 0
for _, row in df_fp.iterrows():
    if row['energia_rede_kw'] > row['demanda_kw']:
        compra_fp_carga_bess += (row['energia_rede_kw'] - row['demanda_kw'])

print(f"\n✓ Compra FP para BESS:  {compra_fp_carga_bess:.1f} kWh")
if compra_fp_carga_bess > 100:
    print(f"  ⚠️  Comprando muito fora ponta para carregar (tarifa R$ 0,45/kWh)")
elif compra_fp_carga_bess > 50:
    print(f"  ⚠️  Comprando moderado fora ponta")
elif compra_fp_carga_bess > 0:
    print(f"  ✓ OK: Compra mínima para carregar BESS")
else:
    print(f"  ✓ ÓTIMO: Não está comprando fora ponta para carregar")

# 3. Uso do BESS na ponta
descarga_ponta = 0
for _, row in df_ponta.iterrows():
    if row['potencia_bess_kw'] > 0:  # Positivo = descarga
        descarga_ponta += row['potencia_bess_kw']

print(f"\n✓ Descarga BESS na ponta: {descarga_ponta:.1f} kWh")
if descarga_ponta > 200:
    print(f"  ✓ ÓTIMO: BESS descarregando bastante na ponta")
elif descarga_ponta > 100:
    print(f"  ✓ OK: BESS ajudando na ponta")
else:
    print(f"  ⚠️  BESS poderia descarregar mais na ponta")

# Resumo financeiro
print("\n" + "="*90)
print("RESUMO FINANCEIRO DIÁRIO:")
print("="*90)
energia_comprada = sum([e for e in resultado['energia_rede_kw'] if e > 0])
energia_vendida = sum([abs(e) for e in resultado['energia_rede_kw'] if e < 0])
custo_total = sum(resultado['custo_hora'])
demanda_pico = max(resultado['demanda_kw'])

print(f"Energia comprada:        {energia_comprada:>8.1f} kWh")
print(f"Energia vendida:         {energia_vendida:>8.1f} kWh")
print(f"Custo total:             R$ {custo_total:>8.2f}")
print(f"Demanda pico:            {demanda_pico:>8.1f} kW")
print("="*90)
