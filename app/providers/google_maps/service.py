from app.providers.google_maps.client import GoogleMapsClient


class GoogleMapsService:

    def __init__(self):
        self.client = GoogleMapsClient()

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

        # Google Places Text Search currently returns
        # the first page through this request.
        # pageToken can be added later for pagination.

        response = await self.client.search_places(payload)

        places = response.get("places", [])

        return {
            "provider": "google_maps",
            "page": page,
            "per_page": per_page,
            "total": len(places),
            "companies": places,
        }