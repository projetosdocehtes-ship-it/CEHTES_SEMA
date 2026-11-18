# pip install pandas sqlalchemy psycopg2-binary

import pandas as pd
from sqlalchemy import create_engine, text

# 1) ajuste estes parâmetros
USER = "postgres"
PASSWORD = "CONFIGURAR_LOCALMENTE"
HOST = "127.0.0.1"
PORT = 5432
DBNAME = "cartorio"
TABLENAME = "cec_modules"  # nome da tabela destino

# 2) lê o CSV
df = pd.read_csv(
    r"C:\Cethes\CEHTES_SEMA\AgenteIA\prime-django\apps\home\CEC Modules.csv"
)

# 3) cria engine (use future=True para o estilo 2.0)
engine = create_engine(
    f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}", future=True
)

# 4) (opcional) criar tabela se não existir
cols = df.columns
ddl = f"""
CREATE TABLE IF NOT EXISTS "{TABLENAME}" (
{',\n'.join(f'    "{c}" TEXT' for c in cols)}
)
"""

# 5) executa o DDL via conexão
with engine.begin() as conn:  # abre uma transação
    conn.execute(text(ddl))  # usa text() para SQL puro

# 6) importa os dados em lotes
df.to_sql(
    TABLENAME,
    engine,
    if_exists="append",  # ou "replace" se quiser recriar
    index=False,
    method="multi",
)

print("Importação concluída!")
