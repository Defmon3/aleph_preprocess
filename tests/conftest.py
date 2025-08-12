from __future__ import annotations

from pathlib import Path


def data_path() -> Path:
    """
    :return: Absolute path to test fixtures dir
    """
    return Path(__file__).parent / "fixtures"


def read_text(path: Path) -> str:
    """
    :param path: File path
    :return: File contents as UTF-8 text
    """
    return path.read_text(encoding="utf-8")
