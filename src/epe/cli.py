from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable

from epe import __version__
from epe.adapters.repository import Repository, default_config, load_config
from epe.adapters.storage import atomic_write_json, acquire_write_lock, WriteConflict
from epe.core.diagnostics import Diagnostic, Severity
from epe.core.models import CommandResult, ResultStatus
from epe.core.registry import build_registry
from epe.design.manager import assess_approval, validate_design, design_revision, validate_approval_record
from epe.adapters.approval_identity import verify_approval_identity
from epe.graph.builder import build_graph, build_graph_incremental, load_graph, load_historical_graph, plan_incremental
from epe.graph.builder import analyze_impact, trace_path
from epe.context.resolver import resolve_context, load_cached_context, store_cached_context
from epe.governance.gates import finalize_gate
from epe.governance.tasks import load_task, save_task, create_task, validate_task, transition_task, check_scope
from epe.governance.policies import validate_policy_files, load_workflow_requirements
from epe.core.policy import validate_policy_document
from epe.governance.baseline import capture_baseline, changeset_paths, compare_baseline, validate_changeset, transition_changeset, changeset_declaration, baseline_binding_version
from epe.parsers.documents import discover_documents, parse_yaml_bytes
from epe.parsers.python import parse_python_tree
from epe.verification.architecture import validate_architecture
from epe.verification.import_boundaries import validate_import_boundaries
from epe.verification.mapping import validate_mapping
from epe.verification.runner import evidence_validity, load_evidence, load_required_checks, run_checks
from epe.adapters.hosts.base import capability_matrix, LocalHostAdapter
from epe.adapters.hosts.hermes import HermesHostAdapter
from epe.adapters.protocol import AgentRequest
from epe.adapters.audit import append_audit, verify_audit, read_audit_events
from epe.adapters.clock import SystemClock


EXIT_CODES = {"passed": 0, "blocked": 1, "error": 3, "unsupported": 4}


def _root(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "engineering" / "epe.yaml").exists() or (candidate / ".git").exists():
            return candidate
    return current


def _safe_input(root: Path, relative: str) -> Path:
    raw = root / relative
    current = root
    for component in Path(relative).parts:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"路径不能经过符号链接: {relative}")
    candidate = raw.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"路径越界: {relative}") from exc
    return candidate


def _append_state_audit(root: Path, config: dict[str, Any], event_type: str, payload: dict[str, Any]) -> None:
    """Append a lifecycle event to the configured hash-chain audit log."""
    audit_path = _safe_input(root, config.get("storage", {}).get("audit", "engineering/audit/events.jsonl"))
    append_audit(audit_path, event_type, payload)


def _result(command: str, status: str, diagnostics: list[Diagnostic] | None = None, data: Any = None, evidence_ids: list[str] | None = None) -> CommandResult:
    unique: list[Diagnostic] = []; seen: set[tuple] = set()
    for diagnostic in diagnostics or []:
        key = (diagnostic.code, diagnostic.path, diagnostic.line, diagnostic.message, diagnostic.entity_id)
        if key not in seen: seen.add(key); unique.append(diagnostic)
    return CommandResult(command, status, unique, data if data is not None else {}, evidence_ids or [])


