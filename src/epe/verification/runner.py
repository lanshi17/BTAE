from __future__ import annotations

import json
import os
import platform
import re
import shutil
from threading import Event
import xml.etree.ElementTree as ET
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from importlib.resources import files

from epe.adapters.git import git_provenance
from epe.adapters.artifact_store import ArtifactStore
from epe.adapters.process import ProcessResult, run_process
from epe.core.diagnostics import Diagnostic, Severity
from epe.core.fingerprint import build_manifest, sha256_bytes
from epe.core.models import Evidence
from epe.core.ports import ClockPort
from epe.core.json_codec import strict_json_loads
from epe.adapters.clock import SystemClock


def now(clock: ClockPort | None = None) -> str: return (clock or SystemClock()).now_utc()


def _safe_verification_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    parsed = Path(relative)
    if not isinstance(relative, str) or not relative or parsed.is_absolute() or ".." in parsed.parts or "\\" in relative:
        raise ValueError(f"验证策略路径必须是仓库相对路径: {relative}")
    current = root
    for component in parsed.parts:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"验证策略路径不能经过符号链接: {relative}")
    path = (root / relative).resolve()
    path.relative_to(root)
    return path


def _verification_policy_fingerprint(root: Path, config: dict[str, Any]) -> str:
    relative = config.get("policies", {}).get("verification", "engineering/policies/verification.yaml")
    path = _safe_verification_path(root, relative)
    return sha256_bytes(path.read_bytes())


def load_required_checks(root: Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    """Read and validate required checks without executing any commands."""
    from epe.parsers.documents import parse_yaml_bytes
    rel = config.get("policies", {}).get("verification", "engineering/policies/verification.yaml")
    try:
        path = _safe_verification_path(root, rel)
        raw, ds = parse_yaml_bytes(path.read_bytes(), str(rel))
    except (OSError, ValueError) as exc:
        return [], [Diagnostic("EPE-VERIFY-POLICY", Severity.ERROR, f"无法读取验证策略: {exc}", path=str(rel))]
    if ds:
        return [], ds
    checks = raw.get("checks") if isinstance(raw, dict) else None
    if not isinstance(checks, list) or not checks:
        return [], [Diagnostic("EPE-VERIFY-NO-CHECKS", Severity.ERROR, "验证策略必须包含必需检查", path=str(rel))]
    seen: set[str] = set()
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("id"), str) or not check["id"].strip() or not isinstance(check.get("command"), list) or not check["command"] or not all(isinstance(x, str) and x for x in check["command"]):
            return [], [Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, "必需检查必须具有非空 ID 和参数数组", path=str(rel))]
        if check["id"] in seen:
            return [], [Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"重复检查 ID: {check['id']}", path=str(rel))]
        try:
            timeout = float(check.get("timeout", 300))
            if not 0 < timeout < float("inf"):
                raise ValueError
        except (ValueError, TypeError):
            return [], [Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"检查超时必须是正有限数: {check['id']}", path=str(rel))]
        allowed_env = check.get("allowed_env")
        if allowed_env is not None and (not isinstance(allowed_env, list)
                or any(not isinstance(name, str) or not name for name in allowed_env)
                or len(set(allowed_env)) != len(allowed_env)):
            return [], [Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"allowed_env 必须是不重复的非空字符串数组: {check['id']}", path=str(rel))]
        artifacts = check.get("artifacts", check.get("expected_artifacts", []))
        if (not isinstance(artifacts, list) or any(not isinstance(item, str) or not item.strip()
                or Path(item).is_absolute() or ".." in Path(item).parts for item in artifacts)
                or len(set(artifacts)) != len(artifacts)):
            return [], [Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"产物必须为不重复的仓库相对路径数组: {check['id']}", path=str(rel))]
        seen.add(check["id"])
    from epe.core.policy import validate_policy_document
    policy_for_validation = dict(raw) if isinstance(raw, dict) else raw
    # Direct library callers historically supplied a minimal checks document;
    # retain that compatibility while still applying the full schema to its
    # fields. Repository CLI configuration always contains schema_version.
    if isinstance(policy_for_validation, dict):
        policy_for_validation.setdefault("schema_version", 1)
    policy_ds = validate_policy_document(root, policy_for_validation, "verification", str(rel))
    if policy_ds:
        return [], policy_ds
    return checks, []


