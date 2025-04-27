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

def get_standard_values():
    """Get standard job titles and departments from Excel files"""
    # Load job titles
    job_titles_df = pd.read_excel("Active_Job_Name.xlsx")
    standard_job_titles = set(job_titles_df['JobName'].str.lower().unique())
    
    # Load departments
    departments_df = pd.read_excel("Active_Crew.xlsx")
    standard_departments = set(departments_df['Department'].str.lower().unique())
    
    return standard_job_titles, standard_departments

def fix_non_standard_values():
    """Fix non-standard job titles and departments in the database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Get standard values
        standard_job_titles, standard_departments = get_standard_values()
        
        # Map non-standard values to standard values
        job_title_mapping = {
            'architect': 'architecture technical office engineer',
            'hr': 'hr specialist',
            'interior designer': 'architecture technical office engineer',
            'market research analyst': 'business development specialist',
            'other': 'other',
            'other (specify)': 'other'
        }
        
        department_mapping = {
            'design department': 'technical office operations',
            'hr department': 'human resources',
            'hse department': 'hse',
            'mep department': 'mep',
            'other': 'other',
            'other (specify)': 'other'
        }
        
        # Update non-standard job titles
        for non_standard, standard in job_title_mapping.items():
            cur.execute("""
                UPDATE pdf_extracted_data 
                SET job_title = %s
                WHERE LOWER(job_title) = %s
            """, (standard, non_standard))
            print(f"Updated job title '{non_standard}' to '{standard}'")
        
        # Update non-standard departments
        for non_standard, standard in department_mapping.items():
            cur.execute("""
                UPDATE pdf_extracted_data 
                SET department = %s
                WHERE LOWER(department) = %s
            """, (standard, non_standard))
            print(f"Updated department '{non_standard}' to '{standard}'")
        
        conn.commit()
        print("\nSuccessfully updated non-standard values")
        
        # Verify the changes
        cur.execute("""
            SELECT DISTINCT LOWER(job_title) 
            FROM pdf_extracted_data 
            WHERE job_title IS NOT NULL 
            AND job_title != ''
        """)
        current_job_titles = set(row[0] for row in cur.fetchall())
        
        cur.execute("""
            SELECT DISTINCT LOWER(department) 
            FROM pdf_extracted_data 
            WHERE department IS NOT NULL 
            AND department != ''
        """)
        current_departments = set(row[0] for row in cur.fetchall())
        
        non_standard_job_titles = current_job_titles - standard_job_titles
        non_standard_departments = current_departments - standard_departments
        
        if non_standard_job_titles:
            print("\nRemaining non-standard job titles:")
            for title in sorted(non_standard_job_titles):
                print(f"- {title}")
        
        if non_standard_departments:
            print("\nRemaining non-standard departments:")
            for dept in sorted(non_standard_departments):
                print(f"- {dept}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error fixing non-standard values: {e}")

if __name__ == "__main__":
    fix_non_standard_values() 