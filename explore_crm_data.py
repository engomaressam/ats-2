import requests
from requests_ntlm import HttpNtlmAuth
import json
from datetime import datetime, timedelta
from urllib.parse import quote

# CRM API Configuration
CRM_URL = "https://rmecrm.rowad-rme.com/RMECRM/api/data/v8.2"
USERNAME = "Rowad\\Omar Essam"
PASSWORD = "PMO@1234"

def get_session():
    session = requests.Session()
    session.auth = HttpNtlmAuth(USERNAME, PASSWORD)
    session.headers.update({
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0"
    })
    return session

def explore_entity_metadata(session, entity_name):
    """Get metadata about an entity to discover available fields"""
    print(f"\nExploring metadata for entity: {entity_name}")
    
    url = f"{CRM_URL}/EntityDefinitions(LogicalName='{entity_name}')"
    
    try:
        response = session.get(url)
        response.raise_for_status()
        metadata = response.json()
        
        # Get attributes metadata
        attributes_url = f"{CRM_URL}/EntityDefinitions(LogicalName='{entity_name}')/Attributes"
        attributes_response = session.get(attributes_url)
        attributes_response.raise_for_status()
        attributes = attributes_response.json()
        
        if "value" in attributes:
            print("\nAvailable fields:")
            for attr in attributes["value"]:
                attr_name = attr.get("LogicalName", "")
                attr_type = attr.get("AttributeType", "")
                print(f"- {attr_name} ({attr_type})")
            
            return [attr.get("LogicalName") for attr in attributes["value"]]
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metadata: {e}")
        return None

def explore_job_applications(session):
    """Explore job applications and their associated data"""
    print("\nExploring job applications...")
    
    # First get metadata to discover available fields
    fields = explore_entity_metadata(session, "new_jobapplication")
    
    if not fields:
        print("Could not get entity metadata. Using basic fields only.")
        fields = ["new_name", "createdon", "new_jobapplicationid"]
    
    # Calculate date range for last 30 days (wider range for exploration)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\nFetching applications from {start_date.date()} to {end_date.date()}")
    
    filter_condition = (
        f"createdon ge {start_date.strftime('%Y-%m-%dT00:00:00Z')} "
        f"and createdon le {end_date.strftime('%Y-%m-%dT23:59:59Z')}"
    )
    
    # First try to get job applications
    url = (
        f"{CRM_URL}/new_jobapplications?"
        f"$select={','.join(fields)}&"
        f"$filter={quote(filter_condition)}&"
        "$top=5"  # Limit to 5 for exploration
    )
    
    try:
        print("\nFetching job applications with all available fields...")
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "value" in data:
            applications = data["value"]
            print(f"\nFound {len(applications)} applications")
            
            if applications:
                print("\nSample job application data with all available fields:")
                print(json.dumps(applications[0], indent=2))
                
                # Now let's explore annotations for the first application
                app = applications[0]
                app_id = app.get('new_jobapplicationid')
                
                if app_id:
                    print(f"\nExploring annotations for application {app_id}...")
                    
                    # First get annotation metadata
                    annotation_fields = explore_entity_metadata(session, "annotation")
                    
                    if not annotation_fields:
                        print("Could not get annotation metadata. Using basic fields only.")
                        annotation_fields = ["filename", "mimetype", "documentbody", "subject", "notetext", "createdon", "modifiedon"]
                    
                    annotations_url = (
                        f"{CRM_URL}/annotations?"
                        f"$filter=_objectid_value eq {app_id}&"
                        f"$select={','.join(annotation_fields)}"
                    )
                    
                    try:
                        annotations_response = session.get(annotations_url)
                        annotations_response.raise_for_status()
                        annotations_data = annotations_response.json()
                        
                        if "value" in annotations_data:
                            annotations = annotations_data["value"]
                            print(f"\nFound {len(annotations)} annotations")
                            
                            if annotations:
                                print("\nSample annotation data (excluding documentbody):")
                                sample_annotation = annotations[0].copy()
                                if "documentbody" in sample_annotation:
                                    sample_annotation["documentbody"] = "[BINARY DATA]"
                                print(json.dumps(sample_annotation, indent=2))
                        
                    except requests.exceptions.RequestException as e:
                        print(f"Error fetching annotations: {e}")
                
                # List all actual fields found in the response
                print("\nActual fields present in job applications response:")
                for key in applications[0].keys():
                    print(f"- {key}")
                
        else:
            print("No applications found in the response")
            
    except requests.exceptions.RequestException as e:
        print(f"Error exploring job applications: {e}")

def main():
    print("Starting CRM exploration...")
    session = get_session()
    explore_job_applications(session)

if __name__ == "__main__":
    main() 