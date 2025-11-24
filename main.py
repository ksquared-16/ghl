import os
import logging
from typing import Dict, Any, List, Optional, Tuple

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
JOBS_OBJECT_URL = f"{LC_BASE_URL}/objects/jobs/records"

# In-memory job store: { job_id (appointmentId): job_summary_dict }
# job_summary shape:
# {
#   "job_id": str,
#   "customer_name": str,
#   "contact_id": str,
#   "service_type": str,
#   "estimated_price": float,
#   "start_time": str,
#   "end_time": str,
#   "notified_contractors": [str, ...],
#   "assigned_contractor_id": Optional[str],
# }
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
        "job_id": calendar.get("appointmentId"),  # this is what we send in SMS & expect back (or infer)
        "customer_name": full_name or "Unknown",
        "contact_id": contact_id,
        "service_type": service_type,
        "estimated_price": estimated_price,
        "start_time": calendar.get("startTime"),
        "end_time": calendar.get("endTime"),
        # these get filled in at dispatch time
        "notified_contractors": [],
        "assigned_contractor_id": None,
    }
    logger.info("Job summary: %s", job_summary)
    return job_summary


def update_job_object(job_id: str, contractor_id: str, contractor_name: str) -> None:
    """
    Upsert into the Jobs custom object in GHL, keyed by external_job_id.
    This is where we were failing with 'LocationId is not specified'.
    Fix: send LocationId both as header and query param.
    """
    if not job_id or not contractor_id:
        logger.warning("update_job_object: missing job_id or contractor_id, skipping. job_id=%s, contractor_id=%s", job_id, contractor_id)
        return

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

    headers = _ghl_headers()
    # IMPORTANT: objects API wants LocationId explicitly
    headers["LocationId"] = GHL_LOCATION_ID

    logger.info(
        "Updating Jobs object on assignment via %s with payload: %s",
        JOBS_OBJECT_URL,
        payload,
    )
    try:
        resp = requests.post(
            JOBS_OBJECT_URL,
            headers=headers,
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
    1. Build a job summary.
    2. Fetch eligible contractors.
    3. Send SMS to each contractor with "Reply YES <job_id> to accept."
       (plus support plain 'YES' by tracking notified_contractors).
    4. Cache the job summary in JOB_STORE with notified_contractors + assigned_contractor_id.
    """
    payload = await request.json()
    logger.info("Received payload from GHL: %s", payload)

    job_summary = build_job_summary(payload)
    job_id = job_summary.get("job_id")

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

    # track who we sent this job to, and that it's still unassigned
    job_summary["notified_contractors"] = notified_ids
    job_summary["assigned_contractor_id"] = None

    if job_id:
        JOB_STORE[job_id] = job_summary
        logger.info(
            "Cached job in memory with id=%s. JOB_STORE now has %d jobs.",
            job_id,
            len(JOB_STORE),
        )
    else:
        logger.warning("No job_id in job_summary; not caching this job.")

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

    Supported formats now:
      1) "YES <job_id>"  (what we've been using in tests)
      2) "YES"           (plain yes – real-world contractor behavior)

    For (2), we infer the job by finding the most recent unassigned job in JOB_STORE
    that was sent to this contractor (contact_id ∈ notified_contractors).
    """
    payload = await request.json()
    logger.info("Received contractor reply webhook: %s", payload)

    # Try multiple spots for contact_id and message_text to be robust to GHL variations
    contact_id = (
        payload.get("contact_id")
        or payload.get("contactId")
        or (payload.get("customData") or {}).get("contact_id")
    )

    raw_message = (
        payload.get("message")
        or (payload.get("customData") or {}).get("body")
        or (payload.get("message") or {}).get("body")
    )

    # Force message_text to string so .strip() always works
    if isinstance(raw_message, dict):
        # e.g., {"type": 2, "body": "Yes"}
        raw_message = raw_message.get("body") or ""
    if raw_message is None:
        raw_message = ""

    message_text = str(raw_message)
    logger.info("Parsed contractor reply: contact_id=%s, message_text=%s", contact_id, message_text)

    text_stripped = message_text.strip()
    parts = text_stripped.split()

    job_id: Optional[str] = None
    job: Optional[Dict[str, Any]] = None

    # Case 1: "YES <job_id>"
    if len(parts) >= 2 and parts[0].upper() == "YES":
        job_id = parts[1]
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

    # Case 2: plain "YES" / "Y" — infer job based on contractor + open jobs
    elif text_stripped.upper() in ("Y", "YES"):
        if not contact_id:
            logger.error("contractor-reply: plain YES but no contact_id, cannot infer job.")
            return JSONResponse(
                {"ok": False, "reason": "no_contact_id_for_plain_yes"},
                status_code=200,
            )

        candidates: List[Tuple[str, Dict[str, Any]]] = []
        for jid, j in JOB_STORE.items():
            notified = j.get("notified_contractors") or []
            assigned = j.get("assigned_contractor_id")
            if contact_id in notified and not assigned:
                candidates.append((jid, j))

        if not candidates:
            logger.error(
                "contractor-reply: no open job found for contractor_id=%s. JOB_STORE keys=%s",
                contact_id,
                list(JOB_STORE.keys()),
            )
            return JSONResponse(
                {"ok": False, "reason": "no_open_job_for_contractor"},
                status_code=200,
            )

        # At your current volume, this should almost always be 1.
        # If multiple, we take the last one (most recently inserted).
        job_id, job = candidates[-1]
        logger.info(
            "contractor-reply: inferred job_id=%s for contractor_id=%s based on notified_contractors",
            job_id,
            contact_id,
        )

    else:
        logger.error("contractor-reply: invalid reply format: %s", message_text)
        return JSONResponse(
            {"ok": False, "reason": "invalid_format", "message_text": message_text},
            status_code=200,
        )

    # Safety check
    if not job or not job_id:
        logger.error("contractor-reply: resolved job is None after parsing. message_text=%s", message_text)
        return JSONResponse(
            {"ok": False, "reason": "job_resolution_failed"},
            status_code=200,
        )

    # Mark in memory that this job is now assigned to this contractor
    job["assigned_contractor_id"] = contact_id
    JOB_STORE[job_id] = job

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

    # 4) Update the Jobs custom object in GHL
    update_job_object(job_id, contact_id or "", contractor_name)

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