from fastapi import APIRouter, HTTPException, status

from app.connection_tracking.service import ConnectionService
from app.connection_tracking.schemas import (
    CreateConnectionRequest,
    UpdateConnectionStatusRequest,
)

router = APIRouter(
    prefix="/api/v1/connections",
    tags=["Connection Tracking"],
)

connection_service = ConnectionService()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    request: CreateConnectionRequest,
):
    try:
        return await connection_service.create_connection(request)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/{connection_id}")
async def get_connection(connection_id: str):
    try:
        return await connection_service.get_connection(connection_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch("/{connection_id}/status")
async def update_connection_status(
    connection_id: str,
    request: UpdateConnectionStatusRequest,
):
    try:
        return await connection_service.update_connection_status(
            connection_id,
            request,
        )

    except ValueError as exc:
        message = str(exc)

        error_status = (
            status.HTTP_404_NOT_FOUND
            if message == "Connection not found"
            else status.HTTP_400_BAD_REQUEST
        )

        raise HTTPException(
            status_code=error_status,
            detail=message,
        )


@router.get("/prospect/{prospect_id}")
async def get_prospect_connections(prospect_id: str):
    return await connection_service.get_prospect_connections(
        prospect_id
    )