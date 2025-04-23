import psycopg2

# Database connection parameters
DB_PARAMS = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'PMO@1234',
    'host': 'localhost',
    'port': '5432'
}

def add_last_attempt_column():
    """Add last_attempt column to pdf_extracted_data table"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Add last_attempt column if it doesn't exist
        cur.execute("""
            ALTER TABLE pdf_extracted_data 
            ADD COLUMN IF NOT EXISTS last_attempt TIMESTAMP
        """)
        
        conn.commit()
        print("Successfully added last_attempt column")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding last_attempt column: {e}")
        return False

if __name__ == "__main__":
    add_last_attempt_column() 