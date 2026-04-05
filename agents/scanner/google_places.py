"""
Google Places API client for discovering businesses.
Uses the Nearby Search and Place Details endpoints.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

BUSINESS_TYPES_WITHOUT_WEBSITES = [
    "bakery", "beauty_salon", "car_repair", "car_wash",
    "dentist", "electrician", "florist", "hair_care",
    "laundry", "locksmith", "painter", "plumber",
    "restaurant", "roofing_contractor", "veterinary_care",
    "general_contractor", "moving_company", "pet_store",
    "physiotherapist", "real_estate_agency", "travel_agency",
    "accounting", "lawyer", "insurance_agency",
]


@dataclass
class PlaceResult:
    place_id: str
    name: str
    address: str = ""
    city: str = ""
    postal_code: str = ""
    phone: str = ""
    website: Optional[str] = None
    latitude: float = 0.0
    longitude: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    business_type: str = ""
    business_hours: dict = field(default_factory=dict)
    photos: list[str] = field(default_factory=list)


class GooglePlacesClient:
    def __init__(self):
        self.api_key = settings.google.places_api_key
        self._client = httpx.AsyncClient(timeout=30)

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: int = None,
        business_type: str = None,
        keyword: str = None,
    ) -> list[PlaceResult]:
        radius = radius or settings.google.search_radius_meters
        params = {
            "location": f"{latitude},{longitude}",
            "radius": radius,
            "key": self.api_key,
        }
        if business_type:
            params["type"] = business_type
        if keyword:
            params["keyword"] = keyword

        results = []
        next_page_token = None

        for page in range(3):
            if page > 0 and next_page_token:
                params["pagetoken"] = next_page_token
                import asyncio
                await asyncio.sleep(2)

            resp = await self._client.get(PLACES_NEARBY_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                logger.error(f"Places API error: {data.get('status')} - {data.get('error_message', '')}")
                break

            for place in data.get("results", []):
                results.append(self._parse_basic(place))

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

        logger.info(f"Found {len(results)} places near ({latitude}, {longitude})")
        return results

    async def search_text(self, query: str, location: str = None) -> list[PlaceResult]:
        params = {
            "query": query,
            "key": self.api_key,
        }
        if location:
            params["query"] = f"{query} in {location}"

        results = []
        next_page_token = None

        for page in range(3):
            if page > 0 and next_page_token:
                params["pagetoken"] = next_page_token
                import asyncio
                await asyncio.sleep(2)

            resp = await self._client.get(PLACES_TEXT_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                logger.error(f"Places API error: {data.get('status')}")
                break

            for place in data.get("results", []):
                results.append(self._parse_basic(place))

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

        logger.info(f"Text search '{query}': {len(results)} results")
        return results

    async def get_details(self, place_id: str) -> PlaceResult:
        params = {
            "place_id": place_id,
            "fields": (
                "place_id,name,formatted_address,formatted_phone_number,"
                "website,geometry,rating,user_ratings_total,types,"
                "opening_hours,photos,address_components"
            ),
            "key": self.api_key,
        }
        resp = await self._client.get(PLACES_DETAILS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK":
            logger.error(f"Details API error for {place_id}: {data.get('status')}")
            return PlaceResult(place_id=place_id, name="Unknown")

        return self._parse_details(data["result"])

    def _parse_basic(self, data: dict) -> PlaceResult:
        location = data.get("geometry", {}).get("location", {})
        types = data.get("types", [])
        return PlaceResult(
            place_id=data.get("place_id", ""),
            name=data.get("name", ""),
            address=data.get("vicinity", data.get("formatted_address", "")),
            latitude=location.get("lat", 0),
            longitude=location.get("lng", 0),
            rating=data.get("rating", 0),
            review_count=data.get("user_ratings_total", 0),
            business_type=types[0] if types else "",
        )

    def _parse_details(self, data: dict) -> PlaceResult:
        location = data.get("geometry", {}).get("location", {})
        types = data.get("types", [])
        components = data.get("address_components", [])

        city = ""
        postal_code = ""
        for comp in components:
            if "locality" in comp.get("types", []):
                city = comp.get("long_name", "")
            if "postal_code" in comp.get("types", []):
                postal_code = comp.get("long_name", "")

        hours = {}
        if oh := data.get("opening_hours"):
            hours = {"weekday_text": oh.get("weekday_text", [])}

        photo_refs = []
        for photo in data.get("photos", [])[:3]:
            if ref := photo.get("photo_reference"):
                photo_refs.append(ref)

        return PlaceResult(
            place_id=data.get("place_id", ""),
            name=data.get("name", ""),
            address=data.get("formatted_address", ""),
            city=city,
            postal_code=postal_code,
            phone=data.get("formatted_phone_number", ""),
            website=data.get("website"),
            latitude=location.get("lat", 0),
            longitude=location.get("lng", 0),
            rating=data.get("rating", 0),
            review_count=data.get("user_ratings_total", 0),
            business_type=types[0] if types else "",
            business_hours=hours,
            photos=photo_refs,
        )

    async def close(self):
        await self._client.aclose()
