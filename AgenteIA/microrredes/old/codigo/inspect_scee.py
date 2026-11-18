import requests
import pandas as pd

def inspect_scee_details():
    url = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
    params = {
        'resource_id': "fcf2906c-7c32-4b9b-a637-054e7a5234f4",
        'q': "SCEE", 
        'limit': 50
    }
    
    print("Fetching SCEE data...")
    r = requests.get(url, params=params)
    data = r.json()
    records = data['result']['records']
    df = pd.DataFrame(records)
    
    if not df.empty:
        # Check if Equatorial has SCEE
        equatorial = df[df['SigAgente'].str.contains('EQUATORIAL', na=False, case=False)]
        
        print("\nAll SCEE records found: ", len(df))
        print("Equatorial SCEE records: ", len(equatorial))
        
        if not equatorial.empty:
            print("\nSample Equatorial SCEE:")
            print(equatorial.iloc[0][['SigAgente', 'DscModalidadeTarifaria', 'NomPostoTarifario', 'VlrTE']].to_dict())
        else:
            print("\nNo Equatorial SCEE found in sample. showing first 5 agents:")
            print(df['SigAgente'].unique()[:5])

if __name__ == "__main__":
    inspect_scee_details()