def _pytest_command_supported(argv: list[str]) -> bool:
    executable = shutil.which(argv[0])
    if not executable or Path(executable).resolve() != Path(sys.executable).resolve():
        return False
    return (len(argv) >= 3 and argv[1:3] == ["-m", "pytest"]
            and not any(arg == "--junitxml" or arg.startswith("--junitxml=") or arg == "--junit-xml" or arg.startswith("--junit-xml=") for arg in argv[3:]))


def _result_from_process(proc, check: dict[str, Any], xml_path: Path | None = None) -> tuple[str, str | None, dict[str, int] | None]:
    if proc.termination_reason == "unsupported_pytest_command": return "error", "unsupported_pytest_command", None
    if proc.termination_reason == "start_error": return "error", "command_start_error", None
    if proc.cancelled or proc.termination_reason == "cancelled": return "error", "cancelled", None
    if proc.timed_out: return "error", "timeout", None
    if check.get("kind", "command") == "test":
        if check.get("result_parser") != "pytest": return "error", "unsupported_test_parser", None
        try:
            if xml_path is None: raise ValueError("missing report")
            tree = ET.parse(xml_path)
            cases = tree.getroot().iter("testcase")
            counts = {"passed": 0, "failed": 0, "skipped": 0}
            for case in cases:
                if case.find("failure") is not None or case.find("error") is not None:
                    counts["failed"] += 1
                elif case.find("skipped") is not None:
                    counts["skipped"] += 1
                else:
                    counts["passed"] += 1
            if counts["failed"]: return "failed", "test_failure_in_report", counts
            if not counts["passed"]: return "error", "test_execution_unconfirmed", counts
            if proc.returncode != 0: return "error", "pytest_nonzero_exit", counts
            return "passed", None, counts
        except (OSError, ET.ParseError, ValueError):
            return "error", "test_report_unavailable", None
    if proc.returncode != 0: return "failed", "nonzero_exit", None
    return "passed", None, None


def _redact(text: str) -> str:
    return re.sub(r"(?i)(\b(?:token|api[_-]?key|password|secret)\b\s*[=:]\s*)[^\s]+", r"\1<redacted>", text)


def _artifact_state(path: Path) -> tuple[int, int, int, int, str] | None:
    try:
        if not path.is_file():
            return None
        stat = path.stat()
        return (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, sha256_bytes(path.read_bytes()))
    except OSError:
        return None


