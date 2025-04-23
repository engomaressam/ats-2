import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from difflib import SequenceMatcher
import requests
import json

# Load environment variables
load_dotenv()

# Database connection parameters
DB_PARAMS = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'PMO@1234',
    'host': 'localhost',
    'port': '5432'
}

# API endpoint
API_URL = "http://localhost:5000/api/search"

def similar(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def load_excel_files():
    """Load and process Excel files"""
    try:
        # Load job titles
        job_titles_df = pd.read_excel("Active_Job_Name.xlsx")
        print("\nJob titles file columns:", job_titles_df.columns.tolist())
        job_titles = job_titles_df['JobName'].str.lower().tolist()
        
        # Load departments
        departments_df = pd.read_excel("Active_Crew.xlsx")
        print("\nCrew file columns:", departments_df.columns.tolist())
        
        # Print first few rows of each file to verify content
        print("\nFirst few job titles:", job_titles[:5])
        print("\nFirst few rows of crew data:\n", departments_df.head())
        
        # Get unique departments
        departments = departments_df['Department'].str.lower().unique().tolist()
        
        # Create mapping of job titles to departments
        job_dept_mapping = {}
        for _, row in departments_df.iterrows():
            job_title = row['Job Name'].lower()  # Note the space in 'Job Name'
            department = row['Department'].lower()
            job_dept_mapping[job_title] = department
        
        print(f"\nLoaded {len(job_titles)} job titles and {len(departments)} departments")
        print("\nAvailable departments:", ", ".join(departments))
        print("\nSample job titles:", ", ".join(job_titles[:10]), "... and more")
        
        return job_titles, departments, job_dept_mapping
    except Exception as e:
        print(f"Error loading Excel files: {e}")
        import traceback
        print("Traceback:", traceback.format_exc())
        print("Current directory:", os.getcwd())
        print("Files in directory:", os.listdir())
        return [], [], {}

def get_all_records():
    """Get all records that need standardization"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Get all records with job titles and departments
        cur.execute("""
            SELECT id, pdf_filename, job_title, department 
            FROM pdf_extracted_data 
            WHERE job_title IS NOT NULL 
            AND job_title != ''
        """)
        
        records = cur.fetchall()
        cur.close()
        conn.close()
        
        return records
    except Exception as e:
        print(f"Error getting records: {e}")
        return []

def find_best_match(value, options, threshold=0.7):
    """Find the best matching option from the list"""
    if not value or pd.isna(value):
        return None
    
    best_match = None
    best_score = 0
    
    for option in options:
        score = similar(value, option)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = option
    
    return best_match

def update_record(record_id, job_title, department):
    """Update record in database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE pdf_extracted_data 
            SET job_title = %s, department = %s 
            WHERE id = %s
        """, (job_title, department, record_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating record {record_id}: {e}")
        return False

def process_records():
    """Main function to process records"""
    # Load Excel data
    job_titles, departments, job_dept_mapping = load_excel_files()
    if not job_titles or not departments:
        print("Failed to load Excel files. Exiting.")
        return
    
    # Get all records
    records = get_all_records()
    if not records:
        print("No records found.")
        return
    
    print(f"Found {len(records)} records to process")
    
    # Process each record
    for record in records:
        record_id, pdf_filename, current_job_title, current_department = record
        print(f"\nProcessing {pdf_filename}")
        
        # First try to match job title
        matched_job_title = None
        if current_job_title:
            # Check if current job title is already in the list
            if current_job_title.lower() in job_titles:
                matched_job_title = current_job_title
            else:
                matched_job_title = find_best_match(current_job_title, job_titles)
        
        # If no job title match, try to extract from PDF text
        if not matched_job_title:
            try:
                # Get OCR text from database
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                cur.execute("SELECT ocr_result FROM pdf_extracted_data WHERE id = %s", (record_id,))
                ocr_text = cur.fetchone()[0]
                cur.close()
                conn.close()
                
                # Use API to extract job title from OCR text
                response = requests.post(API_URL, json={
                    'text': ocr_text,
                    'extract_fields': ['job_title']
                })
                
                if response.status_code == 200:
                    extracted_data = response.json()
                    if 'job_title' in extracted_data:
                        matched_job_title = find_best_match(
                            extracted_data['job_title'], 
                            job_titles
                        )
            except Exception as e:
                print(f"Error extracting job title from OCR: {e}")
        
        # If we have a matched job title, try to get department from mapping
        matched_department = None
        if matched_job_title:
            matched_department = job_dept_mapping.get(matched_job_title.lower())
        
        # If no department from mapping, try to match current department
        if not matched_department and current_department:
            # Check if current department is already in the list
            if current_department.lower() in departments:
                matched_department = current_department
            else:
                matched_department = find_best_match(current_department, departments)
        
        # If still no department, try to extract from OCR text
        if not matched_department:
            try:
                # Use API to extract department from OCR text
                response = requests.post(API_URL, json={
                    'text': ocr_text,
                    'extract_fields': ['department']
                })
                
                if response.status_code == 200:
                    extracted_data = response.json()
                    if 'department' in extracted_data:
                        matched_department = find_best_match(
                            extracted_data['department'], 
                            departments
                        )
            except Exception as e:
                print(f"Error extracting department from OCR: {e}")
        
        # Update record if we found matches
        if matched_job_title or matched_department:
            success = update_record(record_id, matched_job_title, matched_department)
            if success:
                print(f"✓ Updated record {record_id}")
                print(f"  Job Title: {matched_job_title}")
                print(f"  Department: {matched_department}")
            else:
                print(f"❌ Failed to update record {record_id}")
        else:
            print(f"❌ No matches found for record {record_id}")

if __name__ == "__main__":
    process_records() 