from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, DbSessionDep
from app.schemas.chat import (
    CreateSessionRequest,
    MessageResponse,
    SendMessageRequest,
    SessionResponse,
)
from app.services.chat_service import ChatService, SessionNotFoundError

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    payload: CreateSessionRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> SessionResponse:
    session = await ChatService(db).create_session(
        user_id=current_user.id,
        title=payload.title,
    )
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[SessionResponse]:
    sessions = await ChatService(db).list_sessions(user_id=current_user.id)
    return [
        SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_session_messages(
    session_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[MessageResponse]:
    try:
        messages = await ChatService(db).list_messages(
            session_id=session_id,
            user_id=current_user.id,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from exc
    return [
        MessageResponse(
            id=message.id,
            role=message.role.value,
            content=message.content,
            sources=message.sources,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_session_message(
    session_id: int,
    payload: SendMessageRequest,
    current_user: CurrentUserDep,
    db: DbSessionDep,
) -> MessageResponse:
    try:
        message = await ChatService(db).create_user_message(
            session_id=session_id,
            user_id=current_user.id,
            content=payload.content,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from exc

    return MessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        sources=message.sources,
        created_at=message.created_at,
    )
