
import logging
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
from app.conversation_analysis.schemas import ConversationResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["Conversational Analysis"],
)

ImageUpload = Annotated[
    UploadFile,
    WithJsonSchema({
        "type": "string",
        "format": "binary",
    }),
]


@router.post(
    "/upload",
    response_model=ConversationResponse,
)
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
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        logger.exception("Screenshot upload endpoint failed.")

        raise HTTPException(
            status_code=500,
            detail="Screenshot upload failed. Please try again.",
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

    except Exception:
        logger.exception("Get conversations endpoint failed.")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve conversations.",
        )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation(conversation_id: str):
    try:
        return await conversation_service.get_conversation(
            conversation_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception:
        logger.exception(
            "Get conversation endpoint failed: %s",
            conversation_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve conversation.",
        )
