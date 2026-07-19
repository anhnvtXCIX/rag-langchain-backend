from pathlib import Path

import pytest

from app.rag.errors import TextExtractionError
from app.rag.extraction import extract_text


def test_extract_text_reads_txt_file(tmp_path: Path):
    path = tmp_path / "note.txt"
    path.write_text("hello world", encoding="utf-8")

    assert extract_text(path) == "hello world"


def test_extract_text_reads_md_file(tmp_path: Path):
    path = tmp_path / "note.md"
    path.write_text("# Heading\n\nBody text.", encoding="utf-8")

    assert extract_text(path) == "# Heading\n\nBody text."


def test_extract_text_raises_on_unsupported_extension(tmp_path: Path):
    path = tmp_path / "note.csv"
    path.write_text("a,b,c", encoding="utf-8")

    with pytest.raises(TextExtractionError):
        extract_text(path)


def test_extract_text_raises_on_blank_content(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_text("   \n  ", encoding="utf-8")

    with pytest.raises(TextExtractionError):
        extract_text(path)
