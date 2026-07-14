from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.message import Message
from app.rag.errors import LLMNotConfiguredError
from app.schemas.chat import (
    ChatTurnResponse,
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


def _message_to_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        sources=message.sources,
        created_at=message.created_at,
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
    return [_message_to_response(message) for message in messages]


@router.post("/sessions/{session_id}/messages", response_model=ChatTurnResponse)
async def send_session_message(
    session_id: int,
    payload: SendMessageRequest,
    current_user: CurrentUserDep,
    db: DbSessionDep,
) -> ChatTurnResponse:
    try:
        user_message, assistant_message = await ChatService(db).send_message(
            session_id=session_id,
            user_id=current_user.id,
            content=payload.content,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from exc
    except LLMNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not configured",
        ) from exc

    return ChatTurnResponse(
        user_message=_message_to_response(user_message),
        assistant_message=_message_to_response(assistant_message),
    )
