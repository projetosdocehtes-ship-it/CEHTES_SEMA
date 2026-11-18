"""
Script para testar a URL exata fornecida pelo usuário
"""

import requests
import json

# URL exata fornecida
url = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search?resource_id=fcf2906c-7c32-4b9b-a637-054e7a5234f4&q=Equatorial%20GO"

print("Testando URL fornecida pelo usuário")
print("=" * 60)

response = requests.get(url, timeout=30)
data = response.json()

print(f"Status da resposta: {response.status_code}")
print(f"Success: {data.get('success')}")

if data.get('success'):
    result = data.get('result', {})
    records = result.get('records', [])
    total = result.get('total', 0)
    
    print(f"\nTotal de registros: {total}")
    print(f"Registros retornados: {len(records)}")
    
    if records:
        print(f"\nPrimeiro registro:")
        for key, value in records[0].items():
            print(f"  {key}: {value}")
else:
    print(f"Erro: {data.get('error')}")
