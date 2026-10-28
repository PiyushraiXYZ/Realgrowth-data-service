from typing import Literal

from pydantic import BaseModel, Field


ApolloSeniority = Literal[
    "owner",
    "founder",
    "c_suite",
    "partner",
    "vp",
    "head",
    "director",
    "manager",
    "senior",
    "entry",
    "intern",
]


class ApolloPeopleSearchRequest(BaseModel):
    target: str | None = Field(
        default=None,
        description="Company, business type, or keyword",
    )

    country: str | None = Field(
        default=None,
        description="Company headquarters country",
    )

    decision_maker: str | None = Field(
        default=None,
        description="Decision maker job title",
    )

    industry: str | None = Field(
        default=None,
        description="Exact Apollo industry name",
    )

    seniority: ApolloSeniority | None = Field(
        default=None,
        description="Apollo seniority level",
    )

    page: int = Field(
        default=1,
        ge=1,
    )

    per_page: int = Field(
        default=10,
        ge=1,
        le=100,
    )


class ApolloEnrichmentRequest(BaseModel):
    person_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Apollo person IDs to enrich. Maximum 10 per request.",
    )

    reveal_personal_emails: bool = Field(
        default=False,
        description="Whether to request personal emails.",
    )

    reveal_phone_number: bool = Field(
        default=False,
        description="Whether to request phone numbers. Apollo may require asynchronous delivery.",
    )