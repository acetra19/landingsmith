"""
Extracts and validates contact information for outreach.
Searches for email addresses via common patterns and public sources.
"""

import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ContactInfo:
    email: str = ""
    phone: str = ""
    contact_name: str = ""
    source: str = ""
    is_valid: bool = False


def generate_email_guesses(business_name: str, domain: str = "") -> list[str]:
    if not domain:
        return []

    clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    prefixes = [
        "info", "kontakt", "contact", "hello", "mail",
        "office", "anfrage", "service",
    ]
    return [f"{p}@{clean_domain}" for p in prefixes]


def extract_emails_from_text(text: str) -> list[str]:
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    found = re.findall(pattern, text)
    blacklist = {"example.com", "test.com", "email.com", "domain.com"}
    return [e for e in found if e.split("@")[1] not in blacklist]


async def find_contact_info(
    business_name: str,
    phone: str = "",
    city: str = "",
) -> ContactInfo:
    """Try to find usable contact information for a business."""
    contact = ContactInfo(phone=phone)

    if phone:
        contact.is_valid = True
        contact.source = "google_places"

    query = f"{business_name} {city} email kontakt".strip()
    try:
        email = await _search_email_web(query)
        if email:
            contact.email = email
            contact.is_valid = True
            contact.source = "web_search"
    except Exception as e:
        logger.debug(f"Web email search failed: {e}")

    if not contact.email and not contact.phone:
        contact.is_valid = False

    return contact


async def _search_email_web(query: str) -> str:
    """
    Lightweight web search for email.
    In production, this would use SerpAPI or similar.
    For now returns empty — to be connected to a real search backend.
    """
    logger.debug(f"Email web search (stub): {query}")
    return ""


def validate_phone_de(phone: str) -> bool:
    if not phone:
        return False
    cleaned = re.sub(r"[^0-9+]", "", phone)
    if len(cleaned) >= 6:
        return True
    return False
