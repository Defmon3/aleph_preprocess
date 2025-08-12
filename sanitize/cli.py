#!/usr/bin/env python3
"""
SPDX-License-Identifier: LicenseRef-NonCommercial-Only
© 2025 github.com/defmon3 — Non-commercial use only. Commercial use requires permission.

Dependencies:
    uv add loguru beautifulsoup4 lxml servicelayer ftmstore followthemoney click
"""

# sanitize/cli.py
from __future__ import annotations

import click
from loguru import logger as log

from sanitize.worker import ServiceWorker, OP_SANITIZE


@click.group()
def sanitize() -> None:
    """
    CLI for the sanitize stage.
    """
    log.info("sanitize stage ready")


@sanitize.command()
def worker() -> None:
    """
    Start the Redis-backed worker loop.
    """
    ServiceWorker(OP_SANITIZE).run()


if __name__ == "__main__":
    sanitize()
