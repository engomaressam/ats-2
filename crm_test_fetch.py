import requests
from requests_ntlm import HttpNtlmAuth

CRM_URL = "https://rmecrm.rowad-rme.com/RMECRM/api/data/v8.2"
USERNAME = "Rowad\\Omar Essam"
PASSWORD = "PMO@1234"

CANDIDATE_FIELDS = [
    "new_fullname",
    "new_email",
    "new_contactphone",
    "new_telephonenumber",
    "new_city",
    "new_nationality",
    "new_birthdate",
    "new_gender",
    "new_position",
    "new_department",
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
    "modifiedby",
    "new_howdidyouhearaboutrowad",
    "new_listouttheextrasocialactivities",
    "new_languages",
    "new_certifications",
    "new_jobapplicationid"
]

def main():
    session = requests.Session()
    session.auth = HttpNtlmAuth(USERNAME, PASSWORD)
    session.headers.update({
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0"
    })
    print("\nTesting each candidate field individually (with new_fullname):\n")
    for field in CANDIDATE_FIELDS:
        if field == "new_fullname":
            continue  # already included
        fields = ["new_fullname", field]
        url = f"{CRM_URL}/new_jobapplications?$select={','.join(fields)}&$top=1"
        try:
            response = session.get(url)
            response.raise_for_status()
            data = response.json()
            print(f"SUCCESS: {field}")
            if data.get("value"):
                print(f"  Example: {data['value'][0]}")
        except Exception as e:
            print(f"FAIL: {field} - {e}")

if __name__ == "__main__":
    main() 