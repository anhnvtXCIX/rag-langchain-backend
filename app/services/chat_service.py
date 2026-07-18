from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.chat_session import ChatSession
from app.models.message import Message, MessageRole
from app.rag.generation import generate_answer, get_chat_model
from app.rag.vector_store import get_embeddings, search_chunks

HISTORY_LIMIT = 10
SOURCE_SNIPPET_LENGTH = 200


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

    async def send_message(
        self,
        session_id: int,
        user_id: int,
        content: str,
    ) -> tuple[Message, Message]:
        await self._get_owned_session(session_id=session_id, user_id=user_id)

        # Fail fast on missing LLM config before persisting anything, so a
        # 503 does not leave an orphan user message behind.
        get_chat_model()
        get_embeddings()

        # Fetched before inserting the new user message so the question is
        # not duplicated in the history.
        history = await self._get_recent_messages(session_id)

        user_message = Message(
            session_id=session_id, role=MessageRole.user, content=content
        )
        self.db.add(user_message)
        await self.db.commit()
        await self.db.refresh(user_message)

        # If retrieval or generation fails past this point, the user message
        # stays persisted (visible in history, retryable) and the error
        # propagates to the router.
        chunks = await search_chunks(
            content, user_id=user_id, k=get_settings().rag_top_k
        )
        answer = await generate_answer(content, chunks, history)

        sources = [
            {
                "document_id": chunk.metadata["document_id"],
                "filename": chunk.metadata.get("filename", "unknown"),
                "snippet": chunk.page_content[:SOURCE_SNIPPET_LENGTH],
            }
            for chunk in chunks
        ]
        assistant_message = Message(
            session_id=session_id,
            role=MessageRole.assistant,
            content=answer,
            sources=sources or None,
        )
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)

        return user_message, assistant_message

    async def _get_recent_messages(self, session_id: int) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
        return list(reversed(result.scalars().all()))

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
