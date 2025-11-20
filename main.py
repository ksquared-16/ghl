import os
import re
import logging
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
logger = logging.getLogger("uvicorn")

# ---------------------------
# ENV VARIABLES
# ---------------------------
GHL_API_KEY = os.getenv("GHL_API_KEY")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")  # ZO1DxVJw65kU2EbHpHLq
GHL_BASE_URL = "https://services.leadconnectorhq.com"

# ---------------------------
# ROOT + HEALTH
# ---------------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Alloy dispatcher root"}


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Alloy dispatcher is live"}


# ---------------------------
# Helper: strip numbers from messy strings
# ---------------------------
def to_number(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(value))
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except Exception:
        return None


# ---------------------------
# Extract price from payload
# ---------------------------
def extract_estimated_price(payload: dict) -> float:
    direct = payload.get("Estimated Price (Contact)") or payload.get("Estimated Price")
    num = to_number(direct)
    if num is not None:
        return num

    breakdown = payload.get("Price Breakdown (Contact)") or payload.get("Price Breakdown") or ""
    match = re.search(r"Total:\s*\$?([0-9]+(?:\.[0-9]+)?)", breakdown)
    if match:
        return float(match.group(1))

    return 0.0


# ---------------------------
# Normalize tags
# ---------------------------
def normalize_tags(raw_tags):
    if raw_tags is None:
        return []

    if isinstance(raw_tags, list):
        cleaned = []
        for t in raw_tags:
            if isinstance(t, str):
                cleaned.append(t.lower())
            elif isinstance(t, dict) and "name" in t:
                cleaned.append(t["name"].lower())
        return cleaned

    if isinstance(raw_tags, str):
        return [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

    return []


# ---------------------------
# FETCH CONTRACTORS FROM GHL
# ---------------------------
def fetch_contractors_from_ghl():
    if not GHL_API_KEY or not GHL_LOCATION_ID:
        logger.error("GHL_API_KEY or GHL_LOCATION_ID missing — contractors cannot be fetched")
        return []

    url = f"{GHL_BASE_URL}/contacts/"

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
    }

    params = {
        "limit": 100,
        "locationId": GHL_LOCATION_ID,
    }

    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        logger.error(f"GHL contact fetch failed ({resp.status_code}): {resp.text}")
        return []

    data = resp.json()
    contacts = data.get("contacts", [])

    contractors = []

    for c in contacts:
        source = (c.get("source") or "").lower()
        tags = normalize_tags(c.get("tags"))
        phone = c.get("phone")
        name = (c.get("contactName")
                or f"{c.get('firstName','')} {c.get('lastName','')}".strip())

        if not phone:
            continue

        is_source = source == "contractor-cleaning"
        has_tag = any("contractor" in t for t in tags)

        if is_source or has_tag:
            contractors.append({
                "id": c.get("id"),
                "name": name,
                "phone": phone,
                "tags": tags,
                "contact_source": source,
            })

    logger.info(f"Fetched {len(contractors)} contractors from GHL")
    return contractors


@app.get("/contractors")
async def contractors_probe():
    contractors = fetch_contractors_from_ghl()
    return {
        "ok": True,
        "count": len(contractors),
        "contractors": contractors,
    }


# ---------------------------
# SEND SMS VIA LEADCONNECTOR
# ---------------------------
def send_sms_to_contractor(contact_id: str, message: str):
    """
    Sends SMS via LeadConnector Conversations API.
    """
    if not GHL_API_KEY or not GHL_LOCATION_ID:
        logger.error("Missing GHL_API_KEY or GHL_LOCATION_ID; cannot send SMS.")
        return

    url = f"{GHL_BASE_URL}/conversations/messages/send"

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "locationId": GHL_LOCATION_ID,
        "contactId": contact_id,
        "type": "SMS",
        "message": message,
    }

    logger.info(f"Sending SMS via LC: {payload}")

    resp = requests.post(url, headers=headers, json=payload)

    if resp.status_code not in (200, 201, 202):
        logger.error(f"SMS send failed ({resp.status_code}): {resp.text}")
    else:
        logger.info(f"SMS delivered successfully: {resp.text}")


# ---------------------------
# DISPATCH ENDPOINT
# ---------------------------
@app.post("/dispatch")
async def dispatch(request: Request):
    payload = await request.json()
    logger.info(f"Received payload from GHL: {payload}")

    # Calendar / appointment info
    calendar = payload.get("calendar", {})
    job_id = calendar.get("appointmentId") or calendar.get("id")
    start_time = calendar.get("startTime")
    end_time = calendar.get("endTime")

    # Customer identity
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    full_name = payload.get("full_name") or f"{first_name} {last_name}".strip()
    customer_name = full_name or "Unknown"

    # Contact + location
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

    # Home/job details
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
    price_breakdown = payload.get("Price Breakdown (Contact)") or payload.get("Price Breakdown") or ""

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

    # Fetch contractors
    contractors = fetch_contractors_from_ghl()
    logger.info(f"Contractors found: {contractors}")

    # Build SMS message
    msg = (
        f"New cleaning job available:\n"
        f"Customer: {customer_name}\n"
        f"Service: {service_type}\n"
        f"When: {start_time or 'TBD'}\n"
        f"Address: {full_address or 'TBD'}\n"
        f"Est. price: ${estimated_price:.2f}\n\n"
        f"Reply YES to accept."
    )

    notified_ids = []

    for c in contractors:
        c_id = c["id"]
        logger.info(f"About to send SMS to contractor {c_id} ({c['phone']})")
        send_sms_to_contractor(contact_id=c_id, message=msg)
        notified_ids.append(c_id)

    return JSONResponse({
        "ok": True,
        "job": job_summary,
        "contractors_notified": notified_ids,
    })