import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

DEFAULT_REGION = "US"

def extract_phone_numbers(text: str | None) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        return []

    numbers: set[str] = set()
    for match in phonenumbers.PhoneNumberMatcher(text, DEFAULT_REGION):
        try:
            if phonenumbers.is_valid_number(match.number):
                formatted = phonenumbers.format_number(
                    match.number, phonenumbers.PhoneNumberFormat.E164
                )
                numbers.add(formatted)
        except NumberParseException:
            continue
    return sorted(numbers)
