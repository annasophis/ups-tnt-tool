import requests
from requests.auth import HTTPBasicAuth

def get_ups_access_token(client_id, client_secret):
    url = "https://wwwcie.ups.com/security/v1/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data, auth=HTTPBasicAuth(client_id, client_secret))

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("Error getting token:", response.status_code, response.text)
        return None

# Example usage:
access_token = get_ups_access_token(
    "7JcyORAz2zGIAzTwsHUd0Wn6HqMvgx8NOGQHm2ccUzWWykkf",
    "W6LWqMyTCvZGWnvowSx1bg1bWTB0E4zY4Atj2ei3xwftAYVByF5hDXVz9sdoLiaP"
)
print(access_token)