def _print(result: CommandResult, fmt: str) -> int:
    obj = _normalize_result(result)
    if fmt == "json":
        print(json.dumps(obj, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{obj['command']}: {obj['status']}")
        for d in obj["diagnostics"]:
            loc = f" [{d.get('path')}" + (f":{d['line']}" if d.get("line") else "") + "]" if d.get("path") else ""
            print(f"- {d.get('severity', 'error')} {d.get('code')}: {d.get('message')}{loc}")
        if obj["data"] not in ({}, None): print(json.dumps(obj["data"], ensure_ascii=False, indent=2, sort_keys=True))
        if obj["evidence_ids"]: print("evidence: " + ", ".join(obj["evidence_ids"]))
    codes = {d.get("code") for d in obj["diagnostics"]}
    if "EPE-WRITE-CONFLICT" in codes:
        return 5
    parameter_prefixes = ("EPE-CONFIG", "EPE-POLICY-CONFIG", "EPE-TASK-TYPE", "EPE-TASK-ID", "EPE-TASK-STATUS", "EPE-TASK-REQUIRED", "EPE-TASK-RISK", "EPE-TASK-ACCEPTANCE", "EPE-TASK-OBJECTIVE", "EPE-TASK-TARGET", "EPE-TASK-CHANGESET", "EPE-TASK-REVISION", "EPE-TASK-WORKFLOW", "EPE-PATH-OUTSIDE", "EPE-PATH-SYMLINK", "EPE-ENTITY-ID")
    if obj["status"] == "error" and any(str(code).startswith(parameter_prefixes) for code in codes):
        return 2
    return EXIT_CODES.get(obj["status"], 3)


def _normalize_result(result: CommandResult) -> dict[str, Any]:
    """Validate the public result contract before emitting any format."""
    try:
        obj = result.to_dict()
        import jsonschema
        schema = json.loads(files("epe.data.schemas").joinpath("command-result.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(obj)
        json.dumps(obj, ensure_ascii=False, sort_keys=True)
        return obj
    except Exception as exc:
        fallback = CommandResult("internal", "error", [Diagnostic("EPE-RESULT-SCHEMA", Severity.ERROR, f"命令结果不符合公共契约: {exc}")]).to_dict()
        # The fallback is deliberately built only from JSON-native fields.
        return fallback


def _load_registry(root: Path, config: dict[str, Any]):
    docs = discover_documents(root, config.get("managed", {}).get("design_roots", ["docs"]))
    candidates = [(d.frontmatter, d.path, 1) for d in docs if d.is_entity and d.frontmatter is not None]
    ds = [x for d in docs for x in d.diagnostics]
    relation_candidates: list[tuple[dict, str]] = []
    # Engineering relation/entity manifests are optional authority files. Policy, schema,
    # workflow and generated directories are intentionally excluded from this scan.
    engineering = root / "engineering"
    if engineering.exists():
        for path in sorted(engineering.rglob("*.yaml")) + sorted(engineering.rglob("*.yml")) + sorted(engineering.rglob("*.json")):
            rel = path.relative_to(root).as_posix()
            if any(part in {"schemas", "policies", "workflows", "templates", "tasks", "changesets", "approvals", "evidence"} for part in path.relative_to(engineering).parts):
                continue
            try:
                value, pds = parse_yaml_bytes(path.read_bytes(), rel) if path.suffix != ".json" else (json.loads(path.read_text(encoding="utf-8")), [])
            except (OSError, json.JSONDecodeError) as exc:
                ds.append(Diagnostic("EPE-RELATION-PARSE", Severity.ERROR, str(exc), path=rel)); continue
            ds.extend(pds)
            if not isinstance(value, dict): continue
            items = value.get("entities", []) if isinstance(value.get("entities"), list) else ([value] if "id" in value else [])
            candidates.extend((item, rel, 1) for item in items if isinstance(item, dict) and isinstance(item.get("type"), str) and item.get("type") in {"Intent", "Spec", "Architecture", "Module", "Component", "Class", "Contract", "ADR", "Source", "Symbol", "API", "DataModel", "Test", "Evaluation", "Evidence"})
            relations = value.get("relations", [])
            if isinstance(relations, list): relation_candidates.extend((item, rel) for item in relations if isinstance(item, dict))
    built = build_registry(candidates, relation_candidates)
    built.diagnostics = ds + built.diagnostics
    built.complete = built.complete and not any(x.is_error for x in ds)
    return built


def _config_or_result(root: Path, command: str):
    config, ds = load_config(root)
    if config is None or any(d.is_error for d in ds): return None, _result(command, "error", ds)
    return config, None


def _init_path_has_symlink(root: Path, relative: str) -> bool:
    current = root
    for component in Path(relative).parts:
        current = current / component
        if current.is_symlink():
            return True
    return False


def cmd_init(args) -> CommandResult:
    root = _root(args.root); cfg = default_config(); targets = {
        "engineering/epe.yaml": cfg,
        "engineering/policies/architecture.yaml": {"schema_version": 1, "forbidden_dependencies": []},
        "engineering/policies/verification.yaml": {"schema_version": 1, "checks": []},
        "engineering/workflows/feature.yaml": {"schema_version": 1, "type": "feature", "required": ["objective", "acceptance", "target_entities"]},
        "engineering/workflows/bugfix.yaml": {"schema_version": 1, "type": "bugfix", "required": ["objective", "acceptance", "target_entities", "reproduction"]},
        "engineering/workflows/refactor.yaml": {"schema_version": 1, "type": "refactor", "required": ["objective", "acceptance", "target_entities", "baseline_manifest"]},
        "engineering/workflows/exploration.yaml": {"schema_version": 1, "type": "exploration", "required": ["objective", "acceptance", "target_entities", "hypothesis"]},
    }
    template_defaults = {
        "engineering/templates/task.yaml": "schema_version: 1\nid: TASK-001\ntype: feature\nobjective: \"\"\nacceptance: []\nrisk: low\ntarget_entities: []\nstatus: planned\n",
        "engineering/templates/changeset.yaml": "schema_version: 1\nid: CHANGE-001\ntask: TASK-001\nowner: \"\"\naffected_entities: []\nwrite_scope: []\nprotected: []\ndependencies: []\nstatus: planned\n",
        "engineering/templates/approval.yaml": "schema_version: 1\nid: APPROVAL-001\nentity_id: CLASS-001\nrevision: \"\"\ndecision: approved\nidentity:\n  id: \"\"\nauthorization_source: \"\"\ntimestamp: \"\"\nrisk_scope: [low]\nsignature: \"\"\n",
        "engineering/templates/evidence.yaml": "schema_version: 1\nid: EVIDENCE-001\nrun_id: RUN-001\ntarget_entities: []\nchecker: \"\"\nchecker_version: \"1\"\ncommand: []\ncwd: \"\"\nstarted_at: \"\"\nfinished_at: \"\"\nresult: not_run\nvalidity: unknown\ninput_manifest: {}\nartifacts: []\nenvironment: {}\nprovenance: {}\n",
        "engineering/templates/architecture.md": "---\nid: ARCH-001\ntype: Architecture\nname: \"\"\ndesign_status: draft\nimplementation_status: not_started\nverification_status: pending\n---\n\n# Architecture\n\n## Boundary\n\n## Constraints\n",
        "engineering/templates/module.md": "---\nid: MOD-001\ntype: Module\nname: \"\"\ndesign_status: draft\nimplementation_status: not_started\nverification_status: pending\n---\n\n# Module\n\n## Responsibility\n\n## Dependencies\n",
        "engineering/templates/component.md": "---\nid: COMP-001\ntype: Component\nname: \"\"\ndesign_status: draft\nimplementation_status: not_started\nverification_status: pending\n---\n\n# Component\n\n## Responsibility\n",
        "engineering/templates/class.md": "---\nid: CLASS-001\ntype: Class\nname: \"\"\ndesign_status: draft\nimplementation_status: not_started\nverification_status: pending\nimplementation: []\nverification: []\n---\n\n# Class\n\n## Responsibility\n\n## Invariants\n",
        "engineering/templates/contract.yaml": "schema_version: 1\nid: CONTRACT-001\ntype: Contract\nname: \"\"\ndesign_status: draft\nimplementation_status: not_started\nverification_status: pending\nversion: 1\nschema: {}\n",
        "engineering/templates/adr.md": "---\nid: ADR-001\ntype: ADR\nname: \"\"\ndesign_status: reviewed\nimplementation_status: not_started\nverification_status: pending\n---\n\n# ADR\n\n## Context\n\n## Decision\n",
    }
    conflicts: list[Diagnostic] = []
    for rel, value in targets.items():
        path = root / rel
        if _init_path_has_symlink(root, rel):
            conflicts.append(Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, f"初始化目标路径不能包含符号链接: {rel}", path=rel)); continue
        try: path.resolve().relative_to(root)
        except ValueError:
            conflicts.append(Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, f"目标路径解析后逃出仓库根: {rel}", path=rel)); continue
        if path.exists():
            try: existing = path.read_text(encoding="utf-8")
            except OSError: existing = "<unreadable>"
            expected = yaml_dump(value)
            matches = existing == expected
            if rel.endswith(".md") and expected.startswith("---"):
                matches = existing.split("---", 2)[:2] == expected.split("---", 2)[:2]
            if not matches: conflicts.append(Diagnostic("EPE-INIT-CONFLICT", Severity.ERROR, f"目标文件已存在且内容不同: {rel}", path=rel))
    for rel, expected in template_defaults.items():
        path = root / rel
        if _init_path_has_symlink(root, rel):
            conflicts.append(Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, f"初始化目标路径不能包含符号链接: {rel}", path=rel)); continue
        try: path.resolve().relative_to(root)
        except ValueError:
            conflicts.append(Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, f"目标路径解析后逃出仓库根: {rel}", path=rel)); continue
        if path.exists():
            try: existing = path.read_text(encoding="utf-8")
            except OSError: existing = "<unreadable>"
            matches = existing == expected
            if rel.endswith(".md") and expected.startswith("---"):
                matches = existing.split("---", 2)[:2] == expected.split("---", 2)[:2]
            if not matches: conflicts.append(Diagnostic("EPE-INIT-CONFLICT", Severity.ERROR, f"目标文件已存在且内容不同: {rel}", path=rel))
    if conflicts: return _result("init", "blocked", conflicts, {"created": []})
    if _init_path_has_symlink(root, ".engineering"):
        return _result("init", "blocked", [Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, "初始化派生目录不能是符号链接: .engineering", path=".engineering")], {"created": []})
    created: list[str] = []
    created_files: list[tuple[Path, int, int]] = []

    def rollback_created_files() -> None:
        for path, device, inode in reversed(created_files):
            try:
                stat = path.lstat()
                if (stat.st_dev, stat.st_ino) == (device, inode):
                    path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    try:
        try:
            lock = _safe_input(root, ".engineering/.write.lock")
        except ValueError as exc:
            return _result("init", "blocked", [Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, str(exc), path=".engineering")], {"created": []})
        with acquire_write_lock(lock):
            for rel, value in targets.items():
                path = root / rel
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("x", encoding="utf-8") as handle:
                        handle.write(yaml_dump(value)); handle.flush(); os.fsync(handle.fileno())
                        stat = os.fstat(handle.fileno())
                    created_files.append((path, stat.st_dev, stat.st_ino))
                    created.append(rel)
            for rel, value in template_defaults.items():
                path = root / rel
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("x", encoding="utf-8") as handle:
                        handle.write(value); handle.flush(); os.fsync(handle.fileno())
                        stat = os.fstat(handle.fileno())
                    created_files.append((path, stat.st_dev, stat.st_ino))
                    created.append(rel)
            for rel in ["engineering/tasks", "engineering/changesets", "engineering/approvals", "engineering/evidence", "engineering/audit", ".engineering"]:
                if _init_path_has_symlink(root, rel):
                    rollback_created_files()
                    return _result("init", "blocked", [Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, f"初始化目录不能包含符号链接: {rel}", path=rel)], {"created": []})
                (root / rel).mkdir(parents=True, exist_ok=True)
    except WriteConflict as exc:
        rollback_created_files()
        return _result("init", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc))], {"created": []})
    except FileExistsError as exc:
        rollback_created_files()
        return _result("init", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, f"初始化并发冲突: {exc}")], {"created": []})
    except OSError as exc:
        rollback_created_files()
        return _result("init", "error", [Diagnostic("EPE-INIT-STORE", Severity.ERROR, str(exc))], {"created": created})
    return _result("init", "passed", data={"created": created})


def yaml_dump(value: Any) -> str:
    import yaml
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def cmd_inspect(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "inspect")
    if failure: return failure
    built = _load_registry(root, config)
    states: dict[str, int] = {}
    for entity in built.registry.entities.values(): states[entity.implementation_status or "unknown"] = states.get(entity.implementation_status or "unknown", 0) + 1
    return _result("inspect", "error" if any(d.is_error for d in built.diagnostics) else "passed", built.diagnostics, {"root": str(root), "project_id": config.get("project_id"), "managed": config.get("managed", {}), "entity_count": len(built.registry.entities), "implementation_states": states, "entities": sorted(built.registry.entities)})


def cmd_task_create(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "task create")
    if failure: return failure
    try: path = _safe_input(root, args.file)
    except ValueError as exc: return _result("task create", "error", [Diagnostic("EPE-PATH-OUTSIDE", Severity.ERROR, str(exc), path=args.file)])
    try: data, ds = parse_yaml_bytes(path.read_bytes(), str(path.relative_to(root)))
    except OSError as exc: return _result("task create", "error", [Diagnostic("EPE-TASK-FILE", Severity.ERROR, str(exc), path=args.file)])
    if ds or not isinstance(data, dict): return _result("task create", "error", ds or [Diagnostic("EPE-TASK-TYPE", Severity.ERROR, "任务文件必须为对象")])
    task, tds = validate_task(data)
    if task is None: return _result("task create", "error", tds)
    if task.status != "planned" or task.revision != 1:
        return _result("task create", "blocked", [Diagnostic("EPE-TASK-INITIAL-STATE", Severity.ERROR, "新任务必须从 planned、revision 1 开始")])
    try:
        lock = _safe_input(root, config.get("storage", {}).get("derived", ".engineering") + "/.write.lock")
        with acquire_write_lock(lock):
            from epe.governance.tasks import task_path
            if task_path(root, config, task.id).exists():
                return _result("task create", "blocked", [Diagnostic("EPE-TASK-DUPLICATE", Severity.ERROR, f"任务 ID 已存在: {task.id}", entity_id=task.id)])
            create_task(root, config, task)
            from epe.core.fingerprint import sha256_json
            _append_state_audit(root, config, "task_created", {
                "task_id": task.id, "status": task.status, "revision": task.revision,
                "record_sha256": sha256_json(task.to_dict()),
            })
    except WriteConflict as exc:
        return _result("task create", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc))])
    except FileExistsError:
        return _result("task create", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, f"任务 ID 并发冲突: {task.id}", entity_id=task.id)])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return _result("task create", "error", [Diagnostic("EPE-AUDIT-WRITE", Severity.ERROR, f"任务已写入但无法登记审计: {exc}")])
    return _result("task create", "passed", tds, task.to_dict())


