"""OTP and verification-link extraction.

Surfacing the code without the user opening the message is the core UX of this product —
it is what makes sessions short and pleasant.

Strategy: an ordered ladder, most-specific first. A code sitting next to the word
"verification" is far more likely correct than a bare digit run, which might be an order
number, a year, or a price.

Every pattern is bounded. Unbounded nested quantifiers are a ReDoS vector on input that
arrives from anyone on the internet — see docs/SECURITY.md section 5.
"""

from __future__ import annotations

import re

# Ordered: highest confidence first. Bounded quantifiers only.
_OTP_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "Your verification code is 123456"
    re.compile(
        r"(?:verification|confirmation|security|access|login|auth\w{0,10})\s+"
        r"code\s*(?:is|:)?\s*[:\-]?\s*([0-9]{4,8})",
        re.IGNORECASE,
    ),
    # "Your code: 123456" / "OTP: 123456" / "PIN 1234"
    re.compile(r"(?:code|otp|pin|token)\s*(?:is|:)?\s*[:\-]?\s*([0-9]{4,8})", re.IGNORECASE),
    # "123456 is your code"
    re.compile(r"\b([0-9]{4,8})\b\s+is\s+your\s+(?:code|otp|pin)", re.IGNORECASE),
    # Alphanumeric codes: "Code: A1B2C3"
    # Scoped (?i:) on the label only — the code group stays case-sensitive on purpose.
    # Real alphanumeric codes are conventionally uppercase, and allowing lowercase here
    # would match ordinary words ("Code: Please confirm" -> "Please").
    re.compile(r"(?i:code|otp|token)\s*(?:is|:)?\s*[:\-]?\s*([A-Z0-9]{4,8})\b"),
    # Last resort: an isolated 6-digit run on its own line.
    re.compile(r"^\s*([0-9]{6})\s*$", re.MULTILINE),
)

_LINK_PATTERN = re.compile(
    r"https?://[^\s<>\"']{1,500}?"
    r"(?:verify|confirm|activate|validate|signup|register|auth)"
    r"[^\s<>\"']{0,500}",
    re.IGNORECASE,
)

# Years, common false positives that look like codes.
_FALSE_POSITIVES = frozenset({"0000", "1111", "1234", "12345", "123456"})


def extract_otp(text: str) -> str | None:
    """Return the most likely one-time code, or None."""
    for pattern in _OTP_PATTERNS:
        match = pattern.search(text)
        if match:
            candidate = match.group(1)
            if candidate not in _FALSE_POSITIVES:
                return candidate
    return None


def extract_verification_link(text: str) -> str | None:
    """Return the most likely verification URL, or None."""
    match = _LINK_PATTERN.search(text)
    return match.group(0) if match else None
