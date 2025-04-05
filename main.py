# Built-in Modules
import csv
import asyncio
from io import StringIO
from datetime import date, datetime
from typing import Optional

# FastAPI
from fastapi import (
    FastAPI, Depends, Request, UploadFile, File, Form, HTTPException, status
)
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Pydantic
from pydantic import BaseModel

# SQLAlchemy
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

# Other External Libraries
import httpx
from more_itertools import chunked

# Local Modules
from database import SessionLocal, engine
from models import Base, BatchJob, TNTInputData, TNTAPIResponse, BatchSettings
from auth import get_access_token



# In-memory batch logs (simple for now, can move to DB or file later)
batch_logs = {}

def log(batch_id: int, message: str):
    batch_logs.setdefault(batch_id, []).append(message)


class SettingsPayload(BaseModel):
    ship_date: Optional[date]
    avv_flag: bool = False
    residential_indicator: Optional[str] = ""

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
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

def get_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}",
        "transId": "TNT-Tool-001",
        "transactionSrc": "upstnt-app"
    }


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
    retries = 2
    for attempt in range(1, retries + 1):
        async with semaphore:
            try:
                # 🛑 Check stop flag before proceeding
                batch = db.query(BatchJob).get(batch_id)
                if batch.stopped:
                    print(f"🛑 Skipping request {i} — batch {batch_id} was stopped.")
                    log(batch_id, f"🛑 Skipped request {i} — batch {batch_id} was stopped.")
                    return None

              #  print(f"📤 [{i}/{total}] Attempt {attempt}")
               # log(batch_id, f"📤 [{i}/{total}] Attempt {attempt}")

                response = await client.post(UPS_URL, headers=get_headers(), json=payload)


                print(f"📦 [{i}/{total}] Status: {response.status_code}")
                log(batch_id, f"📦 [{i}/{total}] Status: {response.status_code}")
                log(batch_id, f"📩 Response for {payload['destinationCityName']} {payload['destinationPostalCode']}")

                await asyncio.sleep(0.25)
                return response.json()

            except Exception as e:
                print(f"❌ Error attempt {attempt} for request {i}: {e}")
                log(batch_id, f"❌ Error attempt {attempt} for request {i}: {e}")
                await asyncio.sleep(1)
    return {}



CHUNK_SIZE = 250  # Tune this as needed

async def process_batch_async(db: Session, batch_id: int):
    input_rows = db.query(TNTInputData).filter_by(batch_id=batch_id).all()
    total = len(input_rows)
    settings = db.query(BatchSettings).filter_by(batch_id=batch_id).first()
    processed = 0

    print(f"🚀 Starting batch of {total} requests in chunks of {CHUNK_SIZE}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk in chunked(list(enumerate(input_rows)), CHUNK_SIZE):
            batch = db.query(BatchJob).get(batch_id)
            if batch.stopped:
                print(f"🛑 Batch {batch_id} was stopped at {processed}/{total}")
                break

            tasks = [
                call_ups_throttled(client, row_to_payload(row), i + 1, total, db, batch_id)
                for i, row in chunk
            ]
            results = await asyncio.gather(*tasks)

            for (i, row), result in zip(chunk, results):
                if not result:
                    continue
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
                processed += 1

            batch.progress = int((processed / total) * 100)
            db.commit()

    # Final update
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
            origin_city=row["OriginCity"],
            origin_state=row["OriginState"],
            origin_zip=row["OriginZip"],
            #dest_city_input=row["Dest City Input"],
            dest_city_ups=row["DestCity"],
            dest_state=row["DestState"],
            #input_dest_zip=row["INPUT DEST ZIP"],
            ups_dest_zip=row["DestZipFul"],
            dest_country=row["DestCountry"],
            batch_id=batch.id,
            ship_date=date.today(),
            avv_flag=False,
            residential_indicator=""
        )
        db.add(record)

    db.commit()
    return RedirectResponse(url="/dashboard?uploaded=true", status_code=303)

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
    # Step 1: Get all input row IDs (so we can delete their responses)
    input_ids = db.scalars(
        select(TNTInputData.id).where(TNTInputData.batch_id == batch_id)
    ).all()

    # Step 2: Delete TNTAPIResponse entries
    if input_ids:
        db.execute(delete(TNTAPIResponse).where(TNTAPIResponse.input_id.in_(input_ids)))

    # Step 3: Delete TNTInputData, BatchSettings, then BatchJob
    db.execute(delete(TNTInputData).where(TNTInputData.batch_id == batch_id))
    db.execute(delete(BatchSettings).where(BatchSettings.batch_id == batch_id))
    db.execute(delete(BatchJob).where(BatchJob.id == batch_id))
    db.commit()

    return {"message": f"✅ Batch {batch_id} and related data deleted."}


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

@app.get("/logs/{batch_id}")
def get_logs(batch_id: int):
    return {"logs": batch_logs.get(batch_id, ["No logs available."])}




@app.post("/optimize_db")
async def optimize_db():
    # Optional: Check for running batches using a session
    with SessionLocal() as session:
        running = session.query(BatchJob).filter(BatchJob.status == "Started").count()
        if running > 0:
            raise HTTPException(status_code=400, detail="Cannot optimize while batches are running.")

    # Run VACUUM FULL in autocommit mode using a raw engine connection
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM"))

    return {"message": "Database optimized successfully."}