def cmd_task_classify(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "task classify")
    if failure: return failure
    task, ds = load_task(root, config, args.task_id)
    if task is None: return _result("task classify", "error", ds)
    required, workflow_ds = load_workflow_requirements(root, task.type)
    if workflow_ds:
        return _result("task classify", "error", workflow_ds, {"id": task.id, "type": task.type})
    missing = [field for field in required or () if not task.raw.get(field)]
    return _result("task classify", "blocked" if missing else "passed", [Diagnostic("EPE-TASK-INCOMPLETE", Severity.ERROR, "任务缺少必要字段: " + ", ".join(missing))] if missing else [], {"id": task.id, "type": task.type, "risk": task.risk, "missing": missing, "confidence": "declared"})


def cmd_task_transition(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "task transition")
    if failure: return failure
    if args.gate is not None:
        return _result("task transition", "blocked", [Diagnostic("EPE-TASK-GATE-UNTRUSTED", Severity.ERROR, "不接受调用者声明门禁结果；完成时自动执行综合检查")])
    try:
        lock = _safe_input(root, config.get("storage", {}).get("derived", ".engineering") + "/.write.lock")
        with acquire_write_lock(lock):
            task, diagnostics = load_task(root, config, args.task_id)
            if task is None: return _result("task transition", "error", diagnostics)
            workflow_requirements, workflow_diagnostics = load_workflow_requirements(root, task.type)
            if workflow_diagnostics:
                return _result("task transition", "error", workflow_diagnostics, {"task_id": task.id, "status": task.status})
            if args.expected_revision is not None and task.revision != args.expected_revision:
                return _result("task transition", "blocked", [Diagnostic("EPE-TASK-REVISION", Severity.ERROR, f"任务 revision 冲突，当前为 {task.revision}")])
            gate_status = None
            if args.event == "complete":
                from argparse import Namespace
                from epe.core.fingerprint import sha256_json
                original = sha256_json(task.to_dict())
                first = cmd_check(Namespace(root=str(root), task_id=task.id))
                if first.status != "passed":
                    return _result("task transition", "blocked", first.diagnostics + [Diagnostic("EPE-TASK-GATE", Severity.ERROR, "综合检查未通过，不能完成任务")], {"task_id": task.id, "status": task.status, "gate_status": first.status})
                current, diagnostics = load_task(root, config, task.id)
                if current is None or sha256_json(current.to_dict()) != original:
                    return _result("task transition", "blocked", diagnostics + [Diagnostic("EPE-TASK-REVISION", Severity.ERROR, "门禁检查期间任务已变化")])
                second = cmd_check(Namespace(root=str(root), task_id=task.id))
                if second.status != "passed":
                    return _result("task transition", "blocked", second.diagnostics + [Diagnostic("EPE-TASK-GATE", Severity.ERROR, "写入前综合检查未通过")])
                current, diagnostics = load_task(root, config, task.id)
                if current is None or sha256_json(current.to_dict()) != original:
                    return _result("task transition", "blocked", diagnostics + [Diagnostic("EPE-TASK-REVISION", Severity.ERROR, "写入前任务已变化")])
                gate_status = "passed"
            updated, transition_diagnostics = transition_task(task, args.event, gate_status, args.expected_revision, workflow_requirements)
            if transition_diagnostics: return _result("task transition", "blocked", transition_diagnostics, {"task_id": task.id, "status": task.status})
            assert updated is not None
            save_task(root, config, updated)
            from epe.core.fingerprint import sha256_json
            _append_state_audit(root, config, "task_transition", {
                "task_id": updated.id, "event": args.event,
                "previous_status": task.status, "status": updated.status,
                "revision": updated.revision, "record_sha256": sha256_json(updated.to_dict()),
            })
            return _result("task transition", "passed", data=updated.to_dict())
    except WriteConflict as exc:
        return _result("task transition", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc))])
    except (OSError, ValueError) as exc:
        return _result("task transition", "error", [Diagnostic("EPE-TASK-STORE", Severity.ERROR, str(exc))])


def cmd_changeset_transition(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "changeset transition")
    if failure: return failure
    try:
        change_path, _ = changeset_paths(root, config, args.changeset_id)
        lock = _safe_input(root, config.get("storage", {}).get("derived", ".engineering") + "/.write.lock")
        with acquire_write_lock(lock):
            if change_path.is_symlink():
                return _result("changeset transition", "error", [Diagnostic("EPE-CHANGESET-STORE", Severity.ERROR, "ChangeSet 记录不能是符号链接")])
            value = json.loads(change_path.read_text(encoding="utf-8"))
            task_id = value.get("task") if isinstance(value, dict) else ""
            task, tds = load_task(root, config, str(task_id))
            if task is None:
                return _result("changeset transition", "error", tds)
            validate_changeset(value, task.id)
            if value.get("id") != args.changeset_id or task.changeset != args.changeset_id:
                return _result("changeset transition", "blocked", [Diagnostic("EPE-CHANGESET-BINDING", Severity.ERROR, "Task 与 ChangeSet 未双向绑定")])
            if baseline_binding_version(root, config, value) == "legacy":
                return _result("changeset transition", "blocked", [Diagnostic("EPE-CHANGESET-LEGACY", Severity.ERROR, "旧版基线绑定状态字段，需重新登记后迁移")])
            if args.event == "complete" and task.status != "active":
                return _result("changeset transition", "blocked", [Diagnostic("EPE-CHANGESET-GATE", Severity.ERROR, "关联 Task 必须处于 active 才能完成 ChangeSet")])
            scope_ok = True
            scope_diagnostics: list[Diagnostic] = []
            if args.event == "complete":
                try:
                    actual = compare_baseline(root, config, value)
                    scope_ok, violations = check_scope(actual, value["write_scope"], value["protected"])
                    if violations:
                        scope_diagnostics.append(Diagnostic("EPE-GATE-SCOPE", Severity.ERROR, "实际修改超出 ChangeSet 范围: " + ", ".join(violations)))
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    scope_ok = False
                    scope_diagnostics.append(Diagnostic("EPE-SCOPE-BASELINE", Severity.ERROR, f"无法验证 ChangeSet 基线或范围: {exc}"))
            updated, errors = transition_changeset(value, args.event, args.expected_revision, scope_ok)
            if errors:
                code = "EPE-CHANGESET-REVISION" if any("revision" in item for item in errors) else "EPE-CHANGESET-TRANSITION"
                return _result("changeset transition", "blocked", scope_diagnostics + [Diagnostic(code, Severity.ERROR, item) for item in errors])
            assert updated is not None
            if args.event == "complete":
                from argparse import Namespace
                from epe.core.fingerprint import sha256_json
                task_digest = sha256_json(task.to_dict())
                change_digest = sha256_json(value)
                gate = cmd_check(Namespace(root=str(root), task_id=task.id))
                if gate.status != "passed":
                    return _result("changeset transition", "blocked", gate.diagnostics + [Diagnostic("EPE-CHANGESET-GATE", Severity.ERROR, "综合检查未通过，不能完成 ChangeSet")])
                current_task, task_diagnostics = load_task(root, config, task.id)
                if current_task is None or sha256_json(current_task.to_dict()) != task_digest or sha256_json(json.loads(change_path.read_text(encoding="utf-8"))) != change_digest:
                    return _result("changeset transition", "blocked", task_diagnostics + [Diagnostic("EPE-CHANGESET-REVISION", Severity.ERROR, "门禁检查期间 Task 或 ChangeSet 已变化")])
            atomic_write_json(change_path, updated)
            from epe.core.fingerprint import sha256_json
            _append_state_audit(root, config, "changeset_transition", {
                "changeset_id": updated["id"], "task_id": updated["task"], "event": args.event,
                "previous_status": value["status"], "status": updated["status"],
                "revision": updated["revision"], "record_sha256": sha256_json(updated),
            })
            return _result("changeset transition", "passed", scope_diagnostics, updated)
    except WriteConflict as exc:
        return _result("changeset transition", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc))])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _result("changeset transition", "error", [Diagnostic("EPE-CHANGESET-TRANSITION", Severity.ERROR, str(exc))])


