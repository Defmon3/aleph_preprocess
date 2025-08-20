#!/usr/bin/env python3
# /// script
# requires-python = "==3.12.9"
# dependencies = ["pytest", "phonenumberslite"]
# ///

import pytest
import phonenumbers
from phonenumbers import PhoneNumberFormat


cases = [
    ("+1 202 555 0123", "+12025550123"),
    ("+12025550123", "+12025550123"),
    ("202-555-0123", "+12025550123"),
    ("(202) 555-0123", "+12025550123"),
    ("202.555.0123", "+12025550123"),
    ("2025550123", "+12025550123"),
    ("+44 20 7946 0958", "+442079460958"),
    ("0049 30 123456", "+4930123456", "DE"),
    ("+49-30-123456", "+4930123456"),
    ("+91 98765 43210", "+919876543210"),
    ("+7 (495) 123-45-67", "+74951234567"),
    ("+86 10 8888 8888", "+861088888888"),
    ("+33 (0)1 44 55 66 77", "+33144556677"),
]


@pytest.mark.parametrize(
    "raw,expected,region",
    [
        (raw, expected, region if region else "US")
        for *values, region in [(c if len(c) == 3 else (*c, None)) for c in cases]
        for raw, expected in [values]
    ],
)
def test_phonenumbers_normalization(raw: str, expected: str, region: str) -> None:
    parsed = phonenumbers.parse(raw, region)
    formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    assert formatted == expected
