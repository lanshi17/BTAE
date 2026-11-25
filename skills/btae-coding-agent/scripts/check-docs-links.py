#!/usr/bin/env python3
"""Check Markdown links, anchors, backticked repository paths, and BTAE IDs.

Standard library only. Run from the repository root, or pass --root.

With no positional paths, scan every git-tracked Markdown file under the root.
Outside a Git worktree, fall back to a recursive glob. Untracked Markdown
must be named explicitly.

Exit codes: 0 = clean, 1 = problems found, 2 = usage or I/O error.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

DEFAULT_EXCLUDES = (
    ".git",
    ".engineering",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
)

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.*?)\s*#*\s*$")
LINK_RE = re.compile(
    r"!?\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\s*\)"
)
REF_DEF_RE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(\S+)")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HTML_ANCHOR_RE = re.compile(r"""(?:id|name)\s*=\s*["']([^"']+)["']""")

ID_PREFIXES = (
    "TASK",
    "REQ",
    "SPEC",
    "ARCH",
    "MOD",
    "COMP",
    "CLASS",
    "CONTRACT",
    "CHANGE",
    "EVIDENCE",
    "ADR",
    "RUN",
)
ID_RE = re.compile(
    r"\b(?:" + "|".join(ID_PREFIXES) + r")-[A-Za-z0-9._-]*\d[A-Za-z0-9._-]*\b"
)
ID_HEADING_RE = re.compile(
    r"^ {0,3}#{1,6}\s+(?:" + "|".join(ID_PREFIXES) + r")-[A-Za-z0-9._-]*\d[A-Za-z0-9._-]*\b"
)
ID_KEY_RE = re.compile(
    r"""(?ix)
    ^\s*
    (?:
      (?:[-*]\s+)?
      (?:task|task_id|changeset_id|related|id)\s*:\s*["']?
      |
      ["'](?:task_id|changeset_id|id)["']\s*:\s*["']
    )
    ((?:" + "|".join(ID_PREFIXES) + r")-[A-Za-z0-9._-]*\d[A-Za-z0-9._-]*)
    """
)
ID_BARE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?((?:" + "|".join(ID_PREFIXES) + r")-[A-Za-z0-9._-]*\d[A-Za-z0-9._-]*)\s*$"
)

SKIP_SCHEMES = {"http", "https", "mailto", "ftp", "data", "tel"}


def slugify(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")


def split_fences(lines: list[str]) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Return (prose, fenced) line lists as (line_number, text)."""
    prose: list[tuple[int, str]] = []
    fenced: list[tuple[int, str]] = []
    marker: str | None = None
    for number, line in enumerate(lines, start=1):
        match = FENCE_RE.match(line)
        if marker is None:
            if match:
                marker = match.group(1)[0]
                fenced.append((number, line))
            else:
                prose.append((number, line))
        else:
            fenced.append((number, line))
            if match and match.group(1)[0] == marker and len(match.group(1)) >= 3:
                marker = None
    return prose, fenced


def anchors_for(prose: list[tuple[int, str]]) -> set[str]:
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for _, line in prose:
        heading = HEADING_RE.match(line)
        if heading:
            base = slugify(heading.group(1))
            count = seen.get(base, 0)
            seen[base] = count + 1
            anchors.add(base if count == 0 else f"{base}-{count}")
        for value in HTML_ANCHOR_RE.findall(line):
            anchors.add(value)
    return anchors


def is_path_like(token: str, root: Path) -> bool:
    token = token.strip()
    if not token or any(char in token for char in " \t<>$*?{}[]|=\"'`\\,;"):
        return False
    if "://" in token or token.startswith(("/", "~", "//")):
        return False
    if "#" in token:
        return False
    if "/" not in token:
        return False
    if token.endswith("/"):
        return True
    if re.search(r"\.[A-Za-z0-9]{1,12}$", token):
        return True
    first = token.split("/", 1)[0]
    return (root / first).exists()


def resolve_target(md: Path, target: str, root: Path) -> tuple[Path | None, str]:
    raw = target.strip()
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1]
    split = urlsplit(raw)
    if split.scheme.lower() in SKIP_SCHEMES or split.netloc or raw.startswith("//"):
        return None, ""
    path_text = unquote(split.path)
    fragment = unquote(split.fragment)
    if not path_text:
        return md, fragment
    candidate = Path(path_text)
    if not candidate.is_absolute():
        candidate = md.parent / candidate
    return candidate.resolve(), fragment


