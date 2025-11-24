import os
import logging
from typing import Dict, Any, List

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------
# Config & globals
# ---------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alloy-dispatcher")

GHL_API_KEY = os.getenv("GHL_API_KEY")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "ZO1DxVJw65kU2EbHpHLq")

LC_BASE_URL = "https://services.leadconnectorhq.com"
CONTACTS_URL = f"{LC_BASE_URL}/contacts/"
CONVERSATIONS_URL = f"{LC_BASE_URL}/conversations/messages"
OBJECTS_RECORDS_URL = f"{LC_BASE_URL}/objects/jobs/records"

# In-memory job store: { job_id (appointmentId): job_summary_dict }
JOB_STORE: Dict[str, Dict[str, Any]] = {}

app = FastAPI()

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _ghl_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
    }


def _ghl_objects_headers() -> Dict[str, str]:
    # For custom objects, LocationId must be present
    return {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "LocationId": GHL_LOCATION_ID,
    }


def fetch_contractors() -> List[Dict[str, Any]]:
    """
    Fetch contractors from GHL contacts API, filtered by tags.
    Currently: contractor_cleaning + job-pending-assignment.
    """
    params = {
        "locationId": GHL_LOCATION_ID,
        "limit": 50,
    }
    try:
        resp = requests.get(CONTACTS_URL, headers=_ghl_headers(), params=params, timeout=10)
    except Exception as e:
        logger.error("GHL contact fetch exception: %s", e)
        return []

    if not resp.ok:
        logger.error("GHL contact fetch failed (%s): %s", resp.status_code, resp.text)
        return []

    data = resp.json()
    contacts = data.get("contacts", [])
    contractors: List[Dict[str, Any]] = []

    for c in contacts:
        tags = c.get("tags") or []
        if "contractor_cleaning" in tags and "job-pending-assignment" in tags:
            contractors.append(
                {
                    "id": c.get("id"),
                    "name": c.get("contactName") or f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
                    "phone": c.get("phone"),
                    "tags": tags,
                    "contact_source": c.get("source") or "",
                }
            )

    logger.info("Fetched %d contractors from GHL", len(contractors))
    return contractors


