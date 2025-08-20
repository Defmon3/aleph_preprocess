#!/usr/bin/env python3
# /// script
# requires-python = "==3.12.9"
# dependencies = ["beautifulsoup4", "lxml", "followthemoney", "ftmstore", "servicelayer", "phonenumbers"]
# ///

"""
SPDX-License-Identifier: LicenseRef-NonCommercial-Only
© 2025 github.com/defmon3 — Non-commercial use only. Commercial use requires permission.

sanitize.py – HTML sanitization utilities.
"""

import re
from bs4 import BeautifulSoup


import re
from bs4 import BeautifulSoup, FeatureNotFound

def sanitize_html(text: str) -> str:
    """
    Convert minimal HTML to collapsed plain text.

    :param text: Raw or partially structured HTML content.
    :returns: Plain text with scripts/styles removed and whitespace collapsed.
              Returns "" if nothing usable is found.
    """
    if not isinstance(text, str):
        if not isinstance(text, bytes):
            return ""

        try:
            text = text.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    try:
        try:
            soup = BeautifulSoup(text, "lxml")
        except FeatureNotFound:
            soup = BeautifulSoup(text, "html.parser")
    except Exception:
        return ""

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    container = soup.body or soup
    try:
        raw = container.get_text(separator=" ", strip=True)
    except Exception:
        return ""

    result = re.sub(r"\s+", " ", raw).strip()
    return result
