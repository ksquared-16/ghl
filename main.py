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
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")  # MUST be set in Render!
GHL_CONTACTS_URL = "https://services.leadconnectorhq.com"
LC_SMS_URL = "https://public-api.leadconnectorhq.com/conversations/messages/"


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
    except:
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
# Normalize tags (GHL returns in different formats)
# ---------------------------
def normalize_tags(raw_tags):
    if raw_tags is None:
        return []

    # List of strings
    if isinstance(raw_tags, list):
        cleaned = []
        for t in raw_tags:
            if isinstance(t, str):
                cleaned.append(t.lower())
            elif isinstance(t, dict) and "name" in t:
                cleaned.append(t["name"].lower())
        return cleaned

    # Comma-separated string
    if isinstance(raw_tags, str):
        return [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

    return []


# ---------------------------
# Fetch contractors from GHL Contacts API
# ---------------------------
def fetch_contractors_from_ghl():
    if not GHL_API_KEY:
        logger.error("GHL_API_KEY missing — contractors cannot be fetched")
        return []

    url = f"{GHL_CONTACTS_URL}/contacts/"

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
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
        name = f"{c.get('firstName','')} {c.get('lastName','')}".strip()

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
LC_SMS_URL = "https://public-api.leadconnectorhq.com/conversations/messages/"

def send_sms_to_contractor(contact_id: str, message: str):
    """
    Fire an outbound SMS using the LeadConnector Conversations API.
    """
    location_id = "ZO1DxVJw65kU2EbHpHLq"  # Alloy - Cleaning

    if not GHL_API_KEY:
        logger.error("GHL_API_KEY missing — cannot send SMS")
        return False

    payload = {
        "locationId": location_id,
        "contactId": contact_id,
        "type": "SMS",
        "message": message,
    }

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
    }

    logger.info(f"Sending SMS via LC: {payload}")

    try:
        resp = requests.post(LC_SMS_URL, headers=headers, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"SMS send exception: {e}")
        return False

    if resp.status_code >= 200 and resp.status_code < 300:
        logger.info(f"SMS send success ({resp.status_code}): {resp.text}")
        return True
    else:
        logger.error(f"SMS send failed ({resp.status_code}): {resp.text}")
        return False


# ---------------------------
# Dispatch endpoint
# ---------------------------
@app.post("/dispatch")
async def dispatch(request: Request):
    payload = await request.json()
    logger.info(f"Received payload from GHL: {payload}")

    # Dummy job summary for now
    job_summary = {
        "job_id": payload.get("appointmentId"),
        "customer_name": payload.get("full_name", "Unknown"),
        "service_type": "Standard Home Cleaning",
        "estimated_price": 0.0,
    }

    logger.info(f"Job summary: {job_summary}")

    contractors = fetch_contractors_from_ghl()
    logger.info(f"Contractors found: {contractors}")

    notified = []

    # Send SMS to each contractor
    for c in contractors:
        message = (
            "New cleaning job available:\n"
            f"Customer: {job_summary['customer_name']}\n"
            f"Service: {job_summary['service_type']}\n"
            "When: TBD\n"
            "Address: TBD\n"
            f"Est. price: ${job_summary['estimated_price']:.2f}\n\n"
            "Reply YES to accept."
        )

        send_sms_to_contractor(c["id"], message)
        notified.append(c["id"])

    return JSONResponse({
        "ok": True,
        "job": job_summary,
        "contractors_notified": notified,
    })