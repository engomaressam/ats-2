import psycopg2

# Database connection parameters
DB_PARAMS = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'PMO@1234',
    'host': 'localhost',
    'port': '5432'
}

def add_confidence_column():
    """Add confidence column to pdf_extracted_data table"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Add confidence column if it doesn't exist
        cur.execute("""
            ALTER TABLE pdf_extracted_data 
            ADD COLUMN IF NOT EXISTS confidence FLOAT
        """)
        
        conn.commit()
        print("Successfully added confidence column")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding confidence column: {e}")
        return False

if __name__ == "__main__":
    add_confidence_column() 