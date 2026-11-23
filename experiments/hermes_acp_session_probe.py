"""Run a bounded EPE ACP session probe without treating model text as authorization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from epe.adapters.hosts.acp import HermesACPAdapter  # noqa: E402


def probe(command: list[str], cwd: Path, session_cwd: Path, prompt: str,
          timeout: float = 30.0, output_limit: int = 1024 * 1024) -> dict:
    adapter = HermesACPAdapter(command, cwd=cwd, timeout=timeout, output_limit=output_limit)
    with adapter.open_session(cwd=session_cwd) as session:
        result, updates = session.prompt_with_updates(prompt)
        text_chars = 0
        text_updates = 0
        for update in updates:
            content = update.get("content") if isinstance(update, dict) else None
            if isinstance(content, dict) and content.get("type") == "text" and isinstance(content.get("text"), str):
                text_updates += 1
                text_chars += len(content["text"])
        return {
            "protocol_version": 1,
            "session_opened": True,
            "stop_reason": result.get("stopReason"),
            "update_count": len(updates),
            "text_update_count": text_updates,
            "text_update_chars": text_chars,
            "trusted_identity": False,
            "write_isolation": False,
            "mcp_servers": [],
            "scope": "session_prompt_transport_only",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--session-cwd", type=Path, default=None)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output-limit", type=int, default=1024 * 1024)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        result = probe(command, args.cwd, args.session_cwd or args.cwd, args.prompt,
                       timeout=args.timeout, output_limit=args.output_limit)
    except (OSError, ValueError, TimeoutError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
