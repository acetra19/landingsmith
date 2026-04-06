"""
Webhook endpoint for Retell Voice Agent.
Receives call_analyzed events and triggers follow-up actions
(preview email/SMS) based on extracted interest level.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from agents.outreach.agent import OutreachAgent
from database.connection import get_session
from database.models import Lead, LeadStatus, OutreachMessage, RejectionReason
from orchestrator.state_machine import LeadStateMachine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

_outreach_agent: OutreachAgent | None = None


def _get_outreach_agent() -> OutreachAgent:
    global _outreach_agent
    if _outreach_agent is None:
        _outreach_agent = OutreachAgent()
    return _outreach_agent


def _normalize_phone(phone: str) -> str:
    """Normalize to E.164 for comparison."""
    cleaned = phone.replace(" ", "").replace("-", "").replace("/", "").replace("(", "").replace(")", "")
    if cleaned.startswith("0049"):
        cleaned = "+49" + cleaned[4:]
    elif cleaned.startswith("0") and not cleaned.startswith("+"):
        cleaned = "+49" + cleaned[1:]
    elif not cleaned.startswith("+"):
        cleaned = "+49" + cleaned
    return cleaned


def _find_lead_by_phone(session: Session, phone_e164: str) -> Lead | None:
    """Match a Retell to_number to a Lead. Tries exact match first,
    then normalizes all candidate leads for fuzzy matching."""
    lead = session.query(Lead).filter(Lead.phone == phone_e164).first()
    if lead:
        return lead

    candidates = (
        session.query(Lead)
        .filter(
            Lead.phone.isnot(None),
            Lead.status.in_([
                LeadStatus.DEPLOYED,
                LeadStatus.OUTREACH_SENT,
            ]),
        )
        .all()
    )
    for candidate in candidates:
        if _normalize_phone(candidate.phone) == phone_e164:
            return candidate

    return None


def _extract_analysis(payload: dict) -> dict:
    """Pull custom_analysis_data from Retell's call_analyzed payload."""
    call = payload.get("call", {})
    analysis = call.get("call_analysis", {})
    custom = analysis.get("custom_analysis_data", {})
    return {
        "call_id": call.get("call_id", ""),
        "to_number": call.get("to_number", ""),
        "from_number": call.get("from_number", ""),
        "duration_ms": call.get("end_timestamp", 0) - call.get("start_timestamp", 0),
        "transcript": call.get("transcript", ""),
        "interest_level": custom.get("interest_level", ""),
        "contact_email": custom.get("contact_email", ""),
        "contact_phone": custom.get("contact_phone", ""),
        "contact_name": custom.get("contact_name", ""),
        "send_preview_via": custom.get("send_preview_via", "none"),
        "callback_time": custom.get("callback_time", ""),
        "notes": custom.get("notes", ""),
    }


@router.post("/retell")
async def retell_webhook(request: Request):
    """Handle Retell post-call webhook events."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    event = payload.get("event", "")

    if event != "call_analyzed":
        logger.debug(f"Ignoring Retell event: {event}")
        return JSONResponse({"status": "ignored", "event": event})

    data = _extract_analysis(payload)
    logger.info(
        f"Retell call_analyzed: to={data['to_number']} "
        f"interest={data['interest_level']} "
        f"send_via={data['send_preview_via']}"
    )

    if not data["to_number"]:
        logger.warning("No to_number in Retell payload")
        return JSONResponse({"status": "error", "reason": "no_to_number"}, status_code=400)

    session = get_session()
    try:
        lead = _find_lead_by_phone(session, data["to_number"])
        if not lead:
            logger.warning(f"No lead found for phone {data['to_number']}")
            return JSONResponse({"status": "lead_not_found"})

        _record_voice_message(session, lead, data)

        if data["contact_email"] and not lead.email:
            lead.email = data["contact_email"]
            logger.info(f"Updated lead {lead.id} email to {data['contact_email']}")

        interest = data["interest_level"].lower().strip()
        result = await _handle_interest(session, lead, data, interest)

        session.commit()
        logger.info(f"Webhook processed for lead {lead.id}: {result}")
        return JSONResponse({"status": "ok", "lead_id": lead.id, "action": result})

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        session.rollback()
        return JSONResponse({"status": "error", "reason": str(e)}, status_code=500)
    finally:
        session.close()


def _record_voice_message(session: Session, lead: Lead, data: dict) -> None:
    """Store the voice call as an OutreachMessage record."""
    session.add(OutreachMessage(
        lead_id=lead.id,
        channel="voice",
        subject=f"Voice call ({data['interest_level']})",
        body=data.get("transcript", "")[:2000],
        recipient_email=lead.phone,
        message_id=data["call_id"],
        status="sent",
        sent_at=datetime.now(timezone.utc),
    ))
    session.flush()


async def _handle_interest(
    session: Session, lead: Lead, data: dict, interest: str,
) -> str:
    """Route actions based on interest_level extracted by the voice agent."""

    if interest == "interested":
        return await _handle_interested(session, lead, data)

    elif interest == "maybe_later":
        return _handle_maybe_later(session, lead, data)

    elif interest == "not_interested":
        return _handle_not_interested(session, lead)

    else:
        logger.info(f"Lead {lead.id}: no action for interest_level={interest}")
        return f"no_action ({interest})"


async def _handle_interested(
    session: Session, lead: Lead, data: dict,
) -> str:
    """Send preview email/SMS and transition lead to OUTREACH_SENT."""
    agent = _get_outreach_agent()

    send_via = data["send_preview_via"].lower().strip() or "email"
    contact_email = data["contact_email"] or lead.email or ""

    message = await agent.send_voice_followup(
        lead=lead,
        session=session,
        contact_email=contact_email,
        contact_name=data["contact_name"],
        send_via=send_via,
    )

    if lead.status == LeadStatus.DEPLOYED:
        if LeadStateMachine.can_transition(lead.status, LeadStatus.OUTREACH_SENT):
            lead.status = LeadStatus.OUTREACH_SENT
            lead.outreach_at = datetime.now(timezone.utc)

    channel = "email" if message and message.channel == "email" else "sms"
    sent_ok = message and message.status == "sent"
    return f"interested → preview_{channel}_{'sent' if sent_ok else 'failed'}"


def _handle_maybe_later(
    session: Session, lead: Lead, data: dict,
) -> str:
    """Keep lead at DEPLOYED, store callback info for manual follow-up."""
    callback = data.get("callback_time", "")
    notes = data.get("notes", "")
    info_parts = [p for p in [callback, notes] if p]
    if info_parts:
        logger.info(f"Lead {lead.id} maybe_later: {', '.join(info_parts)}")
    return f"maybe_later (callback: {callback or 'none'})"


def _handle_not_interested(session: Session, lead: Lead) -> str:
    """Transition lead to REJECTED."""
    if LeadStateMachine.can_transition(lead.status, LeadStatus.REJECTED):
        lead.status = LeadStatus.REJECTED
        lead.rejection_reason = RejectionReason.MANUAL
        lead.rejection_details = "Not interested (voice call)"
    return "not_interested → rejected"
