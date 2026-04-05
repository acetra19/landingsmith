"""
Uses OpenAI to generate professional website copy
tailored to the business type and details.
"""

import json
import logging
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class WebsiteCopy:
    headline: str = ""
    subheadline: str = ""
    about_text: str = ""
    services: list[str] = field(default_factory=list)
    cta_text: str = ""
    testimonial_placeholder: str = ""
    footer_text: str = ""
    meta_description: str = ""
    color_scheme: dict = field(default_factory=dict)
    raw_json: dict = field(default_factory=dict)


SYSTEM_PROMPT = """You are a professional German copywriter specializing in 
small business websites. You write compelling, modern, and concise website copy.
Always respond in valid JSON format. All text content must be in German."""

GENERATION_PROMPT = """Create website copy for this business:

Business Name: {name}
Business Type: {type}
City: {city}
Phone: {phone}
Rating: {rating} stars ({reviews} reviews)
Opening Hours: {hours}

Generate a complete single-page website copy in JSON format:
{{
    "headline": "A compelling headline (max 8 words)",
    "subheadline": "A supporting subheadline (max 15 words)", 
    "about_text": "About section (2-3 sentences describing the business professionally)",
    "services": ["Service 1", "Service 2", "Service 3", "Service 4"],
    "cta_text": "Call-to-action button text (e.g. 'Jetzt Termin vereinbaren')",
    "testimonial_placeholder": "A realistic-sounding placeholder testimonial",
    "footer_text": "Brief footer text with location mention",
    "meta_description": "SEO meta description (max 155 chars)",
    "color_scheme": {{
        "primary": "#hex color fitting the business type",
        "secondary": "#hex accent color",
        "bg": "#hex background (light)",
        "text": "#hex text color (dark)"
    }}
}}

Make it sound professional, trustworthy, and local. 
The tone should be warm but business-appropriate for a German audience."""


class ContentGenerator:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai.api_key)

    async def generate(
        self,
        business_name: str,
        business_type: str = "",
        city: str = "",
        phone: str = "",
        rating: float = 0,
        review_count: int = 0,
        business_hours: dict = None,
    ) -> WebsiteCopy:
        hours_str = ""
        if business_hours and business_hours.get("weekday_text"):
            hours_str = "\n".join(business_hours["weekday_text"])

        prompt = GENERATION_PROMPT.format(
            name=business_name,
            type=business_type or "Lokales Unternehmen",
            city=city or "Deutschland",
            phone=phone or "Nicht angegeben",
            rating=rating or "N/A",
            reviews=review_count,
            hours=hours_str or "Nicht angegeben",
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.openai.max_tokens,
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)

            return WebsiteCopy(
                headline=data.get("headline", business_name),
                subheadline=data.get("subheadline", ""),
                about_text=data.get("about_text", ""),
                services=data.get("services", []),
                cta_text=data.get("cta_text", "Kontakt aufnehmen"),
                testimonial_placeholder=data.get("testimonial_placeholder", ""),
                footer_text=data.get("footer_text", ""),
                meta_description=data.get("meta_description", ""),
                color_scheme=data.get("color_scheme", {
                    "primary": "#2563eb",
                    "secondary": "#f59e0b",
                    "bg": "#ffffff",
                    "text": "#1f2937",
                }),
                raw_json=data,
            )
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return self._fallback_copy(business_name, business_type, city)

    def _fallback_copy(
        self, name: str, btype: str, city: str
    ) -> WebsiteCopy:
        return WebsiteCopy(
            headline=name,
            subheadline=f"Ihr {btype} in {city}" if btype and city else "Willkommen",
            about_text=(
                f"{name} ist Ihr verlässlicher Partner"
                f"{' in ' + city if city else ''}. "
                "Kontaktieren Sie uns für eine persönliche Beratung."
            ),
            services=["Beratung", "Service", "Qualität", "Erfahrung"],
            cta_text="Jetzt kontaktieren",
            footer_text=f"© {name}" + (f" · {city}" if city else ""),
            meta_description=f"{name} - {btype} in {city}",
            color_scheme={
                "primary": "#2563eb",
                "secondary": "#f59e0b",
                "bg": "#ffffff",
                "text": "#1f2937",
            },
        )
