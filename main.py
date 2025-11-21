import os
import re
import logging
from typing import Dict, Any

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
GHL_CONTACTS_URL = f"{GHL_BASE_URL}/contacts/"
GHL_CONVERSATIONS_URL = f"{GHL_BASE_URL}/conversations/messages/"

# Simple in-memory store: job_id -> job info
JOB_STORE: Dict[str, Dict[str, Any]] = {}


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
    if raw_tags is None:
        return []

    # Already a list
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
# FETCH CONTRACTORS FROM GHL
# ---------------------------
def fetch_contractors_from_ghl():
    if not GHL_API_KEY or not GHL_LOCATION_ID:
        logger.error("GHL_API_KEY or GHL_LOCATION_ID missing — contractors cannot be fetched")
        return []

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Accept": "application/json",
        "Version": "2021-07-28",
    }

    params = {
        "limit": 100,
        "locationId": GHL_LOCATION_ID,
    }

    resp = requests.get(GHL_CONTACTS_URL, headers=headers, params=params)
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
        name = f"{c.get('firstName','')} {c.get('lastName','')}".strip() or c.get("contactName", "").strip()

        if not phone:
            continue

        is_source = source == "contractor-cleaning"
        has_tag = any("contractor_cleaning" in t for t in tags)

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
# SEND SMS VIA CONVERSATIONS API
# ---------------------------
def send_sms_to_contact(contact_id: str, message: str):
    """
    Unified helper to send an SMS to any contact via Conversations API.
    """
    if not GHL_API_KEY or not GHL_LOCATION_ID:
        logger.error("Missing GHL_API_KEY or GHL_LOCATION_ID, cannot send SMS")
        return False

    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": "2021-07-28",
    }

    payload = {
        "locationId": GHL_LOCATION_ID,
        "contactId": contact_id,
        "type": "SMS",
        "message": message,
    }

    logger.info(f"Sending SMS via Conversations API: {payload}")

    try:
        resp = requests.post(GHL_CONVERSATIONS_URL, headers=headers, json=payload)
    except Exception as e:
        logger.error(f"SMS send exception: {e}")
        return False

    # 200/201 are both success. GHL returns 201 Created with conversationId/messageId.
    if resp.status_code in (200, 201):
        logger.info(f"SMS send OK ({resp.status_code}): {resp.text}")
        return True
    else:
        logger.error(f"SMS send failed ({resp.status_code}): {resp.text}")
        return False


# ---------------------------
# DISPATCH ENDPOINT (BOOKING → SEND JOB TO CONTRACTORS)
# ---------------------------
@app.post("/dispatch")
async def dispatch(request: Request):
    payload = await request.json()
    logger.info(f"Received payload from GHL: {payload}")

    # Calendar info
    calendar = payload.get("calendar", {})
    job_id = calendar.get("appointmentId") or calendar.get("id")
    start_time = calendar.get("startTime")
    end_time = calendar.get("endTime")

    # Customer identity
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    full_name = payload.get("full_name") or f"{first_name} {last_name}".strip()
    customer_name = full_name or "Unknown"

    contact_id = payload.get("contact_id")
    # We don't text customer from here yet, but we keep the info
    # phone = payload.get("phone")

    # Service type (normalize to something clean; default standard)
    raw_service = (
        payload.get("Service Type")
        or payload.get("Service Needed")
        or "Standard Home Cleaning"
    )
    service_type = raw_service

    estimated_price = extract_estimated_price(payload)

    job_summary = {
        "job_id": job_id,
        "customer_name": customer_name,
        "contact_id": contact_id,
        "service_type": service_type,
        "estimated_price": estimated_price,
        "start_time": start_time,
        "end_time": end_time,
    }

    logger.info(f"Job summary: {job_summary}")

    # Store in in-memory job store so replies can attach to something
    if job_id:
        JOB_STORE[job_id] = {
            **job_summary,
            "status": "offered",
        }

    # Fetch contractors to notify
    contractors = fetch_contractors_from_ghl()
    logger.info(f"Contractors found: {contractors}")

    # Send job offer SMS to each contractor
    notified_ids = []
    for c in contractors:
        cid = c["id"]
        contractor_name = c["name"]

        msg = (
            f"New cleaning job available:\n"
            f"Customer: {customer_name}\n"
            f"Service: {service_type}\n"
            f"When: {start_time or 'TBD'}\n"
            f"Est. price: ${estimated_price:.2f}\n\n"
            f"Reply YES {job_id} to accept."
            if job_id
            else (
                f"New cleaning job available:\n"
                f"Customer: {customer_name}\n"
                f"Service: {service_type}\n"
                f"When: {start_time or 'TBD'}\n"
                f"Est. price: ${estimated_price:.2f}\n\n"
                "Reply YES to accept."
            )
        )

        ok = send_sms_to_contact(cid, msg)
        if ok:
            notified_ids.append(cid)

    # Keep track of who we pinged (best effort)
    if job_id and job_id in JOB_STORE:
        JOB_STORE[job_id]["notified_contractors"] = notified_ids

    return JSONResponse(
        {
            "ok": True,
            "job": job_summary,
            "contractors_notified": notified_ids,
        }
    )


