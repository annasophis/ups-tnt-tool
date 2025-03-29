import requests
from sqlalchemy.orm import Session
from database import SessionLocal
from models import TNTInputData, TNTAPIResponse
from auth import get_access_token
from datetime import datetime

def call_ups_tnt_api(payload, token):
    url = "https://wwwcie.ups.com/api/shipments/v1/transittimes"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "transId": "TNT-Tool-001",
        "transactionSrc": "upstnt-app"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print("❌ Error:", response.status_code, response.text)
        return None

def build_payload_from_input(row, ship_date_str="2025-03-27"):
    return {
        "originCountryCode": "CA",
        "originStateProvince": row.origin_state,
        "originCityName": row.origin_city,
        "originPostalCode": row.origin_zip,
        "destinationCountryCode": row.dest_country,
        "destinationStateProvince": row.dest_state,
        "destinationCityName": row.dest_city_ups,
        "destinationPostalCode": row.ups_dest_zip,
        "weight": "10.5",
        "weightUnitOfMeasure": "LBS",
        "shipmentContentsValue": "10.5",
        "shipmentContentsCurrencyCode": "USD",
        "billType": "03",
        "shipDate": ship_date_str,
        "avvFlag": True,
        "numberOfPackages": "1"
    }

def process_batch(batch_id):
    db: Session = SessionLocal()
    token = get_access_token()
    input_rows = db.query(TNTInputData).filter_by(batch_id=batch_id).all()

    for row in input_rows:
        payload = build_payload_from_input(row)
        result = call_ups_tnt_api(payload, token)

        if result and "emsResponse" in result and "services" in result["emsResponse"]:
            for service in result["emsResponse"]["services"]:
                response = TNTAPIResponse(
                    service_level=service.get("serviceLevel"),
                    service_description=service.get("serviceLevelDescription"),
                    business_transit_days=service.get("businessTransitDays"),
                    total_transit_days=service.get("totalTransitDays"),
                    delivery_date=parse_date(service.get("deliveryDate")),
                    delivery_time=parse_time(service.get("deliveryTime")),
                    delivery_day_of_week=service.get("deliveryDayOfWeek"),
                    next_day_pickup_indicator=service.get("nextDayPickupIndicator"),
                    saturday_pickup_indicator=service.get("saturdayPickupIndicator"),
                    saturday_delivery_indicator=service.get("saturdayDeliveryIndicator"),
                    saturday_delivery_time=parse_time(service.get("saturdayDeliveryTime")),
                    guarantee_indicator=service.get("guaranteeIndicator"),
                    rest_days_count=service.get("restDaysCount"),
                    holiday_count=service.get("holidayCount"),
                    delay_count=service.get("delayCount"),
                    commit_time=parse_time(service.get("commitTime")),
                    ship_date=parse_date(service.get("shipDate")),
                    pickup_time=parse_time(service.get("pickupTime")),
                    pickup_date=parse_date(service.get("pickupDate")),
                    poddate=parse_date(service.get("poddate")),
                    poddays=service.get("poddays"),
                    cstccutoff_time=parse_time(service.get("cstccutoffTime")),
                    service_remarks_text=service.get("serviceRemarksText"),
                    input_id=row.id
                )
                db.add(response)

    db.commit()
    db.close()
    print("✅ Batch processing completed.")

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

def parse_time(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M:%S").time()
    except:
        return None

# Optional if you want to run via command line
if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        batch_id = int(sys.argv[1])
        process_batch(batch_id)
    else:
        print("Usage: python3 process_batch.py <batch_id>")
