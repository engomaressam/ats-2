import psycopg2
from datetime import datetime
import sys

def connect_db():
    print("Attempting to connect to database...")
    try:
        conn = psycopg2.connect(
            database="postgres",
            user="postgres",
            password="PMO@1234",
            host="localhost",
            port="5432"
        )
        print("Successfully connected to database")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        sys.exit(1)

def create_backup():
    print("\n=== Creating Backup ===")
    conn = connect_db()
    cur = conn.cursor()
    try:
        backup_table = f"pdf_extracted_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"Creating backup table: {backup_table}")
        cur.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM pdf_extracted_data;")
        conn.commit()
        print("Backup created successfully")
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
        print("Database connection closed")

def update_department_names():
    print("\n=== Updating Department Names ===")
    conn = connect_db()
    cur = conn.cursor()
    try:
        print("Fetching current department names...")
        cur.execute("SELECT DISTINCT department FROM pdf_extracted_data WHERE department != 'other';")
        departments = cur.fetchall()
        print(f"Found {len(departments)} departments to process")
        acronyms = {'csr', 'hse', 'mep', 'pmo', 'qc', 'rme'}
        for (dept,) in departments:
            if dept.lower() in acronyms:
                new_name = dept.upper()
            else:
                new_name = dept.capitalize()
            print(f"Processing: {dept} -> {new_name}")
            cur.execute("""
                UPDATE pdf_extracted_data 
                SET department = %s 
                WHERE department = %s;
            """, (new_name, dept))
        conn.commit()
        print("\nAll department names have been updated successfully")
        cur.execute("SELECT DISTINCT department FROM pdf_extracted_data ORDER BY department;")
        results = cur.fetchall()
        print("\nUpdated department list:")
        for (dept,) in results:
            print(f"- {dept}")
    except Exception as e:
        print(f"Error updating departments: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
        print("Database connection closed")

def update_job_titles():
    print("\n=== Updating Job Titles ===")
    conn = connect_db()
    cur = conn.cursor()
    try:
        print("Fetching current job titles...")
        cur.execute("SELECT DISTINCT job_title FROM pdf_extracted_data WHERE job_title IS NOT NULL;")
        job_titles = cur.fetchall()
        print(f"Found {len(job_titles)} job titles to process")
        for (title,) in job_titles:
            if not title:
                continue
            new_title = ' '.join(word.capitalize() for word in title.split())
            if new_title != title:
                print(f"Processing: {title} -> {new_title}")
                cur.execute("""
                    UPDATE pdf_extracted_data 
                    SET job_title = %s 
                    WHERE job_title = %s;
                """, (new_title, title))
        conn.commit()
        print("\nAll job titles have been updated successfully")
        cur.execute("SELECT DISTINCT job_title FROM pdf_extracted_data ORDER BY job_title;")
        results = cur.fetchall()
        print("\nUpdated job title list (first 20 shown):")
        for (title,) in results[:20]:
            print(f"- {title}")
    except Exception as e:
        print(f"Error updating job titles: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
        print("Database connection closed")

def fix_special_departments():
    print("\n=== Fixing Special Department Cases ===")
    conn = connect_db()
    cur = conn.cursor()
    try:
        # Merge 'Csr - human resources' and 'Human resources' into 'HR'
        cur.execute("""
            UPDATE pdf_extracted_data
            SET department = 'HR'
            WHERE department IN ('Csr - human resources', 'Human resources');
        """)
        print("Merged 'Csr - human resources' and 'Human resources' into 'HR'")
        # Set 'Pmo (project management office)' to 'PMO'
        cur.execute("""
            UPDATE pdf_extracted_data
            SET department = 'PMO'
            WHERE department = 'Pmo (project management office)';
        """)
        print("Set 'Pmo (project management office)' to 'PMO'")
        conn.commit()
        print("Special department cases fixed successfully")
    except Exception as e:
        print(f"Error fixing special departments: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
        print("Database connection closed")

if __name__ == "__main__":
    try:
        print("Starting database operations...")
        create_backup()
        update_department_names()
        update_job_titles()
        fix_special_departments()
        print("\nAll operations completed successfully!")
    except Exception as e:
        print(f"\nScript failed with error: {str(e)}")
        sys.exit(1) 