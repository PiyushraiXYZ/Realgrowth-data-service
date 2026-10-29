import asyncio
import logging
from typing import Any

import httpx

from app.clients.nestjs_client import NestJSClient, NestJSScoringError

logger = logging.getLogger(__name__)
SCORE_FIELDS = (
    "partnershipScore", "decisionScore", "overallScore",
    "relationshipStage", "pipelineStage", "stage",
)


class ProspectScoringService:
    def __init__(self, client: NestJSClient | None = None):
        self.client = client or NestJSClient()
        self._semaphore = asyncio.Semaphore(4)

    async def score_saved_prospects(self, provider: str, saved: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prospect_ids = list(dict.fromkeys(
            str(item.get("prospect_id")) for item in saved
            if item.get("action") in {"created", "updated"} and item.get("prospect_id")
        ))
        if not prospect_ids:
            return saved
        results = await asyncio.gather(*(self._score_one(provider, prospect_id) for prospect_id in prospect_ids))
        by_id = dict(zip(prospect_ids, results, strict=True))
        for item in saved:
            prospect_id = str(item.get("prospect_id") or "")
            if prospect_id in by_id:
                item.update(by_id[prospect_id])
        return saved

    async def _score_one(self, provider: str, prospect_id: str) -> dict[str, Any]:
        async with self._semaphore:
            try:
                result = await self.client.recalculate_score(prospect_id)
                if not isinstance(result, dict) or result.get("success") is not True:
                    logger.warning("Prospect scoring failed | provider=%s | prospect_id=%s | status=invalid_response | error=unsuccessful_response", provider, prospect_id)
                    return self._failed_result()
                return {"scoring_status": "scored", **{field: result[field] for field in SCORE_FIELDS if field in result}}
            except Exception as error:
                status = error.status_code if isinstance(error, NestJSScoringError) else "unavailable"
                if isinstance(error, httpx.HTTPStatusError):
                    status = error.response.status_code
                logger.warning("Prospect scoring failed | provider=%s | prospect_id=%s | status=%s | error=%s", provider, prospect_id, status, type(error).__name__)
                return self._failed_result()

    @staticmethod
    def _failed_result() -> dict[str, str]:
        return {"scoring_status": "failed", "scoring_error": "Scoring could not be completed. Run the provider search again to retry."}
