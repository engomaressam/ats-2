import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

def add_crm_columns():
    """Add new CRM-specific columns to the pdf_extracted_data table"""
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # List of new CRM-specific columns to add
        new_columns = [
            # Basic Information
            "crm_fullname VARCHAR(255)",
            "crm_email VARCHAR(255)",
            "crm_contactphone VARCHAR(50)",
            "crm_telephonenumber VARCHAR(50)",
            "crm_city VARCHAR(100)",
            "crm_nationality VARCHAR(100)",
            "crm_birthdate DATE",
            "crm_gender VARCHAR(20)",
            
            # Job Application Details
            "crm_position VARCHAR(255)",
            "crm_department VARCHAR(100)",
            "crm_employmenttype VARCHAR(50)",
            "crm_expectedsalary DECIMAL(12,2)",
            "crm_dateavailableforemployment DATE",
            "crm_currentsalary VARCHAR(100)",
            "crm_company VARCHAR(255)",
            
            # Education and Skills
            "crm_graduationyear VARCHAR(10)",
            "crm_qualitiesattributes TEXT",
            "crm_careergoals TEXT",
            "crm_additionalinformation TEXT",
            
            # Application Status and Processing
            "crm_appstatus VARCHAR(50)",
            "crm_hrinterviewstatus VARCHAR(50)",
            "crm_technicalrating VARCHAR(50)",
            "crm_technicalinterviewcomments TEXT",
            "crm_hrcomment TEXT",
            "crm_createdon TIMESTAMP",
            "crm_modifiedon TIMESTAMP",
            "crm_modifiedby VARCHAR(255)",
            
            # Additional Information
            "crm_source VARCHAR(100)",
            "crm_extrasocialactivities TEXT",
            "crm_languages TEXT",
            "crm_certifications TEXT",
            
            # Tracking
            "crm_applicationid VARCHAR(100)",
            "crm_last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]
        
        # Add each column if it doesn't exist
        for column in new_columns:
            try:
                column_name = column.split()[0]
                cursor.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'pdf_extracted_data' 
                            AND column_name = '{column_name}'
                        ) THEN
                            ALTER TABLE pdf_extracted_data ADD COLUMN {column};
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
    add_crm_columns() 