#!/usr/bin/env python3
"""Executable stdio entrypoint for the repository's BTAE MCP server."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epe.adapters.mcp_server import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
