import requests
from requests_ntlm import HttpNtlmAuth
import json
from datetime import datetime, timedelta
from urllib.parse import quote
import psycopg2
from psycopg2.extras import RealDictCursor
import base64
import os

# CRM API Configuration
CRM_URL = "https://rmecrm.rowad-rme.com/RMECRM/api/data/v8.2"
USERNAME = "Rowad\\Omar Essam"
PASSWORD = "PMO@1234"

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "PMO@1234"
}

def get_session():
    session = requests.Session()
    session.auth = HttpNtlmAuth(USERNAME, PASSWORD)
    session.headers.update({
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0"
    })
    return session

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def get_entity_metadata(session, entity_name):
    """Fetch metadata for an entity to get valid field names"""
    url = f"{CRM_URL}/EntityDefinitions(LogicalName='{entity_name}')/Attributes"
    try:
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        if "value" in data:
            return [attr["LogicalName"] for attr in data["value"]]
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metadata: {e}")
        return []

def fetch_crm_applications_with_filenames(session):
    """Fetch all job applications and their annotation filenames from CRM"""
    print("Fetching all applications and annotation filenames (no date filter)...")
    basic_fields = [
        "new_jobapplicationid",
        "new_fullname",
        "new_contactphone",
        "new_telephonenumber",
        "new_gender",
        "new_position",
        "new_employmenttype",
        "new_expectedsalary",
        "new_dateavailableforemployment",
        "new_currentsalary",
        "new_company",
        "new_graduationyear",
        "new_qualitiesattributes",
        "new_careergoals",
        "new_additionalinformation",
        "new_appstatus",
        "new_hrinterviewstatus",
        "new_technicalrating",
        "new_technicalinterviewcomments",
        "new_hrcomment",
        "createdon",
        "modifiedon",
        "new_howdidyouhearaboutrowad",
        "new_listouttheextrasocialactivities"
    ]
    url = (
        f"{CRM_URL}/new_jobapplications?"
        f"$select={','.join(basic_fields)}"
    )
    try:
        print(f"\nTrying to fetch with fields: {', '.join(basic_fields)}")
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        applications = data.get("value", [])
        # For each application, fetch the annotation (CV) filename
        for app in applications:
            appid = app.get("new_jobapplicationid")
            if not appid:
                continue
            # Fetch annotation for this application
            annotation_url = f"{CRM_URL}/annotations?$select=filename&$filter=(_objectid_value eq {appid})"
            try:
                ann_response = session.get(annotation_url)
                ann_response.raise_for_status()
                ann_data = ann_response.json()
                if ann_data.get("value"):
                    # Use the first annotation's filename
                    app["filename"] = ann_data["value"][0].get("filename")
                else:
                    app["filename"] = None
            except Exception as e:
                print(f"Error fetching annotation for app {appid}: {e}")
                app["filename"] = None
        return applications
    except requests.exceptions.RequestException as e:
        print(f"Error fetching applications: {e}")
        return []

def update_database(applications):
    """Update database with CRM application data, matching by constructed pdf_filename only"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_count = 0
        for app in applications:
            update_data = {
                'crm_applicationid': app.get('new_jobapplicationid'),
                'crm_fullname': app.get('new_fullname'),
                'crm_contactphone': app.get('new_contactphone'),
                'crm_telephonenumber': app.get('new_telephonenumber'),
                'crm_gender': app.get('new_gender'),
                'crm_position': app.get('new_position'),
                'crm_employmenttype': app.get('new_employmenttype'),
                'crm_expectedsalary': app.get('new_expectedsalary'),
                'crm_dateavailableforemployment': app.get('new_dateavailableforemployment'),
                'crm_currentsalary': app.get('new_currentsalary'),
                'crm_company': app.get('new_company'),
                'crm_graduationyear': app.get('new_graduationyear'),
                'crm_qualitiesattributes': app.get('new_qualitiesattributes'),
                'crm_careergoals': app.get('new_careergoals'),
                'crm_additionalinformation': app.get('new_additionalinformation'),
                'crm_appstatus': app.get('new_appstatus'),
                'crm_hrinterviewstatus': app.get('new_hrinterviewstatus'),
                'crm_technicalrating': app.get('new_technicalrating'),
                'crm_technicalinterviewcomments': app.get('new_technicalinterviewcomments'),
                'crm_hrcomment': app.get('new_hrcomment'),
                'crm_createdon': app.get('createdon'),
                'crm_modifiedon': app.get('modifiedon'),
                'crm_howdidyouhearaboutrowad': app.get('new_howdidyouhearaboutrowad'),
                'crm_extrasocialactivities': app.get('new_listouttheextrasocialactivities')
            }
            update_data = {k: v for k, v in update_data.items() if v is not None}
            crm_filename = app.get('filename')
            createdon = app.get('createdon')
            if not crm_filename or not createdon or not update_data:
                continue
            # Extract date part from createdon (format: YYYY-MM-DD)
            created_date = str(createdon).split('T')[0]
            expected_pdf_filename = f"{created_date}_{crm_filename}"
            set_clause = ", ".join([f"{k} = %({k})s" for k in update_data.keys()])
            query = f"""
                UPDATE pdf_extracted_data 
                SET {set_clause}
                WHERE pdf_filename = %(expected_pdf_filename)s
            """
            params = update_data.copy()
            params['expected_pdf_filename'] = expected_pdf_filename
            cursor.execute(query, params)
            if cursor.rowcount > 0:
                updated_count += 1
        conn.commit()
        print(f"Updated {updated_count} records in the database")
    except Exception as e:
        print(f"Error updating database: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def print_sample_filenames(applications):
    print("\nSample filenames from CRM (annotation):")
    count = 0
    for app in applications:
        if app.get('filename'):
            print(f"CRM: {app['filename']}")
            count += 1
        if count >= 10:
            break

    # Print 10 sample filenames from the database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pdf_filename FROM pdf_extracted_data LIMIT 10;")
        rows = cursor.fetchall()
        print("\nSample filenames from database (pdf_filename):")
        for row in rows:
            print(f"DB: {row['pdf_filename']}")
    except Exception as e:
        print(f"Error fetching sample filenames from database: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def manual_match_test(applications):
    # Pick a CRM filename to test
    test_crm_filename = "Wael Mohamed Ibrahim CV.pdf"
    print(f"\nManual match test for CRM filename: '{test_crm_filename}'")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Try to find a row where the pdf_filename ends with the CRM filename (ignoring leading date and spaces)
        cursor.execute("""
            SELECT * FROM pdf_extracted_data
            WHERE TRIM(RIGHT(pdf_filename, LENGTH(%s))) = %s
            OR pdf_filename LIKE %s
            LIMIT 5;
        """, (test_crm_filename, test_crm_filename, f"%{test_crm_filename}",))
        rows = cursor.fetchall()
        if rows:
            print(f"Found {len(rows)} matching row(s) in the database:")
            for row in rows:
                print(row)
        else:
            print("No matching row found in the database.")
    except Exception as e:
        print(f"Error during manual match test: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    print("Starting CRM data sync...")
    session = get_session()
    applications = fetch_crm_applications_with_filenames(session)
    print(f"Found {len(applications)} applications in CRM")
    if applications:
        update_database(applications)
    else:
        print("No applications found to sync")

if __name__ == "__main__":
    main() 