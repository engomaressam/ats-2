import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import os

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

EXCEL_PATH = 'Active_Crew.xlsx'


def get_jobtitle_department_mapping(excel_path):
    df = pd.read_excel(excel_path)
    # Use exact column names from the Excel file
    job_title_col = 'Job Name'
    department_col = 'Department'
    if job_title_col not in df.columns or department_col not in df.columns:
        raise Exception('Could not find Job Name or Department columns in Excel')
    mapping = dict(zip(df[job_title_col].astype(str).str.strip(), df[department_col].astype(str).str.strip()))
    return mapping


def add_department2_column():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'pdf_extracted_data' AND column_name = 'department2'
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE pdf_extracted_data ADD COLUMN department2 TEXT")
                print("Added department2 column.")
            else:
                print("department2 column already exists.")
            conn.commit()


def update_department2(mapping):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all unique job titles in the database
            cur.execute("SELECT DISTINCT job_title FROM pdf_extracted_data WHERE job_title IS NOT NULL")
            db_job_titles = [row['job_title'].strip() for row in cur.fetchall() if row['job_title']]
            print(f"Found {len(db_job_titles)} unique job titles in DB.")
            # For each job title, update department2 if mapping exists, else set to NULL
            for job_title in db_job_titles:
                dept = mapping.get(job_title)
                if dept:
                    cur.execute("""
                        UPDATE pdf_extracted_data SET department2 = %s WHERE job_title = %s
                    """, (dept, job_title))
                else:
                    cur.execute("""
                        UPDATE pdf_extracted_data SET department2 = NULL WHERE job_title = %s
                    """, (job_title,))
            conn.commit()
            print("department2 column updated.")


def main():
    mapping = get_jobtitle_department_mapping(EXCEL_PATH)
    add_department2_column()
    update_department2(mapping)

if __name__ == "__main__":
    main() 