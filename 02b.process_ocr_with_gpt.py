import os
import psycopg2
from openai import OpenAI
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def setup_database():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="PMO@1234"
        )
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

def extract_info_with_gpt(ocr_text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": """Extract the following information from the CV text in JSON format:
                    - name: Full name of the candidate
                    - email: Email address
                    - phone: Phone number
                    - linkedin: LinkedIn profile URL if present
                    - graduation_year: Year of graduation
                    - university: University name
                    - skills: List of technical and soft skills
                    - department: Normalize to one of: [Engineering, IT/Software Development, Sales, Marketing, HR, Finance/Accounting, Operations, Legal, Administrative, Other]
                    - job_title: Normalize to closest match of: [Software Engineer, Project Manager, Business Analyst, Sales Representative, Marketing Specialist, HR Manager, Financial Analyst, Operations Manager, Legal Counsel, Administrative Assistant]
                    - years_of_experience: Total years of experience
                    - current_company: Current or most recent company
                    - location: City/Country
                    - languages: List of languages known
                    - certifications: List of certifications
                    - project_types: Types of projects worked on"""
            }, {
                "role": "user",
                "content": ocr_text[:4000]  # Limit text length to avoid token limits
            }],
            temperature=0.1,
            max_tokens=1000
        )
        
        # Extract and parse the JSON response
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"GPT extraction error: {e}")
        return None

def process_unprocessed_records():
    conn, cursor = setup_database()
    if not conn or not cursor:
        return

    try:
        # Get records with OCR text but missing other fields
        cursor.execute("""
            SELECT id, pdf_filename, ocr_result 
            FROM pdf_extracted_data 
            WHERE ocr_result IS NOT NULL 
            AND (name IS NULL OR department IS NULL OR job_title IS NULL)
        """)
        records = cursor.fetchall()
        
        print(f"Found {len(records)} records to process")
        processed = 0
        failed = 0

        for record_id, filename, ocr_text in records:
            print(f"\nProcessing {filename}")
            
            # Extract information using GPT
            info = extract_info_with_gpt(ocr_text)
            if not info:
                print(f"Failed to extract information for {filename}")
                failed += 1
                continue

            try:
                # Update database with extracted information
                cursor.execute("""
                    UPDATE pdf_extracted_data 
                    SET name = %s,
                        email = %s,
                        phone = %s,
                        linkedin = %s,
                        graduation_year = %s,
                        university = %s,
                        skills = %s,
                        department = %s,
                        job_title = %s,
                        years_of_experience = %s,
                        current_company = %s,
                        location = %s,
                        languages = %s,
                        certifications = %s,
                        project_types = %s
                    WHERE id = %s
                """, (
                    info.get('name', ''),
                    info.get('email', ''),
                    info.get('phone', ''),
                    info.get('linkedin', ''),
                    info.get('graduation_year', ''),
                    info.get('university', ''),
                    json.dumps(info.get('skills', [])),
                    info.get('department', ''),
                    info.get('job_title', ''),
                    info.get('years_of_experience', ''),
                    info.get('current_company', ''),
                    info.get('location', ''),
                    json.dumps(info.get('languages', [])),
                    json.dumps(info.get('certifications', [])),
                    json.dumps(info.get('project_types', [])),
                    record_id
                ))
                conn.commit()
                processed += 1
                print(f"✓ Successfully processed {filename}")
                print(f"  Department: {info.get('department', 'N/A')}")
                print(f"  Job Title: {info.get('job_title', 'N/A')}")

            except Exception as e:
                print(f"Database update error for {filename}: {e}")
                conn.rollback()
                failed += 1

        print(f"\nProcessing completed:")
        print(f"✓ Successfully processed: {processed} records")
        print(f"❌ Failed to process: {failed} records")
        print(f"Total cost estimate: ${(processed + failed) * 0.003:.2f}")

    except Exception as e:
        print(f"Error during processing: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    process_unprocessed_records() 