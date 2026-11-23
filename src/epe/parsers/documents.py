from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from epe.core.diagnostics import Diagnostic, Severity
from epe.core.fingerprint import sha256_bytes


@dataclass
class DocumentParseResult:
    path: str
    frontmatter: dict[str, Any] | None
    body: str
    diagnostics: list[Diagnostic]
    is_entity: bool
    digest: str = ""
    source: str = ""


class StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: StrictLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                "found an unhashable key", key_node.start_mark) from None
        if key in mapping:
            mark = getattr(key_node, "start_mark", None)
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", mark, f"found duplicate key: {key}", mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def parse_yaml_bytes(data: bytes, path: str = "<memory>") -> tuple[Any | None, list[Diagnostic]]:
    ds: list[Diagnostic] = []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, [Diagnostic("EPE-YAML-ENCODING", Severity.ERROR, f"YAML 必须为 UTF-8: {exc}", path=path)]
    try:
        value = yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        return None, [Diagnostic("EPE-YAML-PARSE", Severity.ERROR, str(exc), path=path, line=(mark.line + 1 if mark else None))]
    return value, ds


def parse_markdown(data: bytes, path: str = "<memory>") -> DocumentParseResult:
    ds: list[Diagnostic] = []
    digest = sha256_bytes(data)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return DocumentParseResult(path, None, "", [Diagnostic("EPE-DOC-ENCODING", Severity.ERROR, f"文档必须为 UTF-8: {exc}", path=path)], False, digest, path)
    if not text.startswith("---") or not re.match(r"^---(?:\r?\n|$)", text):
        return DocumentParseResult(path, None, text, ds, False, digest, path)
    match = re.search(r"\r?\n---(?:\r?\n|$)", text[3:])
    if not match:
        return DocumentParseResult(path, None, text[3:], [Diagnostic("EPE-DOC-FRONTMATTER", Severity.ERROR, "YAML Frontmatter 未闭合", path=path, line=1)], False, digest, path)
    end = 3 + match.end()
    header = text[3:3 + match.start()]
    value, yaml_ds = parse_yaml_bytes(header.encode("utf-8"), path)
    ds.extend(yaml_ds)
    if value is None:
        return DocumentParseResult(path, None, text[end:], ds, False, digest, path)
    if not isinstance(value, dict):
        ds.append(Diagnostic("EPE-DOC-METADATA", Severity.ERROR, "Frontmatter 顶层必须为对象", path=path, line=1))
        return DocumentParseResult(path, None, text[end:], ds, False, digest, path)
    return DocumentParseResult(path, value, text[end:], ds, "id" in value or "type" in value, digest, path)


def discover_documents(root: Path, roots: Iterable[str] = ("docs",), extensions: tuple[str, ...] = (".md", ".markdown", ".yaml", ".yml", ".json")) -> list[DocumentParseResult]:
    results: list[DocumentParseResult] = []
    root = root.resolve()
    for root_name in roots:
        raw_base = root / root_name
        if raw_base.is_symlink():
            results.append(DocumentParseResult(str(raw_base), None, "", [Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, "文档根不能是符号链接", path=str(root_name))], False))
            continue
        base = raw_base.resolve()
        if not base.exists():
            continue
        for linked in sorted(p for p in base.rglob("*") if p.is_symlink()):
            results.append(DocumentParseResult(str(linked), None, "", [Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, "文档树不能包含符号链接", path=str(linked.relative_to(root)))], False))
        for path in sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in extensions):
            try:
                rel_path = path.relative_to(root)
                current = root
                linked = False
                for component in rel_path.parts:
                    current = current / component
                    if current.is_symlink():
                        linked = True; break
                if linked:
                    raise ValueError("路径经过符号链接")
                rel = path.resolve().relative_to(root).as_posix()
            except ValueError:
                results.append(DocumentParseResult(str(path), None, "", [Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, "文档路径不能经过符号链接或逃出仓库根", path=str(path))], False))
                continue
            try:
                data = path.read_bytes()
            except OSError as exc:
                results.append(DocumentParseResult(
                    rel, None, "", [Diagnostic("EPE-DOC-READ", Severity.ERROR,
                    f"无法读取文档: {exc}", path=rel)], False))
                continue
            if path.suffix.lower() in {".md", ".markdown"}:
                results.append(parse_markdown(data, rel))
            else:
                value, ds = parse_yaml_bytes(data, rel)
                results.append(DocumentParseResult(rel, value if isinstance(value, dict) else None, "", ds, isinstance(value, dict) and "id" in value))
    return results
