"""
Checks whether a business truly has no functioning website.
Performs DNS lookups, HTTP checks, and smart domain guessing.
Only flags a business as "has website" if the found site actually
belongs to that business (not a generic/unrelated domain).
"""

import logging
import re
from dataclasses import dataclass

import httpx
import dns.resolver

from config.settings import settings

logger = logging.getLogger(__name__)

GENERIC_DOMAINS = {
    "friseur.com", "friseur.de", "salon.com", "salon.de",
    "barbershop.com", "barbershop.de", "barber.com", "barber.de",
    "blumen.de", "blumen.com", "florist.de", "florist.com",
    "bäckerei.de", "baeckerei.de", "bakery.com",
    "restaurant.de", "restaurant.com",
    "zahnarzt.de", "dentist.com",
    "werkstatt.de", "autowerkstatt.de",
    "beauty.de", "beauty.com",
    "the.de", "the.com", "la.de", "la.com",
    "best.de", "best.com", "east.com", "east.de",
    "back.de", "back.com", "back.eu", "back.net",
    "style.de", "style.com", "hair.de", "hair.com",
    "shop.de", "shop.com", "haus.de", "haus.com",
    "studio.de", "studio.com", "art.de", "art.com",
    "cut.de", "cut.com", "wash.de", "wash.com",
}

STOPWORDS = {
    "friseur", "salon", "barbershop", "barber", "shop", "bar",
    "restaurant", "cafe", "bistro", "imbiss", "grill",
    "blumen", "florist", "flowers", "pflanzen",
    "bakery", "baeckerei", "bäckerei", "konditorei",
    "beauty", "nail", "spa", "wellness", "kosmetik",
    "auto", "car", "kfz", "werkstatt", "garage",
    "zahnarzt", "dentist", "praxis", "dr",
    "hair", "haare", "style", "styling", "cut",
    "the", "der", "die", "das", "und", "and", "by", "am", "im", "von",
    "la", "le", "el", "los", "las",
}


@dataclass
class WebsiteCheckResult:
    has_website: bool
    url_found: str = ""
    check_method: str = ""
    details: str = ""


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[äÄ]", "ae", slug)
    slug = re.sub(r"[öÖ]", "oe", slug)
    slug = re.sub(r"[üÜ]", "ue", slug)
    slug = re.sub(r"[ß]", "ss", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def _generate_domain_guesses(business_name: str, city: str = "") -> list[str]:
    """
    Generate plausible domain guesses for a specific business.
    Only uses the FULL business name slug — never single generic words.
    """
    slug = _slugify(business_name)
    city_slug = _slugify(city) if city else ""
    parts = [p for p in slug.split("-") if p not in STOPWORDS and len(p) > 2]

    tlds = [".de", ".com"]
    guesses = []

    for tld in tlds:
        guesses.append(f"{slug}{tld}")
        if city_slug:
            guesses.append(f"{slug}-{city_slug}{tld}")

    if len(parts) >= 2:
        unique_slug = "-".join(parts)
        if unique_slug != slug:
            for tld in tlds:
                guesses.append(f"{unique_slug}{tld}")

    return [g for g in guesses if g.split(".")[0] not in STOPWORDS]


def _is_generic_domain(domain: str) -> bool:
    clean = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
    return clean in GENERIC_DOMAINS


async def check_website_exists(url: str) -> WebsiteCheckResult:
    if not url:
        return WebsiteCheckResult(has_website=False)

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    timeout = settings.pipeline.verification_timeout_seconds
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False
        ) as client:
            resp = await client.get(url)
            if resp.status_code < 400:
                final_domain = str(resp.url).split("/")[2] if "/" in str(resp.url) else ""
                if _is_generic_domain(final_domain):
                    return WebsiteCheckResult(
                        has_website=False,
                        details=f"Redirected to generic domain {final_domain}",
                    )
                return WebsiteCheckResult(
                    has_website=True,
                    url_found=str(resp.url),
                    check_method="http_check",
                    details=f"HTTP {resp.status_code}",
                )
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    except Exception as e:
        logger.debug(f"HTTP check failed for {url}: {e}")

    return WebsiteCheckResult(has_website=False, details=f"No response from {url}")


async def check_dns_exists(domain: str) -> bool:
    try:
        clean = domain.replace("https://", "").replace("http://", "").split("/")[0]
        resolver = dns.resolver.Resolver()
        resolver.lifetime = settings.pipeline.verification_timeout_seconds
        answers = resolver.resolve(clean, "A")
        return len(list(answers)) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
        return False
    except Exception:
        return False


async def deep_website_check(
    business_name: str, city: str = "", known_url: str = ""
) -> WebsiteCheckResult:
    if known_url:
        result = await check_website_exists(known_url)
        if result.has_website:
            return result

    guesses = _generate_domain_guesses(business_name, city)
    logger.debug(f"Domain guesses for '{business_name}': {guesses}")

    for domain in guesses:
        if _is_generic_domain(domain):
            logger.debug(f"Skipping generic domain: {domain}")
            continue

        dns_exists = await check_dns_exists(domain)
        if dns_exists:
            result = await check_website_exists(domain)
            if result.has_website:
                result.check_method = "domain_guess"
                return result

    return WebsiteCheckResult(
        has_website=False,
        check_method="deep_check",
        details=f"Checked {len(guesses)} domain guesses, none matched",
    )
