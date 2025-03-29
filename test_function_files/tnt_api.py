# tnt_api.py

import requests
from auth import get_access_token

def call_time_in_transit_api(payload, version="v1"):
    token = get_access_token()
    if not token:
        print("❌ Could not obtain access token.")
        return None

    url = f"https://wwwcie.ups.com/api/shipments/{version}/transittimes"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "transId": "abc123",  # Static for now, can be randomized
        "transactionSrc": "upstnt"  # Required!
    }

    print(f"📡 Calling UPS Time in Transit API...")
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        print("✅ API call successful.")
        return response.json()
    else:
        print(f"❌ API call failed with status code {response.status_code}")
        print(response.text)
        return None
