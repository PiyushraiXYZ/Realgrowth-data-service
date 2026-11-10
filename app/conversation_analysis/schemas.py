from datetime import datetime
from pydantic import BaseModel, Field


class ScreenshotResponse(BaseModel):
    public_id: str
    image_url: str
    format: str | None = None
    width: int | None = None
    height: int | None = None
    bytes: int | None = None


class ConversationUploadResponse(BaseModel):
    conversation_id: str
    prospect_id: str
    screenshots: list[ScreenshotResponse]
    status: str
    created_at: datetime