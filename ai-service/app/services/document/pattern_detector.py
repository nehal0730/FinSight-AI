import re
from typing import List


class PatternDetector:
    """Detects financial and business patterns in text"""

    # Currency pattern: matches $1,234.56, ₹50,000, 1234 USD, etc.
    CURRENCY_PATTERN = re.compile(
        r"(?:"
        r"(?:₹|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?"
        r"|"
        r"\d[\d,]*(?:\.\d{1,2})?\s?(?:INR|USD|EUR|GBP|Rs\.?)"
        r")",
        re.IGNORECASE
    )

    # Percentage pattern: 12.5%, 45.67 percent
    PERCENTAGE_PATTERN = re.compile(r"\d+\.?\d*\s?%|percent", re.IGNORECASE)

    # Large number patterns (Indian format)
    CRORE_PATTERN = re.compile(r"\d+\.?\d*\s?(?:crore|cr\.?)", re.IGNORECASE)
    LAKH_PATTERN = re.compile(r"\d+\.?\d*\s?(?:lakh|lac)", re.IGNORECASE)
    
    # Large number patterns (International)
    MILLION_PATTERN = re.compile(r"\d+\.?\d*\s?(?:million|M)", re.IGNORECASE)
    BILLION_PATTERN = re.compile(r"\d+\.?\d*\s?(?:billion|B)", re.IGNORECASE)

    # Date patterns (common financial formats)
    DATE_PATTERN = re.compile(
        r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
        re.IGNORECASE
    )

    # Indian compliance patterns
    PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")  # ABCDE1234F
    GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]\b")  # 22AAAAA0000A1Z5

    # Account number pattern (generic, for masking detection)
    ACCOUNT_PATTERN = re.compile(r"\b\d{9,18}\b")  # 9-18 digit sequences

    @staticmethod
    def detect_currencies(text: str) -> int:
        """
        Count currency mentions in text.
        
        Matches patterns like:
        - $1,234.56
        - ₹50,000
        - €1000
        - £500.75
        - 1234 USD
        - 5000 INR
        - Rs. 1000
        
        Args:
            text: Input text to search
        
        Returns:
            Count of detected currency values
        """
        if not text:
            return 0
        return len(PatternDetector.CURRENCY_PATTERN.findall(text))

    @staticmethod
    def detect_percentages(text: str) -> int:
        """Count percentage mentions (12.5%, 45 percent)"""
        if not text:
            return 0
        return len(PatternDetector.PERCENTAGE_PATTERN.findall(text))

    @staticmethod
    def detect_large_numbers(text: str) -> dict:
        """
        Detect large number mentions (crores, lakhs, millions, billions).
        
        Returns:
            Dict with counts per type
        """
        if not text:
            return {"crores": 0, "lakhs": 0, "millions": 0, "billions": 0}
        
        return {
            "crores": len(PatternDetector.CRORE_PATTERN.findall(text)),
            "lakhs": len(PatternDetector.LAKH_PATTERN.findall(text)),
            "millions": len(PatternDetector.MILLION_PATTERN.findall(text)),
            "billions": len(PatternDetector.BILLION_PATTERN.findall(text)),
        }

    @staticmethod
    def detect_dates(text: str) -> int:
        """Count date mentions in various formats"""
        if not text:
            return 0
        return len(PatternDetector.DATE_PATTERN.findall(text))

    @staticmethod
    def detect_pan_numbers(text: str) -> List[str]:
        """
        Detect Indian PAN numbers (Permanent Account Number).
        
        Format: ABCDE1234F (5 letters, 4 digits, 1 letter)
        
        Returns:
            List of detected PAN numbers (for compliance flagging)
        """
        if not text:
            return []
        return PatternDetector.PAN_PATTERN.findall(text)

    @staticmethod
    def detect_gstin_numbers(text: str) -> List[str]:
        """
        Detect Indian GSTIN (Goods and Services Tax ID).
        
        Format: 22AAAAA0000A1Z5 (15 chars)
        
        Returns:
            List of detected GSTIN numbers
        """
        if not text:
            return []
        return PatternDetector.GSTIN_PATTERN.findall(text)

    @staticmethod
    def detect_account_numbers(text: str) -> int:
        """
        Count potential account numbers (9-18 digit sequences).
        
        Used for risk flagging, not extraction (for privacy).
        """
        if not text:
            return 0
        return len(PatternDetector.ACCOUNT_PATTERN.findall(text))

    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        """
        Mask sensitive information in text.
        
        Masks:
        - PAN numbers: ABCDE1234F → XXXXX1234X
        - Account numbers: 1234567890 → ******7890
        
        Returns:
            Text with masked sensitive data
        """
        if not text:
            return text

        # Mask PAN numbers
        def mask_pan(match):
            pan = match.group(0)
            return f"XXXXX{pan[5:9]}X"
        
        text = PatternDetector.PAN_PATTERN.sub(mask_pan, text)

        # Mask account numbers (show last 4 digits)
        def mask_account(match):
            acc = match.group(0)
            if len(acc) >= 4:
                return "*" * (len(acc) - 4) + acc[-4:]
            return "*" * len(acc)
        
        text = PatternDetector.ACCOUNT_PATTERN.sub(mask_account, text)

        return text

    @staticmethod
    def detect_email_addresses(text: str) -> int:
        """
        Count email addresses in text.
        
        Args:
            text: Input text to search
        
        Returns:
            Count of detected email addresses
        """
        if not text:
            return 0
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        return len(re.findall(pattern, text))

    @staticmethod
    def detect_phone_numbers(text: str) -> int:
        """
        Count phone numbers in text (basic pattern).
        
        Args:
            text: Input text to search
        
        Returns:
            Count of detected phone numbers
        """
        if not text:
            return 0
        # Matches: +1-234-567-8900, (123) 456-7890, 123-456-7890
        pattern = r"(?:\+\d{1,3}-?)?\(?\d{3}\)?-?\d{3}-?\d{4}"
        return len(re.findall(pattern, text))
