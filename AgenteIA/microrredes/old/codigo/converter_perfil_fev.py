"""
Converte perfil_carga_horaria_fev.csv para o formato do perfil_carga_ifg.csv
"""

import pandas as pd
import numpy as np

# Ler dados originais
df = pd.read_csv('perfil_carga_horaria_fev.csv')

# Converter datetime para formato pandas
df['datetime'] = pd.to_datetime(df['datetime'])

# Adicionar coluna de hora (0-23)
df['hora'] = df['datetime'].dt.hour

# Identificar dia da semana (0=segunda, 6=domingo)
df['dia_semana_num'] = df['datetime'].dt.dayofweek

# Classificar como util ou fim_semana
df['tipo_dia'] = df['dia_semana_num'].apply(lambda x: 'util' if x < 5 else 'fim_semana')

# Calcular MÁXIMO de demanda por hora e tipo de dia
perfil_agregado = df.groupby(['hora', 'tipo_dia'])['dem_ativa_kw'].max().reset_index()

# Renomear coluna
perfil_agregado = perfil_agregado.rename(columns={'dem_ativa_kw': 'demanda_kw', 'tipo_dia': 'dia_semana'})

# Arredondar valores
perfil_agregado['demanda_kw'] = perfil_agregado['demanda_kw'].round(0).astype(int)

# Reordenar: primeiro dias úteis (0-23h), depois fins de semana (0-23h)
perfil_util = perfil_agregado[perfil_agregado['dia_semana'] == 'util'].sort_values('hora')
perfil_fds = perfil_agregado[perfil_agregado['dia_semana'] == 'fim_semana'].sort_values('hora')

# Concatenar
perfil_final = pd.concat([perfil_util, perfil_fds], ignore_index=True)

# Salvar
perfil_final.to_csv('perfil_carga_horaria_fev.csv', index=False)

print("✓ Arquivo convertido com sucesso!")
print(f"\nResumo:")
print(f"  Total de linhas: {len(perfil_final)}")
print(f"  Dias úteis: {len(perfil_util)} horas")
print(f"  Fins de semana: {len(perfil_fds)} horas")
print(f"\nDemanda média:")
print(f"  Dias úteis: {perfil_util['demanda_kw'].mean():.1f} kW")
print(f"  Fins de semana: {perfil_fds['demanda_kw'].mean():.1f} kW")
print(f"\nDemanda máxima:")
print(f"  Dias úteis: {perfil_util['demanda_kw'].max():.0f} kW (hora {perfil_util.loc[perfil_util['demanda_kw'].idxmax(), 'hora']:.0f}h)")
print(f"  Fins de semana: {perfil_fds['demanda_kw'].max():.0f} kW (hora {perfil_fds.loc[perfil_fds['demanda_kw'].idxmax(), 'hora']:.0f}h)")

print("\nPrimeiras linhas do arquivo convertido:")
print(perfil_final.head(10))
