from __future__ import annotations

from pathlib import Path

import pytest

from sanitize.worker import sanitize_html
from tests.conftest import data_path, read_text


def case_pairs() -> list[tuple[Path, Path]]:
    """
    :return: List of (html_path, expected_txt_path) pairs
    """
    root = data_path()
    return [
        (root / "sample1.html", root / "sample1.txt"),
        (root / "sample2.html", root / "sample2.txt"),
    ]


@pytest.mark.parametrize(("html_path", "txt_path"), case_pairs())
def test_sanitize_matches_golden(html_path: Path, txt_path: Path) -> None:
    """
    :param html_path: HTML input path
    :param txt_path: Expected plain-text path
    """
    html = read_text(html_path)
    expected = read_text(txt_path).strip()
    actual = sanitize_html(html)
    assert actual == expected


def test_empty_input() -> None:
    """
    :return: None
    """
    assert sanitize_html("") == ""
