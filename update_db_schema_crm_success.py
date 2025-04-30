import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

SUCCESSFUL_COLUMNS = [
    ("crm_contactphone", "VARCHAR(50)"),
    ("crm_telephonenumber", "VARCHAR(50)"),
    ("crm_gender", "VARCHAR(20)"),
    ("crm_position", "VARCHAR(255)"),
    ("crm_employmenttype", "VARCHAR(50)"),
    ("crm_expectedsalary", "DECIMAL(12,2)"),
    ("crm_dateavailableforemployment", "DATE"),
    ("crm_currentsalary", "VARCHAR(100)"),
    ("crm_company", "VARCHAR(255)"),
    ("crm_graduationyear", "VARCHAR(10)"),
    ("crm_qualitiesattributes", "TEXT"),
    ("crm_careergoals", "TEXT"),
    ("crm_additionalinformation", "TEXT"),
    ("crm_appstatus", "VARCHAR(50)"),
    ("crm_hrinterviewstatus", "VARCHAR(50)"),
    ("crm_technicalrating", "VARCHAR(50)"),
    ("crm_technicalinterviewcomments", "TEXT"),
    ("crm_hrcomment", "TEXT"),
    ("crm_createdon", "TIMESTAMP"),
    ("crm_modifiedon", "TIMESTAMP"),
    ("crm_howdidyouhearaboutrowad", "VARCHAR(100)"),
    ("crm_extrasocialactivities", "TEXT"),
    ("crm_applicationid", "VARCHAR(100)")
]

def add_successful_crm_columns():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        for column_name, column_type in SUCCESSFUL_COLUMNS:
            try:
                cursor.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'pdf_extracted_data' 
                            AND column_name = '{column_name}'
                        ) THEN
                            ALTER TABLE pdf_extracted_data ADD COLUMN {column_name} {column_type};
                        END IF;
                    END $$;
                """)
                print(f"Added column {column_name}")
            except Exception as e:
                print(f"Error adding column {column_name}: {e}")
        print("\nDatabase schema update completed successfully!")
    except Exception as e:
        print(f"Error updating database schema: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    add_successful_crm_columns() 