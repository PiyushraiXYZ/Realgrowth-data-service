
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import WithJsonSchema

from app.conversation_analysis.service import conversation_service


router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["Conversational Analysis"],
)


# Tell Swagger UI to render UploadFile as a binary file.
ImageUpload = Annotated[
    UploadFile,
    WithJsonSchema({
        "type": "string",
        "format": "binary",
    }),
]


@router.post("/upload")
async def upload_conversation_screenshots(
    prospect_id: Annotated[str, Form(...)],
    files: Annotated[
        list[ImageUpload],
        File(description="Upload multiple conversation screenshots"),
    ],
):
    try:
        return await conversation_service.upload_screenshots(
            prospect_id=prospect_id,
            files=files,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Screenshot upload failed: {str(exc)}",
        )



@router.get("/")
async def get_all_conversations(
    prospect_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    try:
        return await conversation_service.get_all_conversations(
            prospect_id=prospect_id,
            skip=skip,
            limit=limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )