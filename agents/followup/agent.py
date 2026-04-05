"""
Follow-Up Agent: Monitors outreach responses, sends follow-ups
at configured intervals, and tracks conversion status.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from agents.outreach.agent import OutreachAgent
from config.settings import settings
from database.connection import get_session
from database.models import Lead, LeadStatus, OutreachMessage
from orchestrator.state_machine import LeadStateMachine

logger = logging.getLogger(__name__)


@dataclass
class FollowUpResult:
    processed: int = 0
    succeeded: int = 0
    failed: int = 0


class FollowUpAgent(BaseAgent):
    def __init__(self):
        super().__init__("followup")
        self.outreach_agent = OutreachAgent()

    async def execute(self, session: Session = None, **kwargs) -> FollowUpResult:
        session = session or get_session()
        result = FollowUpResult()

        try:
            await self._process_follow_ups(session, result, LeadStatus.OUTREACH_SENT, 1)
            await self._process_follow_ups(session, result, LeadStatus.FOLLOW_UP_1, 2)
            await self._check_bounces(session)
            await self._check_unsubscribes(session)
        except Exception as e:
            self.logger.error(f"Follow-up processing failed: {e}")
            raise

        self.logger.info(
            f"Follow-up complete: {result.processed} processed, "
            f"{result.succeeded} sent, {result.failed} failed"
        )
        return result

    async def _process_follow_ups(
        self,
        session: Session,
        result: FollowUpResult,
        current_status: LeadStatus,
        follow_up_number: int,
    ) -> None:
        if follow_up_number > settings.pipeline.max_follow_ups:
            return

        delay = timedelta(days=settings.pipeline.follow_up_delay_days)
        cutoff = datetime.now(timezone.utc) - delay

        leads = (
            session.query(Lead)
            .filter(
                Lead.status == current_status,
                Lead.outreach_at < cutoff,
                Lead.email.isnot(None),
            )
            .all()
        )

        for lead in leads:
            result.processed += 1
            try:
                message = await self.outreach_agent.send_follow_up(
                    lead=lead,
                    session=session,
                    follow_up_number=follow_up_number,
                )
                if message.status == "sent":
                    next_status = (
                        LeadStatus.FOLLOW_UP_1
                        if follow_up_number == 1
                        else LeadStatus.FOLLOW_UP_2
                    )
                    if LeadStateMachine.can_transition(lead.status, next_status):
                        lead.status = next_status
                        lead.updated_at = datetime.now(timezone.utc)
                    result.succeeded += 1
                else:
                    result.failed += 1
            except Exception as e:
                self.logger.error(f"Follow-up failed for lead {lead.id}: {e}")
                result.failed += 1

        session.commit()

    async def _check_bounces(self, session: Session) -> None:
        bounced_messages = (
            session.query(OutreachMessage)
            .filter(
                OutreachMessage.bounced_at.isnot(None),
                OutreachMessage.status != "bounce_processed",
            )
            .all()
        )

        for msg in bounced_messages:
            lead = session.query(Lead).get(msg.lead_id)
            if lead and LeadStateMachine.can_transition(lead.status, LeadStatus.BOUNCED):
                lead.status = LeadStatus.BOUNCED
                lead.updated_at = datetime.now(timezone.utc)
                msg.status = "bounce_processed"

        if bounced_messages:
            session.commit()
            self.logger.info(f"Processed {len(bounced_messages)} bounces")

    async def _check_unsubscribes(self, session: Session) -> None:
        replied_messages = (
            session.query(OutreachMessage)
            .filter(
                OutreachMessage.replied_at.isnot(None),
                OutreachMessage.status == "sent",
            )
            .all()
        )

        for msg in replied_messages:
            lead = session.query(Lead).get(msg.lead_id)
            if not lead:
                continue

            if LeadStateMachine.can_transition(lead.status, LeadStatus.RESPONDED):
                lead.status = LeadStatus.RESPONDED
                lead.updated_at = datetime.now(timezone.utc)
                msg.status = "replied"

        if replied_messages:
            session.commit()
            self.logger.info(f"Processed {len(replied_messages)} replies")

    async def close(self):
        await self.outreach_agent.close()
