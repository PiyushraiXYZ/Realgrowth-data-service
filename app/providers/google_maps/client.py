import httpx

from app.config.settings import settings


class GoogleMapsClient:
    BASE_URL = "https://places.googleapis.com/v1"

    def __init__(self):
        self.api_key = settings.google_maps_api_key

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,"
                "places.displayName,"
                "places.formattedAddress,"
                "places.location,"
                "places.primaryType,"
                "places.types,"
                "places.websiteUri,"
                "places.nationalPhoneNumber,"
                "places.internationalPhoneNumber,"
                "places.rating,"
                "places.userRatingCount,"
                "places.googleMapsUri"
            ),
        }

    async def search_places(self, payload: dict) -> dict:
        url = f"{self.BASE_URL}/places:searchText"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url=url,
                headers=self.headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Google Maps API error "
                f"{response.status_code}: {response.text}"
            )

        return response.json()