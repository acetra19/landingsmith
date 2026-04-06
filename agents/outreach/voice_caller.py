"""
Retell AI voice call initiator.
Creates outbound phone calls via the Retell API for leads
that have a phone number but no email address.
"""

import logging
from dataclasses import dataclass

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

RETELL_API_URL = "https://api.retell.ai/v2/create-phone-call"


@dataclass
class VoiceCallResult:
    success: bool
    call_id: str = ""
    error: str = ""


class VoiceCaller:
    def __init__(self):
        self.api_key = settings.retell.api_key
        self.agent_id = settings.retell.agent_id
        self.from_number = settings.retell.from_number
        self._client = httpx.AsyncClient(
            timeout=30,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.agent_id and self.from_number)

    async def call(self, to_number: str) -> VoiceCallResult:
        if not self.is_configured:
            return VoiceCallResult(
                success=False,
                error="Retell not configured (missing api_key, agent_id, or from_number)",
            )

        if not to_number:
            return VoiceCallResult(success=False, error="No phone number")

        to_number = self._normalize_de(to_number)

        try:
            payload = {
                "from_number": self.from_number,
                "to_number": to_number,
                "agent_id": self.agent_id,
            }
            resp = await self._client.post(RETELL_API_URL, json=payload)

            if resp.status_code in (200, 201):
                data = resp.json()
                call_id = data.get("call_id", "")
                logger.info(f"Voice call initiated to {to_number}: {call_id}")
                return VoiceCallResult(success=True, call_id=call_id)
            else:
                error_msg = resp.text
                logger.error(f"Retell API error ({resp.status_code}): {error_msg}")
                return VoiceCallResult(success=False, error=error_msg)

        except Exception as e:
            logger.error(f"Voice call failed to {to_number}: {e}")
            return VoiceCallResult(success=False, error=str(e))

    @staticmethod
    def _normalize_de(phone: str) -> str:
        cleaned = phone.replace(" ", "").replace("-", "").replace("/", "")
        if cleaned.startswith("0049"):
            cleaned = "+49" + cleaned[4:]
        elif cleaned.startswith("0") and not cleaned.startswith("+"):
            cleaned = "+49" + cleaned[1:]
        elif not cleaned.startswith("+"):
            cleaned = "+49" + cleaned
        return cleaned

    async def close(self):
        await self._client.aclose()
