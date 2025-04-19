import asyncio
from fedex import get_fedex_transit_times
import datetime
from models import FedExAPIResponse
from database import SessionLocal
from models import TNTInputData

if __name__ == "__main__":
    origin = {
        "city": "TORONTO",
        "stateOrProvinceCode": "qc",
        "postalCode": "J4B6H5",
        "countryCode": "CA",
        "residential": False
    }

    destination = {
        "city": "VANCOUVER",
        "stateOrProvinceCode": "QC",
        "postalCode": "J4B 6H5",
        "countryCode": "CA",
        "residential": False
    }


    ship_date = datetime.date.today().isoformat()
    data = asyncio.run(get_fedex_transit_times(ship_date, origin, destination))  # ✅ here
    print(data)

    session = SessionLocal()

 # 👇 Add this above the loop
input_id = 1
input_row = session.query(TNTInputData).first()
input_id = input_row.id if input_row else None

if not input_id:
    print("⚠️ No TNTInputData found. Please upload a batch first.")
    exit()

# ✅ This loop should run outside the `if`
for service in data["output"].get("rateReplyDetails", []):
    fedex_response = FedExAPIResponse(
        input_id=input_id,
        service_type=service.get("serviceType"),
        service_name=service.get("serviceDescription", {}).get("names", [{}])[0].get("value"),
        packaging_type=service.get("packagingType"),
        commit_day_of_week=service.get("commit", {}).get("dateDetail", {}).get("dayOfWeek"),
        commit_date=service.get("commit", {}).get("dateDetail", {}).get("dayFormat"),
        transit_time=service.get("commit", {}).get("transitDays", {}).get("description"),
        saturday_delivery=service.get("commit", {}).get("saturdayDelivery"),
        service_code=service.get("serviceDescription", {}).get("code"),
        service_description=service.get("serviceDescription", {}).get("description"),
    )
    session.add(fedex_response)

print(f"Inserted {len(session.new)} new responses.")
session.commit()
session.close()
