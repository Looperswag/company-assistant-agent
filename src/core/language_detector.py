"""Language detection module for multilingual query support."""

import re
from enum import Enum
from typing import Optional

from src.utils.logger import logger


class Language(Enum):
    """Supported languages for detection."""
    ENGLISH = "en"
    CHINESE = "zh"
    SPANISH = "es"
    FRENCH = "fr"
    MULTILINGUAL = "multi"

    def __str__(self) -> str:
        return self.value


class LanguageDetector:
    """Detect language of text based on character patterns."""

    # Chinese character ranges (CJK Unified Ideographs)
    CHINESE_PATTERN = re.compile(
        r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002b73f'
        r'\U0002b740-\U0002b81f\U0002b820-\U0002ceaf]'
    )

    # Spanish-specific characters
    SPANISH_PATTERN = re.compile(r'[ñáéíóúü¿¡]')

    # French-specific characters
    FRENCH_PATTERN = re.compile(r'[àâäéèêëïîôùûüÿç]')

    def __init__(self, threshold: float = 0.3) -> None:
        """Initialize the language detector.

        Args:
            threshold: Minimum ratio of language-specific characters to classify
        """
        self.threshold = threshold

    def detect(self, text: str) -> Language:
        """Detect the primary language of the given text.

        Args:
            text: Text to analyze

        Returns:
            Detected language
        """
        if not text or not text.strip():
            return Language.ENGLISH

        text = text.strip()
        total_chars = len(text)

        # Count language-specific characters
        chinese_chars = len(self.CHINESE_PATTERN.findall(text))
        spanish_chars = len(self.SPANISH_PATTERN.findall(text))
        french_chars = len(self.FRENCH_PATTERN.findall(text))

        # Calculate ratios
        chinese_ratio = chinese_chars / max(total_chars, 1)
        spanish_ratio = spanish_chars / max(total_chars, 1)
        french_ratio = french_chars / max(total_chars, 1)

        # Determine language based on ratios
        if chinese_ratio >= self.threshold:
            logger.debug(f"Detected Chinese (ratio: {chinese_ratio:.2f})")
            return Language.CHINESE

        if spanish_ratio > 0 and spanish_ratio >= french_ratio:
            logger.debug(f"Detected Spanish (chars: {spanish_chars})")
            return Language.SPANISH

        if french_ratio > 0:
            logger.debug(f"Detected French (chars: {french_chars})")
            return Language.FRENCH

        # Check for multilingual content (multiple language indicators)
        language_indicators = sum([
            chinese_ratio > 0.05,
            spanish_ratio > 0,
            french_ratio > 0,
        ])

        if language_indicators >= 2:
            logger.debug("Detected multilingual content")
            return Language.MULTILINGUAL

        # Default to English
        logger.debug("Defaulting to English")
        return Language.ENGLISH

    def detect_batch(self, texts: list[str]) -> list[Language]:
        """Detect language for multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of detected languages
        """
        return [self.detect(text) for text in texts]

    def is_chinese(self, text: str) -> bool:
        """Check if text is primarily Chinese.

        Args:
            text: Text to check

        Returns:
            True if text is primarily Chinese
        """
        return self.detect(text) == Language.CHINESE

    def is_english(self, text: str) -> bool:
        """Check if text is primarily English.

        Args:
            text: Text to check

        Returns:
            True if text is primarily English
        """
        return self.detect(text) == Language.ENGLISH


# Singleton instance for easy import
_detector: Optional[LanguageDetector] = None


def get_detector() -> LanguageDetector:
    """Get the singleton language detector instance.

    Returns:
        LanguageDetector instance
    """
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector
