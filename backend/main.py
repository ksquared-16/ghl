"""
Alloy Dispatcher API

This is the core dispatcher/API for Alloy, a marketplace connecting homeowners
with trusted local service professionals (starting with home cleaning in Bend, Oregon).

The dispatcher integrates with:
- GoHighLevel (GHL): For contact management, custom objects (Jobs), and SMS conversations
- Twilio: For SMS flows (via GHL's Conversations API)

Main workflows:
1. Job Dispatch: When a customer books a cleaning appointment via GHL, the /dispatch
   webhook is triggered. The dispatcher:
   - Builds a job summary from the appointment data
   - Fetches eligible contractors (tagged with contractor_cleaning + job-pending-assignment)
   - Sends SMS notifications to all eligible contractors

2. Contractor Reply: When a contractor replies "YES <job_id>" (or just "YES" for the latest job),
   the /contractor-reply webhook processes the acceptance:
   - Assigns the job to that contractor
   - Sends confirmation SMS to the contractor (with access details)
   - Notifies other contractors the job is claimed
   - Notifies the customer their job is assigned
   - Updates the GHL Jobs custom object with assignment details

3. Lead Submission: The /leads/cleaning endpoint accepts cleaning lead submissions
   from the frontend website and creates/updates contacts in GHL.

Environment Variables Required:
- GHL_API_KEY: GoHighLevel API key (Bearer token)
- GHL_LOCATION_ID: GoHighLevel location ID for this Alloy instance
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# ---------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alloy-dispatcher")

# Environment variables
GHL_API_KEY = os.getenv("GHL_API_KEY")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")

# GHL API endpoints
LC_BASE_URL = "https://services.leadconnectorhq.com"
CONTACTS_URL = f"{LC_BASE_URL}/contacts/"
CONVERSATIONS_URL = f"{LC_BASE_URL}/conversations/messages"
JOBS_RECORDS_URL = f"{LC_BASE_URL}/objects/custom_objects.jobs/records"
JOBS_SEARCH_URL = f"{LC_BASE_URL}/objects/custom_objects.jobs/records/search"

# GHL API version header
GHL_API_VERSION = "2021-07-28"

# Contractor filtering tags
CONTRACTOR_TAG_CLEANING = "contractor_cleaning"
CONTRACTOR_TAG_PENDING = "job-pending-assignment"

# Job status values (used in GHL Jobs custom object)
JOB_STATUS_ASSIGNED = "contractor_assigned"

# Service type defaults
SERVICE_TYPE_STANDARD = "Standard Home Cleaning"
SERVICE_TYPE_DEEP = "Deep Cleaning"

# In-memory job store: { job_id (appointmentId): job_summary_dict }
# Note: In production, consider using Redis or a database for persistence
JOB_STORE: Dict[str, Dict[str, Any]] = {}

# FastAPI app instance
app = FastAPI(
    title="Alloy Dispatcher API",
    description="API for dispatching cleaning jobs to contractors via GHL and SMS",
    version="1.0.0",
)

# CORS configuration for Next.js frontend
# In production, replace with actual frontend domain
allowed_origins = [
    "http://localhost:3000",  # Next.js dev server
    # Add production domain here when deployed
    # "https://alloy.example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------
# Pydantic Models for Request/Response
# ---------------------------------------------------------


class CleaningLeadPayload(BaseModel):
    """Payload for submitting a cleaning lead from the frontend."""

    name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    home_size: Optional[str] = None  # e.g., "1-2 bedrooms", "3-4 bedrooms"
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    preferred_frequency: Optional[str] = None  # e.g., "weekly", "bi-weekly", "monthly", "one-time"
    notes: Optional[str] = None


class ProsApplicationPayload(BaseModel):
    """Payload for submitting a pros application from the frontend."""

    name: str
    phone: str
    email: EmailStr
    experience: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------


def _ghl_headers() -> Dict[str, str]:
    """Build standard headers for GHL API requests."""
    return {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": GHL_API_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def fetch_contractors() -> List[Dict[str, Any]]:
    """
    Fetch contractors from GHL contacts API, filtered by tags.

    Returns:
        List of contractor dicts with keys: id, name, phone, tags, contact_source

    Filters for contractors with tags:
        - contractor_cleaning
        - job-pending-assignment
    """
    if not GHL_LOCATION_ID:
        logger.error("GHL_LOCATION_ID is not set; cannot fetch contractors.")
        return []

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
        if CONTRACTOR_TAG_CLEANING in tags and CONTRACTOR_TAG_PENDING in tags:
            contractors.append(
                {
                    "id": c.get("id"),
                    "name": c.get("contactName")
                    or f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
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

    Args:
        contact_id: GHL contact ID of the recipient
        message: SMS message text to send

    Note:
        GHL requires the contact to have a phone number on file.
    """
    if not GHL_LOCATION_ID:
        logger.error("GHL_LOCATION_ID is not set; cannot send SMS.")
        return

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