def cmd_changeset_create(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "changeset create")
    if failure: return failure
    try:
        path = _safe_input(root, args.file)
        value, diagnostics = parse_yaml_bytes(path.read_bytes(), str(path.relative_to(root)))
        if diagnostics: return _result("changeset create", "error", diagnostics)
        if not isinstance(value, dict): raise ValueError("ChangeSet 文件必须是对象")
        task, diagnostics = load_task(root, config, str(value.get("task", "")))
        if task is None: return _result("changeset create", "error", diagnostics)
        validate_changeset(value, task.id)
        if task.changeset != value["id"]: raise ValueError("任务关联的 ChangeSet ID 不匹配")
        if value.get("baseline_manifest") is not None: raise ValueError("登记时不得自带基线摘要")
        change_path, baseline_path = changeset_paths(root, config, value["id"])
        lock = _safe_input(root, config.get("storage", {}).get("derived", ".engineering") + "/.write.lock")
        with acquire_write_lock(lock):
            if change_path.exists() or change_path.is_symlink() or baseline_path.exists() or baseline_path.is_symlink():
                return _result("changeset create", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, "ChangeSet 或基线已存在")])
            first = capture_baseline(root, config, value["id"])
            second = capture_baseline(root, config, value["id"])
            if first != second: raise ValueError("登记期间输入发生变化，未创建基线")
            value["schema_version"] = 1
            from epe.core.fingerprint import sha256_json
            first["digest"] = sha256_json({"entries": first["entries"], "changeset": changeset_declaration(value)})
            value["baseline_manifest"] = first["digest"]
            change_path.parent.mkdir(parents=True, exist_ok=True)
            # O_EXCL prevents replacing existing authority files even if another
            # writer ignores the advisory EPE lock.
            created: list[tuple[Path, int, int]] = []
            try:
                for target, content in ((baseline_path, first), (change_path, value)):
                    with target.open("x", encoding="utf-8") as handle:
                        stat = os.fstat(handle.fileno())
                        created.append((target, stat.st_dev, stat.st_ino))
                        json.dump(content, handle, ensure_ascii=False, sort_keys=True, indent=2)
                        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            except Exception:
                for target, device, inode in reversed(created):
                    try:
                        stat = target.lstat()
                        if (stat.st_dev, stat.st_ino) == (device, inode): target.unlink()
                    except FileNotFoundError:
                        pass
                raise
        try:
            from epe.core.fingerprint import sha256_json
            _append_state_audit(root, config, "changeset_created", {
                "changeset_id": value["id"], "task_id": value["task"], "status": value["status"],
                "revision": value.get("revision", 1), "record_sha256": sha256_json(value),
                "baseline_sha256": sha256_json(first),
            })
        except (OSError, ValueError, TypeError, KeyError) as exc:
            return _result("changeset create", "error", [Diagnostic("EPE-AUDIT-WRITE", Severity.ERROR, f"ChangeSet 已写入但无法登记审计: {exc}")])
        return _result("changeset create", "passed", data={"id": value["id"], "baseline_manifest": first["digest"], "baseline_path": str(baseline_path.relative_to(root)), "excluded": [".git", ".engineering", "virtual environments", "caches", "reports", "evidence", "this changeset's records"]})
    except FileExistsError as exc:
        return _result("changeset create", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc))])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return _result("changeset create", "error", [Diagnostic("EPE-CHANGESET-CREATE", Severity.ERROR, str(exc))])
    except WriteConflict as exc:
        return _result("changeset create", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc))])


def cmd_design_validate(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "design validate")
    if failure: return failure
    built = _load_registry(root, config); data, ds = validate_design(built.registry, args.entity_id, root); all_ds = built.diagnostics + ds
    return _result("design validate", "error" if any(d.is_error for d in all_ds) else "passed", all_ds, data)


def cmd_design_create(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "design create")
    if failure: return failure
    entity_id = args.entity_id
    prefixes = {"INTENT-": ("docs/intent/generated", "Intent", "Intent"), "SPEC-": ("docs/intent/requirements/generated", "Spec", "Spec"), "ARCH-": ("docs/architecture/generated", "Architecture", "Architecture"), "MOD-": ("docs/modules/generated", "Module", "Module"), "COMP-": ("docs/components/generated", "Component", "Component"), "CLASS-": ("docs/classes/generated", "Class", "Class"), "CONTRACT-": ("engineering/contracts", "Contract", "Contract"), "ADR-": ("docs/architecture/decisions", "ADR", "ADR")}
    selected = next(((directory, typ, title) for prefix, (directory, typ, title) in prefixes.items() if entity_id.startswith(prefix)), None)
    if selected is None or not re.fullmatch(r"[A-Z]+-[A-Z0-9][A-Z0-9_-]*", entity_id):
        return _result("design create", "error", [Diagnostic("EPE-DESIGN-ID", Severity.ERROR, f"不支持或非法设计 ID: {entity_id}")])
    directory, typ, title = selected
    suffix = ".yaml" if typ == "Contract" else ".md"
    try: target = _safe_input(root, f"{directory}/{entity_id}{suffix}")
    except ValueError as exc: return _result("design create", "error", [Diagnostic("EPE-PATH-OUTSIDE", Severity.ERROR, str(exc))])
    if target.exists() or target.is_symlink():
        return _result("design create", "blocked", [Diagnostic("EPE-INIT-CONFLICT", Severity.ERROR, f"设计文件已存在: {target.relative_to(root)}", entity_id=entity_id, path=str(target.relative_to(root)))])
    name = re.sub(r"[-_]", " ", entity_id.split("-", 1)[-1]).title()
    if typ == "Contract":
        content = yaml_dump({"schema_version": 1, "id": entity_id, "type": typ, "name": name, "design_status": "draft", "implementation_status": "not_started", "verification_status": "pending", "version": 1, "schema": {}})
    else:
        content = "---\n" + yaml_dump({"id": entity_id, "type": typ, "name": name, "design_status": "draft", "implementation_status": "not_started", "verification_status": "pending"}) + "---\n\n# " + title + "\n\n## Responsibility\n\n## Constraints\n"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            handle.write(content); handle.flush(); os.fsync(handle.fileno())
    except FileExistsError:
        return _result("design create", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, "设计文件并发冲突", path=str(target.relative_to(root)))])
    except OSError as exc:
        return _result("design create", "error", [Diagnostic("EPE-DESIGN-STORE", Severity.ERROR, str(exc), path=str(target.relative_to(root)))])
    return _result("design create", "passed", data={"id": entity_id, "type": typ, "path": str(target.relative_to(root)), "design_status": "draft"})


