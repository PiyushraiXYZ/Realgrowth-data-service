from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.connection_tracking.enums import (
    ConnectionStatus,
    ConnectionPlatform,
    ConnectionEventSource,
)

class CreateConnectionRequest(BaseModel):
    prospect_id: str = Field(..., min_length=1)
    platform: ConnectionPlatform
    status: ConnectionStatus = ConnectionStatus.INITIATED
    event_id: str = Field(..., min_length=1)
    source: ConnectionEventSource = ConnectionEventSource.BROWSER_EXTENSION


class UpdateConnectionStatusRequest(BaseModel):
    status: ConnectionStatus
    event_id: str = Field(..., min_length=1)
    source: ConnectionEventSource = ConnectionEventSource.BROWSER_EXTENSION
    occurred_at: datetime | None = None
    notes: str | None = None

class ConnectionHistoryResponse(BaseModel):
    status: ConnectionStatus
    event_id: str
    source: ConnectionEventSource
    timestamp: datetime
    notes: str | None = None


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connection_id: str
    prospect_id: str
    platform: ConnectionPlatform
    current_status: ConnectionStatus
    history: list[ConnectionHistoryResponse] = []
    created_at: datetime
    updated_at: datetime
