"""
Outreach Agent: Sends personalized cold emails to verified leads
with deployed website previews and domain suggestions.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from agents.outreach.email_sender import EmailSender
from agents.outreach.email_templates import initial_outreach, follow_up_1, follow_up_2
from config.settings import settings
from database.models import Lead, Deployment, DomainSuggestion, OutreachMessage

logger = logging.getLogger(__name__)


class OutreachAgent(BaseAgent):
    def __init__(self):
        super().__init__("outreach")
        self.sender = EmailSender()

    async def execute(
        self, lead: Lead = None, session: Session = None, **kwargs
    ) -> OutreachMessage:
        if not lead:
            raise ValueError("Lead is required for outreach")
        if not lead.email:
            raise ValueError(f"Lead {lead.id} has no email for outreach")

        deployment = self._get_deployment(session, lead.id)
        if not deployment or not deployment.live_url:
            raise ValueError(f"No deployment found for lead {lead.id}")

        domains = self._get_domains(session, lead.id)

        subject, body = initial_outreach(
            lead=lead,
            preview_url=deployment.live_url,
            domain_suggestions=domains,
            sender_name=settings.email.from_name,
        )

        result = await self.sender.send(
            to_email=lead.email,
            subject=subject,
            html_body=body,
        )

        message = OutreachMessage(
            lead_id=lead.id,
            channel="email",
            subject=subject,
            body=body,
            recipient_email=lead.email,
            message_id=result.message_id,
            status="sent" if result.success else "failed",
            sent_at=datetime.now(timezone.utc) if result.success else None,
        )

        if session:
            session.add(message)
            session.commit()

        if result.success:
            self.logger.info(f"Outreach sent to {lead.email} for {lead.business_name}")
        else:
            self.logger.error(
                f"Outreach failed for {lead.business_name}: {result.error}"
            )

        return message

    async def send_follow_up(
        self,
        lead: Lead,
        session: Session,
        follow_up_number: int,
    ) -> OutreachMessage:
        deployment = self._get_deployment(session, lead.id)
        if not deployment:
            raise ValueError(f"No deployment for lead {lead.id}")

        template_fn = follow_up_1 if follow_up_number == 1 else follow_up_2
        subject, body = template_fn(
            lead=lead,
            preview_url=deployment.live_url,
            sender_name=settings.email.from_name,
        )

        result = await self.sender.send(
            to_email=lead.email,
            subject=subject,
            html_body=body,
        )

        message = OutreachMessage(
            lead_id=lead.id,
            channel="email",
            subject=subject,
            body=body,
            recipient_email=lead.email,
            message_id=result.message_id,
            status="sent" if result.success else "failed",
            is_follow_up=True,
            follow_up_number=follow_up_number,
            sent_at=datetime.now(timezone.utc) if result.success else None,
        )

        if session:
            session.add(message)
            session.commit()

        return message

    def _get_deployment(self, session: Session, lead_id: int) -> Deployment:
        if not session:
            return None
        return (
            session.query(Deployment)
            .filter(Deployment.lead_id == lead_id)
            .order_by(Deployment.created_at.desc())
            .first()
        )

    def _get_domains(
        self, session: Session, lead_id: int
    ) -> list[DomainSuggestion]:
        if not session:
            return []
        return (
            session.query(DomainSuggestion)
            .filter(DomainSuggestion.lead_id == lead_id)
            .order_by(DomainSuggestion.is_recommended.desc())
            .all()
        )

    async def close(self):
        await self.sender.close()