def run_checks(root: Path, config: dict[str, Any], task_id: str | None = None, changeset_id: str | None = None, cancel_event: Event | None = None, clock: ClockPort | None = None) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    try:
        policy_fingerprint = _verification_policy_fingerprint(root, config)
    except (OSError, ValueError, TypeError) as exc:
        return [], [Diagnostic("EPE-VERIFY-POLICY", Severity.ERROR, f"无法读取验证策略指纹: {exc}")]
    checks, ds = load_required_checks(root, config)
    clock = clock or SystemClock()
    if ds:
        return [], ds
    try:
        if _verification_policy_fingerprint(root, config) != policy_fingerprint:
            return [], [Diagnostic("EPE-VERIFY-POLICY-CHANGED", Severity.ERROR, "读取期间验证策略发生变化")]
    except (OSError, ValueError, TypeError) as exc:
        return [], [Diagnostic("EPE-VERIFY-POLICY", Severity.ERROR, f"无法读取验证策略指纹: {exc}")]
    manifest_roots = config.get("managed", {}).get("design_roots", []) + config.get("managed", {}).get("code_roots", []) + config.get("managed", {}).get("test_roots", []) + config.get("managed", {}).get("contract_roots", []) + ["engineering/epe.yaml", "engineering/policies"]
    before = build_manifest(root, manifest_roots, tuple(config.get("exclude", [])))
    out: list[dict[str, Any]] = []
    for check in checks:
        if not isinstance(check, dict):
            ds.append(Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, "每项检查必须为对象"))
            continue
        check_id = str(check.get("id", "CHECK-UNKNOWN")); argv = check.get("command")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            ds.append(Diagnostic("EPE-VERIFY-COMMAND", Severity.ERROR, f"检查命令必须为参数数组: {check_id}")); continue
        allowed_env = check.get("allowed_env")
        try:
            timeout = float(check.get("timeout", 300))
            if not 0 < timeout < float("inf"):
                raise ValueError("timeout 必须是正有限数")
        except (ValueError, TypeError):
            ds.append(Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"检查超时必须是正有限数: {check_id}"))
            continue
        expected_artifacts = check.get("artifacts", check.get("expected_artifacts", []))
        artifact_before = {}
        for expected in expected_artifacts:
            try:
                artifact_path = _safe_verification_path(root, str(expected))
                artifact_before[expected] = _artifact_state(artifact_path)
            except ValueError:
                artifact_before[expected] = None
        run_id, evidence_id = f"RUN-{uuid.uuid4().hex}", f"EVIDENCE-{uuid.uuid4().hex}"
        evidence_root = config.get("storage", {}).get("evidence", "engineering/evidence")
        if not isinstance(evidence_root, str) or not evidence_root:
            ds.append(Diagnostic("EPE-VERIFY-ARTIFACT", Severity.ERROR, "Evidence 存储路径必须是非空相对路径"))
            break
        try:
            _safe_verification_path(root, evidence_root)
        except ValueError as exc:
            ds.append(Diagnostic("EPE-VERIFY-ARTIFACT", Severity.ERROR, str(exc), path=evidence_root))
            break
        run_dir_relative = f"{str(evidence_root).rstrip('/')}/{run_id}"
        staging_dir_relative = f"{str(evidence_root).rstrip('/')}/.staging-{run_id}"
        artifact_store = ArtifactStore(root)
        try:
            artifact_store.ensure_directory(staging_dir_relative)
        except (OSError, ValueError, NotImplementedError) as exc:
            ds.append(Diagnostic("EPE-VERIFY-ARTIFACT", Severity.ERROR, f"无法安全创建 Evidence 目录: {exc}"))
            break
        report_dir = root / staging_dir_relative
        xml_path = report_dir / "pytest-result.xml"
        pytest_check = check.get("kind", "command") == "test" and check.get("result_parser") == "pytest"
        effective_argv = argv + [f"--junitxml={xml_path.resolve()}"] if pytest_check else argv
        started = now(clock)
        if pytest_check and not _pytest_command_supported(argv):
            proc = ProcessResult(argv, None, "", "", 0, termination_reason="unsupported_pytest_command")
            effective_argv = []
        else:
            execution_env = None if allowed_env is None else {name: os.environ[name] for name in allowed_env if name in os.environ}
            proc = run_process(effective_argv, root, timeout, env=execution_env, cancel_event=cancel_event)
        try:
            result, reason, test_counts = _result_from_process(proc, check, xml_path if pytest_check else None)
        finally:
            xml_path.unlink(missing_ok=True)
        after = build_manifest(root, manifest_roots, tuple(config.get("exclude", [])))
        try:
            policy_changed = _verification_policy_fingerprint(root, config) != policy_fingerprint
        except (OSError, ValueError, TypeError):
            policy_changed = True
        validity = "stale" if before.digest != after.digest or policy_changed else "valid"
        try:
            artifacts: list[dict[str, Any]] = []
            bundle_files: dict[str, bytes] = {}
            log_relative = f"{run_dir_relative}/output.log"
            log_bytes = _redact(proc.stdout + ("\n--- stderr ---\n" + proc.stderr if proc.stderr else "")).encode("utf-8")
            log_digest = sha256_bytes(log_bytes)
            bundle_files["output.log"] = log_bytes
            artifacts.append({"path": log_relative, "sha256": log_digest})
            if test_counts is not None:
                summary_relative = f"{run_dir_relative}/test-summary.json"
                summary_bytes = (json.dumps(test_counts, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
                bundle_files["test-summary.json"] = summary_bytes
                artifacts.append({"path": summary_relative, "sha256": sha256_bytes(summary_bytes)})
            for expected in expected_artifacts:
                artifact_path = (root / str(expected)).resolve()
                try: artifact_path.relative_to(root.resolve())
                except ValueError:
                    result, reason = "error", "artifact_outside_root"; continue
                state = _artifact_state(artifact_path)
                if state is None:
                    result, reason = "error", "artifact_missing"; continue
                if artifact_before[expected] is not None and state == artifact_before[expected]:
                    result, reason = "error", "artifact_not_updated"; continue
                artifacts.append({"path": str(artifact_path.relative_to(root)), "sha256": state[-1]})
            provenance = {
                "git": git_provenance(root),
                # The report path is canonicalized to the eventual immutable
                # run directory; the staging command remains auditable.
                "effective_command": [arg.replace(str(report_dir.resolve()), str((root / run_dir_relative).resolve())) for arg in effective_argv],
                "executed_command": effective_argv,
                "output_truncated": {"stdout": proc.stdout_truncated, "stderr": proc.stderr_truncated},
                "verification_policy_sha256": policy_fingerprint,
                "environment_mode": "inherited" if allowed_env is None else "allowlist",
                "allowed_env": None if allowed_env is None else list(allowed_env),
            }
            if pytest_check:
                provenance["test_protocol"] = "pytest-junit-v1"
            evidence = Evidence(evidence_id, run_id, task_id, changeset_id, list(check.get("target_entities", [])), check_id, str(check.get("version", "1")), argv, str(root), started, now(clock), proc.returncode, reason, result, validity, after.to_dict(), artifacts, {"python": sys.version.split()[0], "os": platform.platform()}, provenance)
            evidence_bytes = (json.dumps(evidence.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
            bundle_files["evidence.json"] = evidence_bytes
            artifact_store.publish_bundle(run_dir_relative, bundle_files)
            import shutil
            shutil.rmtree(report_dir, ignore_errors=True)
        except (OSError, ValueError, NotImplementedError) as exc:
            ds.append(Diagnostic("EPE-VERIFY-ARTIFACT", Severity.ERROR, f"无法安全发布验证产物或 Evidence: {exc}", path=run_dir_relative))
            import shutil
            shutil.rmtree(report_dir, ignore_errors=True)
            continue
        out.append(evidence.to_dict())
    return out, ds


def _validate_evidence_record(root: Path, value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("Evidence 顶层必须为对象")
    # Older records may not have captured the environment. Keep them readable
    # so validity can conservatively become ``unknown`` instead of hiding the
    # historical result behind a parse failure.
    schema_value = dict(value)
    schema_value.setdefault("environment", {})
    try:
        import jsonschema
        schema_path = root / "engineering/schemas/evidence.schema.json"
        try:
            schema = strict_json_loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            schema = strict_json_loads(files("epe.data.schemas").joinpath("evidence.schema.json").read_text(encoding="utf-8"))
        errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(schema_value), key=lambda error: (tuple(str(p) for p in error.absolute_path), error.message))
    except (ImportError, OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Evidence Schema 不可用: {exc}") from exc
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"Evidence 字段 {location} 无效: {error.message}")


def load_evidence(root: Path, config: dict[str, Any], task_id: str | None = None) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    evidence_relative = config.get("storage", {}).get("evidence", "engineering/evidence")
    try:
        base = _safe_verification_path(root, evidence_relative)
    except ValueError as exc:
        return [], [Diagnostic("EPE-EVIDENCE-READ", Severity.ERROR, str(exc), path=str(evidence_relative))]
    found: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    if not base.exists(): return found, diagnostics
    for directory in sorted(base.glob("RUN-*")):
        path = directory / "evidence.json"
        try:
            if directory.is_symlink() or not directory.is_dir() or path.is_symlink():
                raise ValueError("运行记录路径不是普通目录或文件")
            value = strict_json_loads(path.read_text(encoding="utf-8"))
            _validate_evidence_record(root, value)
            if (not isinstance(value, dict) or value.get("run_id") != directory.name
                    or not isinstance(value.get("id"), str) or not value["id"].startswith("EVIDENCE-")
                    or not isinstance(value.get("checker"), str) or not value["checker"]
                    or not isinstance(value.get("checker_version"), str) or not value["checker_version"]
                    or not isinstance(value.get("command"), list) or not value["command"]
                    or any(not isinstance(arg, str) or not arg for arg in value["command"])
                    or not isinstance(value.get("finished_at"), str)
                    or value.get("result") not in ("passed", "failed", "error", "not_run")
                    or "task_id" not in value or "changeset_id" not in value
                    or (value.get("task_id") is not None and (not isinstance(value.get("task_id"), str) or not value["task_id"]))
                    or (value.get("changeset_id") is not None and not isinstance(value.get("changeset_id"), str))):
                raise ValueError("运行记录缺少有效的识别、排序或结果字段")
            if task_id is None or value.get("task_id") == task_id: found.append(value)
        except (OSError, UnicodeError, ValueError) as exc:
            diagnostics.append(Diagnostic("EPE-EVIDENCE-READ", Severity.ERROR, f"无法读取完整运行记录: {exc}", path=str(path)))
    return found, diagnostics


def evidence_validity(root: Path, config: dict[str, Any], evidence: dict[str, Any], required_check: dict[str, Any] | None = None, clock: ClockPort | None = None) -> str:
    manifest_roots = config.get("managed", {}).get("design_roots", []) + config.get("managed", {}).get("code_roots", []) + config.get("managed", {}).get("test_roots", []) + config.get("managed", {}).get("contract_roots", []) + ["engineering/epe.yaml", "engineering/policies"]
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return "invalid"
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not artifact.get("path") or not artifact.get("sha256"):
            return "invalid"
        try:
            path = _safe_verification_path(root, str(artifact.get("path", "")))
        except ValueError:
            return "invalid"
        if not path.exists(): return "invalid"
        try: digest = sha256_bytes(path.read_bytes())
        except OSError: return "invalid"
        if digest != artifact.get("sha256"): return "invalid"
    policy_fingerprint = evidence.get("provenance", {}).get("verification_policy_sha256") if isinstance(evidence.get("provenance"), dict) else None
    if not isinstance(policy_fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", policy_fingerprint):
        return "unknown"
    try:
        if _verification_policy_fingerprint(root, config) != policy_fingerprint:
            return "stale"
    except (OSError, ValueError, TypeError):
        return "unknown"
    if required_check and required_check.get("kind") == "test" and evidence.get("result") == "passed":
        provenance = evidence.get("provenance")
        run_id = evidence.get("run_id")
        if (required_check.get("result_parser") != "pytest" or not isinstance(provenance, dict)
                or provenance.get("test_protocol") != "pytest-junit-v1"
                or not isinstance(run_id, str) or not re.fullmatch(r"RUN-[0-9a-f]{32}", run_id)
                or evidence.get("exit_code") != 0 or evidence.get("command") != required_check.get("command")):
            return "unknown"
        report_dir = root / config.get("storage", {}).get("evidence", "engineering/evidence") / run_id
        expected_xml = f"--junitxml={(report_dir / 'pytest-result.xml').resolve()}"
        if provenance.get("effective_command") != required_check["command"] + [expected_xml]:
            return "unknown"
        summary_path = report_dir / "test-summary.json"
        try:
            relative_summary = str(summary_path.relative_to(root))
            matches = [a for a in artifacts if a.get("path") == relative_summary]
            if len(matches) != 1:
                return "unknown"
            summary = strict_json_loads(summary_path.read_text(encoding="utf-8"))
            if (not isinstance(summary, dict) or set(summary) != {"passed", "failed", "skipped"}
                    or any(type(value) is not int or value < 0 for value in summary.values())
                    or summary["passed"] < 1 or summary["failed"] != 0):
                return "unknown"
        except (OSError, ValueError, TypeError):
            return "unknown"
    if evidence.get("validity") == "stale":
        return "stale"
    if evidence.get("validity") in {"invalid", "unknown"}:
        return evidence["validity"]
    environment = evidence.get("environment")
    if not isinstance(environment, dict) or not environment.get("python") or not environment.get("os") or not evidence.get("provenance"):
        return "unknown"
    if environment["python"] != sys.version.split()[0] or environment["os"] != platform.platform():
        return "unknown"
    max_age = required_check.get("max_age_seconds") if required_check is not None else None
    if max_age is not None:
        if type(max_age) is not int or max_age < 1:
            return "unknown"
        try:
            finished = datetime.fromisoformat(evidence["finished_at"].replace("Z", "+00:00"))
            current_time = datetime.fromisoformat(now(clock).replace("Z", "+00:00"))
            if finished.utcoffset() is None or current_time.utcoffset() is None:
                return "unknown"
            elapsed = (current_time.astimezone(timezone.utc) - finished.astimezone(timezone.utc)).total_seconds()
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError, OSError):
            return "unknown"
        if elapsed < 0:
            return "unknown"
        if elapsed > max_age:
            return "stale"
    current = build_manifest(root, manifest_roots, tuple(config.get("exclude", []))).digest
    return "valid" if current == evidence.get("input_manifest", {}).get("digest") else "stale"
