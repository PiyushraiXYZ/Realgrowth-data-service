from fastapi import APIRouter, HTTPException

from app.providers.clay.service import ClayService
from app.schemas.clay import ClayPeopleSearchRequest


router = APIRouter(
    prefix="/api/v1/clay",
    tags=["Clay"],
)

clay_service = ClayService()

@router.get("/people/search/fields")
async def get_search_fields():
    """
    Get Clay people-search filter fields.
    """

    try:
        return await clay_service.get_search_fields()

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Clay fields request failed: {str(exc)}",
        )

@router.post("/people/search")
async def search_people(
    request: ClayPeopleSearchRequest,
):
    """
    Search people through Clay.
    """

    try:
        response = await clay_service.search_people(
            target=request.target,
            country=request.country,
            decision_maker=request.decision_maker,
            industry=request.industry,
            seniority=request.seniority,
            page=request.page,
            per_page=request.per_page,
        )

        return response

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Clay request failed: {str(exc)}",
        )