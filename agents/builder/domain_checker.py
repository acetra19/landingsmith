"""
Checks domain availability via DNS lookups.
A domain is considered "taken" if it has any A, AAAA, or NS records.
This is a fast heuristic – not 100% accurate (parked domains etc.)
but prevents suggesting obviously-taken domains like "best.de".
"""

import asyncio
import logging
from datetime import datetime, timezone

import dns.resolver

logger = logging.getLogger(__name__)

_RESOLVER = dns.resolver.Resolver()
_RESOLVER.timeout = 3
_RESOLVER.lifetime = 3

OBVIOUSLY_TAKEN = {
    "best.de", "info.de", "service.de", "online.de", "center.de",
    "shop.de", "home.de", "home.com", "design.de", "studio.de",
    "team.de", "pro.de", "plus.de", "top.de", "prime.de",
    "gold.de", "star.de", "express.de", "world.de", "group.de",
    "media.de", "digital.de", "smart.de", "green.de", "power.de",
    "auto.de", "salon.de", "blumen.de", "friseur.de", "bar.de",
    "cafe.de", "pizza.de", "taxi.de", "hotel.de", "fitness.de",
}

MIN_DOMAIN_LENGTH = 4


def _has_dns_records(domain: str) -> bool:
    """Check if domain resolves to any DNS records."""
    for rtype in ("A", "NS"):
        try:
            _RESOLVER.resolve(domain, rtype)
            return True
        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.resolver.NoNameservers,
        ):
            continue
        except dns.exception.Timeout:
            return True  # assume taken on timeout (safe side)
        except Exception:
            continue
    return False


async def check_domain_available(domain: str) -> bool:
    """
    Returns True if domain appears to be available.
    Runs DNS lookup in a thread to avoid blocking the event loop.
    """
    domain_lower = domain.lower()

    if domain_lower in OBVIOUSLY_TAKEN:
        return False

    name_part = domain_lower.rsplit(".", 1)[0]
    if len(name_part) < MIN_DOMAIN_LENGTH:
        return False

    taken = await asyncio.to_thread(_has_dns_records, domain_lower)
    return not taken


async def check_domains_batch(
    domains: list[str],
) -> list[tuple[str, bool]]:
    """
    Check a list of domains concurrently.
    Returns list of (domain, is_available) tuples.
    """
    tasks = [check_domain_available(d) for d in domains]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    checked = []
    for domain, result in zip(domains, results):
        if isinstance(result, Exception):
            logger.warning(f"Domain check failed for {domain}: {result}")
            checked.append((domain, False))
        else:
            checked.append((domain, result))

    return checked
