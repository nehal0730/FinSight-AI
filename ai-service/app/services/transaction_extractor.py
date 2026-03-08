import importlib
import re
from datetime import datetime
from typing import Any, Optional


class TransactionExtractor:
    """Extract structured transaction records from bank statement text."""

    # Supports: 05 Jan 2025, 05/01/2025, 2025-01-05, Jan 05 2025
    DATE_PATTERN = re.compile(
        r"(?P<date>"
        r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        r"|(?:\d{4}[/-]\d{1,2}[/-]\d{1,2})"
        r"|(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})"
        r"|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})"
        r")",
        re.IGNORECASE,
    )

    # Supports: ₹45,000, INR 45000, 45000 DR, 1200.50 Cr
    AMOUNT_PATTERN = re.compile(
        r"(?P<full>"
        r"(?:(?:₹|Rs\.?|INR|\$)\s*)?"
        r"(?P<amount>\d[\d,]*(?:\.\d{1,2})?)"
        r"\s*(?P<suffix>CR|DR|Cr|Dr)?"
        r")"
    )

    DEBIT_KEYWORDS = {
        "debit",
        "dr",
        "withdrawal",
        "purchase",
        "pos",
        "atm",
        "upi",
        "charges",
        "fee",
    }

    CREDIT_KEYWORDS = {
        "credit",
        "cr",
        "deposit",
        "salary",
        "refund",
        "reversal",
        "interest",
        "cashback",
    }

    NOISE_TOKENS = {
        "txn",
        "txnid",
        "narration",
        "ref",
        "utr",
        "imps",
        "neft",
        "rtgs",
        "upi",
        "pos",
        "debit",
        "credit",
        "dr",
        "cr",
        "payment",
        "transfer",
        "via",
        "to",
        "by",
    }

    NON_TRANSACTION_MARKERS = {
        "opening balance",
        "closing balance",
        "available balance",
        "statement period",
        "balance",
    }

    @classmethod
    def extract_transactions(cls, text: str) -> list[dict[str, Any]]:
        """Parse multiline statement text into normalized transaction records."""
        if not text or not text.strip():
            return []

        transactions: list[dict[str, Any]] = []

        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue

            record = cls._parse_line(line)
            if record is not None:
                transactions.append(record)

        return transactions

    @classmethod
    def to_dataframe(cls, transactions: list[dict[str, Any]]):
        """Convert extracted transactions to a pandas DataFrame if pandas is installed."""
        try:
            pd = importlib.import_module("pandas")
        except ImportError as exc:
            raise ImportError(
                "pandas is required for DataFrame conversion. Install pandas to use to_dataframe()."
            ) from exc

        return pd.DataFrame(transactions, columns=["date", "amount", "type", "merchant"])

    @classmethod
    def _parse_line(cls, line: str) -> Optional[dict[str, Any]]:
        lowered = line.lower()
        if any(marker in lowered for marker in cls.NON_TRANSACTION_MARKERS):
            return None

        date_match = cls.DATE_PATTERN.search(line)
        if not date_match:
            return None

        amount_match = cls._find_amount_candidate(line, date_match.end())
        if not amount_match:
            return None

        normalized_date = cls._normalize_date(date_match.group("date"))
        if not normalized_date:
            return None

        amount_value = cls._to_float(amount_match.group("amount"))
        if amount_value is None:
            return None

        tx_type = cls._infer_transaction_type(line, amount_match.group("suffix"))
        merchant = cls._extract_merchant(line, date_match, amount_match)

        return {
            "date": normalized_date,
            "amount": amount_value,
            "type": tx_type,
            "merchant": merchant,
        }

    @classmethod
    def _find_amount_candidate(cls, line: str, start_pos: int) -> Optional[re.Match[str]]:
        # Prefer amount tokens appearing after the date for statement-like lines.
        candidates = [m for m in cls.AMOUNT_PATTERN.finditer(line) if m.start() >= start_pos]
        if not candidates:
            return None

        scored: list[tuple[int, float, re.Match[str]]] = []
        for match in candidates:
            amount_text = match.group("amount")
            amount_value = cls._to_float(amount_text)
            if amount_value is None:
                continue

            has_currency = bool(re.search(r"₹|Rs\.?|INR|\$", match.group("full"), re.IGNORECASE))
            has_suffix = bool(match.group("suffix"))
            score = (2 if has_currency else 0) + (1 if has_suffix else 0)
            scored.append((score, amount_value, match))

        if not scored:
            return None

        # Use highest confidence; for ties prefer higher amount to avoid picking token IDs.
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return scored[0][2]

    @staticmethod
    def _to_float(amount_text: str) -> Optional[float]:
        cleaned = amount_text.replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    @classmethod
    def _infer_transaction_type(cls, line: str, suffix: Optional[str]) -> str:
        lowered = line.lower()

        if suffix:
            suffix_lower = suffix.lower()
            if suffix_lower == "dr":
                return "debit"
            if suffix_lower == "cr":
                return "credit"

        if any(f" {kw} " in f" {lowered} " for kw in cls.DEBIT_KEYWORDS):
            return "debit"
        if any(f" {kw} " in f" {lowered} " for kw in cls.CREDIT_KEYWORDS):
            return "credit"

        # Default for bank-statement outflow-like records when type is missing.
        return "debit"

    @classmethod
    def _extract_merchant(
        cls,
        line: str,
        date_match: re.Match[str],
        amount_match: re.Match[str],
    ) -> str:
        trailing = line[amount_match.end():].strip(" -:|,./")
        between = line[date_match.end():amount_match.start()].strip(" -:|,./")

        base = trailing if trailing else between
        if not base:
            return "UNKNOWN"

        # Keep business-like tokens, drop common statement boilerplate.
        tokens = re.findall(r"[A-Za-z0-9_&./-]+", base)
        cleaned_tokens = [
            token
            for token in tokens
            if token.lower() not in cls.NOISE_TOKENS and not token.isdigit()
        ]

        merchant = " ".join(cleaned_tokens).strip()
        return merchant if merchant else "UNKNOWN"

    @staticmethod
    def _normalize_date(raw_date: str) -> Optional[str]:
        candidate = raw_date.strip().replace(",", "")

        supported_formats = [
            "%d %b %Y",
            "%d %B %Y",
            "%b %d %Y",
            "%B %d %Y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%d-%m-%Y",
            "%d-%m-%y",
            "%Y/%m/%d",
            "%Y-%m-%d",
        ]

        for fmt in supported_formats:
            try:
                parsed = datetime.strptime(candidate, fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None
