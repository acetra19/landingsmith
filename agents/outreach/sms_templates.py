"""
SMS templates for outreach. All in German.
Kept short to fit SMS limits (~160 chars per segment).
Includes cold outreach and warm voice-call follow-ups.
"""

from database.models import Lead


def initial_sms(
    lead: Lead,
    preview_url: str,
    sender_name: str = "James von Amplivo.net",
) -> str:
    return (
        f"Guten Tag! Wir haben einen Website-Entwurf fuer "
        f"{lead.business_name} erstellt: {preview_url} "
        f"- Fertige Website ab 99EUR einmalig. "
        f"Interesse? james@amplivo.net. "
        f"LG James, Amplivo.net"
    )


def follow_up_sms(
    lead: Lead,
    preview_url: str,
    sender_name: str = "James von Amplivo.net",
) -> str:
    return (
        f"Kurze Erinnerung: Ihr Website-Entwurf fuer "
        f"{lead.business_name} ist noch online: {preview_url} "
        f"- Ab 99EUR fertig mit eigener Domain. "
        f"Fragen? james@amplivo.net. "
        f"LG James, Amplivo.net"
    )


def voice_followup_sms(
    lead: Lead,
    preview_url: str,
) -> str:
    """Short SMS sent after a phone call where the lead requested the preview."""
    return (
        f"Wie besprochen, hier Ihr Website-Entwurf fuer "
        f"{lead.business_name}: {preview_url} "
        f"- Fragen? james@amplivo.net. "
        f"LG James, Amplivo.net"
    )
