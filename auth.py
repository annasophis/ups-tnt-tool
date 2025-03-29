# auth.py

import time
import requests
import base64

CLIENT_ID = "7JcyORAz2zGIAzTwsHUd0Wn6HqMvgx8NOGQHm2ccUzWWykkf"
CLIENT_SECRET = "W6LWqMyTCvZGWnvowSx1bg1bWTB0E4zY4Atj2ei3xwftAYVByF5hDXVz9sdoLiaP"
#DEV_TOKEN_URL = "https://wwwcie.ups.com/security/v1/oauth/token"
TOKEN_URL = "https://onlinetools.ups.com/security/v1/oauth/token"
#TNT PROD - "https://onlinetools.ups.com/api/shipments/{version}/transittimes"

access_token = None
token_expiry = 0

def get_access_token():
    global access_token, token_expiry

    if access_token and time.time() < token_expiry:
        return access_token

    print("🔄 Requesting new UPS access token...")

    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {b64_auth_str}"
    }
    data = "grant_type=client_credentials"

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data["access_token"]

        expires_in = int(token_data.get("expires_in", 0))
        if not expires_in:
            print("❌ Token response did not include 'expires_in'. Full response:")
            print(token_data)
            return None

        token_expiry = time.time() + expires_in - 60
        print("✅ Token refreshed.")
        return access_token
    else:
        print("❌ Failed to get token:", response.status_code)
        print(response.text)
        return None
