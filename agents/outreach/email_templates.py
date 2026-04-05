"""
Email templates for cold outreach. All in German.
Each template returns (subject, body_html) tuples.
"""

from database.models import Lead, DomainSuggestion


def initial_outreach(
    lead: Lead,
    preview_url: str,
    domain_suggestions: list[DomainSuggestion],
    sender_name: str = "WebReach",
) -> tuple[str, str]:
    domains_html = ""
    if domain_suggestions:
        domain_list = "".join(
            f"<li><strong>{d.domain_name}{d.tld}</strong>"
            f"{'  ✓ Empfohlen' if d.is_recommended else ''}</li>"
            for d in domain_suggestions[:3]
        )
        domains_html = f"""
        <p>Passende Domain-Vorschläge für Sie:</p>
        <ul>{domain_list}</ul>
        """

    subject = f"Webseite für {lead.business_name} – kostenloser Entwurf"

    body = f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width: 600px; color: #333; line-height: 1.6;">
        <p>Guten Tag,</p>

        <p>mein Name ist {sender_name}. Ich bin auf <strong>{lead.business_name}</strong>
        aufmerksam geworden und mir ist aufgefallen, dass Sie aktuell
        keine eigene Webseite haben.</p>

        <p>Gerade für lokale Unternehmen wie Ihres ist eine professionelle
        Online-Präsenz heute entscheidend – viele Kunden suchen zuerst
        im Internet, bevor sie sich für einen Anbieter entscheiden.</p>

        <p>Deshalb habe ich mir erlaubt, <strong>unverbindlich einen
        Entwurf für Sie zu erstellen</strong>:</p>

        <p style="text-align: center; margin: 24px 0;">
            <a href="{preview_url}"
               style="background: #2563eb; color: white; padding: 12px 28px;
                      border-radius: 8px; text-decoration: none; font-weight: 600;">
                Ihren Website-Entwurf ansehen
            </a>
        </p>

        {domains_html}

        <p>Falls Ihnen der Entwurf gefällt, können wir die Seite
        innerhalb weniger Tage unter Ihrer eigenen Domain live schalten –
        natürlich passe ich alles nach Ihren Wünschen an.</p>

        <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px">
            <tr style="background:#f8fafc">
                <td style="padding:12px 16px;border:1px solid #e5e7eb"><strong>Website (einmalig)</strong><br>
                    <span style="color:#64748b;font-size:13px">Design, Texte, Anpassungen nach Ihren Wünschen</span></td>
                <td style="padding:12px 16px;border:1px solid #e5e7eb;text-align:right;white-space:nowrap"><strong>99 €</strong></td>
            </tr>
            <tr>
                <td style="padding:12px 16px;border:1px solid #e5e7eb"><strong>Eigene Domain</strong><br>
                    <span style="color:#64748b;font-size:13px">z.B. www.ihr-firmenname.de</span></td>
                <td style="padding:12px 16px;border:1px solid #e5e7eb;text-align:right;white-space:nowrap"><strong>ab 15 €/Jahr</strong></td>
            </tr>
            <tr style="background:#f8fafc">
                <td style="padding:12px 16px;border:1px solid #e5e7eb"><strong>Wartung & Updates</strong><br>
                    <span style="color:#64748b;font-size:13px">Hosting, Pflege, maßgeschneiderte Änderungen</span></td>
                <td style="padding:12px 16px;border:1px solid #e5e7eb;text-align:right;white-space:nowrap"><strong>10 €/Jahr</strong></td>
            </tr>
        </table>

        <p>Haben Sie Interesse oder Fragen? Antworten Sie einfach
        auf diese E-Mail oder rufen Sie mich an.</p>

        <p>Beste Grüße<br>
        <strong>{sender_name}</strong></p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="font-size: 12px; color: #999;">
            Sie erhalten diese E-Mail, weil Ihr Unternehmen öffentlich auf
            Google Maps gelistet ist. Falls Sie keine weiteren Nachrichten
            wünschen, antworten Sie mit "Abbestellen".
        </p>
    </div>
    """
    return subject, body


def follow_up_1(
    lead: Lead, preview_url: str, sender_name: str = "WebReach"
) -> tuple[str, str]:
    subject = f"Re: Webseite für {lead.business_name} – kurze Nachfrage"

    body = f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width: 600px; color: #333; line-height: 1.6;">
        <p>Guten Tag,</p>

        <p>ich wollte kurz nachfragen, ob Sie die Möglichkeit hatten,
        sich den Website-Entwurf für <strong>{lead.business_name}</strong>
        anzuschauen:</p>

        <p style="text-align: center; margin: 24px 0;">
            <a href="{preview_url}"
               style="background: #2563eb; color: white; padding: 12px 28px;
                      border-radius: 8px; text-decoration: none; font-weight: 600;">
                Entwurf ansehen
            </a>
        </p>

        <p>Der Entwurf bleibt noch einige Tage online verfügbar.
        Zur Erinnerung: Eine fertige Website mit eigener Domain
        gibt es bei uns schon <strong>ab einmalig 99 €</strong>.</p>

        <p>Falls Sie Fragen haben oder Anpassungen wünschen,
        stehe ich gerne zur Verfügung.</p>

        <p>Beste Grüße<br>
        <strong>{sender_name}</strong></p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="font-size: 12px; color: #999;">
            Kein Interesse? Antworten Sie mit "Abbestellen".
        </p>
    </div>
    """
    return subject, body


def follow_up_2(
    lead: Lead, preview_url: str, sender_name: str = "WebReach"
) -> tuple[str, str]:
    subject = f"Letzte Nachricht: Webseite für {lead.business_name}"

    body = f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width: 600px; color: #333; line-height: 1.6;">
        <p>Guten Tag,</p>

        <p>dies ist meine letzte Nachricht bezüglich des
        Website-Entwurfs für <strong>{lead.business_name}</strong>.</p>

        <p>Der Entwurf wird in Kürze offline genommen. Falls Sie
        doch noch Interesse haben, können Sie ihn hier ansehen:</p>

        <p style="text-align: center; margin: 24px 0;">
            <a href="{preview_url}"
               style="background: #2563eb; color: white; padding: 12px 28px;
                      border-radius: 8px; text-decoration: none; font-weight: 600;">
                Letzter Blick auf Ihren Entwurf
            </a>
        </p>

        <p>Ich wünsche Ihnen weiterhin viel Erfolg!</p>

        <p>Beste Grüße<br>
        <strong>{sender_name}</strong></p>
    </div>
    """
    return subject, body
