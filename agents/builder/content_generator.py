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


STYLE_FONT_MAP = {
    "bold_dark": ["Space Grotesk", "Outfit", "Sora", "Manrope"],
    "clean_professional": ["Inter", "DM Sans", "Nunito Sans", "Figtree"],
    "elegant_warm": ["Cormorant Garamond", "Playfair Display", "Lora", "Libre Baskerville"],
    "gastro_vibrant": ["Poppins", "Josefin Sans", "Nunito", "Rubik"],
    "medical_trust": ["Source Sans 3", "Nunito", "Open Sans", "Lato"],
    "craft_industrial": ["Barlow", "Barlow Condensed", "Oswald", "Roboto Condensed"],
    "beauty_glow": ["Quicksand", "Raleway", "Comfortaa", "Nunito"],
    "minimal_zen": ["Work Sans", "Karla", "Jost", "Outfit"],
    "urban_edge": ["Archivo Black", "Bebas Neue", "Anton", "Russo One"],
    "tech_grid": ["IBM Plex Sans", "JetBrains Mono", "Fira Code", "Source Code Pro"],
    "local_cozy": ["Nunito", "Rubik", "Quicksand", "Varela Round"],
}

STYLE_BUSINESS_MAP = {
    "bold_dark": [
        "barbershop", "barber", "herren friseur", "herrenfriseur",
    ],
    "elegant_warm": [
        "blumen", "florist", "boutique", "mode", "schmuck", "hochzeit",
        "braut", "atelier",
    ],
    "gastro_vibrant": [
        "pizza", "pizzeria", "doener", "kebab", "imbiss", "restaurant",
        "bistro", "grill", "asia", "sushi", "burger",
    ],
    "medical_trust": [
        "arzt", "zahnarzt", "praxis", "physio", "therapie", "apotheke",
        "orthop", "kinder", "augen", "haut", "heilpraktik",
    ],
    "craft_industrial": [
        "werkstatt", "handwerk", "heizung", "sanitaer", "elektr",
        "schlosser", "montage", "bau", "dach", "maler", "tischler",
        "kfz", "auto werkstatt", "meisterbetrieb",
    ],
    "beauty_glow": [
        "kosmetik", "beauty", "spa", "nagel", "nail", "wimpern",
        "lash", "skin", "pflege", "wellness",
    ],
    "minimal_zen": [
        "yoga", "meditation", "massage", "reiki", "akupunktur",
        "coaching", "beratung",
    ],
    "urban_edge": [
        "tattoo", "piercing", "streetwear", "skate", "graffiti",
        "vinyl", "record",
    ],
    "tech_grid": [
        "computer", "it", "reparatur", "elektronik", "handy",
        "smartphone", "pc", "software", "web", "digital",
    ],
    "local_cozy": [
        "baeckerei", "cafe", "konditorei", "eis", "tee", "kiosk",
        "laden", "geschenk", "keramik", "wolle", "buchladen",
    ],
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
    design_style: str = "clean_professional"
    font: str = "Inter"
    raw_json: dict = field(default_factory=dict)


SYSTEM_PROMPT = """You are a professional German copywriter and web designer 
specializing in small business websites. You create compelling, unique website 
copy with carefully chosen design palettes. Always respond in valid JSON. 
All text content must be in German."""

GENERATION_PROMPT = """Create unique website copy and design for this business:

Business Name: {name}
Business Type: {type}
City: {city}
Phone: {phone}
Rating: {rating} stars ({reviews} reviews)
Opening Hours: {hours}
Design Style: {style}

Generate a complete single-page website copy in JSON format:
{{
    "headline": "A compelling, UNIQUE headline that fits THIS specific business (max 8 words). Be creative, avoid generic phrases.",
    "subheadline": "A supporting subheadline that adds personality (max 15 words)",
    "about_text": "About section (2-3 sentences). Make it sound personal and authentic, not corporate. Mention specific details about the business type and location.",
    "services": ["Service 1", "Service 2", "Service 3", "Service 4"],
    "cta_text": "A call-to-action that fits the business (be creative, not just 'Kontakt')",
    "testimonial_placeholder": "A realistic, specific testimonial that mentions a concrete detail",
    "footer_text": "Brief footer text with location mention",
    "meta_description": "SEO meta description (max 155 chars)",
    "color_scheme": {{
        "primary": "#hex - MUST match the business personality (see rules below)",
        "secondary": "#hex - a complementary accent that creates contrast",
        "bg": "#hex background",
        "text": "#hex text color"
    }}
}}

DESIGN STYLE "{style}" COLOR RULES:
{color_rules}

CRITICAL: Each business should feel UNIQUE. Avoid generic headlines like "Willkommen bei [Name]". 
Instead use creative, personality-driven headlines. Examples:
- Barbershop: "Dein Style. Unser Handwerk." 
- Florist: "Wo jede Bluete eine Geschichte erzaehlt"
- Auto-Werkstatt: "Technik die bewegt — Service der ueberzeugt"
- Zahnarzt: "Ihr Laecheln in besten Haenden"

Make it sound professional, trustworthy, and local."""

COLOR_RULES = {
    "bold_dark": """Dark/bold style — SATURATED, vivid accents:
- Reds (#ef4444, #dc2626), oranges (#f97316), electric blues (#3b82f6),
  neon greens (#22c55e), hot pinks (#ec4899), purples (#8b5cf6)
- bg: #0a0a0f | text: #e4e4e7 — EDGY and MODERN""",

    "clean_professional": """Clean/professional — REFINED, trustworthy:
- Blues (#1d4ed8, #2563eb), teals (#0d9488), slate (#475569),
  greens (#059669), indigo (#4f46e5)
- bg: #ffffff | text: #1e293b — PREMIUM and CLEAN""",

    "elegant_warm": """Elegant/warm — RICH, sophisticated:
- Wines (#881337, #9f1239), forest greens (#166534), burgundy (#7f1d1d),
  copper (#b45309), muted rose (#be123c)
- bg: #fffbf5 | text: #292524 — SOPHISTICATED""",

    "gastro_vibrant": """Gastro/vibrant — APPETIZING, warm, inviting:
- Warm reds (#dc2626, #b91c1c), rich oranges (#ea580c, #c2410c),
  olive (#65a30d), tomato (#e11d48), warm amber (#d97706)
- bg: #fffaf5 | text: #1c1917 — APPETIZING and WARM""",

    "medical_trust": """Medical/trust — CALMING, clinical, trustworthy:
- Calming blues (#0284c7, #0369a1), teals (#0d9488, #0f766e),
  soft greens (#059669, #047857), professional blue (#1e40af)
- bg: #ffffff | text: #1e293b — CALMING and TRUSTWORTHY""",

    "craft_industrial": """Craft/industrial — STRONG, reliable, bold:
- Safety yellows (#eab308, #ca8a04), construction orange (#ea580c),
  steel blue (#475569), industrial red (#dc2626), dark teal (#0f766e)
- bg: #fafaf9 | text: #1c1917 — STRONG and RELIABLE""",

    "beauty_glow": """Beauty/glow — SOFT, luxurious, radiant:
- Soft pinks (#ec4899, #db2777), rose (#e11d48, #f43f5e),
  lavender (#8b5cf6, #a78bfa), soft coral (#fb7185), mauve (#a855f7)
- bg: #fdf4ff or #fff1f2 | text: #1e1b4b — SOFT and LUXURIOUS""",

    "minimal_zen": """Minimal/zen — CALM, serene, muted:
- Sage (#65a30d, #4d7c0f), muted teal (#0d9488), soft stone (#78716c),
  gentle blue (#6366f1), forest (#166534)
- bg: #fafaf9 | text: #44403c — SERENE and MINIMAL""",

    "urban_edge": """Urban/edge — HIGH-CONTRAST, neon, bold:
- Neon green (#22c55e, #4ade80), electric cyan (#06b6d4, #22d3ee),
  hot magenta (#d946ef), acid yellow (#facc15), neon red (#ef4444)
- bg: #000000 | text: #ffffff — BOLD and EDGY""",

    "tech_grid": """Tech/grid — FUTURISTIC, digital, precise:
- Cyber blue (#3b82f6, #60a5fa), matrix green (#22c55e, #4ade80),
  electric purple (#8b5cf6), cyan (#06b6d4), terminal amber (#f59e0b)
- bg: #0c0c14 | text: #c8cad0 — TECHY and FUTURISTIC""",

    "local_cozy": """Local/cozy — WARM, friendly, inviting:
- Warm terracotta (#c2410c, #ea580c), forest green (#166534, #15803d),
  warm blue (#1d4ed8), cozy amber (#b45309), brick (#92400e)
- bg: #faf6f1 | text: #292524 — COZY and FRIENDLY""",
}


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

    def _pick_style(self, business_name: str, business_type: str) -> str:
        """Choose a design style based on the business type."""
        import random
        combined = f"{business_name} {business_type}".lower()

        matches = []
        for style, keywords in STYLE_BUSINESS_MAP.items():
            if any(kw in combined for kw in keywords):
                matches.append(style)

        if matches:
            return matches[0]

        if "friseur" in combined or "salon" in combined or "hair" in combined:
            return random.choice(["bold_dark", "beauty_glow", "clean_professional"])

        if "reinigung" in combined or "schneider" in combined or "schuh" in combined:
            return random.choice(["clean_professional", "local_cozy", "craft_industrial"])

        all_styles = list(STYLE_FONT_MAP.keys())
        return random.choice(all_styles)

    def _pick_font(self, style: str) -> str:
        """Pick a random font for the given style to add variety."""
        import random
        fonts = STYLE_FONT_MAP.get(style, STYLE_FONT_MAP["clean_professional"])
        return random.choice(fonts)

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

        style = self._pick_style(business_name, business_type)
        font = self._pick_font(style)
        color_rules = COLOR_RULES.get(style, COLOR_RULES["clean_professional"])

        logger.info(f"Design: style={style}, font={font}")

        prompt = GENERATION_PROMPT.format(
            name=business_name,
            type=business_type or "Lokales Unternehmen",
            city=city or "Deutschland",
            phone=phone or "Nicht angegeben",
            rating=rating or "N/A",
            reviews=review_count,
            hours=hours_str or "Nicht angegeben",
            style=style,
            color_rules=color_rules,
        )

        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": settings.llm.max_tokens,
                "temperature": 0.85,
            }
            if self.supports_json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)
            raw = response.choices[0].message.content
            data = self._extract_json(raw)

            colors = data.get("color_scheme", {})
            colors = self._sanitize_colors(colors, style)

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
                design_style=style,
                font=font,
                raw_json=data,
            )
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return self._fallback_copy(business_name, business_type, city)

    @staticmethod
    def _sanitize_colors(colors: dict, style: str = "clean_professional") -> dict:
        """Validate colors per style, with sensible fallbacks."""
        style_defaults = {
            "bold_dark": {"primary": "#ef4444", "secondary": "#f97316", "bg": "#0a0a0f", "text": "#e4e4e7"},
            "clean_professional": {"primary": "#2563eb", "secondary": "#f59e0b", "bg": "#ffffff", "text": "#1e293b"},
            "elegant_warm": {"primary": "#881337", "secondary": "#d97706", "bg": "#fffbf5", "text": "#292524"},
            "gastro_vibrant": {"primary": "#dc2626", "secondary": "#ea580c", "bg": "#fffaf5", "text": "#1c1917"},
            "medical_trust": {"primary": "#0284c7", "secondary": "#0d9488", "bg": "#ffffff", "text": "#1e293b"},
            "craft_industrial": {"primary": "#eab308", "secondary": "#ea580c", "bg": "#fafaf9", "text": "#1c1917"},
            "beauty_glow": {"primary": "#ec4899", "secondary": "#a855f7", "bg": "#fdf4ff", "text": "#1e1b4b"},
            "minimal_zen": {"primary": "#65a30d", "secondary": "#0d9488", "bg": "#fafaf9", "text": "#44403c"},
            "urban_edge": {"primary": "#22c55e", "secondary": "#06b6d4", "bg": "#000000", "text": "#ffffff"},
            "tech_grid": {"primary": "#3b82f6", "secondary": "#22c55e", "bg": "#0c0c14", "text": "#c8cad0"},
            "local_cozy": {"primary": "#c2410c", "secondary": "#166534", "bg": "#faf6f1", "text": "#292524"},
        }
        defaults = style_defaults.get(style, style_defaults["clean_professional"])

        if not colors or not isinstance(colors, dict):
            return defaults

        result = {**defaults}
        for key in ("primary", "secondary", "bg", "text"):
            val = colors.get(key, "").strip()
            if val.startswith("#") and len(val) == 7:
                result[key] = val

        primary = result["primary"].lower()
        try:
            r = int(primary[1:3], 16)
            g = int(primary[3:5], 16)
            b = int(primary[5:7], 16)
            is_brown = (r > 80 and g < r * 0.75 and b < r * 0.5)
            is_muddy = (max(r, g, b) - min(r, g, b) < 40 and max(r, g, b) < 140)
            if is_brown or is_muddy:
                result["primary"] = defaults["primary"]
        except (ValueError, IndexError):
            result["primary"] = defaults["primary"]

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
