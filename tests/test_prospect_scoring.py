import httpx
import pytest

from app.clients.nestjs_client import NestJSClient
from app.config.settings import settings
from app.services.prospect_scoring import ProspectScoringService
from app.schemas.clay import ClayPeopleSearchRequest


@pytest.mark.anyio
async def test_nestjs_client_accepts_created_response_and_keeps_key_server_side():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/prospects/abc123/recalculate-score")
        assert request.headers["x-internal-api-key"] == settings.prospect_processing_api_key
        return httpx.Response(201, json={"success": True, "overallScore": 81}, request=request)

    client = NestJSClient(transport=httpx.MockTransport(handler))
    assert await client.recalculate_score("abc123") == {"success": True, "overallScore": 81}


@pytest.mark.anyio
async def test_scores_created_and_updated_records_once_and_returns_existing_fields():
    class FakeClient:
        def __init__(self):
            self.calls = []

        async def recalculate_score(self, prospect_id: str) -> dict:
            self.calls.append(prospect_id)
            return {
                "success": True,
                "prospectId": prospect_id,
                "partnershipScore": 81,
                "decisionScore": 81,
                "overallScore": 81,
                "relationshipStage": "DISCOVERED",
                "pipelineStage": "DISCOVERED",
                "stage": "NEW",
            }

    client = FakeClient()
    service = ProspectScoringService(client=client)
    saved = [
        {"action": "created", "prospect_id": "abc123"},
        {"action": "updated", "prospect_id": "abc123"},
        {"action": "skipped", "prospect_id": "skip123"},
    ]

    result = await service.score_saved_prospects("clay", saved)

    assert client.calls == ["abc123"]
    assert result[0]["overallScore"] == 81
    assert result[1]["partnershipScore"] == 81
    assert result[2] == {"action": "skipped", "prospect_id": "skip123"}
    assert result[0]["scoring_status"] == "scored"


@pytest.mark.anyio
async def test_scoring_failure_is_nonfatal_and_does_not_return_remote_error_text(caplog):
    class FailingClient:
        async def recalculate_score(self, prospect_id: str) -> dict:
            raise RuntimeError("private response body")

    service = ProspectScoringService(client=FailingClient())
    saved = [{"action": "created", "prospect_id": "abc123"}]

    result = await service.score_saved_prospects("apollo", saved)

    assert result[0]["action"] == "created"
    assert result[0]["scoring_status"] == "failed"
    assert "private response body" not in caplog.text
    assert "prospect_id=abc123" in caplog.text


def test_clay_search_accepts_the_frontend_dynamic_filter_payload():
    filters = {"job_title_keywords": ["Founder"], "company_sizes": ["1-10"]}
    request = ClayPeopleSearchRequest(source_type="people", filters=filters, per_page=1)
    assert request.filters == filters
    assert request.source_type == "people"
