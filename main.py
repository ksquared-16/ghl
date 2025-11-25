import os
import logging
from typing import Dict, Any, List
from datetime import datetime

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------
# Config & globals
# ---------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alloy-dispatcher")

GHL_API_KEY = os.getenv("GHL_API_KEY")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")

if not GHL_API_KEY:
    raise RuntimeError("GHL_API_KEY environment variable must be set")

if not GHL_LOCATION_ID:
    raise RuntimeError("GHL_LOCATION_ID environment variable must be set")

LC_BASE_URL = "https://services.leadconnectorhq.com"
CONTACTS_URL = f"{LC_BASE_URL}/contacts/"
CONVERSATIONS_URL = f"{LC_BASE_URL}/conversations/messages"

# IMPORTANT: use the full schema key for the Jobs custom object
JOBS_RECORDS_URL = f"{LC_BASE_URL}/objects/custom_objects.jobs/records"

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
    NOTE: Caller should ensure the contact has a phone number; otherwise GHL returns 422.
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
        # This is the external job id we use everywhere (calendar appointmentId)
        "job_id": calendar.get("appointmentId"),
        "customer_name": full_name or "Unknown",
        "contact_id": contact_id,
        "service_type": service_type,
        "estimated_price": estimated_price,
        "start_time": calendar.get("startTime"),
        "end_time": calendar.get("endTime"),
    }
    logger.info("Job summary: %s", job_summary)
    return job_summary


def upsert_job_assignment_to_ghl(job_id: str, contractor_id: str, contractor_name: str) -> None:
    """
    Upsert assignment details into the Jobs custom object in GHL,
    keyed by external_job_id (which we're using as the unique job_id from the calendar).

    This mirrors the working curl:
    PUT https://services.leadconnectorhq.com/objects/custom_objects.jobs/records/{recordId}?locationId=...
    but uses the POST upsert-by-uniqueField variant:
    POST /objects/custom_objects.jobs/records?locationId=...
    """
    if not job_id or not contractor_id:
        logger.warning("upsert_job_assignment_to_ghl: missing job_id or contractor_id, skipping")
        return

    payload = {
        "uniqueField": "external_job_id",
        "uniqueValue": job_id,
        "properties": {
            # You can omit external_job_id here if you want to match your curl exactly,
            # but including it is safe and keeps the record consistent.
            "external_job_id": job_id,
            "contractor_assigned_id": contractor_id,
            "contractor_assigned_name": contractor_name,
            # Must be one of your defined options:
            # pending_assignment, assigned, contractor_assigned, in_progress, completed, cancelled
            "job_status": "contractor_assigned",
        },
    }

    logger.info(
        "Updating Jobs object on assignment via %s with params locationId=%s and payload: %s",
        JOBS_RECORDS_URL,
        GHL_LOCATION_ID,
        payload,
    )

    try:
        # 🔴 IMPORTANT: add locationId as a QUERY PARAM, not in the body.
        resp = requests.post(
            JOBS_RECORDS_URL,
            headers=_ghl_headers(),
            params={"locationId": GHL_LOCATION_ID},
            json=payload,
            timeout=10,
        )
        if resp.ok:
            logger.info("Jobs object assignment upsert OK: %s", resp.text)
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
    Webhook from GHL when an appointment is booked.
    1. Build a job summary and cache it in JOB_STORE (keyed by job_id / appointmentId).
    2. Fetch eligible contractors.
    3. Send SMS to each contractor with "Reply YES to accept."
    """
    payload = await request.json()
    logger.info("Received payload from GHL: %s", payload)

    job_summary = build_job_summary(payload)

    # enrich with dispatch metadata
    job_summary.setdefault("notified_contractors", [])
    job_summary["assigned_contractor_id"] = None
    job_summary["assigned_contractor_name"] = None    # noqa: E501
    job_summary["dispatched_at"] = datetime.utcnow().isoformat()

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
        f"Reply YES to accept."
    )

    notified_ids: List[str] = []
    for c in contractors:
        # Skip contractors without id or phone to avoid 422 "Missing phone number"
        if not c.get("id") or not c.get("phone"):
            logger.info(
                "Skipping contractor without valid id/phone: id=%s phone=%s",
                c.get("id"),
                c.get("phone"),
            )
            continue

        send_conversation_sms(c["id"], msg)
        notified_ids.append(c["id"])
        job_summary["notified_contractors"].append(c["id"])

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

    Supports:
      - "YES <job_id>"  (explicit job, still supported)
      - "Yes" / "Y" / "Yeah" etc. (we infer latest job sent to that contractor)
    """
    payload = await request.json()
    logger.info("Received contractor reply webhook: %s", payload)

    custom = payload.get("customData") or {}

    contact_id = (
        payload.get("contact_id")
        or payload.get("contactId")
        or custom.get("contact_id")
    )

    # Prefer customData.body, then message.body, then raw message string
    message_obj = payload.get("message") or {}
    raw_message = custom.get("body") or message_obj.get("body") or payload.get("message")

    # Normalize raw_message -> string
    if isinstance(raw_message, dict):
        raw_message = raw_message.get("body") or ""
    if raw_message is None:
        raw_message = ""

    message_text = str(raw_message)
    logger.info("Parsed contractor reply: contact_id=%s, message_text=%s", contact_id, message_text)

    text_stripped = message_text.strip()
    text_upper = text_stripped.upper()
    parts = text_stripped.split()

    # Start with job_id from customData if present and non-empty
    job_id = custom.get("job_id")
    if isinstance(job_id, str):
        job_id = job_id.strip() or None

    # If not provided, try to parse "YES <job_id>" pattern (still allowed,
    # but not required anymore)
    if not job_id and len(parts) >= 2 and parts[0].upper() == "YES":
        job_id = parts[1].strip() or None

    job = None

    # If we have an explicit job_id, try to get it from JOB_STORE
    if job_id:
        job = JOB_STORE.get(job_id)

    # If no job yet, but it's a YES/Y reply, fall back to latest job
    if not job:
        if text_upper not in ("YES", "Y", "YEA", "YEAH", "YEP"):
            logger.error("contractor-reply: invalid reply format: %s", message_text)
            return JSONResponse(
                {"ok": False, "reason": "invalid_format", "message_text": message_text},
                status_code=200,
            )

        # Look for jobs we notified this contractor about
        candidate_jobs = [
            (jid, j)
            for jid, j in JOB_STORE.items()
            if contact_id and contact_id in (j.get("notified_contractors") or [])
        ]
        if not candidate_jobs:
            logger.error(
                "contractor-reply: no matching job found for contractor %s. Known job_ids=%s",
                contact_id,
                list(JOB_STORE.keys()),
            )
            return JSONResponse(
                {"ok": False, "reason": "job_not_found_for_contractor", "contact_id": contact_id},
                status_code=200,
            )

        # Pick the most recently dispatched job
        candidate_jobs.sort(key=lambda pair: pair[1].get("dispatched_at", ""))
        job_id, job = candidate_jobs[-1]

    if not job or not job_id:
        logger.error(
            "contractor-reply: job still not resolved. job_id=%s, known job_ids=%s",
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

    # mark assignment in memory
    job["assigned_contractor_id"] = contact_id
    job["assigned_contractor_name"] = contractor_name

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
        if not cid or cid == contact_id or not c.get("phone"):
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

    # 4) Push assignment into Jobs object
    upsert_job_assignment_to_ghl(job_id, contact_id or "", contractor_name or "")

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