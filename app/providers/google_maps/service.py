import logging

from app.providers.google_maps.client import GoogleMapsClient
from app.repositories.prospect_repository import ProspectRepository
from app.services.prospect_mapper import google_maps_to_prospect


logger = logging.getLogger(__name__)


class GoogleMapsService:

    def __init__(self):
        self.client = GoogleMapsClient()
        self.repository = ProspectRepository()

    async def search_companies(
        self,
        company: str | None = None,
        country: str | None = None,
        city: str | None = None,
        industry: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict:

        search_parts = []

        if company:
            search_parts.append(
                company.strip()
            )

        if industry:
            search_parts.append(
                industry.strip()
            )

        if city:
            search_parts.append(
                city.strip()
            )

        if country:
            search_parts.append(
                country.strip()
            )

        search_query = " ".join(
            search_parts
        )

        if not search_query:
            raise ValueError(
                "At least one search parameter is required."
            )

        payload = {
            "textQuery": search_query,
            "pageSize": per_page,
        }

        # -----------------------------------------------------
        # 1. Search Google Maps
        # -----------------------------------------------------

        response = await self.client.search_places(
            payload
        )

        places = response.get(
            "places",
            []
        )

        created = 0
        updated = 0
        skipped = 0
        saved = []

        # -----------------------------------------------------
        # 2. Normalize and save prospects
        # -----------------------------------------------------

        for place in places:

            prospect = google_maps_to_prospect(
                place
            )

            if not prospect:
                skipped += 1
                continue

            logger.info(
                "Saving Google Maps prospect | name=%s",
                prospect.get("name"),
            )

            # Repository handles:
            # 1. MongoDB insert/update
            # 2. RabbitMQ scoring job publishing

            result = await self.repository.upsert_prospect(
                prospect
            )

            action = result.get(
                "action"
            )

            if action == "created":
                created += 1

            elif action == "updated":
                updated += 1

            else:
                skipped += 1

            saved.append(
                {
                    "name": prospect.get(
                        "name"
                    ),

                    "title": prospect.get(
                        "title"
                    ),

                    "company": prospect.get(
                        "company"
                    ),

                    "website": prospect.get(
                        "website"
                    ),

                    "industry": prospect.get(
                        "industry"
                    ),

                    "location": prospect.get(
                        "location"
                    ),

                    "phone": prospect.get(
                        "phone"
                    ),

                    "provider_id": prospect.get(
                        "providerId"
                    ),

                    "action": action,

                    "prospect_id": result.get(
                        "id"
                    ),
                }
            )

            logger.info(
                "Google Maps prospect saved | action=%s | prospect_id=%s",
                action,
                result.get("id"),
            )

        # IMPORTANT:
        # Do NOT call ProspectScoringService here.
        # RabbitMQ scoring is triggered by ProspectRepository.

        return {
            "provider": "google_maps",
            "page": page,
            "per_page": per_page,
            "total": len(places),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "saved": saved,
            "companies": places,
        }