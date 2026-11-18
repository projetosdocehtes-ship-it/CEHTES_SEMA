"""
Script para investigar todas as vigências e modalidades disponíveis
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
    
    print(f"Total de registros A4: {len(df_a4)}")
    
    # Verificar vigências e modalidades disponíveis
    print("\n" + "="*80)
    print("Vigências e Modalidades Disponíveis:")
    print("="*80)
    
    vigencias_modalidades = df_a4.groupby(['DatInicioVigencia', 'DscBaseTarifaria', 'DscModalidadeTarifaria']).size().reset_index(name='count')
    print(vigencias_modalidades.sort_values('DatInicioVigencia', ascending=False).to_string(index=False))
    
    # Focar na modalidade "Azul" e "Verde"
    print("\n" + "="*80)
    print("Buscando registros de modalidade Azul ou Verde:")
    print("="*80)
    
    df_azul_verde = df_a4[df_a4['DscModalidadeTarifaria'].isin(['Azul', 'Verde'])]
    
    if not df_azul_verde.empty:
        print(f"Total de registros Azul/Verde: {len(df_azul_verde)}")
        
        # Última vigência com Azul/Verde
        data_max_av = df_azul_verde['DatInicioVigencia'].max()
        print(f"Última vigência Azul/Verde: {data_max_av}")
        
        df_recente_av = df_azul_verde[df_azul_verde['DatInicioVigencia'] == data_max_av]
        
        print(f"\nDetalhes da última vigência ({data_max_av}):")
        colunas = ['DscBaseTarifaria', 'DscModalidadeTarifaria', 'DscDetalhe', 'NomPostoTarifario', 
                   'DscUnidadeTerciaria', 'SigAgenteAcessante', 'VlrTUSD', 'VlrTE']
        print(df_recente_av[colunas].to_string(index=False))
    else:
        print("Nenhum registro Azul ou Verde encontrado!")
        print("\nModalidades disponíveis:")
        print(df_a4['DscModalidadeTarifaria'].unique())
