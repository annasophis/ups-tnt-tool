import requests
import json

# UPS API variables
access_token = "eyJraWQiOiI5NzllNmVhYy1iZmExLTQzZmQtYTliZi05NTBhYzE0OGVkNjMiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzM4NCJ9.eyJzdWIiOiJicnVuby5ib3VjaGVyQGdtYWlsLmNvbSIsImNsaWVudGlkIjoiN0pjeU9SQXoyekdJQXpUd3NIVWQwV242SHFNdmd4OE5PR1FIbTJjY1V6V1d5a2tmIiwiaXNzIjoiaHR0cHM6Ly9hcGlzLnVwcy5jb20iLCJ1dWlkIjoiNDNEQTE1MjctNjg1MS0xQzJBLUIwREMtOTgwNTM0MkIzMDBCIiwic2lkIjoiOTc5ZTZlYWMtYmZhMS00M2ZkLWE5YmYtOTUwYWMxNDhlZDYzIiwiYXVkIjoiQnJ1bm9UZXN0YXBwIiwiYXQiOiJyUXcwR25NQU02Nzh1N3dFSElncnE1R2tYcDFEIiwibmJmIjoxNzQzMDQ0NjI2LCJzY29wZSI6IkxvY2F0b3JXaWRnZXQiLCJEaXNwbGF5TmFtZSI6IkJydW5vVGVzdGFwcCIsImV4cCI6MTc0MzA1OTAyNiwiaWF0IjoxNzQzMDQ0NjI2LCJqdGkiOiI2ZTZhOGU3MC0yNjM0LTRlNzktOWViNy05NzBkNmYzZmE4Y2MifQ.k3Ae1SCkPTK2vlTUFk16Nupw5kj668codbPyo70VBKRtma6WcKYZjsJc8QiXEUHDIjH3FaU2Z1RWb1-e_mJVSUPJ08huT4oPlsymHVLX-vl72rflqUUKJ_2-YA_3b0qt3AxcNodXrAvqSviB8DDyLH2yHhRZFKiNhKDk-GQLBdQuZnJn4V_RlT0jUC4K81_hIqlBm7Ezzqmz6waMON3JvN3lqIH_BrGAX0dnws7zNM2j2tApf7GEt7Ciz6TX7BlowY-TDFX1FocNCs_K4DNMpQTsG8sJKyss9Ri_6Et1rSKmANNI9-9P-EJ4WVifRqIl-ype7ovWwt1vzdlzrHK6MsXlhaq2Ry5e3yhwwFehXVlT82VV5reHJHTOYOC_97rqt-iXuOreknbsHHZ65vCydhqo-PW93Zg3BC1pB3H6ADrRHDo3z9JerbVsLhmABrdsQZDfhSYRW_1KqmCsZOjcFqorCLHb47YCSu9rqMNOyHf3DsqRROJDbIyCcy62bM_IjHMoKKV5rqNkUzP0E9znm4Oeit7Rr6flKzT5tS5RjXSPxaCegzM2fgWHzW5HOR6ZVR2uhfrGlx0MiW1-9twlzJ0OADTNzJBissq5X7kRnhivQBmqwBMfSpRMDWO3I6q2bdOt0YSHBxIB3xl9Pzd_w36tXke9cxHjGxf7IcNl7wM"  # Replace this with the token you printed earlier
version = "v1"  # Adjust if UPS changes the version

url = f"https://wwwcie.ups.com/api/shipments/{version}/transittimes"

# Headers
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}",
    "transId": "TNT-Tool-001",  # optional but good for tracking
    "transactionSrc": "upstnt-app"  # required!
}


# Example request body
payload = {
    "originCountryCode": "CA",
    "originStateProvince": "QC",
    "originCityName": "Boucherville",
    "originTownName": "",
    "originPostalCode": "J4B6H5",
    "destinationCountryCode": "US",
    "destinationStateProvince": "NH",
    "destinationCityName": "MANCHESTER",
    "destinationTownName": "",
    "destinationPostalCode": "03104",
    "weight": "10.5",
    "weightUnitOfMeasure": "LBS",
    "shipmentContentsValue": "10.5",
    "shipmentContentsCurrencyCode": "USD",
    "billType": "03",
    "shipDate": "2025-03-27",
    "shipTime": "",
    "residentialIndicator": "",
    "avvFlag": True,
    "numberOfPackages": "1"
}

# Call the TNT API
response = requests.post(url, headers=headers, json=payload)

# Show the raw response
print(f"Status Code: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# Save to file (optional)
with open("sample_response.json", "w") as f:
    json.dump(response.json(), f, indent=2)
    print("Response saved to sample_response.json")
