import os
import requests
from requests_ntlm import HttpNtlmAuth
from urllib.parse import quote
from datetime import datetime, timedelta
import base64

# Constants
CRM_URL = "https://rmecrm.rowad-rme.com/RMECRM/api/data/v8.2"
USERNAME = "Rowad\\Omar Essam"
PASSWORD = "PMO@1234"
DOWNLOAD_DIR = r"C:\cvs"

def get_session():
    session = requests.Session()
    session.auth = HttpNtlmAuth(USERNAME, PASSWORD)
    session.headers.update({
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0"
    })
    return session

def get_job_applications(session):
    """
    Fetch job applications from the last 3 days.
    """
    all_applications = []
    
    # Calculate date range for last 3 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    print(f"Fetching applications from {start_date.date()} to {end_date.date()}")
    
    filter_condition = (
        f"createdon ge {start_date.strftime('%Y-%m-%dT00:00:00Z')} "
        f"and createdon le {end_date.strftime('%Y-%m-%dT23:59:59Z')}"
    )
    
    url = (
        f"{CRM_URL}/new_jobapplications?"
        f"$select=new_name,createdon&"
        f"$filter={quote(filter_condition)}&"
        "$top=5000"
    )
    
    try:
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "value" in data:
            applications = data["value"]
            print(f"Found {len(applications)} applications in the last 3 days")
            
            # Fetch annotations for each application
            for app in applications:
                annotations_url = (
                    f"{CRM_URL}/annotations?"
                    f"$filter=_objectid_value eq {app['new_jobapplicationid']}&"
                    "$select=filename,mimetype,documentbody"
                )
                
                try:
                    annotations_response = session.get(annotations_url)
                    annotations_response.raise_for_status()
                    annotations_data = annotations_response.json()
                    
                    if "value" in annotations_data:
                        app["annotations"] = annotations_data["value"]
                    else:
                        app["annotations"] = []
                        
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching annotations for application {app['new_jobapplicationid']}: {str(e)}")
                    app["annotations"] = []
            
            all_applications.extend(applications)
            print(f"Total applications fetched: {len(all_applications)}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching applications: {str(e)}")

    return all_applications

def download_attachments(applications):
    """
    Download CV attachments from job applications.
    Returns tuple of (downloaded_count, skipped_count).
    """
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    downloaded = 0
    skipped = 0
    
    for app in applications:
        try:
            app_id = app.get("new_jobapplicationid")
            created_date = app.get("createdon", "").split("T")[0]  # Get just the date part
            annotations = app.get("annotations", [])
            
            for annotation in annotations:
                if "documentbody" in annotation and "filename" in annotation:
                    filename = annotation["filename"]
                    if filename.lower().endswith((".pdf", ".doc", ".docx")):
                        try:
                            # Generate unique filename with creation date
                            unique_filename = f"{created_date}_{filename}"
                            file_path = os.path.join(DOWNLOAD_DIR, unique_filename)
                            
                            # Skip if file already exists
                            if os.path.exists(file_path):
                                print(f"Skipping existing file: {unique_filename}")
                                skipped += 1
                                continue
                            
                            # Decode base64 content and save
                            file_content = base64.b64decode(annotation["documentbody"])
                            with open(file_path, "wb") as f:
                                f.write(file_content)
                            print(f"Downloaded: {unique_filename}")
                            downloaded += 1
                        except Exception as e:
                            print(f"Error saving file {filename}: {e}")
        except Exception as e:
            print(f"Error processing application {app.get('new_jobapplicationid')}: {e}")
    
    return downloaded, skipped

def main():
    print("Starting CV download from CRM...")
    session = get_session()
    
    applications = get_job_applications(session)
    print(f"\nTotal job applications found: {len(applications)}")
    
    downloaded, skipped = download_attachments(applications)
    print(f"\nDownload complete!")
    print(f"New CVs downloaded: {downloaded}")
    print(f"Existing CVs skipped: {skipped}")

if __name__ == "__main__":
    main() 