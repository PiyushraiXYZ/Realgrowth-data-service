from app.providers.google_maps.client import GoogleMapsClient
from app.repositories.prospect_repository import ProspectRepository
from app.services.prospect_mapper import google_maps_to_prospect


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
            search_parts.append(company.strip())

        if industry:
            search_parts.append(industry.strip())

        if city:
            search_parts.append(city.strip())

        if country:
            search_parts.append(country.strip())

        search_query = " ".join(search_parts)

        if not search_query:
            raise ValueError(
                "At least one search parameter is required."
            )

        payload = {
            "textQuery": search_query,
            "pageSize": per_page,
        }

        response = await self.client.search_places(payload)

        places = response.get("places", [])

        created = 0
        updated = 0
        skipped = 0
        saved = []

        for place in places:
            prospect = google_maps_to_prospect(place)

            if not prospect:
                skipped += 1
                continue

            result = await self.repository.upsert_prospect(
                prospect
            )

            action = result.get("action")

            if action == "created":
                created += 1
            elif action == "updated":
                updated += 1
            else:
                skipped += 1

            saved.append({
                "provider_id": prospect.get("providerId"),
                "name": prospect.get("name"),
                "company": prospect.get("company"),
                "action": action,
                "prospect_id": result.get("prospect_id"),
            })

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
