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

# Private Integration base URL (NOT rest.gohighlevel.com)
GHL_BASE_URL = "https://services.leadconnectorhq.com"


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

    breakdown = (
        payload.get("Price Breakdown (Contact)")
        or payload.get("Price Breakdown")
        or ""
    )
    match = re.search(r"Total:\s*\$?([0-9]+(?:\.[0-9]+)?)", breakdown)
    if match:
        return float(match.group(1))

    return 0.0


# ---------------------------
# Normalize tags from GHL
# ---------------------------
def normalize_tags(raw_tags):
    if raw_tags is None:
        return []

    # list of strings or list of dicts
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
    if not GHL_API_KEY:
        logger.error("GHL_API_KEY missing — contractors cannot be fetched")
        return []

    if not GHL_LOCATION_ID:
        logger.error("GHL_LOCATION_ID missing — contractors cannot be fetched")
        return []

    url = f"{GHL_BASE_URL}/contacts/"

    headers = {
        # IMPORTANT: for Private Integrations we send the token directly,
        # not "Bearer <token>"
        "Authorization": GHL_API_KEY,
        "Version": "2021-07-28",
        "Accept": "application/json",
    }

    params = {
        "locationId": GHL_LOCATION_ID,
        "limit": 200,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
    except Exception as e:
        logger.error(f"Error calling GHL contacts API: {e}")
        return []

    if response.status_code != 200:
        logger.error(
            f"GHL contact fetch failed "
            f"(status {response.status_code}): {response.text}"
        )
        return []

    data = response.json()
    contacts = data.get("contacts", [])

    contractors = []

    for c in contacts:
        source = (c.get("contactSource") or "").lower()
        tags = normalize_tags(c.get("tags"))
        phone = c.get("phone")
        name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()

        if not phone:
            continue

        is_source = source == "contractor-cleaning"
        has_tag = any("contractor" in t for t in tags)

        if is_source or has_tag:
            contractors.append(
                {
                    "id": c.get("id"),
                    "name": name,
                    "phone": phone,
                    "tags": tags,
                    "contact_source": source,
                }
            )

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

    contractors = fetch_contractors_from_ghl()
    logger.info(f"Contractors found: {contractors}")

    return JSONResponse(
        {
            "ok": True,
            "job": job_summary,
            "contractors": contractors,
        }
    )