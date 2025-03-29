from fastapi import FastAPI, Depends, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from io import StringIO
import csv
import asyncio
import httpx
from datetime import date
from database import SessionLocal, engine
from models import Base, BatchJob, TNTInputData, TNTAPIResponse, BatchSettings
from auth import get_access_token
from pydantic import BaseModel
from typing import Optional
from datetime import date

class SettingsPayload(BaseModel):
    ship_date: Optional[date]
    avv_flag: bool = False
    residential_indicator: Optional[str] = ""

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------- Constants ---------------------------

CONCURRENCY_LIMIT = 250
version = "v1"
UPS_URL = f"https://onlinetools.ups.com/api/shipments/{version}/transittimes"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {get_access_token()}",
    "transId": "TNT-Tool-001",
    "transactionSrc": "upstnt-app"
}
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# --------------------------- Helper Functions ---------------------------

def row_to_payload(row: TNTInputData):
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
        "shipDate": str(row.ship_date),
        "avvFlag": row.avv_flag,
        "residentialIndicator": row.residential_indicator,
        "numberOfPackages": "1"
    }

async def call_ups_throttled(client, payload, i, total, db: Session, batch_id: int):
    retries = 3
    for attempt in range(1, retries + 1):
        async with semaphore:
            try:
                # 🛑 Check stop flag before proceeding
                batch = db.query(BatchJob).get(batch_id)
                if batch.stopped:
                    print(f"🛑 Skipping request {i} — batch {batch_id} was stopped.")
                    return None

                print(f"📤 [{i}/{total}] Attempt {attempt}")
                response = await client.post(UPS_URL, headers=HEADERS, json=payload)
                print(f"📦 [{i}/{total}] Status: {response.status_code}")
                print(f"📩 Response for {payload['destinationCityName']} {payload['destinationPostalCode']}:")
                await asyncio.sleep(0.25)
                return response.json()
            except Exception as e:
                print(f"❌ Error attempt {attempt} for request {i}: {e}")
                await asyncio.sleep(1)
    return {}

async def process_batch_async(db: Session, batch_id: int):
    input_rows = db.query(TNTInputData).filter_by(batch_id=batch_id).all()
    total = len(input_rows)
    settings = db.query(BatchSettings).filter_by(batch_id=batch_id).first()

    print(f"🚀 Starting batch of {total} async requests with concurrency limit {CONCURRENCY_LIMIT}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [
            call_ups_throttled(client, row_to_payload(row), i + 1, total, db, batch_id)
            for i, row in enumerate(input_rows)
        ]

        results = await asyncio.gather(*tasks)

        for row, result in zip(input_rows, results):
            if not result:
                continue  # Skipped due to stop or error

            services = result.get("emsResponse", {}).get("services", [])
            for service in services:
                db.add(TNTAPIResponse(
                    input_id=row.id,
                    service_level=service.get("serviceLevel"),
                    service_description=service.get("serviceLevelDescription"),
                    business_transit_days=service.get("businessTransitDays"),
                    total_transit_days=service.get("totalTransitDays"),
                    delivery_date=service.get("deliveryDate"),
                    delivery_time=service.get("deliveryTime"),
                    delivery_day_of_week=service.get("deliveryDayOfWeek"),
                    ship_date=service.get("shipDate"),
                    pickup_time=service.get("pickupTime"),
                    pickup_date=service.get("pickupDate"),
                    poddate=service.get("poddate"),
                    poddays=service.get("poddays"),
                    cstccutoff_time=service.get("cstccutoffTime"),
                    service_remarks_text=service.get("serviceRemarksText"),
                ))

        batch = db.query(BatchJob).get(batch_id)
        if not batch.stopped:
            batch.status = "Completed"
            batch.progress = 100
        db.commit()


