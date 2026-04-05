"""
SMS sender using Twilio.
Sends short, personalized messages to businesses with a preview link.
"""

import logging
from dataclasses import dataclass

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class SMSResult:
    success: bool
    message_sid: str = ""
    error: str = ""


class SMSSender:
    def __init__(self):
        self.client = Client(
            settings.twilio.account_sid,
            settings.twilio.auth_token,
        )
        self.from_number = settings.twilio.from_number

    async def send(self, to_number: str, body: str) -> SMSResult:
        if not to_number:
            return SMSResult(success=False, error="No phone number")

        to_number = self._normalize_de(to_number)

        if not self._is_mobile(to_number):
            return SMSResult(
                success=False,
                error=f"Landline number {to_number}, SMS not possible",
            )

        try:
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_number,
            )
            logger.info(f"SMS sent to {to_number}: {message.sid}")
            return SMSResult(success=True, message_sid=message.sid)
        except TwilioRestException as e:
            logger.error(f"SMS failed to {to_number}: {e.msg}")
            return SMSResult(success=False, error=e.msg)
        except Exception as e:
            logger.error(f"SMS failed to {to_number}: {e}")
            return SMSResult(success=False, error=str(e))

    @staticmethod
    def _is_mobile(e164_number: str) -> bool:
        """German mobile prefixes: +4915x, +4916x, +4917x."""
        mobile_prefixes = ("+4915", "+4916", "+4917")
        return e164_number.startswith(mobile_prefixes)

    @staticmethod
    def _normalize_de(phone: str) -> str:
        """Normalize German phone numbers to E.164 format (+49...)."""
        cleaned = phone.replace(" ", "").replace("-", "").replace("/", "")
        if cleaned.startswith("0049"):
            cleaned = "+49" + cleaned[4:]
        elif cleaned.startswith("0") and not cleaned.startswith("+"):
            cleaned = "+49" + cleaned[1:]
        elif not cleaned.startswith("+"):
            cleaned = "+49" + cleaned
        return cleaned
