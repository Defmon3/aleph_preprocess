import logging

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

DEFAULT_REGION = "US"
log = logging.getLogger(__name__)


def extract_phone_numbers(text: str | None) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        log.debug("No valid text provided for phone number extraction.")
        return []

    matches = list(phonenumbers.PhoneNumberMatcher(text, DEFAULT_REGION))
    log.debug(f"Found {len(matches)} raw phone candidates in text snippet")

    numbers: set[str] = set()
    for match in matches:
        try:
            if phonenumbers.is_valid_number(match.number):
                formatted = phonenumbers.format_number(
                    match.number, phonenumbers.PhoneNumberFormat.E164
                )
                log.debug(f"Extracted valid phone number: {formatted}")
                numbers.add(formatted)
        except NumberParseException:
            log.debug(f"Invalid phone number found: {match.raw_string}")
            continue
    log.debug(f"Total unique phone numbers extracted: {len(numbers)}")
    return sorted(numbers)