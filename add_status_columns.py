import psycopg2

conn = psycopg2.connect(
    dbname='postgres',
    user='postgres',
    password='PMO@1234',
    host='localhost',
    port='5432'
)
cur = conn.cursor()

try:
    cur.execute('''
        ALTER TABLE pdf_extracted_data
        ADD COLUMN IF NOT EXISTS status_1 VARCHAR(255),
        ADD COLUMN IF NOT EXISTS status_2 VARCHAR(255),
        ADD COLUMN IF NOT EXISTS status_3 VARCHAR(255),
        ADD COLUMN IF NOT EXISTS modified_by_1 VARCHAR(255),
        ADD COLUMN IF NOT EXISTS modified_by_2 VARCHAR(255),
        ADD COLUMN IF NOT EXISTS modified_by_3 VARCHAR(255);
    ''')
    conn.commit()
    print("Columns added successfully.")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close() 