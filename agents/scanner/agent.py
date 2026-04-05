"""
Scanner Agent: Discovers businesses via Google Places API,
filters for those without websites, and stores them as leads.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from agents.scanner.google_places import GooglePlacesClient, BUSINESS_TYPES_WITHOUT_WEBSITES
from config.settings import settings
from database.connection import get_session
from database.models import Lead, LeadStatus

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class ScannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("scanner")
        self.places = GooglePlacesClient()

    async def execute(
        self,
        location: str = "",
        query: str = "",
        radius: Optional[int] = None,
        business_types: Optional[list[str]] = None,
        **kwargs,
    ) -> list[Lead]:
        lat, lng = await self._geocode(location)
        if lat == 0 and lng == 0:
            self.logger.error(f"Could not geocode location: {location}")
            return []

        types_to_scan = business_types or BUSINESS_TYPES_WITHOUT_WEBSITES
        all_places = []

        for btype in types_to_scan:
            search_query = f"{query} {btype}".strip() if query else btype
            places = await self.places.search_nearby(
                latitude=lat,
                longitude=lng,
                radius=radius,
                business_type=btype,
                keyword=query or None,
            )
            all_places.extend(places)
            self.logger.info(f"Scanned type '{btype}': {len(places)} results")

        unique_places = {p.place_id: p for p in all_places}
        self.logger.info(
            f"Total unique places found: {len(unique_places)} "
            f"(from {len(all_places)} raw results)"
        )

        enriched = []
        for place in unique_places.values():
            details = await self.places.get_details(place.place_id)
            enriched.append(details)

        no_website = [p for p in enriched if not p.website]
        self.logger.info(
            f"Places without website: {no_website.__len__()} / {len(enriched)}"
        )

        leads = self._store_leads(no_website, query, location)
        return leads

    def _store_leads(self, places, query: str, location: str) -> list[Lead]:
        session: Session = get_session()
        leads = []
        try:
            for place in places:
                existing = (
                    session.query(Lead)
                    .filter(Lead.place_id == place.place_id)
                    .first()
                )
                if existing:
                    self.logger.debug(f"Duplicate skipped: {place.name}")
                    continue

                lead = Lead(
                    place_id=place.place_id,
                    business_name=place.name,
                    business_type=place.business_type,
                    address=place.address,
                    city=place.city,
                    postal_code=place.postal_code,
                    country="DE",
                    phone=place.phone,
                    existing_website=place.website,
                    latitude=place.latitude,
                    longitude=place.longitude,
                    rating=place.rating,
                    review_count=place.review_count,
                    business_hours=place.business_hours,
                    photos_urls=place.photos,
                    status=LeadStatus.DISCOVERED,
                    scan_source="google_places",
                    scan_query=query,
                    scan_location=location,
                )
                session.add(lead)
                leads.append(lead)

            session.commit()
            self.logger.info(f"Stored {len(leads)} new leads")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        return leads

    async def _geocode(self, location: str) -> tuple[float, float]:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GEOCODE_URL,
                params={"address": location, "key": settings.google.places_api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return 0.0, 0.0

        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]

    async def close(self):
        await self.places.close()
