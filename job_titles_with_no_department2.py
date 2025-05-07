import psycopg2
import pandas as pd

DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

OUTPUT_EXCEL = 'job_titles_with_no_department2.xlsx'

def main():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            # Count how many rows have department2 as NULL
            cur.execute("SELECT COUNT(*) FROM pdf_extracted_data WHERE department2 IS NULL")
            null_count = cur.fetchone()[0]
            print(f"Rows with department2=NULL: {null_count}")

            # Get unique job titles with department2=NULL
            cur.execute("SELECT DISTINCT job_title FROM pdf_extracted_data WHERE department2 IS NULL AND job_title IS NOT NULL")
            rows = cur.fetchall()
            job_titles = [row[0] for row in rows]
            print(f"Unique job titles with department2=NULL: {len(job_titles)}")

            # Save to Excel
            df = pd.DataFrame({'job_title': job_titles})
            df.to_excel(OUTPUT_EXCEL, index=False)
            print(f"Exported to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main() 