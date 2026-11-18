"""
Script para inspecionar a estrutura da resposta da API
"""

import requests
import json

# Testar a API com Equatorial GO
url = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
params = {
    'resource_id': 'fcf2906c-7c32-4b9b-a637-054e7a5234f4',
    'q': 'Equatorial GO',
    'limit': 5
}

print("Testando API com query: 'Equatorial GO'")
print("=" * 60)

response = requests.get(url, params=params, timeout=30)
data = response.json()

if data.get('success'):
    records = data.get('result', {}).get('records', [])
    print(f"\nTotal de registros encontrados: {len(records)}")
    
    if records:
        print(f"\nPrimeiro registro:")
        print(json.dumps(records[0], indent=2, ensure_ascii=False))
        
        print(f"\nColunas disponíveis:")
        for key in records[0].keys():
            print(f"  - {key}")
else:
    print(f"Erro: {data}")