def cmd_design_approve(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "design approve")
    if failure: return failure
    built = _load_registry(root, config); entity = built.registry.get(args.entity_id)
    if entity is None: return _result("design approve", "error", [Diagnostic("EPE-DESIGN-MISSING", Severity.ERROR, f"实体不存在: {args.entity_id}")])
    design_data, design_diagnostics = validate_design(built.registry, args.entity_id, root)
    if any(d.is_error for d in built.diagnostics + design_diagnostics):
        return _result("design approve", "error", built.diagnostics + design_diagnostics)
    revision = design_data["revision"]
    try: path = _safe_input(root, args.record)
    except ValueError as exc: return _result("design approve", "error", [Diagnostic("EPE-PATH-OUTSIDE", Severity.ERROR, str(exc), path=args.record)])
    try: record, ds = parse_yaml_bytes(path.read_bytes(), str(path.relative_to(root)))
    except OSError as exc: return _result("design approve", "error", [Diagnostic("EPE-APPROVAL-FILE", Severity.ERROR, str(exc), path=args.record)])
    if ds or not isinstance(record, dict): return _result("design approve", "error", ds or [Diagnostic("EPE-APPROVAL-TYPE", Severity.ERROR, "审批记录必须为对象")])
    ads = validate_approval_record(record)
    if ads: return _result("design approve", "error", ads)
    if record.get("entity_id") != args.entity_id:
        return _result("design approve", "blocked", [Diagnostic("EPE-APPROVAL-ENTITY", Severity.ERROR, "审批记录 entity_id 与命令目标不一致", entity_id=args.entity_id)])
    identity_fact, error = verify_approval_identity(record, config)
    if error: return _result("design approve", "blocked", [Diagnostic("EPE-APPROVAL-IDENTITY", Severity.ERROR, error)])
    if record["decision"] == "approved":
        state, ads = assess_approval(revision, record, identity_fact)
        if state != "valid": return _result("design approve", "blocked", ads, {"revision": revision, "assessment": state})
    elif record["decision"] != "revoked":
        return _result("design approve", "blocked", [Diagnostic("EPE-APPROVAL-DECISION", Severity.ERROR, "仅支持导入批准或撤销记录")])
    try:
        approval_dir = _safe_input(root, config.get("storage", {}).get("approvals", "engineering/approvals"))
        target = approval_dir / f"{record['id']}.json"
        if record["decision"] == "revoked":
            referenced = approval_dir / f"{record['supersedes']}.json"
            if referenced.is_symlink(): raise ValueError("被撤销记录不能为符号链接")
            prior = json.loads(referenced.read_text(encoding="utf-8"))
            prior_identity, prior_error = verify_approval_identity(prior, config)
            if (prior_error or validate_approval_record(prior) or prior.get("decision") != "approved" or prior.get("entity_id") != record["entity_id"] or prior.get("revision") != record["revision"]
                    or not set(prior.get("risk_scope", [])) <= set(record["risk_scope"])
                    or not set(prior.get("risk_scope", [])) <= set(identity_fact.get("risk_scope", []))):
                raise ValueError("撤销引用的批准不存在、无效或目标不匹配")
        approval_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, TypeError) as exc:
        return _result("design approve", "error", [Diagnostic("EPE-APPROVAL-STORE", Severity.ERROR, str(exc))])
    try:
        from epe.core.fingerprint import sha256_json
        lock = _safe_input(root, config.get("storage", {}).get("derived", ".engineering") + "/.write.lock")
        with acquire_write_lock(lock):
            if target.is_symlink():
                return _result("design approve", "blocked", [Diagnostic("EPE-APPROVAL-STORE", Severity.ERROR, "审批记录不能为符号链接")])
            already_exists = target.exists()
            if already_exists:
                try: existing = json.loads(target.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError): existing = None
                if existing != record:
                    return _result("design approve", "blocked", [Diagnostic("EPE-APPROVAL-DUPLICATE", Severity.ERROR, "审批记录 ID 已存在但内容不同", path=str(target.relative_to(root)))])
            audit_rel = config.get("storage", {}).get("audit", "engineering/audit/events.jsonl")
            audit_raw = root / audit_rel
            if audit_raw.is_symlink(): raise ValueError("审计日志不能是符号链接")
            audit_path = _safe_input(root, audit_rel)
            events = read_audit_events(audit_path)
            record_digest = sha256_json(record)
            committed = any(event["event_type"] == "approval_committed" and event["payload"].get("approval_id") == record["id"] and event["payload"].get("record_sha256") == record_digest for event in events)
            if not already_exists:
                with target.open("x", encoding="utf-8") as handle:
                    json.dump(record, handle, ensure_ascii=False, sort_keys=True, indent=2)
                    handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            if not committed:
                append_audit(audit_path, "approval_committed", {"approval_id": record["id"], "entity_id": record["entity_id"], "decision": record["decision"], "revision": record["revision"], "record_sha256": record_digest})
            return _result("design approve", "passed", data={"stored": str(target.relative_to(root)), "revision": revision, "already_exists": already_exists})
    except WriteConflict as exc:
        return _result("design approve", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc))])
    except FileExistsError:
        return _result("design approve", "blocked", [Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, "审批记录并发冲突")])
    except (OSError, ValueError, TypeError) as exc:
        return _result("design approve", "error", [Diagnostic("EPE-AUDIT-WRITE", Severity.ERROR, str(exc))])


def cmd_mapping(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "mapping validate")
    if failure: return failure
    built = _load_registry(root, config); codes, pds = parse_python_tree(root, config.get("managed", {}).get("code_roots", ["src"]))
    data, ds = validate_mapping(built.registry, codes); all_ds = built.diagnostics + pds + ds
    status = "error" if any(d.is_error for d in built.diagnostics + pds) else ("blocked" if any(d.is_error for d in ds) else "passed")
    return _result("mapping validate", status, all_ds, data)


