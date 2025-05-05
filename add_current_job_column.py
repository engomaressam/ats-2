import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

def add_current_job_column():
    """Add current_job column to pdf_extracted_data table if it doesn't exist"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Check if column exists
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'pdf_extracted_data' 
                    AND column_name = 'current_job'
                """)
                
                if not cur.fetchone():
                    # Add the column if it doesn't exist
                    cur.execute("""
                        ALTER TABLE pdf_extracted_data 
                        ADD COLUMN current_job TEXT
                    """)
                    print("Added current_job column successfully")
                else:
                    print("current_job column already exists")
                
                conn.commit()
    except Exception as e:
        print(f"Error adding column: {str(e)}")

if __name__ == "__main__":
    add_current_job_column() 