from typing import Literal

from pydantic import BaseModel, Field


ClaySeniority = Literal[
    "founder",
    "owner",
    "board-member",
    "partner",
    "c_suite",
    "vp",
    "director",
    "head",
    "manager",
    "senior",
    "mid-level",
    "entry",
    "intern",
    "unknown",
]


class ClayPeopleSearchRequest(BaseModel):
    target: str | None = Field(
        default=None,
        description=(
            "Keyword describing the type of company or business "
            "to search for."
        ),
    )

    country: str | None = Field(
        default=None,
        description="Country where the person is located.",
    )

    decision_maker: str | None = Field(
        default=None,
        description=(
            "Decision maker job title, e.g. CEO, CTO, "
            "Founder, Director."
        ),
    )

    industry: str | None = Field(
        default=None,
        description="Company industry.",
    )

    seniority: ClaySeniority | None = Field(
        default=None,
        description="Person's job-title seniority.",
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number.",
    )

    per_page: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results per page.",
    )