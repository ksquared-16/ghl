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
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")
LC_BASE_URL = "https://services.leadconnectorhq.com"
GHL_BASE_URL = LC_BASE_URL  # for contacts etc.


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
# Normalize GHL tags reliably
# ---------------------------
def normalize_tags(raw_tags):
    """
    GHL can return tags as:
    - a list of strings
    - a list of objects: [{"name": "tag"}]
    - a comma-separated string
    """
    if raw_tags is None:
        return []

    # list case
    if isinstance(raw_tags, list):
        cleaned = []
        for t in raw_tags:
            if isinstance(t, str):
                cleaned.append(t.lower())
            elif isinstance(t, dict) and "name" in t:
                cleaned.append(t["name"].lower())
        return cleaned

    # comma-separated string
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
        "Accept": "application/json",
        "Version": "2021-07-28",  # contacts API version
    }

    params = {
        "limit": 100,
        "locationId": GHL_LOCATION_ID,
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        logger.error(f"GHL contact fetch failed ({response.status_code}): {response.text}")
        return []

    data = response.json()
    contacts = data.get("contacts", [])

    contractors = []

    for c in contacts:
        source = (c.get("source") or "").lower()
        tags = normalize_tags(c.get("tags"))
        phone = c.get("phone")
        name = f"{(c.get('firstName') or '').strip()} {(c.get('lastName') or '').strip()}".strip()
        name = name or c.get("contactName") or "Unknown Contractor"

        # Skip if no phone number
        if not phone:
            continue

        # Contractor detection rules:
        # - source == "contractor-cleaning"
        # - OR tag contains "contractor_cleaning"
        is_source = source == "contractor-cleaning"
        has_tag = any("contractor_cleaning" in t for t in tags)

        if is_source or has_tag:
            contractors.append({
                "id": c.get("id"),
                "name": name.lower(),
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
# Send SMS to contractor via Conversations API
# ---------------------------
def send_sms_to_contractor(contractor: dict, job: dict):
    """
    Uses LeadConnector Conversations API:
    POST /conversations/messages
    """
    if not GHL_API_KEY or not GHL_LOCATION_ID:
        logger.error("Missing GHL_API_KEY or GHL_LOCATION_ID — cannot send SMS")
        return

    url = f"{LC_BASE_URL}/conversations/messages"

    customer_name = job.get("customer_name", "New customer")
    address = job.get("address") or "Address provided in app"
    start_time = job.get("start_time") or "TBD"
    service_type = job.get("service_type") or "Cleaning"
    estimated_price = job.get("estimated_price") or 0.0

    msg = (
        f"New cleaning job available from Alloy:\n\n"
        f"Customer: {customer_name}\n"
        f"Service: {service_type}\n"
        f"When: {start_time}\n"
        f"Address: {address}\n"
        f"Estimate: ${estimated_price:.0f}\n\n"
        f"Reply YES in this thread if you can take it."
    )

    body = {
        "contactId": contractor["id"],
        "locationId": GHL_LOCATION_ID,
        "type": "SMS",
        "message": msg,
    }

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Content-Type": "application/json",
        "Version": "2021-04-15",  # conversations/messages API version
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        if resp.status_code not in (200, 201):
            logger.error(
                f"Failed to send SMS to contractor {contractor['id']} "
                f"({contractor['phone']}): {resp.status_code} {resp.text}"
            )
        else:
            logger.info(f"Sent SMS to contractor {contractor['id']} ({contractor['phone']})")
    except Exception as e:
        logger.exception(f"Error sending SMS to contractor {contractor['id']}: {e}")


# ---------------------------
# Dispatch endpoint
# ---------------------------
@app.post("/dispatch")
async def dispatch(request: Request):
    payload = await request.json()
    logger.info(f"Received payload from GHL: {payload}")

    # Extract calendar
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

    # Fetch contractors
    contractors = fetch_contractors_from_ghl()
    logger.info(f"Contractors found: {contractors}")

    # 🔥 Broadcast SMS to all contractors (for now)
    for c in contractors:
        send_sms_to_contractor(c, job_summary)

    # Return everything for now for debugging
    return JSONResponse({
        "ok": True,
        "job": job_summary,
        "contractors_notified": [c["id"] for c in contractors],
    })