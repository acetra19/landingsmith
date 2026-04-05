"""
Uses an LLM (Groq by default, OpenAI as fallback) to generate
professional website copy tailored to the business type and details.
Groq is preferred for speed and cost — its API is OpenAI-compatible.
"""

import json
import logging
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

PROVIDER_DEFAULTS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
    },
}


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
        "primary": "#hex - a bold, modern, saturated color. Use deep blues, teals, emerald greens, rich purples, or vibrant indigos. NEVER use brown, beige, tan, or muted earth tones.",
        "secondary": "#hex - a complementary accent, brighter/warmer than primary",
        "bg": "#hex background - use #ffffff or a very subtle cool-tinted off-white like #f8fafc",
        "text": "#hex text - dark gray like #1e293b"
    }}
}}

IMPORTANT color rules:
- Primary color must be modern and vibrant: blues (#2563eb, #0ea5e9), teals (#0d9488), greens (#059669), purples (#7c3aed), slate (#475569)
- NEVER use brown (#663300, #8B4513, etc), beige, tan, olive, or muddy colors
- The website should look sleek, modern, and premium — like a top Squarespace template

Make it sound professional, trustworthy, and local. 
The tone should be warm but business-appropriate for a German audience."""


class ContentGenerator:
    def __init__(self):
        llm = settings.llm
        base_url = llm.base_url or PROVIDER_DEFAULTS.get(
            llm.provider, PROVIDER_DEFAULTS["groq"]
        )["base_url"]
        self.model = llm.model or PROVIDER_DEFAULTS.get(
            llm.provider, PROVIDER_DEFAULTS["groq"]
        )["model"]

        self.client = AsyncOpenAI(
            api_key=llm.api_key,
            base_url=base_url,
        )
        self.supports_json_mode = llm.provider == "openai"
        logger.info(f"LLM provider: {llm.provider} | model: {self.model}")

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
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": settings.llm.max_tokens,
                "temperature": 0.7,
            }
            if self.supports_json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)
            raw = response.choices[0].message.content
            data = self._extract_json(raw)

            colors = data.get("color_scheme", {})
            colors = self._sanitize_colors(colors)

            return WebsiteCopy(
                headline=data.get("headline", business_name),
                subheadline=data.get("subheadline", ""),
                about_text=data.get("about_text", ""),
                services=data.get("services", []),
                cta_text=data.get("cta_text", "Kontakt aufnehmen"),
                testimonial_placeholder=data.get("testimonial_placeholder", ""),
                footer_text=data.get("footer_text", ""),
                meta_description=data.get("meta_description", ""),
                color_scheme=colors,
                raw_json=data,
            )
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return self._fallback_copy(business_name, business_type, city)

    @staticmethod
    def _sanitize_colors(colors: dict) -> dict:
        """Reject muddy/brown colors and enforce a modern palette."""
        defaults = {
            "primary": "#2563eb",
            "secondary": "#f59e0b",
            "bg": "#ffffff",
            "text": "#1e293b",
        }
        if not colors or not isinstance(colors, dict):
            return defaults

        result = {**defaults, **colors}

        primary = result.get("primary", "").lower()
        try:
            if primary.startswith("#") and len(primary) == 7:
                r = int(primary[1:3], 16)
                g = int(primary[3:5], 16)
                b = int(primary[5:7], 16)
                is_brown = (r > 80 and g < r * 0.75 and b < r * 0.5)
                is_muddy = (max(r, g, b) - min(r, g, b) < 60 and max(r, g, b) < 160)
                is_too_dark = max(r, g, b) < 50
                if is_brown or is_muddy or is_too_dark:
                    result["primary"] = "#2563eb"
        except (ValueError, IndexError):
            result["primary"] = "#2563eb"

        if result.get("bg", "").lower() not in ("#ffffff", "#f8fafc", "#f9fafb", "#fafafa", "#f8f9fa"):
            result["bg"] = "#ffffff"

        return result

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        return json.loads(text)

    def _fallback_copy(
        self, name: str, btype: str, city: str
    ) -> WebsiteCopy:
        return WebsiteCopy(
            headline=name,
            subheadline=f"Ihr {btype} in {city}" if btype and city else "Willkommen",
            about_text=(
                f"{name} ist Ihr verlaesslicher Partner"
                f"{' in ' + city if city else ''}. "
                "Kontaktieren Sie uns fuer eine persoenliche Beratung."
            ),
            services=["Beratung", "Service", "Qualitaet", "Erfahrung"],
            cta_text="Jetzt kontaktieren",
            footer_text=f"(c) {name}" + (f" - {city}" if city else ""),
            meta_description=f"{name} - {btype} in {city}",
            color_scheme={
                "primary": "#2563eb",
                "secondary": "#f59e0b",
                "bg": "#ffffff",
                "text": "#1f2937",
            },
        )