def cmd_graph(args) -> CommandResult:
    command_name = getattr(args, "command_name", "graph build")
    root = _root(args.root); config, failure = _config_or_result(root, command_name)
    if failure: return failure
    built = _load_registry(root, config)
    codes, pds = [], []
    if not getattr(args, "incremental_from", None):
        codes, pds = parse_python_tree(root, config.get("managed", {}).get("code_roots", ["src"]))
    if not built.complete or any(d.is_error for d in pds): return _result(command_name, "error", built.diagnostics + pds, {"published": False})
    previous = None
    if getattr(args, "incremental_from", None):
        try: previous = json.loads(_safe_input(root, args.incremental_from).read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc: return _result(command_name, "error", [Diagnostic("EPE-GRAPH-PREVIOUS", Severity.ERROR, str(exc), path=args.incremental_from)])
    graph = build_graph_incremental(root, built.registry, previous, config) if previous is not None else build_graph(root, built.registry, codes, config)
    all_ds = built.diagnostics + pds + graph.diagnostics
    return _result(command_name, "passed" if graph.published else ("blocked" if any(d.code == "EPE-WRITE-CONFLICT" for d in all_ds) else "error"), all_ds, {"published": graph.published, "content_digest": graph.snapshot.get("content_digest") if graph.snapshot else None, "node_count": len(graph.snapshot.get("nodes", [])) if graph.snapshot else 0, "edge_count": len(graph.snapshot.get("edges", [])) if graph.snapshot else 0})


def cmd_architecture(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "architecture validate")
    if failure: return failure
    snap, sds = load_graph(root, config)
    if snap is None: return _result("architecture validate", "error", sds)
    data, ds = _check_architecture_policy(root, config, snap)
    return _result("architecture validate", "error" if any(d.code.startswith(("EPE-ARCH-POLICY", "EPE-YAML")) for d in ds) else ("blocked" if any(d.is_error for d in ds) else "passed"), sds + ds, data)


def _check_architecture_policy(root: Path, config: dict[str, Any], snap: dict) -> tuple[dict, list[Diagnostic]]:
    rel = config.get("policies", {}).get("architecture", "engineering/policies/architecture.yaml")
    try:
        path = (root / rel).resolve()
        path.relative_to(root.resolve())
        policy, diagnostics = parse_yaml_bytes(path.read_bytes(), str(rel))
    except (OSError, ValueError) as exc:
        return {}, [Diagnostic("EPE-ARCH-POLICY", Severity.ERROR, f"无法读取架构策略: {exc}")]
    if diagnostics:
        return {}, diagnostics
    policy_diagnostics = validate_policy_document(root, policy, "architecture", str(rel))
    if policy_diagnostics:
        return {}, [Diagnostic("EPE-ARCH-POLICY", d.severity, d.message, path=d.path, line=d.line) for d in policy_diagnostics]
    if (not isinstance(policy, dict) or not isinstance(policy.get("forbidden_dependencies"), list)
            or ("unknown_is_blocking" in policy and not isinstance(policy["unknown_is_blocking"], bool))
            or any(not isinstance(rule, dict) or not isinstance(rule.get("from"), str) or not rule["from"].strip()
                   or not isinstance(rule.get("to"), str) or not rule["to"].strip() for rule in policy.get("forbidden_dependencies", []))):
        return {}, [Diagnostic("EPE-ARCH-POLICY", Severity.ERROR, "架构策略缺少有效 forbidden_dependencies 规则")]
    report, diagnostics = validate_architecture(snap, policy)
    import_report, import_diagnostics = validate_import_boundaries(root, config, policy)
    report["import_boundaries"] = import_report
    report["violations"] = list(report.get("violations", [])) + list(import_report.get("violations", []))
    diagnostics.extend(import_diagnostics)
    if any(d.is_error for d in import_diagnostics): report["status"] = "fail"
    return report, diagnostics


def cmd_verify(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "verify")
    if failure: return failure
    task, tds = load_task(root, config, args.task_id)
    if task is None: return _result("verify", "error", tds)
    evidences, ds = run_checks(root, config, task.id, task.changeset)
    from epe.core.fingerprint import sha256_bytes
    for evidence in evidences:
        try:
            evidence_root = config.get("storage", {}).get("evidence", "engineering/evidence")
            record_path = _safe_input(root, f"{evidence_root}/{evidence['run_id']}/evidence.json")
            audit_path = _safe_input(root, config.get("storage", {}).get("audit", "engineering/audit/events.jsonl"))
            append_audit(audit_path, "evidence_committed", {"run_id": evidence["run_id"], "task_id": task.id,
                         "evidence_id": evidence["id"], "record_sha256": sha256_bytes(record_path.read_bytes())})
        except (OSError, ValueError, TypeError, KeyError) as exc:
            ds.append(Diagnostic("EPE-EVIDENCE-AUDIT", Severity.ERROR, f"无法登记证据审计: {exc}"))
    return _result("verify", "error" if any(d.is_error for d in ds) or any(e.get("result") == "error" for e in evidences) else ("blocked" if any(e.get("result") != "passed" or e.get("validity") != "valid" for e in evidences) else "passed"), tds + ds, {"results": evidences}, [e["id"] for e in evidences])


def _check_evidence_audit(root: Path, config: dict[str, Any], task_id: str | None, evidences: list[dict[str, Any]]) -> list[Diagnostic]:
    from epe.core.fingerprint import sha256_bytes
    diagnostics: list[Diagnostic] = []
    try:
        audit_path = _safe_input(root, config.get("storage", {}).get("audit", "engineering/audit/events.jsonl"))
        events = read_audit_events(audit_path)
        evidence_root = config.get("storage", {}).get("evidence", "engineering/evidence")
        committed: dict[str, dict[str, Any]] = {}
        for event in events:
            if event["event_type"] != "evidence_committed": continue
            payload = event["payload"]
            run_id = payload.get("run_id")
            if (not isinstance(run_id, str) or re.fullmatch(r"RUN-[0-9a-f]{32}", run_id) is None
                    or not isinstance(payload.get("task_id"), str)
                    or not isinstance(payload.get("evidence_id"), str)
                    or not isinstance(payload.get("record_sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", payload["record_sha256"]) is None
                    or run_id in committed):
                raise ValueError("证据审计事件无效或重复")
            committed[run_id] = payload
            if task_id is not None and payload["task_id"] != task_id: continue
            record_path = _safe_input(root, f"{evidence_root}/{run_id}/evidence.json")
            if sha256_bytes(record_path.read_bytes()) != payload["record_sha256"]:
                raise ValueError(f"证据记录摘要不匹配: {run_id}")
        for evidence in evidences:
            payload = committed.get(evidence["run_id"])
            if payload is None:
                evidence["validity"] = "unknown"
            elif payload["task_id"] != evidence.get("task_id") or payload["evidence_id"] != evidence.get("id"):
                raise ValueError(f"证据记录身份不匹配: {evidence['run_id']}")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        for evidence in evidences:
            if evidence.get("validity") == "valid":
                evidence["validity"] = "unknown"
        diagnostics.append(Diagnostic("EPE-EVIDENCE-AUDIT", Severity.ERROR, f"无法核对证据审计: {exc}"))
    return diagnostics


def cmd_check(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "check")
    if failure: return failure
    task_id = args.task_id; task, tds = load_task(root, config, task_id) if task_id else (None, [])
    built = _load_registry(root, config); target_ids = task.target_entities if task else list(built.registry.entities)
    design_ok = True; design_ds: list[Diagnostic] = []
    for eid in target_ids:
        _, ds = validate_design(built.registry, eid, root); design_ds.extend(ds)
    design_ok = not any(d.is_error for d in design_ds + built.diagnostics)
    if task and task.risk in {"medium", "high"}:
        try:
            approval_dir = _safe_input(root, config.get("storage", {}).get("approvals", "engineering/approvals"))
        except (ValueError, TypeError):
            approval_dir = None
        approved_entities: set[str] = set()
        records: dict[str, tuple[dict, dict]] = {}
        committed_approvals: set[tuple[str, str]] = set()
        try:
            from epe.core.fingerprint import sha256_json
            audit_rel = config.get("storage", {}).get("audit", "engineering/audit/events.jsonl")
            if (root / audit_rel).is_symlink(): raise ValueError("审计日志不能是符号链接")
            for event in read_audit_events(_safe_input(root, audit_rel)):
                if event["event_type"] == "approval_committed":
                    payload = event["payload"]
                    committed_approvals.add((payload.get("approval_id"), payload.get("record_sha256")))
        except (OSError, ValueError, TypeError) as exc:
            design_ok = False
            design_ds.append(Diagnostic("EPE-AUDIT-INTEGRITY", Severity.ERROR, f"无法验证审批审计: {exc}"))
        if approval_dir is not None and approval_dir.exists():
            for record_path in sorted(approval_dir.glob("*.json")):
                if record_path.is_symlink(): continue
                try: record = json.loads(record_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError): continue
                if not isinstance(record, dict) or validate_approval_record(record) or record_path.name != record.get("id", "") + ".json": continue
                identity, error = verify_approval_identity(record, config)
                if error: continue
                # A signed revocation is conservatively effective even if its
                # audit commit failed; an approval must have a matching commit.
                if record["decision"] == "approved" and (record["id"], sha256_json(record)) not in committed_approvals:
                    continue
                records[record["id"]] = (record, identity)
        revoked: set[str] = set()
        for record, identity in records.values():
            if record["decision"] != "revoked": continue
            previous = records.get(record.get("supersedes"))
            if not previous: continue
            prior = previous[0]
            if (prior["decision"] == "approved" and prior["entity_id"] == record["entity_id"] and prior["revision"] == record["revision"]
                    and set(prior["risk_scope"]) <= set(record["risk_scope"]) and set(prior["risk_scope"]) <= set(identity["risk_scope"])):
                revoked.add(prior["id"])
        owner = None
        if task.changeset:
            try:
                change_path, _ = changeset_paths(root, config, task.changeset)
                if not change_path.is_symlink(): owner = json.loads(change_path.read_text(encoding="utf-8")).get("owner")
            except (OSError, ValueError, AttributeError): pass
        for record, identity in records.values():
            if record["id"] in revoked: continue
            entity = built.registry.get(str(record.get("entity_id", "")))
            if entity is None: continue
            if task.risk == "medium" and (not owner or identity["id"] == owner): continue
            try: revision = design_revision(root, entity, built.registry)
            except (OSError, ValueError): continue
            state, _ = assess_approval(revision, record, identity, task.risk)
            if state == "valid": approved_entities.add(entity.id)
        missing_approvals = [eid for eid in target_ids if eid not in approved_entities]
        if missing_approvals:
            design_ok = False
            design_ds.append(Diagnostic("EPE-GATE-APPROVAL", Severity.ERROR, f"{task.risk} 风险任务缺少适用的可信审批: {', '.join(missing_approvals)}"))
    codes, pds = parse_python_tree(root, config.get("managed", {}).get("code_roots", ["src"])); _, map_ds = validate_mapping(built.registry, codes); mapping_ok = not any(d.is_error for d in map_ds + pds)
    snap, gds = load_graph(root, config); arch_ok = False; arch_ds: list[Diagnostic] = []
    if snap:
        _, arch_ds = _check_architecture_policy(root, config, snap)
        arch_ok = not any(d.is_error for d in arch_ds)
    scope_ok = True; scope_ds: list[Diagnostic] = []
    if task is None or not task.changeset:
        scope_ok = False
        scope_ds.append(Diagnostic("EPE-CHANGESET-MISSING", Severity.ERROR, "缺少任务或关联 ChangeSet，无法核对范围"))
    if task and task.changeset:
        try:
            changeset_path, _ = changeset_paths(root, config, task.changeset)
            if changeset_path.is_symlink(): raise ValueError("ChangeSet 记录不能是符号链接")
            changeset = json.loads(changeset_path.read_text(encoding="utf-8"))
            validate_changeset(changeset, task.id)
            if changeset["id"] != task.changeset: raise ValueError("ChangeSet ID 不匹配")
            if changeset["status"] not in {"active", "completed"}: raise ValueError("ChangeSet 未激活或已中止，不能满足完成门禁")
            actual = compare_baseline(root, config, changeset)
            from epe.governance.tasks import check_scope
            scope_ok, violations = check_scope(actual, changeset["write_scope"], changeset["protected"])
            if violations: scope_ds.append(Diagnostic("EPE-GATE-SCOPE", Severity.ERROR, "实际修改超出 ChangeSet 范围: " + ", ".join(violations)))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            scope_ok = False
            scope_ds.append(Diagnostic("EPE-SCOPE-BASELINE", Severity.ERROR, f"无法验证 ChangeSet 基线或范围: {exc}"))
    evidences, evidence_ds = load_evidence(root, config, task_id)
    required_checks, policy_ds = load_required_checks(root, config)
    checks_by_id = {check["id"]: check for check in required_checks}
    for evidence in evidences:
        evidence["validity"] = evidence_validity(root, config, evidence, checks_by_id.get(evidence.get("checker")))
    evidence_ds += _check_evidence_audit(root, config, task_id, evidences)
    status, gate_ds = finalize_gate(task, design_ok, mapping_ok, arch_ok, evidences, scope_ok, required_checks)
    all_ds = tds + built.diagnostics + design_ds + pds + map_ds + gds + arch_ds + scope_ds + policy_ds + evidence_ds + gate_ds
    if any(d.is_error for d in tds + gds + policy_ds + evidence_ds): status = "error"
    return _result("check", status, all_ds, {"task_id": task_id, "design_ok": design_ok, "mapping_ok": mapping_ok, "architecture_ok": arch_ok, "evidence": evidences}, [e["id"] for e in evidences])


def cmd_unsupported(args) -> CommandResult:
    return _result(args.command_name, "unsupported", [Diagnostic("EPE-UNSUPPORTED", Severity.INFO, "该接口属于后续 V0.3/V1.0，当前未实现")])


def cmd_host_capabilities(args) -> CommandResult:
    if getattr(args, "host", None) == "hermes" and getattr(args, "command_json", None) is not None:
        try:
            command = json.loads(args.command_json)
        except (TypeError, json.JSONDecodeError) as exc:
            return _result("host capabilities", "error", [Diagnostic("EPE-HOST-COMMAND", Severity.ERROR, f"command-json 必须是 JSON 数组: {exc}")])
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
            return _result("host capabilities", "error", [Diagnostic("EPE-HOST-COMMAND", Severity.ERROR, "command-json 必须是非空字符串数组")])
        capabilities = HermesHostAdapter(command, cwd=_root(args.root)).handshake()
        status = "passed" if capabilities.status in {"handshaken", "handshaken-untrusted"} else ("unsupported" if capabilities.status == "unsupported-unintegrated" else "error")
        return _result("host capabilities", status, data={"protocol_version": "1", "hosts": [capabilities.to_dict()]})
    return _result("host capabilities", "passed", data={"protocol_version": "1", "hosts": [item.to_dict() for item in capability_matrix()]})


def cmd_host_request(args) -> CommandResult:
    root = _root(args.root)
    try:
        parameters = json.loads(args.parameters)
    except (TypeError, json.JSONDecodeError) as exc:
        return _result("host request", "error", [Diagnostic("EPE-HOST-PARAMETERS", Severity.ERROR, f"parameters 必须是 JSON 对象: {exc}")])
    if not isinstance(parameters, dict):
        return _result("host request", "error", [Diagnostic("EPE-HOST-PARAMETERS", Severity.ERROR, "parameters 必须是 JSON 对象")])
    command = args.command
    if args.command_json is not None:
        if command is not None:
            return _result("host request", "error", [Diagnostic("EPE-HOST-COMMAND", Severity.ERROR, "--command 与 --command-json 不能同时使用")])
        try:
            command = json.loads(args.command_json)
        except (TypeError, json.JSONDecodeError) as exc:
            return _result("host request", "error", [Diagnostic("EPE-HOST-COMMAND", Severity.ERROR, f"command-json 必须是 JSON 数组: {exc}")])
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
            return _result("host request", "error", [Diagnostic("EPE-HOST-COMMAND", Severity.ERROR, "command-json 必须是非空字符串数组")])
    request = AgentRequest(args.request_id, args.operation, args.task_id, args.changeset_id,
                           tuple(args.target_entity), args.expected_design_revision,
                           tuple(args.write_scope), parameters,
                           {"source": args.identity_source})
    if args.host == "local-cli":
        response = LocalHostAdapter().dispatch(request)
    elif args.host == "hermes":
        if not command:
            response = HermesHostAdapter(cwd=root).dispatch(request)
        else:
            response = HermesHostAdapter(command, cwd=root).dispatch(request)
    else:
        return _result("host request", "unsupported", [Diagnostic("EPE-HOST-UNSUPPORTED", Severity.INFO, f"不支持的宿主: {args.host}")])
    status = {"accepted": "passed", "blocked": "blocked", "unsupported": "unsupported", "error": "error"}.get(response.decision, "error")
    return _result("host request", status, response.diagnostics, data=response.to_dict(), evidence_ids=response.evidence_ids)


def cmd_audit_verify(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "audit verify")
    if failure: return failure
    try: path = _safe_input(root, config.get("storage", {}).get("audit", "engineering/audit/events.jsonl"))
    except ValueError as exc: return _result("audit verify", "error", [Diagnostic("EPE-AUDIT-PATH", Severity.ERROR, str(exc))])
    valid, error, count = verify_audit(path)
    if not valid: return _result("audit verify", "blocked", [Diagnostic("EPE-AUDIT-INTEGRITY", Severity.ERROR, error or "审计链无效", path=str(path.relative_to(root)))], {"events": count, "valid": False})
    return _result("audit verify", "passed", data={"events": count, "valid": True, "path": str(path.relative_to(root))})


def cmd_policy_validate(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "policy validate")
    if failure: return failure
    data, diagnostics = validate_policy_files(root, config)
    return _result("policy validate", "error" if any(d.is_error for d in diagnostics) else "passed", diagnostics, data)


def cmd_impact(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "impact analyze")
    if failure: return failure
    current, ds = load_graph(root, config)
    if current is None: return _result("impact analyze", "error", ds)
    if args.previous_generation is None:
        if args.new_entity is not None:
            return _result("impact analyze", "blocked", [Diagnostic("EPE-IMPACT-OPTIONS", Severity.ERROR, "--new-entity 需要 --previous-generation")])
        if not any(n.get("id") == args.entity_id for n in current.get("nodes", [])):
            return _result("impact analyze", "blocked", [Diagnostic("EPE-IMPACT-ENTITY", Severity.ERROR, f"图中不存在实体: {args.entity_id}", entity_id=args.entity_id)])
        return _result("impact analyze", "passed", data=analyze_impact(current, [args.entity_id], args.budget))
    previous, diagnostics = load_historical_graph(root, config, args.previous_generation)
    if previous is None:
        return _result("impact analyze", "error", diagnostics)
    if not any(isinstance(n, dict) and n.get("id") == args.entity_id for n in previous["nodes"]):
        return _result("impact analyze", "blocked", [Diagnostic("EPE-IMPACT-ENTITY", Severity.ERROR, f"历史图中不存在实体: {args.entity_id}", entity_id=args.entity_id)])
    if args.new_entity is not None and not any(n.get("id") == args.new_entity for n in current.get("nodes", [])):
        return _result("impact analyze", "blocked", [Diagnostic("EPE-IMPACT-ENTITY", Severity.ERROR, f"当前图中不存在实体: {args.new_entity}", entity_id=args.new_entity)])
    return _result("impact analyze", "passed", data={
        "historical": analyze_impact(previous, [args.entity_id], args.budget),
        "current": analyze_impact(current, [args.new_entity], args.budget) if args.new_entity else None,
        "historical_generation": args.previous_generation,
        "current_generation": current.get("content_digest"),
        "historical_scope": "caller_selected_not_verified_as_immediately_previous",
        "identity_mapping": "caller_supplied" if args.new_entity else "not_supplied",
    })


def cmd_graph_path(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "graph path")
    if failure: return failure
    snapshot, diagnostics = load_graph(root, config)
    if snapshot is None: return _result("graph path", "error", diagnostics)
    try:
        data = trace_path(snapshot, args.source, args.target, direction=args.direction,
                          relation_types=set(args.relation) if args.relation is not None else None, budget=args.budget)
    except ValueError as exc:
        return _result("graph path", "blocked", [Diagnostic("EPE-GRAPH-PATH", Severity.ERROR, str(exc))])
    return _result("graph path", "passed", data=data)


def cmd_impact_plan(args) -> CommandResult:
    root = _root(args.root); config, failure = _config_or_result(root, "impact plan")
    if failure: return failure
    current, diagnostics = load_graph(root, config)
    if current is None: return _result("impact plan", "error", diagnostics)
    try:
        previous_path = _safe_input(root, args.previous)
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _result("impact plan", "error", [Diagnostic("EPE-IMPACT-PREVIOUS", Severity.ERROR, str(exc), path=args.previous)])
    return _result("impact plan", "passed", data=plan_incremental(previous, current, args.parser_version, args.previous_parser_version))


def cmd_context(args) -> CommandResult:
    clock = SystemClock()
    started = clock.monotonic()
    root = _root(args.root); config, failure = _config_or_result(root, "context resolve")
    if failure: return failure
    task, tds = load_task(root, config, args.task_id)
    if task is None: return _result("context resolve", "error", tds)
    required_sources = []
    omissions = []
    for policy_name in ("architecture", "verification"):
        path = config.get("policies", {}).get(policy_name, f"engineering/policies/{policy_name}.yaml")
        try:
            relative = _safe_input(root, path).relative_to(root).as_posix()
            required_sources.append({"path": relative, "reason": f"{policy_name} 策略来源（未评估）", "source_type": "policy"})
        except (ValueError, TypeError):
            omissions.append(f"policy:{policy_name}")
    if task.changeset:
        try:
            change_path, _ = changeset_paths(root, config, task.changeset)
            if change_path.is_symlink(): raise ValueError("ChangeSet 不能是符号链接")
            change = json.loads(change_path.read_text(encoding="utf-8"))
            validate_changeset(change, task.id)
            if change.get("id") != task.changeset: raise ValueError("ChangeSet ID 不匹配")
            required_sources.append({"path": change_path.relative_to(root).as_posix(), "reason": "任务声明的 ChangeSet 范围（不构成授权）", "source_type": "changeset", "entity_id": task.changeset})
        except (OSError, ValueError, TypeError, KeyError):
            omissions.append(f"changeset:{task.changeset}")
    else:
        omissions.append("changeset:missing")
    built = _load_registry(root, config); snapshot, sds = load_graph(root, config)
    source_assessments: dict[str, Any] = {"entities": {}, "evidence": {}}
    required_checks, check_ds = load_required_checks(root, config)
    checks_by_id = {check["id"]: check for check in required_checks}
    evidences, evidence_ds = load_evidence(root, config, task.id)
    for evidence in evidences:
        evidence["validity"] = evidence_validity(root, config, evidence, checks_by_id.get(evidence.get("checker")))
    evidence_ds += _check_evidence_audit(root, config, task.id, evidences)
    for evidence in evidences:
        evidence_path = f"{config.get('storage', {}).get('evidence', 'engineering/evidence').rstrip('/')}/{evidence.get('run_id', '')}/evidence.json"
        source_assessments["evidence"][evidence_path] = {"validity": evidence["validity"]}
    data = None if omissions else load_cached_context(root, config, task, snapshot, args.budget, required_sources, source_assessments)
    cached = data is not None
    if data is None:
        data = resolve_context(root, config, task, built.registry, snapshot, args.budget, required_sources, omissions, source_assessments)
        store_cached_context(root, config, task, snapshot, args.budget, data, required_sources, source_assessments)
    data["cache"] = "hit" if cached else "miss"
    data["metrics"] = {
        "item_count": len(data.get("items", [])),
        "content_bytes": sum(len(str(item.get("content", "")).encode("utf-8")) for item in data.get("items", [])),
        "elapsed_seconds": round(clock.monotonic() - started, 6),
        "estimated_tokens": None,
        "token_estimator": "unavailable",
    }
    # Verification policy applicability is provenance input; an absent required
    # check does not make context resolution itself fail.
    all_ds = tds + built.diagnostics + sds + evidence_ds
    status = "error" if any(d.is_error for d in all_ds) else ("blocked" if data["incomplete"] else "passed")
    return _result("context resolve", status, all_ds, data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="epe", description="BTAE Engineering Protocol Engine")
    parser.add_argument("--root", default=None); parser.add_argument("--format", choices=["text", "json"], default="text")
    sub = parser.add_subparsers(dest="command", required=True)
    def common(p):
        p.add_argument("--root", default=argparse.SUPPRESS); p.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS)
    p = sub.add_parser("init"); common(p); p.set_defaults(func=cmd_init)
    p = sub.add_parser("inspect"); common(p); p.set_defaults(func=cmd_inspect)
    changeset = sub.add_parser("changeset"); common(changeset); change_commands = changeset.add_subparsers(dest="changeset_command", required=True)
    p = change_commands.add_parser("create"); common(p); p.add_argument("--file", required=True); p.set_defaults(func=cmd_changeset_create)
    p = change_commands.add_parser("transition"); common(p); p.add_argument("changeset_id"); p.add_argument("event", choices=["activate", "complete", "abort"]); p.add_argument("--expected-revision", type=int, default=None); p.set_defaults(func=cmd_changeset_transition)
    task = sub.add_parser("task"); common(task); ts = task.add_subparsers(dest="task_command", required=True)
    p = ts.add_parser("create"); common(p); p.add_argument("--file", required=True); p.set_defaults(func=cmd_task_create)
    p = ts.add_parser("classify"); common(p); p.add_argument("task_id"); p.set_defaults(func=cmd_task_classify)
    p = ts.add_parser("transition"); common(p); p.add_argument("task_id"); p.add_argument("event", choices=["activate", "complete", "abort"]); p.add_argument("--gate", default=None); p.add_argument("--expected-revision", type=int, default=None); p.set_defaults(func=cmd_task_transition)
    design = sub.add_parser("design"); common(design); ds = design.add_subparsers(dest="design_command", required=True)
    p = ds.add_parser("create"); common(p); p.add_argument("entity_id"); p.set_defaults(func=cmd_design_create)
    p = ds.add_parser("validate"); common(p); p.add_argument("entity_id"); p.set_defaults(func=cmd_design_validate)
    p = ds.add_parser("approve"); common(p); p.add_argument("entity_id"); p.add_argument("--record", required=True); p.set_defaults(func=cmd_design_approve)
    p = sub.add_parser("mapping"); common(p); ms = p.add_subparsers(dest="mapping_command", required=True); p = ms.add_parser("validate"); common(p); p.set_defaults(func=cmd_mapping)
    p = sub.add_parser("graph"); common(p); gs = p.add_subparsers(dest="graph_command", required=True); p = gs.add_parser("build"); common(p); p.add_argument("--incremental-from", default=None); p.set_defaults(func=cmd_graph)
    p = gs.add_parser("path"); common(p); p.add_argument("source"); p.add_argument("target"); p.add_argument("--direction", choices=("out", "in", "both"), default="out"); p.add_argument("--relation", action="append"); p.add_argument("--budget", type=int, default=1000); p.set_defaults(func=cmd_graph_path)
    p = sub.add_parser("architecture"); common(p); gs = p.add_subparsers(dest="architecture_command", required=True); p = gs.add_parser("validate"); common(p); p.set_defaults(func=cmd_architecture)
    p = sub.add_parser("verify"); common(p); p.add_argument("task_id"); p.set_defaults(func=cmd_verify)
    p = sub.add_parser("sync"); common(p); p.set_defaults(func=cmd_graph, command_name="sync")
    p = sub.add_parser("check"); common(p); p.add_argument("--task", dest="task_id", default=None); p.set_defaults(func=cmd_check)
    host = sub.add_parser("host"); common(host); hs = host.add_subparsers(dest="host_command", required=True)
    p = hs.add_parser("capabilities"); common(p); p.add_argument("--host", choices=("local-cli", "hermes"), default=None); p.add_argument("--command-json", default=None); p.set_defaults(func=cmd_host_capabilities)
    p = hs.add_parser("request"); common(p)
    p.add_argument("--host", choices=("local-cli", "hermes"), required=True)
    p.add_argument("--operation", choices=("start_implementation", "verify", "finalize"), required=True)
    p.add_argument("--request-id", required=True); p.add_argument("--task-id", required=True)
    p.add_argument("--changeset-id", default=None); p.add_argument("--target-entity", action="append", required=True)
    p.add_argument("--expected-design-revision", default=None); p.add_argument("--write-scope", action="append", default=[])
    p.add_argument("--identity-source", required=True); p.add_argument("--parameters", default="{}")
    p.add_argument("--command", nargs="+", default=None, help="Hermes JSON-line bridge command; argv only, no shell")
    p.add_argument("--command-json", default=None, help="Hermes bridge argv as a JSON string array")
    p.set_defaults(func=cmd_host_request)
    audit = sub.add_parser("audit"); common(audit); aus = audit.add_subparsers(dest="audit_command", required=True)
    p = aus.add_parser("verify"); common(p); p.set_defaults(func=cmd_audit_verify)
    policy = sub.add_parser("policy"); common(policy); ps = policy.add_subparsers(dest="policy_command", required=True)
    p = ps.add_parser("validate"); common(p); p.set_defaults(func=cmd_policy_validate)
    context = sub.add_parser("context"); common(context); cs = context.add_subparsers(dest="context_command", required=True)
    p = cs.add_parser("resolve"); common(p); p.add_argument("task_id"); p.add_argument("--budget", type=int, default=32); p.set_defaults(func=cmd_context)
    impact = sub.add_parser("impact"); common(impact); ims = impact.add_subparsers(dest="impact_command", required=True)
    p = ims.add_parser("analyze"); common(p); p.add_argument("entity_id"); p.add_argument("--budget", type=int, default=100); p.add_argument("--previous-generation"); p.add_argument("--new-entity"); p.set_defaults(func=cmd_impact)
    p = ims.add_parser("plan"); common(p); p.add_argument("--previous", required=True); p.add_argument("--parser-version", default="1"); p.add_argument("--previous-parser-version", default="1"); p.set_defaults(func=cmd_impact_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try: args = parser.parse_args(argv)
    except SystemExit as exc: return int(exc.code)
    result = args.func(args)
    return _print(result, getattr(args, "format", "text"))


if __name__ == "__main__": raise SystemExit(main())
