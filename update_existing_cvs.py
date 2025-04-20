import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables and setup OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def setup_database():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="PMO@1234"
        )
        cursor = conn.cursor()
        
        # Add new columns if they don't exist
        cursor.execute("""
            ALTER TABLE pdf_extracted_data 
            ADD COLUMN IF NOT EXISTS department VARCHAR(255),
            ADD COLUMN IF NOT EXISTS job_title VARCHAR(255),
            ADD COLUMN IF NOT EXISTS years_of_experience VARCHAR(50),
            ADD COLUMN IF NOT EXISTS current_company VARCHAR(255),
            ADD COLUMN IF NOT EXISTS location VARCHAR(255),
            ADD COLUMN IF NOT EXISTS languages TEXT,
            ADD COLUMN IF NOT EXISTS certifications TEXT,
            ADD COLUMN IF NOT EXISTS project_types TEXT
        """)
        conn.commit()
        return conn, cursor
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

def extract_additional_info(ocr_text):
    prompt = """Extract the following information from the resume text. Format the response as a strict JSON object with string values only. All values must be strings, not arrays or objects.
{
    "Department": "Determine the most likely department (e.g., IT Department, Technical Office, etc.)",
    "Job_Title": "Extract the main job title without seniority levels",
    "Years_of_Experience": "Total years of experience as a string",
    "Current_Company": "Current or most recent company",
    "Location": "City/Location",
    "Languages": "Language proficiencies as comma-separated string",
    "Certifications": "Professional certifications as comma-separated string",
    "Project_Types": "Types of projects as comma-separated string"
}

For Department, use ONLY these exact strings:
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
- Other

For Job_Title, use ONLY these exact strings:
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
- Other

Resume Text:
""" + ocr_text

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a resume parser that outputs only valid JSON with string values. Never use arrays or nested objects. Use comma-separated strings instead."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # Lower temperature for more consistent outputs
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in AI extraction: {e}")
        return None

def update_records():
    conn, cursor = setup_database()
    if not conn or not cursor:
        return

    try:
        # Get records that don't have department or job_title
        cursor.execute("""
            SELECT id, ocr_result, pdf_filename 
            FROM pdf_extracted_data 
            WHERE department IS NULL 
            OR job_title IS NULL
            LIMIT 40
        """)
        records = cursor.fetchall()
        
        print(f"Found {len(records)} records to update")
        
        for record_id, ocr_text, filename in records:
            print(f"\nProcessing record {record_id} - File: {filename}")
            
            # Extract new information
            info = extract_additional_info(ocr_text)
            if not info:
                print(f"Skipping record {record_id} - extraction failed")
                continue
            
            try:
                import json
                data = json.loads(info)
                
                # Ensure all values are strings
                for key in data:
                    if not isinstance(data[key], str):
                        data[key] = str(data[key])
                
                # Print extracted info for verification
                print(f"Raw AI response: {info}")
                print(f"Extracted Department: {data.get('Department', 'N/A')}")
                print(f"Extracted Job Title: {data.get('Job_Title', 'N/A')}")
                
                # Update database
                cursor.execute("""
                    UPDATE pdf_extracted_data 
                    SET 
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
                    str(data.get('Department', 'N/A')),
                    str(data.get('Job_Title', 'N/A')),
                    str(data.get('Years_of_Experience', 'N/A')),
                    str(data.get('Current_Company', 'N/A')),
                    str(data.get('Location', 'N/A')),
                    str(data.get('Languages', 'N/A')),
                    str(data.get('Certifications', 'N/A')),
                    str(data.get('Project_Types', 'N/A')),
                    record_id
                ))
                conn.commit()
                print(f"✓ Successfully updated record {record_id}")
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON for record {record_id}")
                print(f"Error details: {str(e)}")
                print(f"Raw response: {info}")
                continue
            except Exception as e:
                print(f"❌ Error updating record {record_id}: {e}")
                print(f"Data that caused error: {data if 'data' in locals() else 'No data available'}")
                continue
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()
        
    print("\nProcessing complete. Review the results above and adjust the prompt if needed.")

if __name__ == "__main__":
    update_records() 