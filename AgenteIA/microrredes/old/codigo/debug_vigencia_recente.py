"""
Verificar os 20 registros da vigência mais recente
"""

import requests
import pandas as pd

url = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
params = {
    'resource_id': 'fcf2906c-7c32-4b9b-a637-054e7a5234f4',
    'q': 'Equatorial GO',
    'limit': 1000
}

response = requests.get(url, params=params, timeout=30)
data = response.json()

if data.get('success'):
    records = data.get('result', {}).get('records', [])
    df = pd.DataFrame(records)
    
    # Filtrar por grupo A4
    df_a4 = df[df['DscSubGrupo'] == 'A4']
    
    # Converter data
    df_a4['DatInicioVigencia_dt'] = pd.to_datetime(df_a4['DatInicioVigencia'], format='%Y-%m-%d', errors='coerce')
    
    # Filtrar Tarifa de Aplicação
    df_aplicacao = df_a4[df_a4['DscBaseTarifaria'] == 'Tarifa de Aplicação']
    
    # Filtrar Azul/Verde
    df_av = df_aplicacao[df_aplicacao['DscModalidadeTarifaria'].isin(['Azul', 'Verde'])]
    
    # Pegar última vigência
    data_max = df_av['DatInicioVigencia_dt'].max()
    df_recente = df_av[df_av['DatInicioVigencia_dt'] == data_max]
    
    print(f"Vigência mais recente: {data_max.strftime('%Y-%m-%d')}")
    print(f"Total de registros: {len(df_recente)}\n")
    
    colunas = ['DscModalidadeTarifaria', 'DscDetalhe', 'NomPostoTarifario', 
               'DscUnidadeTerciaria', 'SigAgenteAcessante', 'VlrTUSD', 'VlrTE']
    
    print("="*120)
    print("TODOS OS REGISTROS DA VIGÊNCIA MAIS RECENTE:")
    print("="*120)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 120)
    print(df_recente[colunas].to_string(index=True))
    
    print("\n" + "="*120)
    print("FILTRO: DscDetalhe = 'Não se aplica'")
    print("="*120)
    df_na = df_recente[df_recente['DscDetalhe'] == 'Não se aplica']
    print(df_na[colunas].to_string(index=True))
