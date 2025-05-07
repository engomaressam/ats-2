import psycopg2
import pandas as pd

DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

OUTPUT_EXCEL = 'unique_crm_pleasesepcify.xlsx'

def main():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT crm_pleasesepcify FROM pdf_extracted_data WHERE crm_pleasesepcify IS NOT NULL")
            rows = cur.fetchall()
            values = [row[0] for row in rows]
            print(f"Found {len(values)} unique values.")
            df = pd.DataFrame({'crm_pleasesepcify': values})
            df.to_excel(OUTPUT_EXCEL, index=False)
            print(f"Exported to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main() 