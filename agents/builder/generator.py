"""
Combines templates with generated content to produce
complete, self-contained HTML files ready for deployment.
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from agents.builder.content_generator import ContentGenerator, WebsiteCopy
from database.models import Lead

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class WebsiteGenerator:
    def __init__(self):
        self.content_gen = ContentGenerator()
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    async def generate(
        self, lead: Lead
    ) -> tuple[str, str, WebsiteCopy]:
        copy = await self.content_gen.generate(
            business_name=lead.business_name,
            business_type=lead.business_type or "",
            city=lead.city or "",
            phone=lead.phone or "",
            rating=lead.rating or 0,
            review_count=lead.review_count or 0,
            business_hours=lead.business_hours or {},
        )

        template_name = copy.design_style
        logger.info(
            f"Using template '{template_name}' with font '{copy.font}' "
            f"for {lead.business_name}"
        )

        css = self._render_css(template_name, copy)
        html = self._render_html(template_name, lead, copy, css)

        return html, css, copy

    def _render_css(self, template_name: str, copy: WebsiteCopy) -> str:
        css_template = self.jinja_env.get_template(f"{template_name}.css")
        return css_template.render(colors=copy.color_scheme, font=copy.font)

    def _render_html(
        self,
        template_name: str,
        lead: Lead,
        copy: WebsiteCopy,
        css: str,
    ) -> str:
        html_template = self.jinja_env.get_template(f"{template_name}.html")

        hours = []
        if lead.business_hours and lead.business_hours.get("weekday_text"):
            hours = lead.business_hours["weekday_text"]

        return html_template.render(
            business_name=lead.business_name,
            business_type=lead.business_type or "",
            headline=copy.headline,
            subheadline=copy.subheadline,
            about_text=copy.about_text,
            services=copy.services,
            cta_text=copy.cta_text,
            testimonial=copy.testimonial_placeholder,
            footer_text=copy.footer_text,
            meta_description=copy.meta_description,
            css_content=css,
            font_family=copy.font,
            phone=lead.phone or "",
            email=lead.email or "",
            address=lead.address or "",
            rating=lead.rating,
            review_count=lead.review_count or 0,
            hours=hours,
        )

    def generate_domain_suggestions(self, lead: Lead) -> list[str]:
        """Generate sensible domain name suggestions for the business."""
        import re

        name = lead.business_name.lower().strip()
        name = re.sub(r"[äÄ]", "ae", name)
        name = re.sub(r"[öÖ]", "oe", name)
        name = re.sub(r"[üÜ]", "ue", name)
        name = re.sub(r"[ß]", "ss", name)
        slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")

        city = ""
        if lead.city:
            city = lead.city.lower().strip()
            city = re.sub(r"[äÄ]", "ae", city)
            city = re.sub(r"[öÖ]", "oe", city)
            city = re.sub(r"[üÜ]", "ue", city)
            city = re.sub(r"[ß]", "ss", city)
            city = re.sub(r"[^a-z0-9]+", "-", city).strip("-")

        suggestions = [
            f"{slug}.de",
            f"{slug}.com",
        ]
        if city:
            suggestions.extend([
                f"{slug}-{city}.de",
                f"{slug}-{city}.com",
            ])

        parts = slug.split("-")
        if len(parts) > 1:
            short = parts[0]
            suggestions.append(f"{short}.de")
            if city:
                suggestions.append(f"{short}-{city}.de")

        return suggestions[:6]
