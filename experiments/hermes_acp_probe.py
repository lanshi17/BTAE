"""Prototype: bounded ACP initialize probe, not an EPE authorization adapter."""
from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path


def probe(command: list[str], cwd: Path, timeout: float = 10.0, limit: int = 1048576) -> dict:
    if not command or not all(isinstance(arg, str) and arg for arg in command) or timeout <= 0 or limit <= 0:
        raise ValueError("invalid command, timeout, or output limit")
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": 1, "clientCapabilities": {}, "clientInfo": {"name": "btae-acp-probe", "version": "0.1"}}}
    proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    selector = selectors.DefaultSelector()
    try:
        proc.stdin.write((json.dumps(request) + "\n").encode())
        proc.stdin.flush()
        selector.register(proc.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        pending = b""
        consumed = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("ACP initialize timed out")
            chunk = os.read(proc.stdout.fileno(), min(65536, limit + 1 - consumed))
            if not chunk:
                raise ValueError("ACP stream closed before initialize response")
            consumed += len(chunk)
            if consumed > limit:
                raise ValueError("ACP output limit exceeded")
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                try:
                    message = json.loads(line)
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise ValueError("invalid ACP JSON") from exc
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    raise ValueError("invalid ACP message")
                if "id" not in message and isinstance(message.get("method"), str):
                    continue
                if type(message.get("id")) is not int or message["id"] != 1:
                    raise ValueError("unexpected ACP response ID")
                result = message.get("result")
                if ("error" in message or not isinstance(result, dict)
                        or type(result.get("protocolVersion")) is not int or result["protocolVersion"] != 1):
                    raise ValueError("ACP initialization failed or version mismatch")
                info = result.get("agentInfo")
                if not isinstance(info, dict) or not isinstance(info.get("name"), str) or not info["name"]:
                    raise ValueError("missing ACP agent information")
                return {"protocol_version": 1, "agent_name": info["name"], "agent_version": info.get("version"),
                        "trusted_identity": False, "write_isolation": False, "scope": "initialize_only"}
    finally:
        selector.close()
        # The session leader can exit before its descendants; clean the group
        # even when poll() has already observed that exit.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        proc.stdin.close()
        proc.stdout.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        print(json.dumps(probe(command, args.cwd, args.timeout), ensure_ascii=False))
    except (OSError, ValueError, TimeoutError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