def send_conversation_sms(contact_id: str, message: str) -> None:
    """
    Send an SMS via GHL Conversations API.
    """
    payload = {
        "locationId": GHL_LOCATION_ID,
        "contactId": contact_id,
        "type": "SMS",
        "message": message,
    }
    logger.info("Sending SMS via Conversations API: %s", payload)
    try:
        resp = requests.post(CONVERSATIONS_URL, headers=_ghl_headers(), json=payload, timeout=10)
        if resp.status_code == 201:
            logger.info("SMS send OK (201): %s", resp.text)
        else:
            logger.error("SMS send failed (%s): %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("SMS send exception: %s", e)


def build_job_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a normalized job summary dict from the GHL appointment / calendar payload.
    """
    calendar = payload.get("calendar") or {}
    contact_id = payload.get("contact_id")
    full_name = payload.get("full_name") or (
        (payload.get("first_name") or "") + " " + (payload.get("last_name") or "")
    ).strip()

    price_breakdown = payload.get("Price Breakdown (Contact)") or ""
    estimated_price = 0.0
    # Very simple parse: look for 'Total: $99' or 'Total: 99'
    for line in price_breakdown.splitlines():
        if "Total:" in line:
            try:
                part = line.split("Total:")[-1].strip().replace("$", "")
                estimated_price = float(part)
            except Exception:
                pass

    service_type = "Standard Home Cleaning"
    if "Deep" in price_breakdown:
        service_type = "Deep Cleaning"

    job_summary = {
        "job_id": calendar.get("appointmentId"),  # this is what we send in SMS & expect back
        "customer_name": full_name or "Unknown",
        "contact_id": contact_id,
        "service_type": service_type,
        "estimated_price": estimated_price,
        "start_time": calendar.get("startTime"),
        "end_time": calendar.get("endTime"),
    }
    logger.info("Job summary: %s", job_summary)
    return job_summary


def update_job_object_on_assignment(job_id: str, contractor_id: str, contractor_name: str) -> None:
    """
    Upsert into Jobs custom object:
      - external_job_id (unique)
      - contractor_assigned_id
      - contractor_assigned_name
      - job_status = 'assigned'
    """
    payload = {
        "uniqueField": "external_job_id",
        "uniqueValue": job_id,
        "fields": {
            "external_job_id": job_id,
            "contractor_assigned_id": contractor_id,
            "contractor_assigned_name": contractor_name,
            "job_status": "assigned",
        },
    }
    logger.info(
        "Updating Jobs object on assignment via %s with payload: %s",
        OBJECTS_RECORDS_URL,
        payload,
    )
    try:
        # add locationId as query param as well, because API keeps whining
        resp = requests.post(
            OBJECTS_RECORDS_URL,
            headers=_ghl_objects_headers(),
            params={"locationId": GHL_LOCATION_ID},
            json=payload,
            timeout=10,
        )
        if resp.ok:
            logger.info("Jobs object assignment upsert OK (%s): %s", resp.status_code, resp.text)
        else:
            logger.error(
                "Jobs object assignment upsert failed (%s): %s",
                resp.status_code,
                resp.text,
            )
    except Exception as e:
        logger.error("Jobs object assignment upsert exception: %s", e)


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

@app.get("/")
def root():
    return {"ok": True, "service": "alloy-dispatcher"}


@app.get("/contractors")
def get_contractors():
    contractors = fetch_contractors()
    return {"ok": True, "count": len(contractors), "contractors": contractors}


@app.get("/debug/jobs")
def debug_jobs():
    """
    Simple debug endpoint to see what jobs are currently cached in memory.
    """
    return {
        "ok": True,
        "count": len(JOB_STORE),
        "job_ids": list(JOB_STORE.keys()),
        "jobs": JOB_STORE,
    }


@app.post("/dispatch")
async def dispatch(request: Request):
    """
    Webhook from GHL when an appointment is booked (or when we manually trigger via curl).
    1. Build a job summary and cache it in JOB_STORE (keyed by job_id / appointmentId).
    2. Fetch eligible contractors.
    3. Send SMS to each contractor with "Reply YES <job_id> to accept."
    """
    payload = await request.json()
    logger.info("Received payload from GHL: %s", payload)

    job_summary = build_job_summary(payload)

    # Cache the job in memory so /contractor-reply can find it
    job_id = job_summary.get("job_id")
    if job_id:
        JOB_STORE[job_id] = job_summary
        logger.info("Cached job in memory with id=%s. JOB_STORE now has %d jobs.", job_id, len(JOB_STORE))
    else:
        logger.warning("No job_id in job_summary; not caching this job.")

    contractors = fetch_contractors()
    logger.info("Contractors found: %s", contractors)

    if not contractors:
        logger.warning("No contractors available for dispatch.")
        return JSONResponse(
            {
                "ok": False,
                "reason": "no_contractors",
                "job": job_summary,
            }
        )

    # Build contractor SMS message
    msg = (
        f"New cleaning job available:\n"
        f"Customer: {job_summary['customer_name']}\n"
        f"Service: {job_summary['service_type']}\n"
        f"When: {job_summary['start_time'] or 'TBD'}\n"
        f"Est. price: ${job_summary['estimated_price']:.2f}\n\n"
        f"Reply YES {job_summary['job_id']} to accept."
    )

    notified_ids: List[str] = []
    for c in contractors:
        if not c.get("id"):
            continue
        send_conversation_sms(c["id"], msg)
        notified_ids.append(c["id"])

    return JSONResponse(
        {
            "ok": True,
            "job": job_summary,
            "contractors_notified": notified_ids,
        }
    )


@app.post("/contractor-reply")
async def contractor_reply(request: Request):
    """
    Webhook from GHL when a *contractor* replies to the dispatch SMS.

    Your workflow is sending:
      customData.body      = {{body}}
      customData.contact_id= {{contact.id}}
      customData.job_id    = {{appointment.id}}

    We:
      1) Read message text (body)
      2) Make sure it starts with YES
      3) Read job_id from customData.job_id FIRST
      4) If job_id missing, fallback to parsing from "YES <job_id>"
      5) Update JOB_STORE + Jobs custom object
    """
    payload = await request.json()
    logger.info("Received contractor reply webhook: %s", payload)

    custom = payload.get("customData") or {}

    # contact id
    contact_id = (
        custom.get("contact_id")
        or payload.get("contact_id")
        or payload.get("contactId")
    )

    # message body
    raw_message = custom.get("body")
    if isinstance(raw_message, dict):
        raw_message = raw_message.get("body")

    if raw_message is None:
        raw_message = payload.get("message")
        if isinstance(raw_message, dict):
            raw_message = raw_message.get("body")

    if raw_message is None:
        raw_message = ""

    message_text = str(raw_message)
    logger.info("Parsed contractor reply: contact_id=%s, message_text=%s", contact_id, message_text)

    text_stripped = message_text.strip()

    # Must at least start with YES
    if not text_stripped or not text_stripped.upper().startswith("YES"):
        logger.error("contractor-reply: invalid reply format: %s", message_text)
        return JSONResponse(
            {"ok": False, "reason": "invalid_format", "message_text": message_text},
            status_code=200,
        )

    # Job id: from customData.job_id first
    job_id = custom.get("job_id")

    # Fallback: parse from "YES <jobid>" if user text includes it
    if not job_id:
        parts = text_stripped.split()
        if len(parts) >= 2:
            job_id = parts[1]

    if not job_id:
        logger.error("contractor-reply: no job_id in payload or message")
        return JSONResponse(
            {"ok": False, "reason": "job_id_missing", "message_text": message_text},
            status_code=200,
        )

    job = JOB_STORE.get(job_id)

    if not job:
        logger.error(
            "contractor-reply: job not found for job_id=%s. Known job_ids=%s",
            job_id,
            list(JOB_STORE.keys()),
        )
        return JSONResponse(
            {"ok": False, "reason": "job_not_found", "job_id": job_id},
            status_code=200,
        )

    # Lookup contractor info (mainly for name in logs / notifications)
    contractors = fetch_contractors()
    contractor = next((c for c in contractors if c.get("id") == contact_id), None)

    contractor_name = contractor.get("name") if contractor else "Unknown contractor"

    # 1) Confirm to the accepting contractor
    confirm_msg = (
        f"You accepted this job:\n"
        f"Customer: {job['customer_name']}\n"
        f"When: {job['start_time']}\n"
        f"Est. price: ${job['estimated_price']:.2f}\n\n"
        "We'll share final details in your Alloy dashboard."
    )
    if contact_id:
        send_conversation_sms(contact_id, confirm_msg)

    # 2) Notify all other contractors that the job was claimed
    for c in contractors:
        cid = c.get("id")
        if not cid or cid == contact_id:
            continue
        send_conversation_sms(
            cid,
            f"Job for {job['customer_name']} on {job['start_time']} has been claimed by another contractor.",
        )

    # 3) Notify the customer their job has been assigned (if we have their contact_id)
    customer_contact_id = job.get("contact_id")
    if customer_contact_id:
        customer_msg = (
            f"Your cleaning on {job['start_time']} has been assigned to one of our partner teams. "
            f"They will contact you before arrival."
        )
        send_conversation_sms(customer_contact_id, customer_msg)

    # 4) Update Jobs custom object in GHL
    if job_id and contact_id:
        update_job_object_on_assignment(job_id, contact_id, contractor_name)

    logger.info(
        "contractor-reply: job %s assigned to contractor %s (%s)",
        job_id,
        contact_id,
        contractor_name,
    )

    return JSONResponse(
        {
            "ok": True,
            "job_id": job_id,
            "contractor_id": contact_id,
            "contractor_name": contractor_name,
        }
    )