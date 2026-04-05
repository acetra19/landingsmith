"""
Deployer Agent: Marks websites as "published" and generates
preview URLs pointing to our own FastAPI preview server.

All websites are served from ONE app — no separate Railway projects.
The preview URL format is: {APP_BASE_URL}/preview/{lead_id}
"""

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from config.settings import settings
from database.models import Lead, Website, Deployment

logger = logging.getLogger(__name__)


class DeployerAgent(BaseAgent):
    def __init__(self):
        super().__init__("deployer")

    async def execute(
        self, lead: Lead = None, session: Session = None, **kwargs
    ) -> Deployment:
        if not lead:
            raise ValueError("Lead is required for deployment")

        website = self._get_latest_website(session, lead.id)
        if not website:
            raise ValueError(f"No website found for lead {lead.id}")

        self.logger.info(f"Publishing preview for: {lead.business_name}")

        slug = self._make_slug(lead.business_name)
        base_url = settings.railway.app_base_url.rstrip("/")
        preview_url = f"{base_url}/preview/{lead.id}/{slug}"

        deployment = Deployment(
            lead_id=lead.id,
            website_id=website.id,
            live_url=preview_url,
            status="published",
            deployed_at=datetime.now(timezone.utc),
        )

        if session:
            session.add(deployment)
            website.preview_url = preview_url
            session.commit()

        self.logger.info(f"Published {lead.business_name} -> {preview_url}")
        return deployment

    def _get_latest_website(self, session: Session, lead_id: int) -> Website:
        if not session:
            return None
        return (
            session.query(Website)
            .filter(Website.lead_id == lead_id)
            .order_by(Website.version.desc())
            .first()
        )

    def _make_slug(self, name: str) -> str:
        slug = name.lower().strip()
        slug = re.sub(r"[äÄ]", "ae", slug)
        slug = re.sub(r"[öÖ]", "oe", slug)
        slug = re.sub(r"[üÜ]", "ue", slug)
        slug = re.sub(r"[ß]", "ss", slug)
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        return slug[:60]
