"""Markdown file parser for knowledge base."""

import re
from pathlib import Path
from typing import List, Tuple

from src.utils.logger import logger


class MarkdownParser:
    """Parser for Markdown files in the knowledge base."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        """Initialize the parser.

        Args:
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Overlap size between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def parse_file(self, file_path: Path) -> List[Tuple[str, dict]]:
        """Parse a Markdown file into chunks.

        Args:
            file_path: Path to the Markdown file

        Returns:
            List of tuples containing (text_chunk, metadata)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract title from first heading
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem

            # Split by headings to preserve structure
            sections = self._split_by_headings(content)
            chunks: List[Tuple[str, dict]] = []

            # If no sections found, treat entire content as one section
            if not sections:
                sections = [content]

            for section in sections:
                section_chunks = self._chunk_text(section, file_path, title)
                chunks.extend(section_chunks)

            logger.info(f"Parsed {file_path.name}: {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _split_by_headings(self, content: str) -> List[str]:
        """Split content by headings while preserving context.

        Args:
            content: Markdown content

        Returns:
            List of sections
        """
        # Split by headings (## or ###)
        pattern = r"(?=^##+\s+)"
        sections = re.split(pattern, content, flags=re.MULTILINE)

        # Filter out empty sections
        return [s.strip() for s in sections if s.strip()]

    def _chunk_text(self, text: str, file_path: Path, title: str) -> List[Tuple[str, dict]]:
        """Split text into chunks with overlap.

        Args:
            text: Text to chunk
            file_path: Source file path
            title: Document title

        Returns:
            List of tuples containing (chunk_text, metadata)
        """
        # Clean text: remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        if len(text) <= self.chunk_size:
            return [
                (
                    text,
                    {
                        "source": str(file_path),
                        "title": title,
                        "chunk_index": 0,
                    },
                )
            ]

        chunks: List[Tuple[str, dict]] = []
        words = text.split()
        current_chunk: List[str] = []
        current_length = 0
        chunk_index = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    (
                        chunk_text,
                        {
                            "source": str(file_path),
                            "title": title,
                            "chunk_index": chunk_index,
                        },
                    )
                )

                # Start new chunk with overlap
                overlap_words = current_chunk[-self.chunk_overlap :] if self.chunk_overlap > 0 else []
                current_chunk = overlap_words + [word]
                current_length = sum(len(w) + 1 for w in current_chunk)
                chunk_index += 1
            else:
                current_chunk.append(word)
                current_length += word_length

        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                (
                    chunk_text,
                    {
                        "source": str(file_path),
                        "title": title,
                        "chunk_index": chunk_index,
                    },
                )
            )

        return chunks

    def parse_directory(self, directory: Path) -> List[Tuple[str, dict]]:
        """Parse all Markdown files in a directory.

        Args:
            directory: Directory containing Markdown files

        Returns:
            List of tuples containing (text_chunk, metadata)
        """
        all_chunks: List[Tuple[str, dict]] = []

        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return all_chunks

        md_files = list(directory.glob("*.md"))
        logger.info(f"Found {len(md_files)} Markdown files in {directory}")

        for md_file in md_files:
            chunks = self.parse_file(md_file)
            all_chunks.extend(chunks)

        return all_chunks
