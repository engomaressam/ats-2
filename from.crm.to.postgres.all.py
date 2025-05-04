import requests
import pandas as pd
from sqlalchemy import create_engine

# --------------------------
# CRM API Configuration
# --------------------------
crm_url = "http://10.10.11.222/RMECRM/api/data/v8.2/new_jobapplications?$top=5000&$orderby=createdon desc&$expand=new_jobapplication_Annotations"
crm_auth = ('Omar Essam', 'PMO@1234')  # Use Basic Auth

# --------------------------
# PostgreSQL Configuration
# --------------------------
pg_user = "postgres"
pg_pass = "PMO@1234"
pg_host = "localhost"
pg_port = "5432"
pg_db   = "postgres"
pg_table = "crm_jobapplications"

# SQLAlchemy connection string
pg_engine = create_engine(f'postgresql+psycopg2://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')

# --------------------------
# Fetch CRM Data
# --------------------------
print("📡 Fetching CRM data...")
response = requests.get(crm_url, auth=crm_auth)

if response.status_code != 200:
    print(f"❌ Failed to fetch CRM data: {response.status_code}")
    exit()

crm_data = response.json().get('value', [])
print(f"✅ Fetched {len(crm_data)} records.")

# Normalize nested JSON (flatten)
df = pd.json_normalize(crm_data)

# Clean column names
df.columns = [col.replace('.', '_') for col in df.columns]

# --------------------------
# Insert into PostgreSQL
# --------------------------
print("📥 Inserting into PostgreSQL...")
df.to_sql(pg_table, con=pg_engine, if_exists='replace', index=False)
print(f"✅ Data inserted into table '{pg_table}' in PostgreSQL.")