def create_or_update_contact_in_ghl(
    name: str,
    email: str,
    phone: str,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Create or update a contact in GHL.

    Args:
        name: Full name of the contact
        email: Email address
        phone: Phone number
        custom_fields: Optional dict of custom field values to set

    Returns:
        GHL contact ID if successful, None otherwise
    """
    if not GHL_LOCATION_ID:
        logger.error("GHL_LOCATION_ID is not set; cannot create/update contact.")
        return None

    # Split name into first/last (simple heuristic)
    name_parts = name.strip().split(maxsplit=1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    payload = {
        "locationId": GHL_LOCATION_ID,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phone": phone,
        "source": "Website Lead",
    }

    if custom_fields:
        payload.update(custom_fields)

    try:
        resp = requests.post(CONTACTS_URL, headers=_ghl_headers(), json=payload, timeout=10)
        if resp.ok:
            data = resp.json()
            contact_id = data.get("contact", {}).get("id")
            logger.info("Created/updated contact in GHL: %s", contact_id)
            return contact_id
        else:
            logger.error("Failed to create/update contact in GHL (%s): %s", resp.status_code, resp.text)
            return None
    except Exception as e:
        logger.error("Exception creating/updating contact in GHL: %s", e)
        return None


def build_job_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a normalized job summary dict from the GHL appointment / calendar payload.

    Args:
        payload: Raw webhook payload from GHL appointment booking

    Returns:
        Dict with keys: job_id, customer_name, contact_id, service_type, estimated_price,
        start_time, end_time, access_method, access_notes

    Price parsing logic:
        - Primary source: "Estimated Price (Contact)" field (numeric)
        - Fallback: Parse from "Price Breakdown (Contact)" text (looks for "Total: $XXX")

    Service type detection:
        - Default: "Standard Home Cleaning"
        - If "Deep" appears in price breakdown: "Deep Cleaning"
    """
    calendar = payload.get("calendar") or {}
    contact_id = payload.get("contact_id")
    full_name = payload.get("full_name") or (
        (payload.get("first_name") or "") + " " + (payload.get("last_name") or "")
    ).strip()

    price_breakdown = payload.get("Price Breakdown (Contact)") or ""

    # 1) Try direct numeric value from "Estimated Price (Contact)"
    estimated_price = 0.0
    est_raw = payload.get("Estimated Price (Contact)") or payload.get("Estimated Price")
    if est_raw:
        try:
            est_str = str(est_raw).replace("$", "").replace(",", "").strip()
            estimated_price = float(est_str)
        except Exception as e:
            logger.warning("Failed to parse 'Estimated Price (Contact)'='%s': %s", est_raw, e)

    # 2) Fallback: parse from breakdown text if still zero
    if estimated_price <= 0 and price_breakdown:
        for line in price_breakdown.splitlines():
            if "Total" in line:
                try:
                    part = line.split(":", 1)[-1].strip().replace("$", "")
                    estimated_price = float(part)
                    break
                except Exception:
                    pass

    service_type = SERVICE_TYPE_STANDARD
    if "Deep" in price_breakdown:
        service_type = SERVICE_TYPE_DEEP

    # Home access fields – try multiple possible label variants, fall back to ""
    access_method = (
        payload.get("How Will Your Cleaner Get Into Your Home")
        or payload.get("How will your cleaner get into your home")
        or payload.get("How Will Your Cleaner Get Into Your Home?")
        or payload.get("How will your cleaner get into your home?")
        or ""
    )

    access_notes = (
        payload.get("Access Notes For Your Cleaner")
        or payload.get("Access notes for your cleaner")
        or payload.get("Access notes for your cleaner?")
        or ""
    )

    job_summary = {
        "job_id": calendar.get("appointmentId"),
        "customer_name": full_name or "Unknown",
        "contact_id": contact_id,
        "service_type": service_type,
        "estimated_price": estimated_price,
        "start_time": calendar.get("startTime"),
        "end_time": calendar.get("endTime"),
        "access_method": access_method,
        "access_notes": access_notes,
    }
    logger.info("Job summary: %s", job_summary)
    return job_summary


def find_job_record_id(external_job_id: str) -> Optional[str]:
    """
    Lookup the Jobs custom object record id using external_job_id.

    Args:
        external_job_id: The appointment ID (used as external_job_id in GHL)

    Returns:
        GHL Jobs custom object record ID if found, None otherwise

    Uses POST /objects/custom_objects.jobs/records/search to find the record.
    """
    if not external_job_id:
        return None
    if not GHL_LOCATION_ID:
        logger.error("find_job_record_id: GHL_LOCATION_ID not set")
        return None

    body = {
        "locationId": GHL_LOCATION_ID,
        "page": 1,
        "pageLimit": 1,
        "filters": [
            {
                "group": "AND",
                "filters": [
                    {
                        "group": "AND",
                        "filters": [
                            {
                                "field": "properties.external_job_id",
                                "operator": "eq",
                                "value": external_job_id,
                            }
                        ],
                    }
                ],
            }
        ],
    }

    try:
        logger.info("Searching job record id for external_job_id=%s", external_job_id)
        resp = requests.post(
            JOBS_SEARCH_URL, headers=_ghl_headers(), json=body, timeout=10
        )
    except Exception as e:
        logger.error("find_job_record_id: exception: %s", e)
        return None

    if not resp.ok:
        logger.error(
            "find_job_record_id: search failed (%s): %s",
            resp.status_code,
            resp.text,
        )
        return None

    data = resp.json()
    records = data.get("records") or data.get("customObjectRecords") or []
    if not records:
        logger.error(
            "find_job_record_id: no records found for external_job_id=%s",
            external_job_id,
        )
        return None

    record_id = records[0].get("id")
    logger.info(
        "find_job_record_id: found record_id=%s for external_job_id=%s",
        record_id,
        external_job_id,
    )
    return record_id


def upsert_job_assignment_to_ghl(job_id: str, contractor_id: str, contractor_name: str) -> None:
    """
    Update assignment details into the Jobs custom object in GHL.

    Args:
        job_id: External job ID (appointment ID)
        contractor_id: GHL contact ID of the assigned contractor
        contractor_name: Name of the assigned contractor

    Process:
        1. Find record id via /objects/custom_objects.jobs/records/search using external_job_id
        2. PUT /objects/custom_objects.jobs/records/{id}?locationId=...
           with properties:
             - contractor_assigned_id
             - contractor_assigned_name
             - job_status (set to "contractor_assigned")
             - how_will_your_cleaner_get_into_your_home
             - access_notes_for_your_cleaner
    """
    if not job_id or not contractor_id:
        logger.warning(
            "upsert_job_assignment_to_ghl: missing job_id or contractor_id, skipping. "
            "job_id=%s contractor_id=%s",
            job_id,
            contractor_id,
        )
        return
    if not GHL_LOCATION_ID:
        logger.error("upsert_job_assignment_to_ghl: GHL_LOCATION_ID not set")
        return

    record_id = find_job_record_id(job_id)
    if not record_id:
        logger.error(
            "upsert_job_assignment_to_ghl: could not find job record for external_job_id=%s",
            job_id,
        )
        return

    # Pull the in-memory job to get access info (if available)
    job = JOB_STORE.get(job_id, {})

    payload = {
        "properties": {
            "external_job_id": job_id,
            "contractor_assigned_id": contractor_id,
            "contractor_assigned_name": contractor_name,
            "job_status": JOB_STATUS_ASSIGNED,
            # These keys must match the Unique Key of your Job custom fields in GHL
            "how_will_your_cleaner_get_into_your_home": job.get("access_method", ""),
            "access_notes_for_your_cleaner": job.get("access_notes", ""),
        }
    }
    params = {"locationId": GHL_LOCATION_ID}

    logger.info(
        "Updating Jobs object on assignment via %s/%s with params %s and payload: %s",
        JOBS_RECORDS_URL,
        record_id,
        params,
        payload,
    )

    try:
        resp = requests.put(
            f"{JOBS_RECORDS_URL}/{record_id}",
            headers=_ghl_headers(),
            params=params,
            json=payload,
            timeout=10,
        )
    except Exception as e:
        logger.error("Jobs object assignment upsert exception: %s", e)
        return

    if resp.ok:
        logger.info("Jobs object assignment upsert OK: %s", resp.text)
    else:
        logger.error(
            "Jobs object assignment upsert failed (%s): %s",
            resp.status_code,
            resp.text,
        )


# ---------------------------------------------------------
# API Routes
# ---------------------------------------------------------


@app.get("/")
def root():
    """
    Health check endpoint.

    Returns:
        Simple JSON response indicating the service is running.
    """
    return {"ok": True, "service": "alloy-dispatcher"}


@app.get("/contractors")
def get_contractors():
    """
    Get list of eligible contractors.

    Returns:
        JSON with count and list of contractors (filtered by tags:
        contractor_cleaning + job-pending-assignment)
    """
    contractors = fetch_contractors()
    return {"ok": True, "count": len(contractors), "contractors": contractors}


@app.get("/debug/jobs")
def debug_jobs():
    """
    Debug endpoint to see what jobs are currently cached in memory.

    Returns:
        JSON with count, job_ids list, and full jobs dict.
        Useful for troubleshooting during development.
    """
    return {
        "ok": True,
        "count": len(JOB_STORE),
        "job_ids": list(JOB_STORE.keys()),
        "jobs": JOB_STORE,
    }


@app.post("/leads/cleaning")
async def submit_cleaning_lead(payload: CleaningLeadPayload):
    """
    Submit a cleaning lead from the frontend website.

    Args (request body):
        - name: Customer full name
        - email: Customer email
        - phone: Customer phone number
        - address: Optional street address
        - city: Optional city (defaults to "Bend" if not provided)
        - zip: Optional ZIP code
        - home_size: Optional home size description
        - bedrooms: Optional number of bedrooms
        - bathrooms: Optional number of bathrooms
        - preferred_frequency: Optional cleaning frequency preference
        - notes: Optional additional notes

    Returns:
        JSON with ok=True and contact_id if successful.

    Side effects:
        - Creates or updates a contact in GHL with the provided information
        - Sets custom fields for cleaning-specific data (home size, frequency, etc.)
    """
    logger.info("Received cleaning lead submission: %s", payload.dict())

    # Build custom fields dict for GHL
    custom_fields = {}
    if payload.address:
        custom_fields["address"] = payload.address
    if payload.city:
        custom_fields["city"] = payload.city
    else:
        custom_fields["city"] = "Bend"  # Default to Bend
    if payload.zip:
        custom_fields["zip"] = payload.zip
    if payload.home_size:
        custom_fields["home_size"] = payload.home_size
    if payload.bedrooms is not None:
        custom_fields["bedrooms"] = str(payload.bedrooms)
    if payload.bathrooms is not None:
        custom_fields["bathrooms"] = str(payload.bathrooms)
    if payload.preferred_frequency:
        custom_fields["preferred_frequency"] = payload.preferred_frequency
    if payload.notes:
        custom_fields["notes"] = payload.notes

    # Add tag to indicate this is a cleaning lead
    custom_fields["tags"] = ["cleaning_lead", "website_lead"]

    contact_id = create_or_update_contact_in_ghl(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        custom_fields=custom_fields,
    )

    if not contact_id:
        raise HTTPException(
            status_code=500,
            detail="Failed to create contact in GHL. Please try again or contact support.",
        )

    return JSONResponse(
        {
            "ok": True,
            "contact_id": contact_id,
            "message": "Lead submitted successfully. We'll contact you shortly.",
        }
    )


@app.post("/leads/pros")
async def submit_pros_application(payload: ProsApplicationPayload):
    """
    Submit a pros (contractor) application from the frontend.

    Args (request body):
        - name: Applicant full name
        - phone: Applicant phone number
        - email: Applicant email
        - experience: Optional experience description
        - notes: Optional additional notes

    Returns:
        JSON with ok=True and contact_id if successful.

    Side effects:
        - Creates or updates a contact in GHL with pros application information
        - Tags the contact for pros recruitment review
    """
    logger.info("Received pros application: %s", payload.dict())

    custom_fields = {}
    if payload.experience:
        custom_fields["experience"] = payload.experience
    if payload.notes:
        custom_fields["notes"] = payload.notes

    # Add tag to indicate this is a pros application
    custom_fields["tags"] = ["pros_application", "website_lead"]

    contact_id = create_or_update_contact_in_ghl(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        custom_fields=custom_fields,
    )

    if not contact_id:
        raise HTTPException(
            status_code=500,
            detail="Failed to submit application. Please try again or contact support.",
        )

    return JSONResponse(
        {
            "ok": True,
            "contact_id": contact_id,
            "message": "Application submitted successfully. We'll review and contact you soon.",
        }
    )


@app.post("/dispatch")
async def dispatch(request: Request):
    """
    Webhook endpoint called by GHL when a customer books a cleaning appointment.

    Args (request body):
        GHL webhook payload containing appointment/calendar data and contact information.

    Returns:
        JSON with ok=True, job summary, and list of notified contractor IDs.

    Side effects:
        1. Builds a job summary from the appointment payload
        2. Caches the job in JOB_STORE (keyed by job_id / appointmentId)
        3. Fetches eligible contractors (tagged with contractor_cleaning + job-pending-assignment)
        4. Sends SMS to each contractor with job details and "Reply YES <job_id> to accept"

    Note:
        The SMS sent to contractors does NOT include home access information yet.
        Access info is only shared after a contractor accepts the job.
    """
    payload = await request.json()
    logger.info("Received payload from GHL: %s", payload)

    job_summary = build_job_summary(payload)

    # Enrich with dispatch metadata
    job_summary.setdefault("notified_contractors", [])
    job_summary["assigned_contractor_id"] = None
    job_summary["assigned_contractor_name"] = None
    job_summary["dispatched_at"] = datetime.utcnow().isoformat()

    # Cache the job in memory so /contractor-reply can find it
    job_id = job_summary.get("job_id")
    if job_id:
        JOB_STORE[job_id] = job_summary
        logger.info(
            "Cached job in memory with id=%s. JOB_STORE now has %d jobs.",
            job_id,
            len(JOB_STORE),
        )
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

    # Build contractor SMS message (NO access info yet – only broadcast)
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
        cid = c.get("id")
        phone = c.get("phone")
        if not cid or not phone:
            logger.info(
                "Skipping contractor without valid id/phone: id=%s phone=%s",
                cid,
                phone,
            )
            continue
        send_conversation_sms(cid, msg)
        notified_ids.append(cid)
        job_summary["notified_contractors"].append(cid)

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
    Webhook endpoint called by GHL when a contractor replies to a dispatch SMS.

    Args (request body):
        GHL webhook payload containing:
        - contact_id: GHL contact ID of the contractor
        - message: The SMS reply text
        - customData: Optional metadata (may include job_id)

    Returns:
        JSON with ok=True, job_id, contractor_id, and contractor_name if successful.

    Supported reply formats:
        - "YES <job_id>" (explicit job ID)
        - "Yes" / "Y" / "Yeah" / "Yep" (infers latest job sent to that contractor)

    Side effects:
        1. Assigns the job to the accepting contractor
        2. Sends confirmation SMS to the contractor (NOW includes home access info)
        3. Notifies all other contractors that the job was claimed
        4. Notifies the customer their job has been assigned
        5. Updates the GHL Jobs custom object with assignment details
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
    raw_message = custom.get("body") or message_obj.get("body") or payload.get(
        "message"
    )

    # Normalize raw_message -> string
    if isinstance(raw_message, dict):
        raw_message = raw_message.get("body") or ""
    if raw_message is None:
        raw_message = ""

    message_text = str(raw_message)
    logger.info(
        "Parsed contractor reply: contact_id=%s, message_text=%s",
        contact_id,
        message_text,
    )

    text_stripped = message_text.strip()
    text_upper = text_stripped.upper()
    parts = text_stripped.split()

    # Start with job_id from customData if present and non-empty
    job_id = custom.get("job_id")
    if isinstance(job_id, str):
        job_id = job_id.strip() or None

    # If not provided, try to parse "YES <job_id>" pattern
    if not job_id and len(parts) >= 2 and parts[0].upper() == "YES":
        job_id = parts[1].strip() or None

    job = None

    # If we have an explicit job_id, try to get it from JOB_STORE
    if job_id:
        job = JOB_STORE.get(job_id)

    # If no job yet, but it's a YES/Y reply, fall back to latest job
    if not job:
        if text_upper not in ("YES", "Y", "YEA", "YEAH", "YEP"):
            logger.error(
                "contractor-reply: invalid reply format: %s", message_text
            )
            return JSONResponse(
                {
                    "ok": False,
                    "reason": "invalid_format",
                    "message_text": message_text,
                },
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
                {
                    "ok": False,
                    "reason": "job_not_found_for_contractor",
                    "contact_id": contact_id,
                },
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

    # Mark assignment in memory
    job["assigned_contractor_id"] = contact_id
    job["assigned_contractor_name"] = contractor_name

    # 1) Confirm to the accepting contractor — NOW including access info
    access_method = job.get("access_method") or "Not specified"
    access_notes = job.get("access_notes") or ""

    confirm_msg = (
        f"You accepted this job:\n"
        f"Customer: {job['customer_name']}\n"
        f"When: {job['start_time']}\n"
        f"Est. price: ${job['estimated_price']:.2f}\n"
        f"Entry: {access_method}\n"
    )

    if access_notes:
        confirm_msg += f"Notes: {access_notes}\n"

    confirm_msg += "\nWe'll share final details in your Alloy dashboard."

    if contact_id:
        send_conversation_sms(contact_id, confirm_msg)

    # 2) Notify all other contractors that the job was claimed
    for c in contractors:
        cid = c.get("id")
        phone = c.get("phone")
        if not cid or not phone or cid == contact_id:
            if not cid or not phone:
                logger.info(
                    "Skipping contractor without valid id/phone: id=%s phone=%s",
                    cid,
                    phone,
                )
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

    # 4) Push assignment into Jobs object (custom_objects.jobs)
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

