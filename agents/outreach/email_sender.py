"""
Email delivery via Resend API.
Handles sending, tracking, and rate limiting.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


@dataclass
class SendResult:
    success: bool
    message_id: str = ""
    error: str = ""


class EmailSender:
    def __init__(self):
        self.api_key = settings.email.resend_api_key
        self.from_email = settings.email.from_email
        self.from_name = settings.email.from_name
        self._client = httpx.AsyncClient(
            timeout=30,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        self._sent_today = 0

    async def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
    ) -> SendResult:
        if self._sent_today >= settings.pipeline.outreach_daily_limit:
            logger.warning("Daily email limit reached")
            return SendResult(success=False, error="Daily limit reached")

        payload = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        if reply_to:
            payload["reply_to"] = reply_to

        try:
            resp = await self._client.post(RESEND_API_URL, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                self._sent_today += 1
                logger.info(f"Email sent to {to_email}: {data.get('id', '')}")
                return SendResult(
                    success=True,
                    message_id=data.get("id", ""),
                )
            else:
                error_msg = resp.text
                logger.error(f"Resend API error ({resp.status_code}): {error_msg}")
                return SendResult(success=False, error=error_msg)

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return SendResult(success=False, error=str(e))

    @property
    def remaining_today(self) -> int:
        return max(0, settings.pipeline.outreach_daily_limit - self._sent_today)

    async def close(self):
        await self._client.aclose()
