import httpx

from app.config.settings import settings


class ClayClient:
    BASE_URL = "https://api.clay.com/public/v0"

    def __init__(self):
        self.api_key = settings.clay_api_key

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_search_fields(
        self,
        source_type: str = "people",
    ) -> dict:
        """
        Get Clay search filter fields.
        """

        url = f"{self.BASE_URL}/search/filters-mode/fields"

        params = {
            "source_type": source_type,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url=url,
                headers=self.headers,
                params=params,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Clay fields error "
                f"{response.status_code}: {response.text}"
            )

        return response.json()

    async def create_people_search(
        self,
        payload: dict,
    ) -> dict:
        """
        Create a Clay people search.
        """

        url = f"{self.BASE_URL}/search/filters-mode"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url=url,
                headers=self.headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Clay create search error "
                f"{response.status_code}: {response.text}"
            )

        return response.json()

    async def run_people_search(
        self,
        search_id: str,
        payload: dict,
    ) -> dict:
        """
        Run a previously created Clay people search.
        """

        url = (
            f"{self.BASE_URL}/search/filters-mode/"
            f"{search_id}/run"
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url=url,
                headers=self.headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Clay run search error "
                f"{response.status_code}: {response.text}"
            )

        return response.json()