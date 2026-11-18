"""
Script para inspecionar os dados filtrados da Equatorial GO
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
    
    # Filtrar por Tarifa de Aplicação
    df_aplicacao = df_a4[df_a4['DscBaseTarifaria'] == 'Tarifa de Aplicação']
    
    # Pegar a última vigência
    data_max = df_aplicacao['DatInicioVigencia'].max()
    print(f"Última vigência encontrada: {data_max}")
    
    df_recente = df_aplicacao[df_aplicacao['DatInicioVigencia'] == data_max]
    
    print(f"\nTotal de registros (última vigência): {len(df_recente)}")
    
    # Filtrar por modalidade
    df_azul = df_recente[df_recente['DscModalidadeTarifaria'] == 'Azul']
    df_verde = df_recente[df_recente['DscModalidadeTarifaria'] == 'Verde']
    
    print(f"\nRegistros Azul: {len(df_azul)}")
    print(f"Registros Verde: {len(df_verde)}")
    
    # Mostrar alguns registros da Azul
    print("\n" + "="*100)
    print("Amostra de registros AZUL (DscDetalhe='Não se aplica'):")
    print("="*100)
    
    df_azul_na = df_azul[df_azul['DscDetalhe'] == 'Não se aplica']
    
    colunas_importantes = ['DscModalidadeTarifaria', 'DscDetalhe', 'NomPostoTarifario', 
                          'DscUnidadeTerciaria', 'SigAgenteAcessante', 'VlrTUSD', 'VlrTE']
    
    print(df_azul_na[colunas_importantes].to_string(index=False))
    
    print("\n" + "="*100)
    print("Amostra de registros VERDE (DscDetalhe='Não se aplica'):")
    print("="*100)
    
    df_verde_na = df_verde[df_verde['DscDetalhe'] == 'Não se aplica']
    print(df_verde_na[colunas_importantes].to_string(index=False))
    
    # Verificar valores únicos
    print("\n" + "="*100)
    print("Valores únicos de DscUnidadeTerciaria:")
    print(df_recente['DscUnidadeTerciaria'].unique())
    
    print("\nValores únicos de NomPostoTarifario:")
    print(df_recente['NomPostoTarifario'].unique())
    
    print("\nValores únicos de SigAgenteAcessante (primeiros 20):")
    print(df_recente['SigAgenteAcessante'].unique()[:20])
