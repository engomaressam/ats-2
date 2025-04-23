import os
import psycopg2
import pandas as pd

# Database connection parameters
DB_PARAMS = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'PMO@1234',
    'host': 'localhost',
    'port': '5432'
}

def get_unmatched_records():
    """Get records where job_title is None or department is None"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Get records with missing job title or department
        cur.execute("""
            SELECT id, pdf_filename, job_title, department, skills, ocr_result 
            FROM pdf_extracted_data 
            WHERE job_title IS NULL 
            OR department IS NULL 
            OR job_title = '' 
            OR department = ''
        """)
        
        records = cur.fetchall()
        
        # Load standard job titles and departments
        job_titles_df = pd.read_excel("Active_Job_Name.xlsx")
        departments_df = pd.read_excel("Active_Crew.xlsx")
        
        standard_jobs = job_titles_df['JobName'].str.lower().tolist()
        standard_depts = departments_df['Department'].str.lower().unique().tolist()
        
        print("\nUnmatched Records Report")
        print("=======================")
        print(f"Found {len(records)} unmatched records\n")
        
        # Create a file to store the report
        with open('unmatched_records_report.txt', 'w', encoding='utf-8') as f:
            f.write("Unmatched Records Report\n")
            f.write("=======================\n\n")
            
            for record in records:
                record_id, filename, job_title, department, skills, ocr_text = record
                f.write(f"Record ID: {record_id}\n")
                f.write(f"Filename: {filename}\n")
                f.write(f"Current Job Title: {job_title}\n")
                f.write(f"Current Department: {department}\n")
                f.write(f"Skills: {skills}\n")
                f.write("-" * 80 + "\n\n")
                
                print(f"Record ID: {record_id}")
                print(f"Filename: {filename}")
                print(f"Current Job Title: {job_title}")
                print(f"Current Department: {department}")
                print("-" * 40)
        
        print("\nFull report has been saved to 'unmatched_records_report.txt'")
        print("\nAvailable Standard Job Titles:", ", ".join(standard_jobs[:10]), "... and more")
        print("\nAvailable Standard Departments:", ", ".join(standard_depts))
        
        cur.close()
        conn.close()
        
        return records
    except Exception as e:
        print(f"Error getting unmatched records: {e}")
        return []

if __name__ == "__main__":
    get_unmatched_records() 