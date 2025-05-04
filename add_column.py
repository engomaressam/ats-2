import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def add_column():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            ALTER TABLE pdf_extracted_data
            ADD COLUMN IF NOT EXISTS crm_pleasesepcify TEXT;
        """)
        conn.commit()
        print("Successfully added crm_pleasesepcify column")
    except Exception as e:
        print(f"Error adding column: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    add_column() 