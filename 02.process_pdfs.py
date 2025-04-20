import os
import re
import json
import uuid
import psycopg2
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from openai import OpenAI

# Load environment variables and setup OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setup database connection and create table if not exists
def setup_database():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="PMO@1234"
        )
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
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

# Configure Tesseract path (update this to your Tesseract installation path)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Directory containing PDFs
cvs_directory = r"C:\cvs"

# Function to extract text from PDF using OCR
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

# Function to extract structured data using GPT-3.5
def extract_info_with_ai(ocr_text):
    try:
        prompt = """Extract information from the resume and format it EXACTLY as the following JSON template:
{
    "Name": "Full Name",
    "Email": "email@example.com",
    "Phone": "+1234567890",
    "LinkedIn": "linkedin profile url",
    "Graduation Year": "YYYY",
    "University": "University Name",
    "Skills": "Skill1, Skill2, Skill3",
    "Department": "Department name from the list below",
    "Job_Title": "Job title from the list below",
    "Years_of_Experience": "X years",
    "Current_Company": "Company name",
    "Location": "City/Location",
    "Languages": "Language proficiencies",
    "Certifications": "Professional certifications",
    "Project_Types": "Types of projects worked on"
}

For Department, categorize into one of these:
- IT Department
- Technical Office Department
- Quality Control Department
- Construction Department
- Design Department
- MEP Department
- Architecture Department
- Contracts Department
- Planning Department
- HSE Department
- Other (specify)

For Job_Title, normalize to these main categories:
- Civil Engineer
- Architect
- MEP Engineer
- Project Manager
- Construction Manager
- Quality Engineer
- Safety Engineer
- Quantity Surveyor
- Planning Engineer
- Site Engineer
- Other (specify)

IMPORTANT: Ensure the response is valid JSON. Use empty string "" for missing fields.

Resume Text:
""" + ocr_text

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a resume parser that outputs ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI extraction error: {e}")
        return None

def insert_data_to_db(cursor, conn, pdf_filename, ocr_text, extracted_info):
    try:
        # Check if file already exists in database
        cursor.execute("SELECT id FROM pdf_extracted_data WHERE pdf_filename = %s", (pdf_filename,))
        if cursor.fetchone():
            print(f"Skipping already processed file: {pdf_filename}")
            return False

        # Parse the AI response as JSON
        try:
            data = json.loads(extracted_info)
        except:
            print(f"Error parsing AI response as JSON for {pdf_filename}")
            return False

        # Insert the extracted data into the database
        cursor.execute(
            """
            INSERT INTO pdf_extracted_data 
            (pdf_filename, ocr_result, name, email, phone, linkedin, graduation_year, university, skills,
             department, job_title, years_of_experience, current_company, location, languages, certifications, project_types)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                pdf_filename,
                ocr_text,
                data.get("Name", "N/A"),
                data.get("Email", "N/A"),
                data.get("Phone", "N/A"),
                data.get("LinkedIn", "N/A"),
                data.get("Graduation Year", "N/A"),
                data.get("University", "N/A"),
                data.get("Skills", "N/A"),
                data.get("Department", "N/A"),
                data.get("Job_Title", "N/A"),
                data.get("Years_of_Experience", "N/A"),
                data.get("Current_Company", "N/A"),
                data.get("Location", "N/A"),
                data.get("Languages", "N/A"),
                data.get("Certifications", "N/A"),
                data.get("Project_Types", "N/A")
            )
        )
        conn.commit()
        print(f"Successfully processed and stored data for: {pdf_filename}")
        return True
    except Exception as e:
        print(f"Database insertion error for {pdf_filename}: {e}")
        conn.rollback()
        return False

# Function to process all PDFs in the specified directory
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
        cursor.execute("SELECT pdf_filename FROM pdf_extracted_data")
        processed_files = {row[0] for row in cursor.fetchall()}
        print(f"Found {len(processed_files)} already processed files in database")

        # Process each PDF file
        new_files = 0
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
                    continue

                # Extract structured information using AI
                extracted_info = extract_info_with_ai(ocr_text)
                if not extracted_info:
                    print(f"Failed to extract structured info from {filename}")
                    continue

                # Insert data into database
                try:
                    # Double-check if file was processed by another process while we were working
                    cursor.execute("SELECT id FROM pdf_extracted_data WHERE pdf_filename = %s", (filename,))
                    if cursor.fetchone():
                        print(f"File was processed by another process while we were working: {filename}")
                        continue

                    # Insert the extracted data into the database
                    if insert_data_to_db(cursor, conn, filename, ocr_text, extracted_info):
                        conn.commit()
                except Exception as e:
                    print(f"Database insertion error for {filename}: {e}")
                    conn.rollback()
                    continue

        print(f"\nProcessing completed. Processed {new_files} new files.")
    except Exception as e:
        print(f"Error during processing: {e}")
        conn.rollback()
    finally:
        conn.autocommit = True
        cursor.close()
        conn.close()

if __name__ == "__main__":
    process_pdfs_in_directory(cvs_directory)
