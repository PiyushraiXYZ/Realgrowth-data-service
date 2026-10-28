from pydantic import BaseModel, Field


class GoogleMapsCompanySearchRequest(BaseModel):
    company: str | None = Field(
        default=None,
        description="Company name, company keyword, or business category.",
    )

    country: str | None = Field(
        default=None,
        description="Country where the company is located.",
    )

    city: str | None = Field(
        default=None,
        description="City where the company is located.",
    )

    industry: str | None = Field(
        default=None,
        description="Industry or business category.",
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number.",
    )

    per_page: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of companies to return.",
    )