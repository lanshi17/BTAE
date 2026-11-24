"""Small dependency-free stdio MCP entrypoint for BTAE coding agents.

The server intentionally exposes read-only context, planning, and validation
surfaces. It does not write project authority files or infer approvals.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from epe.core.json_codec import strict_json_loads


PROTOCOL_VERSION = "2024-11-05"
SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18"}
SERVER_INFO = {"name": "btae", "version": "0.1.0"}
MAX_SOURCE_BYTES = 32_000


def _root(value: Any = None) -> Path:
    candidate = Path(value or os.environ.get("BTAE_ROOT") or Path.cwd()).expanduser().resolve()
    if not candidate.is_dir():
        raise ValueError(f"BTAE root is not a directory: {candidate}")
    return candidate


def _safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts or "\\" in relative:
        raise ValueError(f"source path must be repository-relative: {relative}")
    path = (root / relative).resolve()
    path.relative_to(root)
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"source path cannot cross a symlink: {relative}")
    return path


def _read_source(root: Path, relative: str, source_type: str) -> dict[str, Any]:
    path = _safe_file(root, relative)
    data = path.read_bytes()
    return {
        "path": relative,
        "source_type": source_type,
        "sha256": __import__("hashlib").sha256(data).hexdigest(),
        "content": data[:MAX_SOURCE_BYTES].decode("utf-8", errors="replace"),
        "truncated": len(data) > MAX_SOURCE_BYTES,
    }


def _existing_sources(root: Path, objective: str, target_entities: list[str]) -> list[dict[str, Any]]:
    candidates: list[tuple[str, str]] = [
        ("AGENTS.md", "rule"),
        ("docs/index.md", "index"),
        ("docs/intent/PRD-BTAE.md", "intent"),
        ("docs/intent/requirements/SPEC-BTAE.md", "spec"),
        ("docs/architecture/engineering-protocol.md", "architecture"),
        ("docs/architecture/overview.md", "architecture"),
        ("docs/architecture/boundaries.md", "architecture"),
        ("docs/modules/README.md", "module-index"),
    ]
    terms = {term.lower() for term in objective.split() if len(term) > 3}
    for path in sorted(root.glob("plans/active/*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(entity in text for entity in target_entities) or any(term in text.lower() for term in terms):
            candidates.append((path.relative_to(root).as_posix(), "plan"))
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative, source_type in candidates:
        if relative in seen:
            continue
        try:
            result.append(_read_source(root, relative, source_type))
            seen.add(relative)
        except (OSError, UnicodeError, ValueError):
            continue
    return result


def project_context(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments.get("root"))
    objective = str(arguments.get("objective", "")).strip()
    if not objective:
        raise ValueError("objective is required")
    change_type = arguments.get("change_type", "feature")
    if change_type not in {"feature", "bugfix", "refactor", "exploration"}:
        raise ValueError("change_type must be feature, bugfix, refactor, or exploration")
    target_entities = arguments.get("target_entities", [])
    if not isinstance(target_entities, list) or any(not isinstance(item, str) or not item for item in target_entities):
        raise ValueError("target_entities must be a string array")
    sources = _existing_sources(root, objective, target_entities)
    return {
        "status": "ready" if sources else "incomplete",
        "root": str(root),
        "change_type": change_type,
        "objective": objective,
        "target_entities": target_entities,
        "sources": sources,
        "source_policy": "C0 rules and task constraints precede C1 architecture and C2 implementation context",
        "limitations": [
            "This context bundle is advisory and does not grant approval or write permission.",
            "Missing, truncated, or unreadable sources must remain explicit to the coding agent.",
        ],
    }


def design_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    objective = str(arguments.get("objective", "")).strip()
    if not objective:
        raise ValueError("objective is required")
    change_type = arguments.get("change_type", "feature")
    if change_type not in {"feature", "bugfix", "refactor", "exploration"}:
        raise ValueError("change_type must be feature, bugfix, refactor, or exploration")
    targets = arguments.get("target_entities", [])
    if not isinstance(targets, list) or any(not isinstance(item, str) or not item for item in targets):
        raise ValueError("target_entities must be a string array")
    risk = arguments.get("risk", "medium")
    if risk not in {"low", "medium", "high"}:
        raise ValueError("risk must be low, medium, or high")
    workflow_fields = {
        "feature": ["objective", "acceptance", "target_entities"],
        "bugfix": ["objective", "acceptance", "target_entities", "reproduction"],
        "refactor": ["objective", "acceptance", "target_entities", "baseline_manifest"],
        "exploration": ["objective", "acceptance", "target_entities", "hypothesis"],
    }[change_type]
    return {
        "status": "draft",
        "approval_required": risk in {"medium", "high"},
        "task": {
            "type": change_type,
            "objective": objective,
            "risk": risk,
            "target_entities": targets,
            "required_fields": workflow_fields,
            "status": "planned",
        },
        "traceability_chain": [
            "Intent/Spec",
            "Architecture/Module boundary",
            "Component/Class/Contract design",
            "Implementation mapping",
            "Behavior tests and verification",
            "Evidence and finalize gate",
        ],
        "required_artifacts": [
            "plans/active/TASK-<stable-id>.md",
            "a machine-valid task record under engineering/tasks/",
            "a ChangeSet declaration and baseline before writes",
            "design and contract updates for changed public boundaries",
            "tests and evidence tied to the affected entities",
        ],
        "workflow_specific": {
            "bugfix": "reproduce the failure and record root cause before the fix",
            "refactor": "capture an architecture or behavior baseline before editing",
            "exploration": "label prototypes and hypotheses; do not present them as production design",
            "feature": "define acceptance behavior and affected entities before implementation",
        }[change_type],
        "gates": ["design", "mapping", "architecture", "test", "scope", "evidence", "finalize"],
        "id_policy": "Assign stable non-reused IDs such as TASK-*, CHANGE-*, SPEC-*, ARCH-*, MOD-*, CLASS-*; this tool does not reserve IDs.",
        "limitations": [
            "The plan is not an approval and does not change repository files.",
            "Host identity, CI enforcement, and external immutable audit remain separate evidence requirements.",
        ],
    }


def _run_epe(root: Path, command: list[str]) -> dict[str, Any]:
    env = dict(os.environ)
    src = str(root / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    process = subprocess.run([sys.executable, "-m", "epe", "--root", str(root), "--format", "json", *command], cwd=root, env=env, capture_output=True, text=True, timeout=30)
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    try:
        result = strict_json_loads(lines[-1]) if lines else {}
    except (ValueError, json.JSONDecodeError):
        result = {"status": "error", "diagnostics": [{"code": "EPE-MCP-CLI", "message": process.stdout[-1000:]}]}
    return {"argv": command, "exit_code": process.returncode, "result": result, "stderr": process.stderr}


def validate_project(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments.get("root"))
    checks = [_run_epe(root, ["policy", "validate"]), _run_epe(root, ["inspect"])]
    graph_current = root / ".engineering" / "current.json"
    if graph_current.exists():
        checks.append(_run_epe(root, ["architecture", "validate"]))
    else:
        checks.append({"argv": ["architecture", "validate"], "status": "skipped", "reason": "no current graph snapshot"})
    errors = [item for item in checks if item.get("status") == "error" or item.get("result", {}).get("status") == "error"]
    return {"status": "error" if errors else "checked", "root": str(root), "checks": checks, "write_effects": "none"}


TOOLS = [
    {"name": "btae_project_context", "description": "Read-only bounded BTAE C0-C2 context for a coding task. Call before editing.", "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}, "inputSchema": {"type": "object", "required": ["objective"], "properties": {"root": {"type": "string"}, "objective": {"type": "string"}, "change_type": {"type": "string", "enum": ["feature", "bugfix", "refactor", "exploration"]}, "target_entities": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "btae_design_plan", "description": "Return a draft BTAE design-first plan, traceability chain, artifacts, and gates without writing files.", "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}, "inputSchema": {"type": "object", "required": ["objective"], "properties": {"objective": {"type": "string"}, "change_type": {"type": "string", "enum": ["feature", "bugfix", "refactor", "exploration"]}, "risk": {"type": "string", "enum": ["low", "medium", "high"]}, "target_entities": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "btae_validate_project", "description": "Run existing read-only EPE policy, registry, and current-graph architecture checks for a project.", "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}, "inputSchema": {"type": "object", "properties": {"root": {"type": "string"}}}},
]


RESOURCE_MAP = {
    "btae://charter": ("AGENTS.md", "text/markdown"),
    "btae://spec": ("docs/intent/requirements/SPEC-BTAE.md", "text/markdown"),
    "btae://architecture/overview": ("docs/architecture/overview.md", "text/markdown"),
    "btae://architecture/protocol": ("docs/architecture/engineering-protocol.md", "text/markdown"),
    "btae://workflow/feature": ("engineering/workflows/feature.yaml", "text/yaml"),
    "btae://workflow/bugfix": ("engineering/workflows/bugfix.yaml", "text/yaml"),
    "btae://workflow/refactor": ("engineering/workflows/refactor.yaml", "text/yaml"),
    "btae://workflow/exploration": ("engineering/workflows/exploration.yaml", "text/yaml"),
}


def _tool_result(value: Any, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, sort_keys=True)}], "structuredContent": value, "isError": is_error}


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "btae_project_context":
        return _tool_result(project_context(arguments))
    if name == "btae_design_plan":
        return _tool_result(design_plan(arguments))
    if name == "btae_validate_project":
        return _tool_result(validate_project(arguments))
    return _tool_result({"code": "EPE-MCP-TOOL", "message": f"unknown tool: {name}"}, True)


def _response(request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    response = {"jsonrpc": "2.0", "id": request_id}
    response["error" if error else "result"] = error if error else result
    return response


def dispatch(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method in {"notifications/initialized", "notifications/cancelled", "notifications/progress"}:
        return None
    if method == "initialize":
        requested = str((message.get("params") or {}).get("protocolVersion", ""))
        selected = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
        return _response(request_id, {"protocolVersion": selected, "capabilities": {"tools": {}, "resources": {}, "prompts": {}}, "serverInfo": SERVER_INFO})
    if method == "ping":
        return _response(request_id, {})
    if method == "tools/list":
        return _response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params") or {}
        try:
            return _response(request_id, _dispatch_tool(str(params.get("name", "")), params.get("arguments") or {}))
        except (OSError, TypeError, ValueError, subprocess.SubprocessError) as exc:
            return _response(request_id, _tool_result({"code": "EPE-MCP-TOOL", "message": str(exc)}, True))
    if method == "resources/list":
        return _response(request_id, {"resources": [{"uri": uri, "name": relative, "mimeType": mime} for uri, (relative, mime) in RESOURCE_MAP.items()]})
    if method == "resources/read":
        uri = str((message.get("params") or {}).get("uri", ""))
        if uri not in RESOURCE_MAP:
            return _response(request_id, error={"code": -32602, "message": "unknown resource"})
        root = _root()
        relative, mime = RESOURCE_MAP[uri]
        try:
            source = _read_source(root, relative, "btae-authority")
            return _response(request_id, {"contents": [{"uri": uri, "mimeType": mime, "text": source["content"]}]})
        except (OSError, ValueError) as exc:
            return _response(request_id, error={"code": -32000, "message": str(exc)})
    if method == "prompts/list":
        return _response(request_id, {"prompts": [{"name": "btae_design_workflow", "description": "Guide a coding agent through BTAE design, traceability, implementation, and evidence."}]})
    if method == "prompts/get":
        name = str((message.get("params") or {}).get("name", ""))
        if name != "btae_design_workflow":
            return _response(request_id, error={"code": -32602, "message": "unknown prompt"})
        return _response(request_id, {"description": "BTAE design-first coding workflow", "messages": [{"role": "user", "content": {"type": "text", "text": "Follow BTAE: read the charter and bounded context, classify the work, produce a draft design/traceability plan, preserve stable IDs and ChangeSet scope, implement only after design context is explicit, run relevant checks, and report evidence plus unresolved approvals. Do not claim approved, passed, or valid without evidence."}}]})
    if request_id is None:
        return None
    return _response(request_id, error={"code": -32601, "message": f"method not found: {method}"})


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = strict_json_loads(line)
            if not isinstance(message, dict):
                raise ValueError("MCP message must be an object")
            result = dispatch(message)
            if result is not None:
                sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except (ValueError, json.JSONDecodeError) as exc:
            sys.stdout.write(json.dumps(_response(None, error={"code": -32700, "message": str(exc)}), ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0
