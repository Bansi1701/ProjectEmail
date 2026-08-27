"""OTP extraction tests.

The false-positive cases matter as much as the happy path: surfacing an order number as
a verification code is worse than surfacing nothing.
"""

import pytest

from app.mail.otp import extract_otp, extract_verification_link


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Your verification code is 847362", "847362"),
        ("Your code: 592014", "592014"),
        ("OTP: 4821", "4821"),
        ("583920 is your code", "583920"),
        ("Code: A1B2C3", "A1B2C3"),
        ("code: XY7Z9Q", "XY7Z9Q"),
        ("Token: 8F3K2M", "8F3K2M"),
        ("Please use\n\n739104\n\nto sign in", "739104"),
    ],
)
def test_extracts_codes(text: str, expected: str) -> None:
    assert extract_otp(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Your order #12345678 has shipped",
        "Copyright 2026 Example Inc",
        "Thanks for signing up!",
        "Your code is 123456",  # sequential — rejected as a false positive
        "Code: Please confirm your email",  # a word, not a code
    ],
)
def test_rejects_non_codes(text: str) -> None:
    assert extract_otp(text) is None


def test_prefers_labelled_code_over_bare_digits() -> None:
    text = "Order 998877. Your verification code is 445566."
    assert extract_otp(text) == "445566"


def test_extracts_verification_link() -> None:
    text = "Click https://example.com/verify?token=abc123 to continue"
    assert extract_verification_link(text) == "https://example.com/verify?token=abc123"
