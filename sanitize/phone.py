import logging

import phonenumbers
from followthemoney import model
from followthemoney.types import registry
from phonenumbers.phonenumberutil import NumberParseException

from .sanitize import sanitize_html

DEFAULT_REGION = "US"
log = logging.getLogger(__name__)


def extract_phone_numbers(text: str | None) -> list[str]:
    log.debug("Extracting phone numbers from text snippet")
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


def process_entity_phones(writer, entity) -> None:
    if not entity.schema.is_a("Analyzable"):
        return

    texts = entity.get_type_values(registry.text)
    if not texts:
        return

    phones: list[str] = []
    for t in texts:
        if t:
            phones.extend(extract_phone_numbers(sanitize_html(t)))

    if not phones:
        return

    # Partial update for the entity itself
    partial = model.make_entity(entity.schema)
    partial.id = entity.id
    for p in phones:
        partial.add("phone", p, quiet=True)
    writer.put(partial)

    # Add mention entities for each phone
    for p in phones:
        mention = model.make_entity("Mention")
        mention.add("mention", p)
        mention.add("resolved", p)
        mention.add("entity", entity.id)
        writer.put(mention)

    log.debug(
        f"Entity {entity.id}: added {len(phones)} phones "
        f"and {len(phones)} phone mentions"
    )