def check_file(md: Path, root: Path, check_ids: bool) -> list[str]:
    try:
        text = md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{md}: cannot read: {exc}"]

    errors: list[str] = []
    lines = text.splitlines()
    prose, fenced = split_fences(lines)
    own_anchors = anchors_for(prose)
    rel_md = md.relative_to(root).as_posix()

    for number, line in prose:
        targets = [match.group(1) for match in LINK_RE.finditer(INLINE_CODE_RE.sub("", line))]
        ref_def = REF_DEF_RE.match(line)
        if ref_def:
            targets.append(ref_def.group(1))
        for target in targets:
            resolved, fragment = resolve_target(md, target, root)
            if resolved is None:
                continue
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"{rel_md}:{number}: link escapes the repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{rel_md}:{number}: broken link target: {target}")
                continue
            if fragment and resolved.is_file() and resolved.suffix.lower() == ".md":
                if re.fullmatch(r"L\d+(?:-L\d+)?", fragment):
                    continue
                if resolved == md:
                    available = own_anchors
                else:
                    try:
                        target_prose, _ = split_fences(
                            resolved.read_text(encoding="utf-8").splitlines()
                        )
                    except (OSError, UnicodeDecodeError):
                        available = set()
                    else:
                        available = anchors_for(target_prose)
                if fragment not in available:
                    errors.append(f"{rel_md}:{number}: missing anchor #{fragment} in {target}")

        for code in INLINE_CODE_RE.findall(line):
            token = code.strip()
            if is_path_like(token, root):
                bare = token.rstrip("/").split("::", 1)[0]
                candidates = [root / bare, md.parent / bare]
                if not any(candidate.exists() for candidate in candidates):
                    errors.append(f"{rel_md}:{number}: missing repository path: {token}")
                continue
            if check_ids:
                for identifier in ID_RE.findall(token):
                    if identifier.endswith(".md"):
                        continue
                    if identifier not in DECLARATIONS:
                        errors.append(
                            f"{rel_md}:{number}: undeclared ID reference: {identifier}"
                        )

    if check_ids:
        collect_declarations(md, prose, fenced)
    return errors


DECLARATIONS: set[str] = set()


def collect_declarations(
    md: Path, prose: list[tuple[int, str]], fenced: list[tuple[int, str]]
) -> None:
    for _, line in prose:
        if ID_HEADING_RE.match(line):
            DECLARATIONS.update(ID_RE.findall(line))
        key = ID_KEY_RE.match(line)
        if key:
            DECLARATIONS.add(key.group(1))
        bare = ID_BARE_RE.match(line)
        if bare:
            DECLARATIONS.add(bare.group(1))
    # A fenced example is documentation, not an authoritative declaration, but
    # it is also not a cross-reference; skip it deliberately.


def tracked_markdown(root: Path) -> list[Path] | None:
    """Return git-tracked Markdown, or None when root is not a Git worktree."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "*.md"],
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    names = [name for name in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if name]
    return [root / name for name in names if (root / name).is_file()]


def collect_files(root: Path, paths: list[str], excludes: list[str]) -> list[Path]:
    candidates: list[Path] = []
    if paths:
        for item in paths:
            target = (root / item).resolve()
            if target.is_dir():
                candidates.extend(target.rglob("*.md"))
            elif target.is_file():
                candidates.append(target)
            else:
                raise FileNotFoundError(f"path not found: {item}")
    else:
        candidates = tracked_markdown(root) or list(root.rglob("*.md"))

    selected: list[Path] = []
    for path in sorted(set(candidates)):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        parts = rel.split("/")
        if any(part in DEFAULT_EXCLUDES for part in parts):
            continue
        if any(fnmatch.fnmatch(rel, pattern) for pattern in excludes):
            continue
        selected.append(path)
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Markdown links, anchors, backticked repo paths, and BTAE IDs."
    )
    parser.add_argument("paths", nargs="*", help="files or directories (default: all git-tracked Markdown)")
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip matching repository-relative paths; repeatable",
    )
    parser.add_argument(
        "--check-ids",
        action="store_true",
        help="require backticked BTAE IDs to be declared in the scanned files",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        files = collect_files(root, args.paths, args.exclude)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not files:
        print("error: no Markdown files selected", file=sys.stderr)
        return 2

    global DECLARATIONS
    DECLARATIONS = set()
    # Definitions must be collected before references are judged.
    if args.check_ids:
        for md in files:
            try:
                prose, fenced = split_fences(md.read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeDecodeError):
                continue
            collect_declarations(md, prose, fenced)

    problems: list[str] = []
    for md in files:
        problems.extend(check_file(md, root, args.check_ids))

    if args.json:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "checked": len(files),
                    "problems": problems,
                    "ok": not problems,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for problem in problems:
            print(problem)
        print(f"checked {len(files)} file(s): {'ok' if not problems else f'{len(problems)} problem(s)'}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
