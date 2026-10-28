from fastapi import APIRouter, HTTPException

from app.providers.apollo.service import ApolloService
from app.schemas.apollo import (
    ApolloEnrichmentRequest,
    ApolloPeopleSearchRequest,
)

router = APIRouter(
    prefix="/api/v1/apollo",
    tags=["Apollo"],
)

apollo_service = ApolloService()

@router.post("/people/search")
async def search_people(
    request: ApolloPeopleSearchRequest,
):
    try:
        payload = {
            "page": request.page,
            "per_page": request.per_page,
        }

        if request.target:
            payload["q_keywords"] = request.target.strip()

        if request.country:
            payload["organization_locations"] = [
                request.country.strip()
            ]

        if request.decision_maker:
            payload["person_titles"] = [
                request.decision_maker.strip()
            ]

            payload["include_similar_titles"] = False

        if request.industry:
            payload["organization_industries"] = [
                request.industry.strip().lower()
            ]

        if request.seniority:
            payload["person_seniorities"] = [
                request.seniority
            ]

        return await apollo_service.search_people(
            payload
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Apollo request failed: {str(exc)}",
        )


@router.post("/people/enrich")
async def enrich_people(
    request: ApolloEnrichmentRequest,
):
    try:
        return await apollo_service.enrich_people(
            person_ids=request.person_ids,
            reveal_personal_emails=(
                request.reveal_personal_emails
            ),
            reveal_phone_number=(
                request.reveal_phone_number
            ),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Apollo enrichment failed: {str(exc)}",
        )