
from pydantic import BaseModel, Field


class ExtractedMessageResponse(BaseModel):
    sequence: int
    sender: str | None = None
    timestamp: str | None = None
    date: str | None = None
    text: str


class ConversationResponse(BaseModel):
    conversation_id: str
    status: str
    analysis_status: str
    extracted_text: list[ExtractedMessageResponse] = Field(
        default_factory=list
    )
    analysis_result: dict | None = None


class ConversationUploadResponse(BaseModel):
    conversation_id: str
    task_id: str
    status: str
    analysis_status: str
    message: str