# --------------------------- Routes ---------------------------

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload/")
async def upload_csv(batch_date: str = Form(...), file: UploadFile = File(...)):
    db: Session = next(get_db())
    batch = BatchJob(batch_date=datetime.strptime(batch_date, "%Y-%m-%d").date())
    db.add(batch)
    db.commit()
    db.refresh(batch)

    contents = await file.read()
    lines = contents.decode().splitlines()
    reader = csv.DictReader(lines)
    reader.fieldnames[0] = reader.fieldnames[0].lstrip('\ufeff')

    for row in reader:
        record = TNTInputData(
            origin_city=row["Origin City"],
            origin_state=row["Origin State"],
            origin_zip=row["Origin Zip"],
            dest_city_input=row["Dest City Input"],
            dest_city_ups=row["Dest City"],
            dest_state=row["Dest State"],
            input_dest_zip=row["INPUT DEST ZIP"],
            ups_dest_zip=row["UPS Dest Zip"],
            dest_country=row["Dest Country"],
            batch_id=batch.id,
            ship_date=date.today(),
            avv_flag=False,
            residential_indicator=""
        )
        db.add(record)

    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/save_settings/{batch_id}")
def save_settings(batch_id: int, settings: SettingsPayload, db: Session = Depends(get_db)):
    db.query(TNTInputData).filter_by(batch_id=batch_id).update({
        TNTInputData.ship_date: settings.ship_date,
        TNTInputData.avv_flag: settings.avv_flag,
        TNTInputData.residential_indicator: settings.residential_indicator
    })
    db.commit()
    return {"message": "Settings updated for all input rows"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    db: Session = next(get_db())
    batches = db.query(BatchJob).all()
    enriched = [{
        "id": b.id,
        "batch_date": b.batch_date,
        "address_count": len(b.addresses),
        "status": b.status,
        "progress": b.progress
    } for b in batches]
    return templates.TemplateResponse("dashboard.html", {"request": request, "batches": enriched})

@app.post("/start_batch/{batch_id}")
async def start_batch(batch_id: int):
    db = SessionLocal()
    batch = db.query(BatchJob).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch.status = "In Progress"
    batch.stopped = False
    batch.progress = 0
    db.commit()

    input_ids = [row.id for row in batch.addresses]
    if input_ids:
        db.query(TNTAPIResponse).filter(TNTAPIResponse.input_id.in_(input_ids)).delete(synchronize_session=False)
        db.commit()

    await process_batch_async(db, batch_id)
    return {"message": f"Batch {batch_id} completed!"}

@app.get("/export/{batch_id}")
def export_batch(batch_id: int):
    db: Session = next(get_db())
    input_rows = db.query(TNTInputData).filter_by(batch_id=batch_id).options(joinedload(TNTInputData.responses)).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Input ID", "Origin City", "Origin State", "Origin Zip",
        "Dest City Input", "Dest City (UPS)", "Dest State",
        "Input Dest Zip", "UPS Dest Zip", "Dest Country",
        "Service Level", "Service Description", "Business Transit Days",
        "Total Transit Days", "Delivery Date", "Delivery Time",
        "Delivery Day of Week", "Commit Time", "Pickup Date",
        "Pickup Time", "POD Date", "CSTC Cutoff Time"
    ])
    for row in input_rows:
        for resp in row.responses:
            writer.writerow([
                row.id, row.origin_city, row.origin_state, row.origin_zip,
                row.dest_city_input, row.dest_city_ups, row.dest_state,
                row.input_dest_zip, row.ups_dest_zip, row.dest_country,
                resp.service_level, resp.service_description, resp.business_transit_days,
                resp.total_transit_days, resp.delivery_date, resp.delivery_time,
                resp.delivery_day_of_week, resp.commit_time, resp.pickup_date,
                resp.pickup_time, resp.poddate, resp.cstccutoff_time
            ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=batch_{batch_id}_export.csv"
    })

@app.get("/batch_status/{batch_id}")
def get_batch_status(batch_id: int):
    db: Session = next(get_db())
    batch = db.query(BatchJob).filter_by(id=batch_id).first()
    if batch:
        return {"status": batch.status, "progress": batch.progress}
    return {"error": "Batch not found"}, 404

@app.delete("/delete_batch/{batch_id}")
async def delete_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(BatchJob).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    db.delete(batch)
    db.commit()
    return {"message": f"Batch {batch_id} and related data deleted."}

@app.post("/stop_batch/{batch_id}")
def stop_batch(batch_id: int):
    db = SessionLocal()
    batch = db.query(BatchJob).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.stopped = True
    batch.status = "Stopped"
    # db.commit()
    return {"message": f"Batch {batch_id} marked as stopped."}
