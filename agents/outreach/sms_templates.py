"""
SMS templates for cold outreach. All in German.
Kept short to fit SMS limits (~160 chars per segment).
"""

from database.models import Lead


def initial_sms(
    lead: Lead,
    preview_url: str,
    sender_name: str = "LandingSmith",
) -> str:
    return (
        f"Guten Tag! Wir haben einen Website-Entwurf fuer "
        f"{lead.business_name} erstellt: {preview_url} "
        f"- Fertige Website ab 99EUR einmalig. "
        f"Interesse? james@amplivo.net. "
        f"LG {sender_name}"
    )


def follow_up_sms(
    lead: Lead,
    preview_url: str,
    sender_name: str = "LandingSmith",
) -> str:
    return (
        f"Kurze Erinnerung: Ihr Website-Entwurf fuer "
        f"{lead.business_name} ist noch online: {preview_url} "
        f"- Ab 99EUR fertig mit eigener Domain. "
        f"Fragen? james@amplivo.net. "
        f"LG {sender_name}"
    )
