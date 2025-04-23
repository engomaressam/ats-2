import psycopg2

# Database connection parameters
DB_PARAMS = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'PMO@1234',
    'host': 'localhost',
    'port': '5432'
}

def check_counts():
    """Check the number of unmatched records and total records"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Get count of unmatched records
        cur.execute("""
            SELECT COUNT(*) 
            FROM pdf_extracted_data 
            WHERE (job_title IS NULL OR job_title = '') 
            AND (department IS NULL OR department = '')
        """)
        unmatched = cur.fetchone()[0]
        
        # Get total count
        cur.execute("SELECT COUNT(*) FROM pdf_extracted_data")
        total = cur.fetchone()[0]
        
        print(f"Unmatched records: {unmatched}")
        print(f"Total records: {total}")
        print(f"Percentage unmatched: {(unmatched/total)*100:.2f}%")
        
        cur.close()
        conn.close()
        return unmatched, total
    except Exception as e:
        print(f"Error checking counts: {e}")
        return None, None

if __name__ == "__main__":
    check_counts() 