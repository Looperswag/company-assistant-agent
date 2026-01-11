"""Tests for Markdown parser."""

import tempfile
from pathlib import Path

import pytest

from src.knowledge.parser import MarkdownParser


class TestMarkdownParser:
    """Test cases for MarkdownParser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = MarkdownParser(chunk_size=100, chunk_overlap=10)

    def test_parse_simple_file(self) -> None:
        """Test parsing a simple Markdown file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# Test Document\n\nThis is a test document with some content.")
            temp_path = Path(f.name)

        try:
            chunks = self.parser.parse_file(temp_path)
            assert len(chunks) > 0
            assert chunks[0][0]  # Text content exists
            assert "metadata" in chunks[0][1] or "source" in chunks[0][1]
        finally:
            temp_path.unlink()

    def test_parse_empty_file(self) -> None:
        """Test parsing an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            chunks = self.parser.parse_file(temp_path)
            # Empty file should return empty list or minimal chunks
            assert isinstance(chunks, list)
        finally:
            temp_path.unlink()

    def test_chunking(self) -> None:
        """Test text chunking functionality."""
        long_text = " ".join(["word"] * 200)  # Create long text
        chunks = self.parser._chunk_text(long_text, Path("test.md"), "Test")
        assert len(chunks) > 1  # Should be split into multiple chunks

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing a non-existent file."""
        nonexistent = Path("nonexistent_file.md")
        chunks = self.parser.parse_file(nonexistent)
        assert chunks == []
