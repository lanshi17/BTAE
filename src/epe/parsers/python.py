from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from epe.core.diagnostics import Diagnostic, Severity
from epe.core.fingerprint import sha256_bytes


@dataclass(frozen=True)
class SymbolRecord:
    qualified_name: str
    kind: str
    name: str
    path: str
    line: int
    end_line: int | None
    signature: str | None = None
    async_: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"qualified_name": self.qualified_name, "kind": self.kind, "name": self.name, "path": self.path, "line": self.line, "end_line": self.end_line, "signature": self.signature, "async": self.async_}


@dataclass(frozen=True)
class ImportFact:
    module: str
    names: tuple[str, ...]
    path: str
    line: int
    level: int = 0
    dynamic: bool = False
    kind: str = "import"

    def to_dict(self) -> dict[str, Any]:
        return {"module": self.module, "names": list(self.names), "path": self.path, "line": self.line, "level": self.level, "dynamic": self.dynamic, "kind": self.kind}


@dataclass
class CodeParseResult:
    path: str
    digest: str
    symbols: list[SymbolRecord]
    imports: list[ImportFact]
    diagnostics: list[Diagnostic]
    gaps: list[Diagnostic]
    complete: bool

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "digest": self.digest, "symbols": [s.to_dict() for s in self.symbols], "imports": [i.to_dict() for i in self.imports], "diagnostics": [d.to_dict() for d in self.diagnostics], "gaps": [d.to_dict() for d in self.gaps], "complete": self.complete}


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        return "(" + ast.unparse(node.args) + ")"
    except Exception:
        return None  # type: ignore[return-value]


class _Visitor(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.symbols: list[SymbolRecord] = []
        self.imports: list[ImportFact] = []
        self.gaps: list[Diagnostic] = []
        self._scope: list[str] = []

    def _qname(self, name: str) -> str:
        return ".".join(self._scope + [name])

    def visit_ClassDef(self, node: ast.ClassDef):
        q = self._qname(node.name)
        self.symbols.append(SymbolRecord(q, "class", node.name, self.path, node.lineno, getattr(node, "end_lineno", None)))
        self._scope.append(node.name); self.generic_visit(node); self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        q = self._qname(node.name)
        self.symbols.append(SymbolRecord(q, "function", node.name, self.path, node.lineno, getattr(node, "end_lineno", None), _signature(node), False))
        self._scope.append(node.name); self.generic_visit(node); self._scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        q = self._qname(node.name)
        self.symbols.append(SymbolRecord(q, "function", node.name, self.path, node.lineno, getattr(node, "end_lineno", None), _signature(node), True))
        self._scope.append(node.name); self.generic_visit(node); self._scope.pop()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ImportFact(alias.name, (alias.asname or alias.name.split(".")[0],), self.path, node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = "." * node.level + (node.module or "")
        self.imports.append(ImportFact(module, tuple(a.name for a in node.names), self.path, node.lineno, node.level, False, "from"))
        if any(a.name == "*" for a in node.names):
            self.gaps.append(Diagnostic("EPE-AST-STAR-IMPORT", Severity.WARNING, "星号导入无法确定符号边界", path=self.path, line=node.lineno))

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"__import__", "eval", "exec"}:
            self.gaps.append(Diagnostic("EPE-AST-DYNAMIC", Severity.WARNING, f"动态执行/导入: {node.func.id}", path=self.path, line=node.lineno))
        elif isinstance(node.func, ast.Attribute) and node.func.attr in {"import_module", "reload"}:
            self.gaps.append(Diagnostic("EPE-AST-DYNAMIC", Severity.WARNING, f"动态模块操作: {node.func.attr}", path=self.path, line=node.lineno))
        self.generic_visit(node)


def parse_python(data: bytes, path: str = "<memory>") -> CodeParseResult:
    digest = sha256_bytes(data)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        d = Diagnostic("EPE-AST-ENCODING", Severity.ERROR, f"Python 文件必须为 UTF-8: {exc}", path=path)
        return CodeParseResult(path, digest, [], [], [d], [], False)
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        d = Diagnostic("EPE-AST-SYNTAX", Severity.ERROR, f"Python 语法错误: {exc.msg}", path=path, line=exc.lineno)
        return CodeParseResult(path, digest, [], [], [d], [], False)
    visitor = _Visitor(path); visitor.visit(tree)
    return CodeParseResult(path, digest, sorted(visitor.symbols, key=lambda s: (s.qualified_name, s.line)), visitor.imports, [], visitor.gaps, True)


def parse_python_tree(root: Path, roots: Iterable[str] = ("src",)) -> tuple[list[CodeParseResult], list[Diagnostic]]:
    results: list[CodeParseResult] = []
    ds: list[Diagnostic] = []
    for root_name in roots:
        base = root / root_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            try:
                path.resolve().relative_to(root.resolve())
            except ValueError:
                ds.append(Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, "符号链接解析后逃出仓库根", path=str(path)))
                continue
            rel = path.relative_to(root).as_posix()
            result = parse_python(path.read_bytes(), rel)
            results.append(result); ds.extend(result.diagnostics); ds.extend(result.gaps)
    return results, ds
