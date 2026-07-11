from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatSession
from app.models.message import Message, MessageRole


class SessionNotFoundError(Exception):
    pass


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_session(self, user_id: int, title: str) -> ChatSession:
        session = ChatSession(title=title, user_id=user_id)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def list_sessions(self, user_id: int) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def list_messages(self, session_id: int, user_id: int) -> list[Message]:
        await self._get_owned_session(session_id=session_id, user_id=user_id)
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_user_message(
        self,
        session_id: int,
        user_id: int,
        content: str,
    ) -> Message:
        await self._get_owned_session(session_id=session_id, user_id=user_id)
        message = Message(session_id=session_id, role=MessageRole.user, content=content)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def _get_owned_session(self, session_id: int, user_id: int) -> ChatSession:
        session_result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        session = session_result.scalar_one_or_none()
        if session is None:
            raise SessionNotFoundError
        return session
