import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
import json

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

Rules:
1. Department MUST be exactly one of these (no variations allowed):
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
   - HR Department
   - Other

2. Job_Title MUST be one of these (remove any seniority levels like 'Senior', 'Lead', 'Junior', etc.):
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
   - Technical Office Engineer
   - BIM Engineer
   - Mechanical Engineer
   - Electrical Engineer
   - Contracts Engineer
   - Cost Control Engineer
   - HR Specialist
   - Other

Expected JSON format:
{
    "Department": "MUST be from the exact list above",
    "Job_Title": "MUST be from the exact list above, without seniority levels",
    "Years_of_Experience": "Number as string (e.g., '5')",
    "Current_Company": "Company name",
    "Location": "City, Country",
    "Languages": "Languages as comma-separated string",
    "Certifications": "Certifications as comma-separated string",
    "Project_Types": "Project types as comma-separated string"
}

Resume Text:
""" + ocr_text

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a resume parser that outputs only valid JSON with string values. Never use arrays or nested objects. Use comma-separated strings instead. You MUST use exact values from the provided lists for Department and Job_Title fields."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # Low temperature for consistent outputs
        )
        
        # Get the response
        result = response.choices[0].message.content.strip()
        
        # Validate and clean the response
        try:
            data = json.loads(result)
            
            # Validate Department
            valid_departments = {
                "IT Department", "Technical Office Department", "Quality Control Department",
                "Construction Department", "Design Department", "MEP Department",
                "Architecture Department", "Contracts Department", "Planning Department",
                "HSE Department", "HR Department", "Other"
            }
            if data['Department'] not in valid_departments:
                data['Department'] = "Other"
            
            # Clean and validate Job_Title
            job_title = data['Job_Title']
            # Remove seniority levels
            for prefix in ['Senior ', 'Lead ', 'Junior ', 'Chief ', 'Head ', 'Principal ']:
                job_title = job_title.replace(prefix, '')
            
            valid_job_titles = {
                "Civil Engineer", "Architect", "MEP Engineer", "Project Manager",
                "Construction Manager", "Quality Engineer", "Safety Engineer",
                "Quantity Surveyor", "Planning Engineer", "Site Engineer",
                "Technical Office Engineer", "BIM Engineer", "Mechanical Engineer",
                "Electrical Engineer", "Contracts Engineer", "Cost Control Engineer",
                "HR Specialist", "Other"
            }
            if job_title not in valid_job_titles:
                job_title = "Other"
            
            data['Job_Title'] = job_title
            
            # Ensure all values are strings
            for key in data:
                if not isinstance(data[key], str):
                    data[key] = str(data[key])
            
            return json.dumps(data, ensure_ascii=False)
            
        except json.JSONDecodeError:
            print(f"Invalid JSON response: {result}")
            return None
            
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
        """)
        records = cursor.fetchall()
        
        print(f"Found {len(records)} records to update")
        successful_updates = 0
        failed_updates = 0
        
        for record_id, ocr_text, filename in records:
            print(f"\nProcessing record {record_id} - File: {filename}")
            
            # Extract new information
            info = extract_additional_info(ocr_text)
            if not info:
                print(f"❌ Skipping record {record_id} - extraction failed")
                failed_updates += 1
                continue
            
            try:
                data = json.loads(info)
                
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
                successful_updates += 1
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON for record {record_id}")
                print(f"Error details: {str(e)}")
                print(f"Raw response: {info}")
                failed_updates += 1
                continue
            except Exception as e:
                print(f"❌ Error updating record {record_id}: {e}")
                print(f"Data that caused error: {data if 'data' in locals() else 'No data available'}")
                failed_updates += 1
                continue
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()
        
    print("\nProcessing complete:")
    print(f"✓ Successfully updated: {successful_updates} records")
    print(f"❌ Failed updates: {failed_updates} records")
    print(f"Total processed: {successful_updates + failed_updates} records")

if __name__ == "__main__":
    update_records() 