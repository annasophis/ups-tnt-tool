import httpx
import datetime

# FedEx Production Credentials
FEDEX_CLIENT_ID = "l78b75c9d0103e4c9e9555693656261fc0"
FEDEX_CLIENT_SECRET = "b63d1e571f474f92b070936625d39d4e"
FEDEX_AUTH_URL = "https://apis.fedex.com/oauth/token"
FEDEX_RATE_URL = "https://apis.fedex.com/rate/v1/rates/quotes"
SHIPPER_ACCOUNT = "202600195"

# Get OAuth token from FedEx
async def get_fedex_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": FEDEX_CLIENT_ID,
        "client_secret": FEDEX_CLIENT_SECRET
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(FEDEX_AUTH_URL, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]

# Submit a Rate Request (Transit Times Only)
async def get_fedex_transit_times(ship_date: str, origin: dict, destination: dict):
    token = await get_fedex_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "accountNumber": {
            "value": SHIPPER_ACCOUNT
        },
        "rateRequestControlParameters": {
            "returnTransitTimes": True,
            "rateSortOrder": "COMMITASCENDING"
        },
        "requestedShipment": {
            "preferredCurrency": "CAD",
            "shipDateStamp": ship_date,
            "rateRequestType": ["ACCOUNT"],
            "shipper": {
                "address": origin
            },
            "recipient": {
                "address": destination
            },
            "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
            "requestedPackageLineItems": [
                {
                    "groupPackageCount": 1,
                    "weight": {
                        "units": "LB",
                        "value": 5
                    },
                    "dimensions": {
                        "length": 5,
                        "width": 5,
                        "height": 5,
                        "units": "IN"
                    },
                    "contentRecord": [
                        {
                            "receivedQuantity": 1,
                            "description": "test"
                        }
                    ]
                }
            ],
            "packagingType": "YOUR_PACKAGING"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(FEDEX_RATE_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
