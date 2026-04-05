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
        f"- Interesse? Schreiben Sie uns: james@amplivo.net "
        f"oder antworten Sie auf diese SMS. {sender_name}"
    )


def follow_up_sms(
    lead: Lead,
    preview_url: str,
    sender_name: str = "LandingSmith",
) -> str:
    return (
        f"Kurze Erinnerung: Ihr kostenloser Website-Entwurf fuer "
        f"{lead.business_name} ist noch online: {preview_url} "
        f"- Fragen? james@amplivo.net oder einfach antworten. {sender_name}"
    )
