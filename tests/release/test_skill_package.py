"""Acceptance criteria for the packaged skill zip.

Adapted from life-planning-coach/tests/release/test_skill_package.py. Stdlib + pytest
only (no PyYAML — frontmatter is parsed with a minimal line scan, matching the project's
stdlib-only constraint).

The session fixture rebuilds the zip via scripts/build_skill.py, then every test validates
a single acceptance criterion against the produced archive.

Run:  python -m pytest tests/release/test_skill_package.py -q
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_NAME = "deep-research-skill"
PLUGIN_JSON = REPO_ROOT / "plugins" / SKILL_NAME / ".claude-plugin" / "plugin.json"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_skill.py"

MAX_ZIP_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB hard limit
WORD_LIMIT = 5000  # advisory SKILL.md limit (warn, not fail)
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Anything matching these must NOT appear anywhere in the archive.
FORBIDDEN_SEGMENTS = {"__pycache__", ".pytest_cache", ".mypy_cache", "tests", "evals", ".git"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo")


def _version() -> str:
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]


@pytest.fixture(scope="session")
def zip_path() -> Path:
    """Build the skill zip fresh and return its path."""
    proc = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"build failed:\n{proc.stdout}\n{proc.stderr}"
    path = REPO_ROOT / "dist" / f"{SKILL_NAME}-v{_version()}.zip"
    assert path.exists(), f"build did not produce {path}"
    return path


@pytest.fixture(scope="session")
def names(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.namelist()


# 1 — integrity
def test_zip_valid_and_extracts(zip_path: Path, tmp_path_factory):
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None, "corrupt entry (CRC mismatch)"
        out = tmp_path_factory.mktemp("extracted")
        zf.extractall(out)  # must extract without error
        assert (out / SKILL_NAME / "SKILL.md").exists()


# 2 — size
def test_zip_under_size_limit(zip_path: Path):
    size = zip_path.stat().st_size
    assert size < MAX_ZIP_SIZE_BYTES, f"{size} bytes >= {MAX_ZIP_SIZE_BYTES}"


# 3 — exactly one kebab-case root folder, no flat files at root
def test_single_kebab_root_folder(names: list[str]):
    top = {n.split("/", 1)[0] for n in names if n.strip()}
    assert top == {SKILL_NAME}, f"expected single root '{SKILL_NAME}/', got {top}"
    assert KEBAB_RE.match(SKILL_NAME), "root folder name is not kebab-case"
    flat = [n for n in names if "/" not in n.rstrip("/")]
    # the only acceptable top-level entry is the folder entry itself
    assert flat in ([], [f"{SKILL_NAME}/"]) or all(
        n == f"{SKILL_NAME}/" for n in flat
    ), f"flat files at archive root: {flat}"


# 4 — SKILL.md present inside the folder
def test_skill_md_present(names: list[str]):
    assert f"{SKILL_NAME}/SKILL.md" in names


# 5 — SKILL.md has valid frontmatter with name + description
def test_skill_md_frontmatter(zip_path: Path):
    with zipfile.ZipFile(zip_path) as zf:
        text = zf.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    assert text.startswith("---"), "SKILL.md must open with YAML frontmatter"
    end = text.find("\n---", 3)
    assert end != -1, "frontmatter not closed with '---'"
    block = text[3:end]
    keys = {line.split(":", 1)[0].strip() for line in block.splitlines() if ":" in line}
    assert "name" in keys, "frontmatter missing 'name'"
    assert "description" in keys, "frontmatter missing 'description'"


# 6 — no forbidden dev files leaked into the archive
def test_no_forbidden_files(names: list[str]):
    leaked = []
    for n in names:
        segments = n.strip("/").split("/")
        if any(seg in FORBIDDEN_SEGMENTS for seg in segments):
            leaked.append(n)
        elif n.endswith(FORBIDDEN_SUFFIXES):
            leaked.append(n)
    assert not leaked, f"forbidden files in archive: {leaked}"


# 7 — references/ present and non-empty
def test_references_present(names: list[str]):
    refs = [n for n in names if n.startswith(f"{SKILL_NAME}/references/") and not n.endswith("/")]
    assert refs, "references/ missing or empty"


# 8 — advisory word limit (warn, never fail)
def test_skill_md_word_count_advisory(zip_path: Path):
    with zipfile.ZipFile(zip_path) as zf:
        text = zf.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    wc = len(text.split())
    if wc > WORD_LIMIT:
        warnings.warn(
            f"SKILL.md is {wc} words (> advisory {WORD_LIMIT}); consider trimming.",
            stacklevel=2,
        )
    assert wc > 0  # sanity only — this criterion is advisory, not blocking
