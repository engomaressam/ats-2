import os
import psycopg2
from pdf2image import convert_from_path
import pytesseract

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Directory containing PDFs
cvs_directory = r"C:\cvs"

def setup_database():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="PMO@1234"
        )
        cursor = conn.cursor()
        
        # Create table with all fields (same as original)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pdf_extracted_data (
                id SERIAL PRIMARY KEY,
                pdf_filename VARCHAR(255),
                ocr_result TEXT,
                name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(255),
                linkedin VARCHAR(255),
                graduation_year VARCHAR(255),
                university VARCHAR(255),
                skills TEXT,
                department VARCHAR(255),
                job_title VARCHAR(255),
                years_of_experience VARCHAR(50),
                current_company VARCHAR(255),
                location VARCHAR(255),
                languages TEXT,
                certifications TEXT,
                project_types TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return conn, cursor
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

def extract_text_from_pdf(pdf_path):
    try:
        # Convert PDF to images
        images = convert_from_path(
            pdf_path,
            poppler_path=r"C:\poppler\Library\bin"
        )
        
        text = ""
        for img in images:
            try:
                # Extract text from each page
                text += pytesseract.image_to_string(img) + "\n"
            except Exception as e:
                print(f"OCR error on page: {e}")
                continue
        return text.strip()
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return None

def process_pdfs_in_directory(directory_path):
    # Setup database connection
    conn, cursor = setup_database()
    if not conn or not cursor:
        print("Failed to setup database connection. Exiting.")
        return

    # Create directory if it doesn't exist
    os.makedirs(directory_path, exist_ok=True)

    # Start a transaction
    conn.autocommit = False

    try:
        # Get list of already processed files from database
        cursor.execute("SELECT pdf_filename FROM pdf_extracted_data WHERE ocr_result IS NOT NULL")
        processed_files = {row[0] for row in cursor.fetchall()}
        print(f"Found {len(processed_files)} already processed files in database")

        # Process each PDF file
        new_files = 0
        failed_files = 0
        for filename in os.listdir(directory_path):
            if filename.endswith(".pdf"):
                # Skip if file is already processed
                if filename in processed_files:
                    print(f"Skipping already processed file: {filename}")
                    continue

                file_path = os.path.join(directory_path, filename)
                print(f"\nProcessing new file: {filename}")
                new_files += 1

                # Extract text using OCR
                ocr_text = extract_text_from_pdf(file_path)
                if not ocr_text:
                    print(f"Failed to extract text from {filename}")
                    failed_files += 1
                    continue

                try:
                    # Double-check if file was processed by another process
                    cursor.execute("SELECT id FROM pdf_extracted_data WHERE pdf_filename = %s", (filename,))
                    if cursor.fetchone():
                        print(f"File was processed by another process while we were working: {filename}")
                        continue

                    # Insert only the OCR text into the database
                    cursor.execute(
                        """
                        INSERT INTO pdf_extracted_data 
                        (pdf_filename, ocr_result)
                        VALUES (%s, %s)
                        """,
                        (filename, ocr_text)
                    )
                    conn.commit()
                    print(f"✓ Successfully saved OCR text for: {filename}")

                except Exception as e:
                    print(f"Database insertion error for {filename}: {e}")
                    conn.rollback()
                    failed_files += 1
                    continue

        print(f"\nOCR Processing completed:")
        print(f"✓ Successfully processed: {new_files - failed_files} files")
        print(f"❌ Failed to process: {failed_files} files")
        print(f"Total attempted: {new_files} files")

    except Exception as e:
        print(f"Error during processing: {e}")
        conn.rollback()
    finally:
        conn.autocommit = True
        cursor.close()
        conn.close()

if __name__ == "__main__":
    process_pdfs_in_directory(cvs_directory) 