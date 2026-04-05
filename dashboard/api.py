"""
REST API endpoints for the dashboard.
Provides stats, lead management, and pipeline control.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from database.connection import get_session
from database.models import (
    Lead, LeadStatus, Website, Deployment,
    OutreachMessage, PipelineRun, DomainSuggestion,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class StatsResponse(BaseModel):
    total_leads: int
    by_status: dict[str, int]
    websites_built: int
    deployments_active: int
    emails_sent: int
    response_rate: float
    conversion_rate: float


class LeadResponse(BaseModel):
    id: int
    business_name: str
    business_type: Optional[str]
    city: Optional[str]
    status: str
    email: Optional[str]
    phone: Optional[str]
    rating: Optional[float]
    preview_url: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PipelineRunResponse(BaseModel):
    id: int
    agent_name: str
    status: str
    leads_processed: int
    leads_succeeded: int
    leads_failed: int
    started_at: str
    finished_at: Optional[str]


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    session = get_session()
    try:
        total = session.query(Lead).count()

        by_status = {}
        for status in LeadStatus:
            count = session.query(Lead).filter(Lead.status == status).count()
            if count > 0:
                by_status[status.value] = count

        websites = session.query(Website).count()
        deployments = (
            session.query(Deployment).filter(Deployment.status == "deployed").count()
        )
        emails_sent = (
            session.query(OutreachMessage)
            .filter(OutreachMessage.status == "sent")
            .count()
        )
        responded = session.query(Lead).filter(
            Lead.status.in_([
                LeadStatus.RESPONDED, LeadStatus.INTERESTED, LeadStatus.CONVERTED
            ])
        ).count()
        converted = session.query(Lead).filter(
            Lead.status == LeadStatus.CONVERTED
        ).count()

        response_rate = (responded / emails_sent * 100) if emails_sent > 0 else 0
        conversion_rate = (converted / total * 100) if total > 0 else 0

        return StatsResponse(
            total_leads=total,
            by_status=by_status,
            websites_built=websites,
            deployments_active=deployments,
            emails_sent=emails_sent,
            response_rate=round(response_rate, 1),
            conversion_rate=round(conversion_rate, 1),
        )
    finally:
        session.close()


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(
    status: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    session = get_session()
    try:
        q = session.query(Lead)
        if status:
            q = q.filter(Lead.status == LeadStatus(status))
        if city:
            q = q.filter(Lead.city.ilike(f"%{city}%"))

        leads = q.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()

        result = []
        for lead in leads:
            preview = None
            dep = (
                session.query(Deployment)
                .filter(Deployment.lead_id == lead.id)
                .first()
            )
            if dep:
                preview = dep.live_url

            result.append(LeadResponse(
                id=lead.id,
                business_name=lead.business_name,
                business_type=lead.business_type,
                city=lead.city,
                status=lead.status.value,
                email=lead.email,
                phone=lead.phone,
                rating=lead.rating,
                preview_url=preview,
                created_at=lead.created_at.isoformat(),
            ))
        return result
    finally:
        session.close()


@router.get("/leads/{lead_id}")
def get_lead_detail(lead_id: int):
    session = get_session()
    try:
        lead = session.query(Lead).get(lead_id)
        if not lead:
            return {"error": "Lead not found"}

        websites = session.query(Website).filter(Website.lead_id == lead_id).all()
        deployments = session.query(Deployment).filter(Deployment.lead_id == lead_id).all()
        messages = session.query(OutreachMessage).filter(OutreachMessage.lead_id == lead_id).all()
        domains = session.query(DomainSuggestion).filter(DomainSuggestion.lead_id == lead_id).all()

        return {
            "lead": {
                "id": lead.id,
                "business_name": lead.business_name,
                "business_type": lead.business_type,
                "address": lead.address,
                "city": lead.city,
                "status": lead.status.value,
                "email": lead.email,
                "phone": lead.phone,
                "rating": lead.rating,
                "review_count": lead.review_count,
            },
            "websites": [{"id": w.id, "version": w.version, "preview_url": w.preview_url} for w in websites],
            "deployments": [{"id": d.id, "live_url": d.live_url, "status": d.status} for d in deployments],
            "messages": [
                {"id": m.id, "subject": m.subject, "status": m.status, "sent_at": str(m.sent_at)}
                for m in messages
            ],
            "domains": [
                {"domain": f"{d.domain_name}{d.tld}", "available": d.is_available, "recommended": d.is_recommended}
                for d in domains
            ],
        }
    finally:
        session.close()


@router.get("/pipeline/runs", response_model=list[PipelineRunResponse])
def list_pipeline_runs(limit: int = Query(default=20, le=100)):
    session = get_session()
    try:
        runs = (
            session.query(PipelineRun)
            .order_by(PipelineRun.started_at.desc())
            .limit(limit)
            .all()
        )
        return [
            PipelineRunResponse(
                id=r.id,
                agent_name=r.agent_name,
                status=r.status,
                leads_processed=r.leads_processed,
                leads_succeeded=r.leads_succeeded,
                leads_failed=r.leads_failed,
                started_at=r.started_at.isoformat(),
                finished_at=r.finished_at.isoformat() if r.finished_at else None,
            )
            for r in runs
        ]
    finally:
        session.close()


@router.post("/leads/{lead_id}/status")
def update_lead_status(lead_id: int, new_status: str):
    session = get_session()
    try:
        lead = session.query(Lead).get(lead_id)
        if not lead:
            return {"error": "Lead not found"}

        try:
            target = LeadStatus(new_status)
        except ValueError:
            return {"error": f"Invalid status: {new_status}"}

        from orchestrator.state_machine import LeadStateMachine
        if not LeadStateMachine.can_transition(lead.status, target):
            allowed = [s.value for s in LeadStateMachine.get_allowed_transitions(lead.status)]
            return {"error": f"Cannot transition to {new_status}. Allowed: {allowed}"}

        lead.status = target
        lead.updated_at = datetime.now(timezone.utc)
        session.commit()
        return {"success": True, "new_status": lead.status.value}
    finally:
        session.close()


@router.post("/preview/{lead_id}/view")
def track_preview_view(lead_id: int):
    """Track when someone views a preview (fired from the preview page)."""
    session = get_session()
    try:
        messages = (
            session.query(OutreachMessage)
            .filter(
                OutreachMessage.lead_id == lead_id,
                OutreachMessage.opened_at.is_(None),
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        for msg in messages:
            msg.opened_at = now
        if messages:
            session.commit()
        return {"tracked": len(messages)}
    finally:
        session.close()
