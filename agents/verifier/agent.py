"""
Verifier Agent: Validates that leads truly have no website,
finds contact information, and marks invalid leads as rejected.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from agents.verifier.website_checker import deep_website_check
from agents.verifier.contact_finder import find_contact_info, validate_phone_de
from database.models import Lead, RejectionReason

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    is_valid: bool
    rejection_reason: Optional[RejectionReason] = None
    details: str = ""


class VerifierAgent(BaseAgent):
    def __init__(self):
        super().__init__("verifier")

    async def execute(
        self, lead: Lead = None, session: Session = None, **kwargs
    ) -> VerificationResult:
        if not lead:
            raise ValueError("Lead is required for verification")

        self.logger.info(f"Verifying lead: {lead.business_name} ({lead.place_id})")

        website_result = await deep_website_check(
            business_name=lead.business_name,
            city=lead.city or "",
            known_url=lead.existing_website or "",
        )

        if website_result.has_website:
            lead.existing_website = website_result.url_found
            if session:
                session.commit()
            return VerificationResult(
                is_valid=False,
                rejection_reason=RejectionReason.HAS_WEBSITE,
                details=f"Website found: {website_result.url_found} "
                        f"(via {website_result.check_method})",
            )

        contact = await find_contact_info(
            business_name=lead.business_name,
            phone=lead.phone or "",
            city=lead.city or "",
        )

        if contact.email:
            lead.email = contact.email
        if contact.phone and not lead.phone:
            lead.phone = contact.phone

        has_valid_phone = validate_phone_de(lead.phone or "")
        has_email = bool(lead.email)

        if not has_valid_phone and not has_email:
            if session:
                session.commit()
            return VerificationResult(
                is_valid=False,
                rejection_reason=RejectionReason.NO_CONTACT_INFO,
                details="No valid email or phone number found",
            )

        if session:
            session.commit()

        self.logger.info(
            f"Lead verified: {lead.business_name} "
            f"(email={has_email}, phone={has_valid_phone})"
        )
        return VerificationResult(is_valid=True)
