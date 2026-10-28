from fastapi import APIRouter, HTTPException

from app.providers.google_maps.service import GoogleMapsService
from app.schemas.google_maps import GoogleMapsCompanySearchRequest
from app.services.normalization import normalize_google_places


router = APIRouter(
    prefix="/api/v1/google-maps",
    tags=["Google Maps"],
)

google_maps_service = GoogleMapsService()


@router.post("/companies/search")
async def search_companies(
    request: GoogleMapsCompanySearchRequest,
):
    try:
        response = await google_maps_service.search_companies(
            company=request.company,
            country=request.country,
            city=request.city,
            industry=request.industry,
            page=request.page,
            per_page=request.per_page,
        )

        companies = normalize_google_places(
         response.get("companies", [])
         )



        return {
            "provider": "google_maps",
            "page": response["page"],
            "per_page": response["per_page"],
            "total": len(companies),
            "companies": companies,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Google Maps company search failed: {str(exc)}",
        )