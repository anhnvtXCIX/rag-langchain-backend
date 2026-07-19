from app.rag.chunking import CHUNK_SIZE, chunk_text


def test_chunk_text_carries_metadata_on_every_chunk():
    text = "word " * 500  # long enough to force multiple chunks
    chunks = chunk_text(text, user_id=1, document_id=42, filename="report.txt")

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.metadata == {
            "user_id": 1,
            "document_id": 42,
            "filename": "report.txt",
        }


def test_chunk_text_single_chunk_for_short_text():
    text = "A short document."
    chunks = chunk_text(text, user_id=1, document_id=1, filename="short.txt")

    assert len(chunks) == 1
    assert chunks[0].page_content == text


def test_chunk_text_more_chunks_for_longer_input():
    short_text = "word " * 50
    long_text = "word " * (CHUNK_SIZE * 5)

    short_chunks = chunk_text(short_text, user_id=1, document_id=1, filename="a.txt")
    long_chunks = chunk_text(long_text, user_id=1, document_id=1, filename="b.txt")

    assert len(long_chunks) > len(short_chunks)


def test_chunk_text_empty_string_returns_no_chunks():
    assert chunk_text("", user_id=1, document_id=1, filename="empty.txt") == []
