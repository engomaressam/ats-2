import psycopg2
import pandas as pd
from typing import Tuple, Set

# Database connection parameters
DB_PARAMS = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'PMO@1234',
    'host': 'localhost',
    'port': '5432'
}

def get_standard_values() -> Tuple[Set[str], Set[str]]:
    """Get standard job titles and departments from Excel files"""
    # Load job titles
    job_titles_df = pd.read_excel("Active_Job_Name.xlsx")
    standard_job_titles = set(job_titles_df['JobName'].str.lower().unique())
    
    # Load departments
    departments_df = pd.read_excel("Active_Crew.xlsx")
    standard_departments = set(departments_df['Department'].str.lower().unique())
    
    return standard_job_titles, standard_departments

def get_database_values() -> Tuple[Set[str], Set[str]]:
    """Get unique job titles and departments from database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Get unique job titles
        cur.execute("SELECT DISTINCT LOWER(job_title) FROM pdf_extracted_data WHERE job_title IS NOT NULL AND job_title != ''")
        db_job_titles = set(row[0] for row in cur.fetchall())
        
        # Get unique departments
        cur.execute("SELECT DISTINCT LOWER(department) FROM pdf_extracted_data WHERE department IS NOT NULL AND department != ''")
        db_departments = set(row[0] for row in cur.fetchall())
        
        cur.close()
        conn.close()
        return db_job_titles, db_departments
    except Exception as e:
        print(f"Error getting database values: {e}")
        return set(), set()

def verify_values():
    """Verify that database only contains standard values"""
    # Get standard and database values
    standard_job_titles, standard_departments = get_standard_values()
    db_job_titles, db_departments = get_database_values()
    
    print("\nStandard Job Titles:")
    for title in sorted(standard_job_titles):
        print(f"- {title}")
    
    print("\nStandard Departments:")
    for dept in sorted(standard_departments):
        print(f"- {dept}")
    
    print("\nDatabase Job Titles:")
    for title in sorted(db_job_titles):
        print(f"- {title}")
    
    print("\nDatabase Departments:")
    for dept in sorted(db_departments):
        print(f"- {dept}")
    
    # Find non-standard values
    non_standard_job_titles = db_job_titles - standard_job_titles
    non_standard_departments = db_departments - standard_departments
    
    if non_standard_job_titles:
        print("\nNon-standard Job Titles found in database:")
        for title in sorted(non_standard_job_titles):
            print(f"- {title}")
    
    if non_standard_departments:
        print("\nNon-standard Departments found in database:")
        for dept in sorted(non_standard_departments):
            print(f"- {dept}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"Total standard job titles: {len(standard_job_titles)}")
    print(f"Total standard departments: {len(standard_departments)}")
    print(f"Total database job titles: {len(db_job_titles)}")
    print(f"Total database departments: {len(db_departments)}")
    print(f"Non-standard job titles: {len(non_standard_job_titles)}")
    print(f"Non-standard departments: {len(non_standard_departments)}")

if __name__ == "__main__":
    verify_values() 