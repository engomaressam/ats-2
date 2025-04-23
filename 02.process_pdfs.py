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
        images = convert_from_path(
            pdf_path,
            poppler_path=r"C:\poppler\Library\bin"
        )
        
        text = ""
        for img in images:
            try:
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

def estimate_token_cost(text):
    # Rough estimation: 1 token ≈ 4 characters
    num_tokens = len(text) / 4
    cost_per_1k_tokens = 0.0015
    return (num_tokens / 1000) * cost_per_1k_tokens

def process_pdfs_in_directory(directory_path):
    # Setup database connection
    conn, cursor = setup_database()
    if not conn or not cursor:
        return

    try:
        # Get list of PDF files
        pdf_files = [f for f in os.listdir(directory_path) if f.endswith('.pdf')]
        unprocessed_files = []
        
        # Check which files haven't been processed
        for pdf_file in pdf_files:
            cursor.execute("SELECT id FROM pdf_extracted_data WHERE pdf_filename = %s", (pdf_file,))
            if not cursor.fetchone():
                unprocessed_files.append(pdf_file)
        
        if not unprocessed_files:
            print("No new PDFs to process.")
            return
            
        total_files = len(unprocessed_files)
        print(f"Found {total_files} unprocessed PDFs")
        
        # Calculate total estimated cost
        total_estimated_cost = 0
        for pdf_file in unprocessed_files:
            pdf_path = os.path.join(directory_path, pdf_file)
            ocr_text = extract_text_from_pdf(pdf_path)
            if ocr_text:
                total_estimated_cost += estimate_token_cost(ocr_text)
        
        print(f"Estimated total cost: ${total_estimated_cost:.3f}")
        print("Starting processing...")
        
        # Process all files
        successful = 0
        failed = 0
        
        for index, pdf_file in enumerate(unprocessed_files, 1):
            pdf_path = os.path.join(directory_path, pdf_file)
            print(f"\nProcessing [{index}/{total_files}]: {pdf_file}")
            
            # Extract text using OCR
            ocr_text = extract_text_from_pdf(pdf_path)
            if not ocr_text:
                print(f"❌ Skipping {pdf_file} - could not extract text")
                failed += 1
                continue
            
            # Extract information using AI
            extracted_info = extract_info_with_ai(ocr_text)
            if not extracted_info:
                print(f"❌ Failed to extract information from {pdf_file}")
                failed += 1
                continue
            
            # Store in database
            success = insert_data_to_db(cursor, conn, pdf_file, ocr_text, extracted_info)
            if success:
                print(f"✓ Successfully processed: {pdf_file}")
                successful += 1
            else:
                print(f"❌ Failed to process: {pdf_file}")
                failed += 1
        
        print(f"\nProcessing complete!")
        print(f"✓ Successfully processed: {successful} files")
        print(f"❌ Failed to process: {failed} files")
        print(f"Total processed: {successful + failed} files")
        print(f"Estimated total cost spent: ${total_estimated_cost:.3f}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    process_pdfs_in_directory(cvs_directory)
