import os
import json
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict, Tuple
from datetime import datetime

# Load environment variables
load_dotenv()

# Setup OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OpenAI API key not found in environment variables")

# Database connection parameters
DB_PARAMS = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'PMO@1234',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

def load_standard_data() -> Tuple[List[str], List[str]]:
    """Load standard job titles and departments from Excel files"""
    # Load job titles
    job_titles_df = pd.read_excel("Active_Job_Name.xlsx")
    job_titles = job_titles_df['JobName'].str.lower().tolist()
    print("\nStandard Job Titles:")
    for title in job_titles:
        print(f"- {title}")
    
    # Load departments
    departments_df = pd.read_excel("Active_Crew.xlsx")
    departments = departments_df['Department'].str.lower().unique().tolist()
    print("\nStandard Departments:")
    for dept in departments:
        print(f"- {dept}")
    
    return job_titles, departments

def get_unmatched_records(batch_size=10):
    """Get records that haven't been processed yet"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, ocr_result, skills, job_title, department
            FROM pdf_extracted_data 
            WHERE (job_title IS NULL OR job_title = '')
            AND (department IS NULL OR department = '')
            AND (last_attempt IS NULL OR last_attempt < NOW() - INTERVAL '1 day')
            LIMIT %s
        """, (batch_size,))
        return cur.fetchall()

def create_gpt_prompt(records, job_titles, departments):
    prompt = """You are a CV analyzer that matches job titles and departments. Your task is to analyze each CV and determine the most appropriate job title and department from the provided lists.

IMPORTANT: You must respond with a valid JSON object containing a "matches" array. Each match must have exactly these fields:
- record_id (number)
- job_title (string, must be from the provided list)
- department (string, must be from the provided list)
- confidence (number between 0 and 1)

Available Job Titles (use EXACTLY one of these, in lowercase):
{}

Available Departments (use EXACTLY one of these, in lowercase):
{}

Records to analyze:
{}

Respond ONLY with a JSON object in this EXACT format:
{{
    "matches": [
        {{
            "record_id": 123,
            "job_title": "exact job title from list",
            "department": "exact department from list",
            "confidence": 0.95
        }}
    ]
}}

DO NOT include any other text or explanation in your response, ONLY the JSON object."""

    # Format records for the prompt
    records_text = []
    for record in records:
        # Limit OCR text to first 1000 characters to save tokens
        ocr_excerpt = record['ocr_result'][:1000] if record['ocr_result'] else ''
        record_text = f"""Record ID: {record['id']}
Current job title: {record['job_title'] if record['job_title'] else 'None'}
Current department: {record['department'] if record['department'] else 'None'}
OCR Text excerpt: {ocr_excerpt}
Skills: {record['skills'] if record['skills'] else 'Not specified'}
---"""
        records_text.append(record_text)

    # Format the prompt with the data
    formatted_prompt = prompt.format(
        "\n".join(job_titles),  # Include all job titles since we need exact matches
        "\n".join(departments),
        "\n".join(records_text)
    )

    return formatted_prompt

def log_suggested_matches(record_id: int, suggested_job_title: str, suggested_department: str, confidence: float):
    """Log suggested matches to a file for later review"""
    log_entry = {
        'record_id': record_id,
        'suggested_job_title': suggested_job_title,
        'suggested_department': suggested_department,
        'confidence': confidence,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('suggested_matches.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def mark_attempted(record_id: int):
    """Mark a record as attempted"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE pdf_extracted_data 
            SET last_attempt = NOW()
            WHERE id = %s
        """, (record_id,))
        conn.commit()

def process_batch(batch, job_titles, departments):
    """Process a batch of records with GPT"""
    try:
        # Create prompt for the batch
        prompt = create_gpt_prompt(batch, job_titles, departments)
        
        print("\nSending request to GPT...")
        # Call GPT API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that matches CV text to job titles and departments. You MUST use EXACTLY the job titles and departments from the provided lists."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        # Get the response content
        response_content = response.choices[0].message.content
        print("\nGPT Response:", response_content)

        # Parse response
        try:
            # Remove ```json markers if present
            response_content = response_content.replace('```json', '').replace('```', '').strip()
            result = json.loads(response_content)
            if not isinstance(result, dict) or 'matches' not in result:
                print("Error: Invalid response format from GPT")
                return 0

            matches = result['matches']
            if not matches:
                print("No matches found in GPT response")
                return 0

            # Validate matches
            valid_matches = []
            for match in matches:
                if all(k in match for k in ['record_id', 'job_title', 'department', 'confidence']):
                    # Convert job title and department to lowercase for comparison
                    match['job_title'] = match['job_title'].lower()
                    match['department'] = match['department'].lower()
                    
                    # Mark the record as attempted
                    mark_attempted(match['record_id'])
                    
                    # Verify job title and department are in our standard lists
                    if match['job_title'] in job_titles and match['department'] in departments:
                        valid_matches.append(match)
                        print(f"\nValid match found for record {match['record_id']}:")
                        print(f"Job Title: {match['job_title']}")
                        print(f"Department: {match['department']}")
                        print(f"Confidence: {match['confidence']}")
                    else:
                        print(f"\nWarning: Invalid job title or department for record {match['record_id']}")
                        print(f"Suggested job_title: {match['job_title']}")
                        print(f"Suggested department: {match['department']}")
                        if match['job_title'] not in job_titles:
                            print(f"Job title '{match['job_title']}' is not in the standard list")
                        if match['department'] not in departments:
                            print(f"Department '{match['department']}' is not in the standard list")
                        
                        # Log the suggested match for later review
                        log_suggested_matches(
                            match['record_id'],
                            match['job_title'],
                            match['department'],
                            match['confidence']
                        )

            if not valid_matches:
                print("No valid matches found after validation")
                return 0

            # Update database with matches
            with get_db_connection() as conn:
                cur = conn.cursor()
                for match in valid_matches:
                    record_id = match['record_id']
                    job_title = match['job_title']
                    department = match['department']
                    confidence = match['confidence']
                    
                    cur.execute("""
                        UPDATE pdf_extracted_data 
                        SET job_title = %s, department = %s, confidence = %s, last_attempt = NOW()
                        WHERE id = %s
                    """, (job_title, department, confidence, record_id))
                conn.commit()
                
            print(f"\nSuccessfully processed and updated {len(valid_matches)} records")
            return len(valid_matches)
            
        except json.JSONDecodeError as e:
            print(f"Error parsing GPT response as JSON: {e}")
            print("Raw response:", response_content)
            return 0
            
    except Exception as e:
        print(f"Error processing batch: {str(e)}")
        return 0

def process_unmatched_records():
    """Main function to process unmatched records using GPT"""
    print("Starting to process unmatched records...")
    
    # Get job titles and departments
    job_titles, departments = load_standard_data()
    print(f"Loaded {len(job_titles)} job titles and {len(departments)} departments")
    
    total_processed = 0
    batch_size = 10
    
    while True:
        # Get next batch of unmatched records
        records = get_unmatched_records(batch_size)
        if not records:
            print("\nNo more unmatched records to process")
            break
            
        print(f"\nProcessing batch of {len(records)} records...")
        processed = process_batch(records, job_titles, departments)
        total_processed += processed
        
        if processed < len(records):
            print("Warning: Some records in batch failed to process")
            
    print(f"\nFinished processing. Total records processed: {total_processed}")

if __name__ == "__main__":
    process_unmatched_records() 