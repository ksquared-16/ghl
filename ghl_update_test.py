import os
import json
import requests

BASE_URL = "https://services.leadconnectorhq.com"

# You can hardcode these just to test, or pull from env
GHL_API_KEY = os.getenv("GHL_API_KEY", "pit-44df8b38-fe41-4146-80a9-90f70b76bdb0")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "ZO1DxVJw65kU2EbHpHLq")

# This is the record id from your working example
JOB_RECORD_ID = "6925f09161aa2b1ef677c6cb"

url = f"{BASE_URL}/objects/custom_objects.jobs/records/{JOB_RECORD_ID}"
params = {"locationId": GHL_LOCATION_ID}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Version": "2021-07-28",
    "Authorization": f"Bearer {GHL_API_KEY}",
}

payload = {
    "properties": {
        "contractor_assigned_id": "oy0OCEseVNyGeMZhJdDP",
        "contractor_assigned_name": "Kelly Kurzman",
        "job_status": "contractor_assigned",
    }
}

print("PUT", url, "params=", params)
print("payload:", json.dumps(payload))

resp = requests.put(url, headers=headers, params=params, json=payload, timeout=15)

print("Status:", resp.status_code)
print("Body:", resp.text)