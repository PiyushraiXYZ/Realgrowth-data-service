import httpx

from app.config.settings import settings

class ApolloClient:
    BASE_URL = "https://api.apollo.io"

    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "x-api-key": settings.apollo_api_key,
        }

    async def search_people(self, payload: dict) -> dict:
        url = f"{self.BASE_URL}/api/v1/mixed_people/api_search"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Apollo API error {response.status_code}: {response.text}"
            )

        return response.json()

    async def bulk_enrich_people(
        self,
        person_ids: list[str],
        reveal_personal_emails: bool = False,
        reveal_phone_number: bool = False,
    ) -> dict:

        url = f"{self.BASE_URL}/api/v1/people/bulk_match"

        payload = {
            "details": [
                {
                    "id": person_id,
                }
                for person_id in person_ids
            ]
        }

        params = {
            "reveal_personal_emails": str(
                reveal_personal_emails
            ).lower(),
            "reveal_phone_number": str(
                reveal_phone_number
            ).lower(),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=self.headers,
                params=params,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Apollo enrichment error "
                f"{response.status_code}: {response.text}"
            )

        return response.json()