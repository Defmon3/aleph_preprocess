import logging
import os

import phonenumbers
from followthemoney import model # noqa: F401
from phonenumbers.phonenumberutil import NumberParseException

from .sanitize import sanitize_html

DEFAULT_REGION = os.environ.get("PHONE_REGION", "US")
log = logging.getLogger(__name__)


def extract_phone_numbers(text: str | None, region: str = DEFAULT_REGION) -> list[str]:
    log.debug("Extracting phone numbers from text snippet")
    if not isinstance(text, str) or not text.strip():
        log.debug("No valid text provided for phone number extraction.")
        return []

    matches = list(phonenumbers.PhoneNumberMatcher(text, region))
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


def process_text_mentions(
    writer,
    text: str | None,
    link_entity_id: str | None = None,
    link_document_id: str | None = None,
    region: str = DEFAULT_REGION,
) -> int:
    log.info("[phone.process_text_mentions] enter")
    if not isinstance(text, str) or not text.strip():
        log.warning("[phone.process_text_mentions] empty_text")
        return 0
    cleaned = sanitize_html(text)
    phones = sorted(set(extract_phone_numbers(cleaned, region=region)))
    log.info("[phone.process_text_mentions] found=%d", len(phones))
    for p in phones:
        mention = model.make_entity("Mention")
        mention.make_id("phone-mention", link_document_id or link_entity_id or "none", p)
        mention.add("name", p)
        mention.add("resolved", p)
        mention.add("detectedSchema", "Phone")
        if link_document_id:
            mention.add("document", link_document_id)
        if link_entity_id:
            mention.add("entity", link_entity_id)
        writer.put(mention)
        log.debug("[phone.process_text_mentions] emitted=%s", p)
    log.info("[phone.process_text_mentions] exit emitted=%d", len(phones))
    return len(phones)
