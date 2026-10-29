import httpx

from app.config.settings import settings



class NestJSScoringError(RuntimeError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"NestJS scoring failed with HTTP {status_code}.")


class NestJSClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport
        self.base_url = settings.nestjs_base_url.rstrip("/")
        self.api_key = settings.prospect_processing_api_key

    async def recalculate_score(self, prospect_id: str) -> dict:
        url = (
            f"{self.base_url}"
            f"/prospects/{prospect_id}/recalculate-score"
        )

        headers = {
            "x-internal-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0, transport=self.transport) as client:
            response = await client.post(
                url,
                headers=headers,
            )

        if response.status_code >= 400:
            raise NestJSScoringError(response.status_code)

        return response.json()