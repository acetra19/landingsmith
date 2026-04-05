"""
Checks whether a business truly has no functioning website.
Performs DNS lookups, HTTP checks, and common domain pattern guessing.
"""

import logging
import re
from dataclasses import dataclass

import httpx
import dns.resolver

from config.settings import settings

logger = logging.getLogger(__name__)


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
    slug = _slugify(business_name)
    city_slug = _slugify(city) if city else ""
    parts = slug.split("-")
    short = parts[0] if parts else slug

    tlds = [".de", ".com", ".net", ".eu", ".info"]
    guesses = []

    for tld in tlds:
        guesses.append(f"{slug}{tld}")
        if city_slug:
            guesses.append(f"{slug}-{city_slug}{tld}")
        if short != slug:
            guesses.append(f"{short}{tld}")

    return guesses


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

    for domain in guesses:
        dns_exists = await check_dns_exists(domain)
        if dns_exists:
            result = await check_website_exists(domain)
            if result.has_website:
                result.check_method = "domain_guess"
                return result

    return WebsiteCheckResult(
        has_website=False,
        check_method="deep_check",
        details=f"Checked {len(guesses)} domain guesses, none resolved",
    )
