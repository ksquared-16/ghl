from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import re

app = FastAPI()
logger = logging.getLogger("uvicorn")


@app.get("/")
async def root():
    return {"status": "ok", "message": "Alloy dispatcher root"}


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Alloy dispatcher is live"}


def to_number(value):
    """Best-effort helper: turn strings like '99', '$99', '1,200' into a number."""
    if value is None:
        return None
    s = str(value)
    # strip everything except digits and dot
    cleaned = re.sub(r"[^\d.]", "", s)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_estimated_price(payload: dict) -> float:
    """
    Try to get an estimated price from:
    - 'Estimated Price (Contact)' field
    - fallback: parse from 'Price Breakdown (Contact)' total line
    """
    direct = payload.get("Estimated Price (Contact)") or payload.get("Estimated Price")
    num = to_number(direct)
    if num is not None:
        return num

    breakdown = payload.get("Price Breakdown (Contact)") or payload.get("Price Breakdown") or ""
    # Look for a line like 'Total: $169'
    match = re.search(r"Total:\s*\$?([0-9]+(?:\.[0-9]+)?)", breakdown)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    return 0.0


@app.post("/dispatch")
async def dispatch(request: Request):
    """
    Receive webhook from GHL, extract a clean 'job summary',
    and (later) use that to drive contractor assignment.
    """
    payload = await request.json()
    logger.info(f"Received payload from GHL: {payload}")

    # Calendar / appointment info
    calendar = payload.get("calendar") or {}
    job_id = calendar.get("appointmentId") or calendar.get("id")
    start_time = calendar.get("startTime")
    end_time = calendar.get("endTime")

    # Customer identity
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    full_name = payload.get("full_name") or f"{first_name} {last_name}".strip()
    customer_name = full_name or "Unknown"

    # Contact + location info
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

    # Home / job details
    home_type = payload.get("Home Type") or payload.get("HomeType") or ""
    sqft = payload.get("Approximate Square Footage") or ""
    bedrooms = payload.get("Bedrooms") or ""
    bathrooms = payload.get("Bathrooms") or ""

    # Service type — from your new field, or fallback
    service_type = (
        payload.get("Service Type")
        or payload.get("Service Needed")
        or "Standard Home Cleaning"
    )

    # Pricing
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

    # GHL doesn't care about the body, but returning it helps with curl tests
    return JSONResponse({"ok": True, "job": job_summary})