# ---------------------------
# CONTRACTOR REPLY ENDPOINT (YES → ASSIGN JOB)
# ---------------------------
@app.post("/contractor-reply")
async def contractor_reply(request: Request):
    """
    Webhook target for GHL workflow:
    Trigger: 'Customer replied' LIMITED to contacts with contractor_cleaning tag.
    Action: Webhook → POST to this endpoint with the full event payload.

    We:
      - Identify contractor contact_id
      - Parse message text
      - If it starts with YES, assign them the job
      - Notify other contractors job is taken
      - Optionally notify customer
    """
    payload = await request.json()
    logger.info(f"Received contractor reply webhook: {payload}")

    # Try to get contact_id
    contact_id = (
        payload.get("contact_id")
        or payload.get("contactId")
        or (payload.get("contact") or {}).get("id")
    )

    # Try to get message text from common fields
    message_text = (
        payload.get("message")
        or payload.get("body")
        or payload.get("text")
        or payload.get("last_message")
        or (payload.get("conversation") or {}).get("message")
        or ""
    )

    if not contact_id:
        logger.error("contractor-reply: missing contact_id in payload")
        return JSONResponse({"ok": False, "reason": "missing contact_id"})

    if not message_text:
        logger.error("contractor-reply: missing message_text in payload")
        return JSONResponse({"ok": False, "reason": "missing message_text"})

    logger.info(f"Parsed contractor reply: contact_id={contact_id}, message_text={message_text}")

    # Normalize
    text_stripped = message_text.strip()
    text_upper = text_stripped.upper()

    # Only treat YES as acceptance
    if not text_upper.startswith("YES"):
        logger.info("contractor-reply: message not an acceptance, ignoring")
        return JSONResponse({"ok": True, "ignored": True})

    # Try to parse job_id from the reply (YES <job_id>)
    parts = text_stripped.split()
    job_id = None
    if len(parts) >= 2:
        job_id = parts[1].strip()

    # Fallback: if no job_id in message, grab "latest offered" job in memory
    if not job_id and JOB_STORE:
        # last inserted key: crude but works for early phase
        job_id = list(JOB_STORE.keys())[-1]
        logger.info(f"contractor-reply: no job id in message, falling back to latest job {job_id}")

    job_info = JOB_STORE.get(job_id) if job_id else None
    if not job_info:
        logger.error(f"contractor-reply: job not found for job_id={job_id}")
        return JSONResponse({"ok": False, "reason": "job_not_found", "job_id": job_id})

    # Fetch contractors again so we can identify this contractor & others
    contractors = fetch_contractors_from_ghl()
    accepter = next((c for c in contractors if c["id"] == contact_id), None)

    if not accepter:
        logger.error(f"contractor-reply: contractor {contact_id} not found in GHL")
        return JSONResponse({"ok": False, "reason": "contractor_not_found"})

    # Mark in memory as assigned
    job_info["status"] = "assigned"
    job_info["assigned_contractor_id"] = contact_id
    job_info["assigned_contractor_name"] = accepter["name"]
    JOB_STORE[job_id] = job_info

    customer_name = job_info.get("customer_name")
    start_time = job_info.get("start_time")
    est_price = job_info.get("estimated_price", 0.0)

    # 1) Confirm to accepting contractor
    contractor_confirm_msg = (
        f"You accepted this job:\n"
        f"Customer: {customer_name}\n"
        f"When: {start_time}\n"
        f"Est. price: ${est_price:.2f}\n\n"
        f"We'll share final details in your Alloy dashboard."
    )
    send_sms_to_contact(contact_id, contractor_confirm_msg)

    # 2) Notify other contractors that job is taken
    notified_ids = job_info.get("notified_contractors") or [c["id"] for c in contractors]
    taken_msg = (
        f"Job for {customer_name} on {start_time} has been claimed by another contractor."
    )

    for c in contractors:
        cid = c["id"]
        if cid == contact_id:
            continue
        if cid not in notified_ids:
            # They might not have actually been notified; we can skip or include.
            # Early phase: we can still notify them; no harm.
            pass
        send_sms_to_contact(cid, taken_msg)

    # 3) Notify customer (if we have their contact_id)
    customer_contact_id = job_info.get("contact_id")
    if customer_contact_id:
        customer_msg = (
            f"Your cleaning on {start_time} has been assigned to one of our partner teams. "
            f"They will contact you before arrival."
        )
        send_sms_to_contact(customer_contact_id, customer_msg)

    logger.info(
        f"contractor-reply: job {job_id} assigned to contractor {contact_id} ({accepter['name']})"
    )

    return JSONResponse(
        {
            "ok": True,
            "job_id": job_id,
            "assigned_to": contact_id,
            "assigned_contractor_name": accepter["name"],
        }
    )