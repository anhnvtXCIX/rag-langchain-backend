from fastapi import APIRouter, HTTPException

from app.schemas.chat import (
    CreateSessionRequest,
    MessageResponse,
    SendMessageRequest,
    SessionResponse,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=SessionResponse)
async def create_session(payload: CreateSessionRequest) -> SessionResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions() -> list[SessionResponse]:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_session_messages(session_id: int) -> list[MessageResponse]:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_session_message(
    session_id: int, payload: SendMessageRequest
) -> MessageResponse:
    raise HTTPException(status_code=501, detail="Not implemented")
