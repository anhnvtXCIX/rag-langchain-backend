from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings
from app.models.message import Message, MessageRole
from app.rag.errors import LLMNotConfiguredError

SYSTEM_PROMPT_WITH_CONTEXT = """\
You are a helpful assistant answering questions about the user's documents.
Answer using the numbered context excerpts below. If the context does not
contain the answer, say so instead of guessing.

Context:
{context}"""

SYSTEM_PROMPT_NO_CONTEXT = """\
You are a helpful assistant. No excerpts from the user's documents matched
their question. Answer from general knowledge and mention that the answer
is not based on their documents."""


@lru_cache
def get_chat_model() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.google_api_key:
        raise LLMNotConfiguredError
    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.google_api_key,
    )


def _format_context(chunks: list[Document]) -> str:
    return "\n\n".join(
        f"[{index}] {chunk.metadata.get('filename', 'unknown')}:\n{chunk.page_content}"
        for index, chunk in enumerate(chunks, start=1)
    )


def _history_to_messages(history: list[Message]) -> list[BaseMessage]:
    return [
        HumanMessage(message.content)
        if message.role == MessageRole.user
        else AIMessage(message.content)
        for message in history
    ]


async def generate_answer(
    question: str,
    context_chunks: list[Document],
    history: list[Message],
) -> str:
    if context_chunks:
        system_prompt = SYSTEM_PROMPT_WITH_CONTEXT.format(
            context=_format_context(context_chunks)
        )
    else:
        system_prompt = SYSTEM_PROMPT_NO_CONTEXT

    response = await get_chat_model().ainvoke(
        [
            SystemMessage(system_prompt),
            *_history_to_messages(history),
            HumanMessage(question),
        ]
    )

    content = response.content
    if isinstance(content, list):
        content = "".join(part for part in content if isinstance(part, str))
    return content
