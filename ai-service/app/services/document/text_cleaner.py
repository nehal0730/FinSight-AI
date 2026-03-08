import re
import unicodedata


class TextCleaner:
    """Normalize and clean extracted text"""

    WORD_PATTERN = re.compile(r"\b\w+\b")

    @staticmethod
    def clean(raw_text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Operations:
        - Unicode normalization (NFKC)
        - Line break standardization
        - Whitespace collapsing
        - Empty line removal
        
        Args:
            raw_text: Raw extracted text from PDF
        
        Returns:
            Cleaned text
        """
        if not raw_text:
            return ""

        # Normalize Unicode characters
        normalized = unicodedata.normalize("NFKC", raw_text)
        
        # Standardize line breaks
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # Process lines: collapse multiple spaces, remove empty lines
        lines = []
        for line in normalized.split("\n"):
            compact = re.sub(r"\s+", " ", line).strip()
            if compact:
                lines.append(compact)

        return "\n".join(lines)

    @staticmethod
    def word_count(text: str) -> int:
        """
        Count total words in text.
        
        Args:
            text: Cleaned text
        
        Returns:
            Word count
        """
        if not text:
            return 0
        return len(TextCleaner.WORD_PATTERN.findall(text))
