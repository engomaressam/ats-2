import psycopg2
from psycopg2.extras import RealDictCursor
import openai
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

# OpenAI configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_current_job(text):
    """Extract current job from the first 40% of the CV text using GPT (OpenAI v1.x syntax)"""
    text_length = len(text)
    first_portion = text[:int(text_length * 0.4)]
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a CV parser. Extract the current job title from the CV text. Return ONLY the job title, nothing else. If you can't find it, return 'Not specified'."},
                {"role": "user", "content": f"Extract the current job title from this CV text:\n\n{first_portion}"}
            ],
            temperature=0.3,
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling GPT API: {str(e)}")
        return "Error processing"

def update_current_jobs():
    """Update current_job for all CVs in the database"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all CVs that don't have current_job set
                cur.execute("""
                    SELECT id, ocr_result 
                    FROM pdf_extracted_data 
                    WHERE current_job IS NULL 
                    AND ocr_result IS NOT NULL
                """)
                
                cvs = cur.fetchall()
                total = len(cvs)
                print(f"Found {total} CVs to process")
                
                for i, cv in enumerate(cvs, 1):
                    print(f"Processing CV {i}/{total} (ID: {cv['id']})")
                    
                    # Get current job using GPT
                    current_job = get_current_job(cv['ocr_result'])
                    
                    # Update the database
                    cur.execute("""
                        UPDATE pdf_extracted_data 
                        SET current_job = %s 
                        WHERE id = %s
                    """, (current_job, cv['id']))
                    
                    conn.commit()
                    
                    # Add a small delay to avoid hitting API rate limits
                    time.sleep(1)
                
                print("Finished processing all CVs")
                
    except Exception as e:
        print(f"Error updating current jobs: {str(e)}")

if __name__ == "__main__":
    update_current_jobs() 