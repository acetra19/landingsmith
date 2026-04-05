"""
Builder Agent: Generates complete websites for verified leads.
Combines LLM-generated content with modern HTML/CSS templates,
stores the result, and generates domain suggestions.
"""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from agents.builder.generator import WebsiteGenerator
from config.settings import settings
from database.models import Lead, Website, DomainSuggestion

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(settings.base_dir) / "output" / "websites"


class BuilderAgent(BaseAgent):
    def __init__(self):
        super().__init__("builder")
        self.generator = WebsiteGenerator()

    async def execute(
        self, lead: Lead = None, session: Session = None, **kwargs
    ) -> Website:
        if not lead:
            raise ValueError("Lead is required for building")

        self.logger.info(f"Building website for: {lead.business_name}")

        html, css, copy = await self.generator.generate(lead)

        website = Website(
            lead_id=lead.id,
            template_name=copy.design_style,
            html_content=html,
            css_content=css,
            generated_copy=copy.raw_json,
            version=self._get_next_version(session, lead.id),
            quality_score=0.85,
        )

        if session:
            session.add(website)
            session.flush()

        self._save_to_disk(lead, website)
        self._generate_domains(lead, session)

        if session:
            session.commit()

        self.logger.info(
            f"Website built for {lead.business_name} (v{website.version})"
        )
        return website

    def _get_next_version(self, session: Session, lead_id: int) -> int:
        if not session:
            return 1
        existing = (
            session.query(Website)
            .filter(Website.lead_id == lead_id)
            .count()
        )
        return existing + 1

    def _save_to_disk(self, lead: Lead, website: Website) -> None:
        slug = lead.business_name.lower().replace(" ", "-")[:40]
        site_dir = OUTPUT_DIR / f"{lead.id}_{slug}"
        site_dir.mkdir(parents=True, exist_ok=True)

        index_path = site_dir / "index.html"
        index_path.write_text(website.html_content, encoding="utf-8")

        website.screenshot_path = str(site_dir / "index.html")
        self.logger.debug(f"Saved website to {site_dir}")

    def _generate_domains(self, lead: Lead, session: Session) -> None:
        if not session:
            return

        suggestions = self.generator.generate_domain_suggestions(lead)
        for domain_str in suggestions:
            name, tld = domain_str.rsplit(".", 1)
            existing = (
                session.query(DomainSuggestion)
                .filter(
                    DomainSuggestion.lead_id == lead.id,
                    DomainSuggestion.domain_name == name,
                )
                .first()
            )
            if not existing:
                session.add(DomainSuggestion(
                    lead_id=lead.id,
                    domain_name=name,
                    tld=f".{tld}",
                    is_recommended=(domain_str == suggestions[0]),
                ))
