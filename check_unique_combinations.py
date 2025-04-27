import psycopg2
import sys

def main():
    print("Starting database connection...")
    try:
        # Database connection parameters
        conn = psycopg2.connect(
            database="postgres",
            user="postgres",
            password="PMO@1234",
            host="localhost",
            port="5432"
        )
        print("Successfully connected to the database")

        # Create a cursor
        cur = conn.cursor()
        print("Executing query...")

        # Execute query
        query = """
        SELECT DISTINCT job_title, department 
        FROM pdf_extracted_data 
        WHERE job_title != 'other' 
        AND department != 'other' 
        ORDER BY job_title, department;
        """
        cur.execute(query)
        
        # Fetch all results
        results = cur.fetchall()
        print(f"\nFound {len(results)} unique combinations:")
        
        if len(results) == 0:
            print("No results found in the database.")
        else:
            print("\nJob Title | Department")
            print("-" * 50)
            for job_title, department in results:
                print(f"{job_title} | {department}")

    except psycopg2.Error as e:
        print(f"Database error occurred: {e}")
        print(f"Error details: {e.diag.message_primary if hasattr(e, 'diag') else 'No additional details'}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        try:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
                print("\nDatabase connection closed.")
        except Exception as e:
            print(f"Error while closing database connection: {str(e)}")

if __name__ == "__main__":
    main() 