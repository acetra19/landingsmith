"""
Deployer Agent: Takes built websites and deploys them to Railway,
generating preview URLs for the outreach emails.
"""

import logging

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from agents.deployer.railway_client import RailwayClient
from database.models import Lead, Website, Deployment

logger = logging.getLogger(__name__)


class DeployerAgent(BaseAgent):
    def __init__(self):
        super().__init__("deployer")
        self.railway = RailwayClient()

    async def execute(
        self, lead: Lead = None, session: Session = None, **kwargs
    ) -> Deployment:
        if not lead:
            raise ValueError("Lead is required for deployment")

        website = self._get_latest_website(session, lead.id)
        if not website:
            raise ValueError(f"No website found for lead {lead.id}")

        self.logger.info(f"Deploying website for: {lead.business_name}")

        project = await self.railway.create_project(lead.business_name)
        service_id = await self.railway.create_service(project.project_id)

        await self.railway.set_service_source(
            service_id=service_id,
            environment_id=project.environment_id,
            html_content=website.html_content,
        )

        live_url = await self.railway.generate_domain(
            service_id=service_id,
            environment_id=project.environment_id,
        )

        deployment = Deployment(
            lead_id=lead.id,
            website_id=website.id,
            railway_project_id=project.project_id,
            railway_service_id=service_id,
            railway_environment_id=project.environment_id,
            live_url=live_url,
            status="deployed",
        )

        if session:
            session.add(deployment)
            website.preview_url = live_url
            session.commit()

        self.logger.info(
            f"Deployed {lead.business_name} → {live_url}"
        )
        return deployment

    def _get_latest_website(
        self, session: Session, lead_id: int
    ) -> Website:
        if not session:
            return None
        return (
            session.query(Website)
            .filter(Website.lead_id == lead_id)
            .order_by(Website.version.desc())
            .first()
        )

    async def close(self):
        await self.railway.close()
