import os
import re
import logging
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
logger = logging.getLogger("uvicorn")

# Load GHL API Key from Render Environment
GHL_API_KEY = os.getenv("GHL_API_KEY")

# Base LeadConnector API URL
GHL_BASE_URL = "https://rest.gohighlevel.com/v1"


@app.get("/")
async def root():
    return {"status": "ok", "message": "Alloy dispatcher root"}


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Alloy dispatcher is live"}


# ---------------------------
# Number helper
# ---------------------------
def to_number(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(value))
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except:
        return None


# ---------------------------
# Extract estimated price
# ---------------------------
def extract_estimated_price(payload: dict) -> float:
    direct = payload.get("Estimated Price (Contact)") or payload.get("Estimated Price")
    num = to_number(direct)
    if num is not None:
        return num

    breakdown = payload.get("Price Breakdown (Contact)") or payload.get("Price Breakdown") or ""

    # Example: "Total: $169"
    match = re.search(r"Total:\s*\$?([0-9]+(?:\.[0-9]+)?)", breakdown)
    if match:
        return float(match.group(1))

    return 0.0


# ---------------------------
# Fetch contractors dynamically from GHL
# ---------------------------
def fetch_contractors_from_ghl():
    """
    Pull all contractors with:
    - contact_source == "contractor-cleaning"
      OR
    - tag contains contractor_cleaning
    """

    url = f"{GHL_BASE_URL}/contacts/"

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Accept": "application/json",
    }

    params = {
        "limit": 200  # pagination later if needed
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        logger.error(f"GHL contractor fetch failed: {response.text}")
        return []

    data = response.json()
    contacts = data.get("contacts", [])

    contractors = []

    for c in contacts:
        source = (c.get("contactSource") or "").lower()
        tags = [t.lower() for t in c.get("tags", [])]
        phone = c.get("phone")
        name = f"{c.get('firstName','')} {c.get('lastName','')}".strip()

        if not phone:
            continue

        if source == "contractor-cleaning" or "contractor_cleaning" in tags:
            contractors.append({
                "id": c.get("id"),
                "name": name,
                "phone": phone,
                "tags": tags,
            })

    logger.info(f"Fetched {len(contractors)} contractors from GHL")
    return contractors


# ---------------------------
# Send SMS (placeholder for Twilio or LC API)
# ---------------------------
def send_sms_to_contractor(phone, message):
    """
    Placeholder: we will integrate Twilio or LeadConnector SMS here.
    For now, just log.
    """
    logger.info(f"Would send SMS to {phone}: {message}")


# ---------------------------
# DISPATCH ENDPOINT
# ---------------------------
@app.post("/dispatch")
async def dispatch(request: Request):
    payload = await request.json()
    logger.info(f"Received payload from GHL: {payload}")

    # ---------------------------
    # Extract Job Summary
    # ---------------------------
    calendar = payload.get("calendar", {})
    job_id = calendar.get("appointmentId") or calendar.get("id")
    start_time = calendar.get("startTime")
    end_time = calendar.get("endTime")

    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    full_name = payload.get("full_name") or f"{first_name} {last_name}".strip()
    customer_name = full_name or "Unknown"

    contact_id = payload.get("contact_id")
    phone = payload.get("phone")
    tags = payload.get("tags", "")
    contact_source = payload.get("contact_source")

    location = payload.get("location") or {}
    full_address = (
        payload.get("full_address")
        or calendar.get("address")
        or location.get("fullAddress")
        or ""
    )

    home_type = payload.get("Home Type") or ""
    sqft = payload.get("Approximate Square Footage") or ""
    bedrooms = payload.get("Bedrooms") or ""
    bathrooms = payload.get("Bathrooms") or ""

    service_type = (
        payload.get("Service Type")
        or payload.get("Service Needed")
        or "Standard Home Cleaning"
    )

    estimated_price = extract_estimated_price(payload)
    price_breakdown = payload.get("Price Breakdown (Contact)") or ""

    job_summary = {
        "job_id": job_id,
        "customer_name": customer_name,
        "contact_id": contact_id,
        "phone": phone,
        "tags": tags,
        "contact_source": contact_source,
        "start_time": start_time,
        "end_time": end_time,
        "address": full_address,
        "home_type": home_type,
        "square_footage": sqft,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "service_type": service_type,
        "estimated_price": estimated_price,
        "price_breakdown": price_breakdown,
        "location_name": location.get("name"),
    }

    logger.info(f"Job summary: {job_summary}")

    # ---------------------------
    # Fetch contractors from GHL
    # ---------------------------
    contractors = fetch_contractors_from_ghl()

    logger.info(f"Contractors found: {contractors}")

    # ---------------------------
    # Placeholder for next step: sending SMS
    # ---------------------------
    # for c in contractors:
    #     send_sms_to_contractor(c["phone"], "New cleaning job available...")

    return JSONResponse({"ok": True, "job": job_summary, "contractors": contractors})