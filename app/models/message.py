from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Text,
    desc,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index(
            "ix_messages_session_id_created_at_desc",
            "session_id",
            desc("created_at"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
