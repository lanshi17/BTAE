import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "skills/btae-coding-agent/scripts/check-docs-links.py"
)


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


def git_add_all(root: Path) -> None:
    _ = subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    _ = subprocess.run(["git", "add", "."], cwd=root, check=True)


def test_default_scan_covers_root_and_nested_tracked_markdown(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("[guide](docs/guide.md)\n", encoding="utf-8")
    (tmp_path / "docs/guide.md").write_text("# Guide\n", encoding="utf-8")
    git_add_all(tmp_path)

    result = run(tmp_path)

    assert result.returncode == 0
    assert "checked 2 file(s)" in result.stdout


def test_broken_link_is_a_detectable_negative_control(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/broken.md").write_text("[missing](nowhere.md)\n", encoding="utf-8")
    git_add_all(tmp_path)

    result = run(tmp_path)

    assert result.returncode == 1
    assert "broken link target: nowhere.md" in result.stdout
