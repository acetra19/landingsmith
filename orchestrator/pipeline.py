"""
Central pipeline that orchestrates all agents in sequence.
Processes leads in batches, respecting the state machine transitions.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from config.settings import settings
from database.connection import get_session
from database.models import Lead, LeadStatus, PipelineRun
from orchestrator.state_machine import LeadStateMachine

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self):
        self._agents: dict[str, object] = {}

    def register_agent(self, name: str, agent) -> None:
        self._agents[name] = agent
        logger.info(f"Registered agent: {name}")

    def get_agent(self, name: str):
        agent = self._agents.get(name)
        if agent is None:
            raise ValueError(f"Agent '{name}' not registered")
        return agent

    def transition_lead(
        self, session: Session, lead: Lead, new_status: LeadStatus
    ) -> None:
        old_status = lead.status
        validated = LeadStateMachine.transition(old_status, new_status)
        lead.status = validated
        lead.updated_at = datetime.now(timezone.utc)
        session.commit()
        logger.info(
            f"Lead {lead.id} ({lead.business_name}): "
            f"{old_status.value} → {validated.value}"
        )

    async def run_scan(
        self, location: str, query: str, radius: Optional[int] = None
    ) -> PipelineRun:
        scanner = self.get_agent("scanner")
        run = self._start_run("scanner")
        session = get_session()
        try:
            leads = await scanner.execute(
                location=location, query=query, radius=radius
            )
            run.leads_processed = len(leads)
            run.leads_succeeded = sum(1 for l in leads if l is not None)
            self._finish_run(session, run, "completed")
        except Exception as e:
            self._finish_run(session, run, "failed", str(e))
            raise
        finally:
            session.close()
        return run

    async def run_verification(self, batch_size: Optional[int] = None) -> PipelineRun:
        verifier = self.get_agent("verifier")
        batch_size = batch_size or settings.pipeline.batch_size
        run = self._start_run("verifier")
        session = get_session()
        try:
            leads = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.DISCOVERED)
                .limit(batch_size)
                .all()
            )
            succeeded, failed = 0, 0
            for lead in leads:
                try:
                    result = await verifier.execute(lead=lead, session=session)
                    if result.is_valid:
                        self.transition_lead(session, lead, LeadStatus.VERIFIED)
                        lead.verified_at = datetime.now(timezone.utc)
                        succeeded += 1
                    else:
                        lead.rejection_reason = result.rejection_reason
                        lead.rejection_details = result.details
                        self.transition_lead(session, lead, LeadStatus.REJECTED)
                        failed += 1
                except Exception as e:
                    logger.error(f"Verification failed for lead {lead.id}: {e}")
                    failed += 1
            session.commit()
            run.leads_processed = len(leads)
            run.leads_succeeded = succeeded
            run.leads_failed = failed
            self._finish_run(session, run, "completed")
        except Exception as e:
            self._finish_run(session, run, "failed", str(e))
            raise
        finally:
            session.close()
        return run

    async def run_build(self, batch_size: Optional[int] = None) -> PipelineRun:
        builder = self.get_agent("builder")
        batch_size = batch_size or settings.pipeline.batch_size
        run = self._start_run("builder")
        session = get_session()
        try:
            leads = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.VERIFIED)
                .limit(batch_size)
                .all()
            )
            succeeded, failed = 0, 0
            for lead in leads:
                try:
                    self.transition_lead(session, lead, LeadStatus.WEBSITE_BUILDING)
                    website = await builder.execute(lead=lead, session=session)
                    if website and website.quality_score and website.quality_score >= 0.7:
                        website.is_approved = True
                        self.transition_lead(session, lead, LeadStatus.WEBSITE_READY)
                        succeeded += 1
                    elif website:
                        self.transition_lead(session, lead, LeadStatus.WEBSITE_READY)
                        succeeded += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Build failed for lead {lead.id}: {e}")
                    failed += 1
            session.commit()
            run.leads_processed = len(leads)
            run.leads_succeeded = succeeded
            run.leads_failed = failed
            self._finish_run(session, run, "completed")
        except Exception as e:
            self._finish_run(session, run, "failed", str(e))
            raise
        finally:
            session.close()
        return run

    async def run_deploy(self, batch_size: Optional[int] = None) -> PipelineRun:
        deployer = self.get_agent("deployer")
        batch_size = batch_size or settings.pipeline.batch_size
        run = self._start_run("deployer")
        session = get_session()
        try:
            leads = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.WEBSITE_READY)
                .limit(batch_size)
                .all()
            )
            succeeded, failed = 0, 0
            for lead in leads:
                try:
                    deployment = await deployer.execute(lead=lead, session=session)
                    if deployment and deployment.live_url:
                        self.transition_lead(session, lead, LeadStatus.DEPLOYED)
                        succeeded += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Deploy failed for lead {lead.id}: {e}")
                    failed += 1
            session.commit()
            run.leads_processed = len(leads)
            run.leads_succeeded = succeeded
            run.leads_failed = failed
            self._finish_run(session, run, "completed")
        except Exception as e:
            self._finish_run(session, run, "failed", str(e))
            raise
        finally:
            session.close()
        return run

    async def run_outreach(self, batch_size: Optional[int] = None) -> PipelineRun:
        outreach = self.get_agent("outreach")
        batch_size = batch_size or min(
            settings.pipeline.batch_size, settings.pipeline.outreach_daily_limit
        )
        run = self._start_run("outreach")
        session = get_session()
        try:
            leads = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.DEPLOYED)
                .limit(batch_size)
                .all()
            )
            succeeded, failed = 0, 0
            for lead in leads:
                try:
                    message = await outreach.execute(lead=lead, session=session)
                    if message and message.status == "sent":
                        self.transition_lead(session, lead, LeadStatus.OUTREACH_SENT)
                        lead.outreach_at = datetime.now(timezone.utc)
                        succeeded += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Outreach failed for lead {lead.id}: {e}")
                    failed += 1
            session.commit()
            run.leads_processed = len(leads)
            run.leads_succeeded = succeeded
            run.leads_failed = failed
            self._finish_run(session, run, "completed")
        except Exception as e:
            self._finish_run(session, run, "failed", str(e))
            raise
        finally:
            session.close()
        return run

    async def run_followup(self) -> PipelineRun:
        followup = self.get_agent("followup")
        run = self._start_run("followup")
        session = get_session()
        try:
            result = await followup.execute(session=session)
            run.leads_processed = result.processed
            run.leads_succeeded = result.succeeded
            run.leads_failed = result.failed
            self._finish_run(session, run, "completed")
        except Exception as e:
            self._finish_run(session, run, "failed", str(e))
            raise
        finally:
            session.close()
        return run

    async def run_full_pipeline(
        self, location: str, query: str, radius: Optional[int] = None
    ) -> dict[str, PipelineRun]:
        results = {}
        results["scan"] = await self.run_scan(location, query, radius)
        results["verify"] = await self.run_verification()
        results["build"] = await self.run_build()
        results["deploy"] = await self.run_deploy()
        results["outreach"] = await self.run_outreach()
        results["followup"] = await self.run_followup()
        return results

    def _start_run(self, agent_name: str) -> PipelineRun:
        session = get_session()
        run = PipelineRun(agent_name=agent_name, status="running")
        session.add(run)
        session.commit()
        session.close()
        return run

    def _finish_run(
        self,
        session: Session,
        run: PipelineRun,
        status: str,
        error: str = None,
    ) -> None:
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        if error:
            run.error_log = error
        session.merge(run)
        session.commit()
