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
        f"Guten Tag! Wir haben eine kostenlose Website fuer "
        f"{lead.business_name} erstellt: {preview_url} "
        f"- Interesse? Schreiben Sie uns an james@amplivo.net. "
        f"LG {sender_name}"
    )


def follow_up_sms(
    lead: Lead,
    preview_url: str,
    sender_name: str = "LandingSmith",
) -> str:
    return (
        f"Kurze Erinnerung: Ihr kostenloser Website-Entwurf fuer "
        f"{lead.business_name} ist noch online: {preview_url} "
        f"- Fragen? Melden Sie sich gerne: james@amplivo.net. "
        f"LG {sender_name}"
    )
