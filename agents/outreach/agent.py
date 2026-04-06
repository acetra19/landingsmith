"""
Outreach Agent: Sends personalized cold outreach to verified leads
with deployed website previews and domain suggestions.
Uses email if available, otherwise SMS via Twilio.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from agents.outreach.email_sender import EmailSender
from agents.outreach.email_templates import (
    initial_outreach, follow_up_1, follow_up_2, voice_followup,
)
from agents.outreach.sms_sender import SMSSender
from agents.outreach.sms_templates import initial_sms, follow_up_sms, voice_followup_sms
from agents.outreach.voice_caller import VoiceCaller
from config.settings import settings
from database.models import Lead, Deployment, DomainSuggestion, OutreachMessage

logger = logging.getLogger(__name__)


NOTIFICATION_EMAIL = "james@amplivo.net"


class OutreachAgent(BaseAgent):
    def __init__(self):
        super().__init__("outreach")
        self.email_sender = EmailSender()
        self._sms_sender = None
        self._voice_caller = None

    @property
    def sms_sender(self) -> SMSSender:
        if self._sms_sender is None:
            self._sms_sender = SMSSender()
        return self._sms_sender

    @property
    def voice_caller(self) -> VoiceCaller:
        if self._voice_caller is None:
            self._voice_caller = VoiceCaller()
        return self._voice_caller

    async def execute(
        self, lead: Lead = None, session: Session = None, **kwargs
    ) -> OutreachMessage:
        if not lead:
            raise ValueError("Lead is required for outreach")

        deployment = self._get_deployment(session, lead.id)
        if not deployment or not deployment.live_url:
            raise ValueError(f"No deployment found for lead {lead.id}")

        if lead.email:
            return await self._send_email(lead, deployment, session)
        elif lead.phone and self.voice_caller.is_configured:
            return await self._initiate_voice_call(lead, deployment, session)
        elif lead.phone:
            self.logger.info(
                f"Lead {lead.id} ({lead.business_name}): has phone but "
                f"Retell not configured, skipping"
            )
            return OutreachMessage(
                lead_id=lead.id,
                channel="voice",
                subject=f"Voice nicht konfiguriert fuer {lead.phone}",
                body="Retell not configured – cannot initiate voice call",
                recipient_email=lead.phone,
                status="skipped",
            )
        else:
            self.logger.info(
                f"Lead {lead.id} ({lead.business_name}): no email or phone"
            )
            return OutreachMessage(
                lead_id=lead.id,
                channel="none",
                subject="Kein Kontaktkanal verfuegbar",
                body="No email or phone available for outreach",
                recipient_email="",
                status="skipped",
            )

    async def _send_email(
        self, lead: Lead, deployment: Deployment, session: Session
    ) -> OutreachMessage:
        domains = self._get_domains(session, lead.id)

        subject, body = initial_outreach(
            lead=lead,
            preview_url=deployment.live_url,
            domain_suggestions=domains,
            sender_name=settings.email.from_name,
        )

        result = await self.email_sender.send(
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
            self.logger.info(
                f"Email sent to {lead.email} for {lead.business_name}"
            )
            await self._send_notification(lead, "email", deployment)
        else:
            self.logger.error(
                f"Email failed for {lead.business_name}: {result.error}"
            )

        return message

    async def _initiate_voice_call(
        self, lead: Lead, deployment: Deployment, session: Session
    ) -> OutreachMessage:
        """Initiate a Retell voice call for leads with phone but no email."""
        result = await self.voice_caller.call(lead.phone)

        if result.success:
            status = "voice_initiated"
        else:
            is_landline = "landline" in (result.error or "").lower()
            status = "skipped" if is_landline else "failed"

        message = OutreachMessage(
            lead_id=lead.id,
            channel="voice",
            subject=f"Voice call an {lead.phone}",
            body=f"Retell call initiated (call_id: {result.call_id})" if result.success
                 else f"Voice call failed: {result.error}",
            recipient_email=lead.phone,
            message_id=result.call_id,
            status=status,
            sent_at=datetime.now(timezone.utc) if result.success else None,
        )

        if session:
            session.add(message)
            session.commit()

        if result.success:
            self.logger.info(
                f"Voice call initiated to {lead.phone} for {lead.business_name}"
            )
            await self._send_notification(lead, "voice", deployment)
        else:
            self.logger.error(
                f"Voice call failed for {lead.business_name}: {result.error}"
            )

        return message

    async def _send_sms(
        self, lead: Lead, deployment: Deployment, session: Session
    ) -> OutreachMessage:
        body = initial_sms(
            lead=lead,
            preview_url=deployment.live_url,
            sender_name=settings.email.from_name,
        )

        result = await self.sms_sender.send(
            to_number=lead.phone,
            body=body,
        )

        is_landline = not result.success and "Landline" in (result.error or "")
        if is_landline:
            status = "skipped"
        elif result.success:
            status = "sent"
        else:
            status = "failed"

        message = OutreachMessage(
            lead_id=lead.id,
            channel="sms",
            subject=f"SMS an {lead.phone}",
            body=body,
            recipient_email=lead.phone,
            message_id=result.message_sid,
            status=status,
            sent_at=datetime.now(timezone.utc) if result.success else None,
        )

        if session:
            session.add(message)
            session.commit()

        if result.success:
            self.logger.info(
                f"SMS sent to {lead.phone} for {lead.business_name}"
            )
            await self._send_notification(lead, "sms", deployment)
        elif is_landline:
            self.logger.info(
                f"Skipped {lead.business_name}: landline {lead.phone}"
            )
        else:
            self.logger.error(
                f"SMS failed for {lead.business_name}: {result.error}"
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

        prev_message = (
            session.query(OutreachMessage)
            .filter(OutreachMessage.lead_id == lead.id)
            .order_by(OutreachMessage.created_at.desc())
            .first()
        )
        channel = prev_message.channel if prev_message else "email"

        if channel == "sms" and settings.twilio.account_sid:
            return await self._send_follow_up_sms(
                lead, deployment, session, follow_up_number
            )
        else:
            return await self._send_follow_up_email(
                lead, deployment, session, follow_up_number
            )

    async def _send_follow_up_email(
        self, lead, deployment, session, follow_up_number
    ) -> OutreachMessage:
        template_fn = follow_up_1 if follow_up_number == 1 else follow_up_2
        subject, body = template_fn(
            lead=lead,
            preview_url=deployment.live_url,
            sender_name=settings.email.from_name,
        )

        result = await self.email_sender.send(
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

    async def _send_follow_up_sms(
        self, lead, deployment, session, follow_up_number
    ) -> OutreachMessage:
        body = follow_up_sms(
            lead=lead,
            preview_url=deployment.live_url,
            sender_name=settings.email.from_name,
        )

        result = await self.sms_sender.send(
            to_number=lead.phone,
            body=body,
        )

        message = OutreachMessage(
            lead_id=lead.id,
            channel="sms",
            subject=f"Follow-up SMS #{follow_up_number}",
            body=body,
            recipient_email=lead.phone,
            message_id=result.message_sid,
            status="sent" if result.success else "failed",
            is_follow_up=True,
            follow_up_number=follow_up_number,
            sent_at=datetime.now(timezone.utc) if result.success else None,
        )

        if session:
            session.add(message)
            session.commit()
        return message

    async def send_voice_followup(
        self,
        lead: Lead,
        session: Session,
        contact_email: str = "",
        contact_name: str = "",
        send_via: str = "email",
    ) -> OutreachMessage | None:
        """Send preview link after a voice call where the lead was interested."""
        deployment = self._get_deployment(session, lead.id)
        if not deployment or not deployment.live_url:
            self.logger.error(f"No deployment for lead {lead.id}, can't send followup")
            return None

        if send_via == "email" and contact_email:
            return await self._send_voice_email(
                lead, deployment, session, contact_email, contact_name,
            )
        elif send_via == "sms" and lead.phone:
            return await self._send_voice_sms(lead, deployment, session)
        elif contact_email:
            return await self._send_voice_email(
                lead, deployment, session, contact_email, contact_name,
            )
        else:
            self.logger.warning(
                f"Voice followup for lead {lead.id}: no email or phone available"
            )
            return None

    async def _send_voice_email(
        self,
        lead: Lead,
        deployment: Deployment,
        session: Session,
        contact_email: str,
        contact_name: str,
    ) -> OutreachMessage:
        domains = self._get_domains(session, lead.id)

        subject, body = voice_followup(
            lead=lead,
            preview_url=deployment.live_url,
            domain_suggestions=domains,
            contact_name=contact_name,
            sender_name=settings.email.from_name,
        )

        result = await self.email_sender.send(
            to_email=contact_email,
            subject=subject,
            html_body=body,
        )

        message = OutreachMessage(
            lead_id=lead.id,
            channel="email",
            subject=subject,
            body=body,
            recipient_email=contact_email,
            message_id=result.message_id,
            status="sent" if result.success else "failed",
            sent_at=datetime.now(timezone.utc) if result.success else None,
        )

        if session:
            session.add(message)
            session.commit()

        if result.success:
            self.logger.info(
                f"Voice followup email sent to {contact_email} for {lead.business_name}"
            )
            await self._send_notification(lead, "voice+email", deployment)
        else:
            self.logger.error(
                f"Voice followup email failed for {lead.business_name}: {result.error}"
            )

        return message

    async def _send_voice_sms(
        self, lead: Lead, deployment: Deployment, session: Session,
    ) -> OutreachMessage:
        body = voice_followup_sms(
            lead=lead,
            preview_url=deployment.live_url,
        )

        result = await self.sms_sender.send(
            to_number=lead.phone,
            body=body,
        )

        message = OutreachMessage(
            lead_id=lead.id,
            channel="sms",
            subject=f"Voice followup SMS an {lead.phone}",
            body=body,
            recipient_email=lead.phone,
            message_id=result.message_sid,
            status="sent" if result.success else "failed",
            sent_at=datetime.now(timezone.utc) if result.success else None,
        )

        if session:
            session.add(message)
            session.commit()

        if result.success:
            self.logger.info(
                f"Voice followup SMS sent to {lead.phone} for {lead.business_name}"
            )
            await self._send_notification(lead, "voice+sms", deployment)
        else:
            self.logger.error(
                f"Voice followup SMS failed for {lead.business_name}: {result.error}"
            )

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
            .filter(
                DomainSuggestion.lead_id == lead_id,
                DomainSuggestion.is_available == True,
            )
            .order_by(DomainSuggestion.is_recommended.desc())
            .all()
        )

    async def _send_notification(
        self, lead: Lead, channel: str, deployment: Deployment
    ):
        """Send confirmation email to admin after successful outreach."""
        try:
            contact = lead.email if channel == "email" else lead.phone
            subject = f"Outreach gesendet: {lead.business_name}"
            body = f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
              <h2 style="color:#2563eb">Outreach Bestaetigung</h2>
              <table style="width:100%;border-collapse:collapse">
                <tr><td style="padding:8px;font-weight:bold">Unternehmen</td>
                    <td style="padding:8px">{lead.business_name}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Kanal</td>
                    <td style="padding:8px">{channel.upper()}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Kontakt</td>
                    <td style="padding:8px">{contact}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Adresse</td>
                    <td style="padding:8px">{lead.address or '-'}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Preview</td>
                    <td style="padding:8px">
                      <a href="{deployment.live_url}">{deployment.live_url}</a>
                    </td></tr>
              </table>
            </div>
            """
            await self.email_sender.send(
                to_email=NOTIFICATION_EMAIL,
                subject=subject,
                html_body=body,
            )
        except Exception as e:
            self.logger.warning(f"Notification email failed: {e}")

    async def close(self):
        await self.email_sender.close()
        if self._voice_caller:
            await self._voice_caller.close()
