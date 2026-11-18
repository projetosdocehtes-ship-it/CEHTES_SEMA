"""
Script para buscar registros mais recentes da Equatorial GO
"""

import requests
import json
import pandas as pd

# Testar a API com Equatorial GO
url = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
params = {
    'resource_id': 'fcf2906c-7c32-4b9b-a637-054e7a5234f4',
    'q': 'Equatorial GO',
    'limit': 1000
}

print("Buscando todos os registros da Equatorial GO")
print("=" * 60)

response = requests.get(url, params=params, timeout=30)
data = response.json()

if data.get('success'):
    records = data.get('result', {}).get('records', [])
    print(f"\nTotal de registros encontrados: {len(records)}")
    
    if records:
        df = pd.DataFrame(records)
        
        # Verificar colunas
        print(f"\nColunas disponíveis:")
        print(df.columns.tolist())
        
        # Filtrar por grupo A4
        if 'DscSubGrupo' in df.columns:
            df_a4 = df[df['DscSubGrupo'] == 'A4']
            print(f"\nRegistros grupo A4: {len(df_a4)}")
            
            if not df_a4.empty:
                # Ordenar por data de vigência
                df_a4_sorted = df_a4.sort_values('DatInicioVigencia', ascending=False)
                print(f"\nÚltimos 3 registros (mais recentes):")
                print(df_a4_sorted[['DatInicioVigencia', 'DscModalidadeTarifaria', 'DscDetalhe', 'NomPostoTarifario', 'VlrTUSD', 'VlrTE']].head(10))
        else:
            print("\nColuna DscSubGrupo não encontrada")
else:
    print(f"Erro: {data}")
