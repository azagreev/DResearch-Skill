#!/usr/bin/env python3
"""Package the deep-research-skill into a .zip for Claude Desktop / claude.ai upload.

Adapted from life-planning-coach/scripts/build-skill.py. Cross-platform (pathlib),
no third-party deps. Produces a zip whose ROOT is a single kebab-case folder
(`deep-research-skill/`) — the structure the Claude apps' Skill upload requires —
with text files LF-normalized for cross-platform stability.

Usage:
    python scripts/build_skill.py            # build dist/deep-research-skill-v<version>.zip
    python scripts/build_skill.py --out DIR  # override output dir (default: dist/)

What ships vs. what is excluded is the FAITHFUL "current skill" minus non-runtime
dev artifacts (tests/evals/caches) — see EXCLUDE_* below.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "deep-research-skill"
SKILL_SRC = REPO_ROOT / "plugins" / SKILL_NAME / "skills" / SKILL_NAME
PLUGIN_JSON = REPO_ROOT / "plugins" / SKILL_NAME / ".claude-plugin" / "plugin.json"

# Non-runtime dev artifacts — excluded from the shipped skill (same philosophy as
# life-planning-coach excluding tests/scripts/caches).
EXCLUDE_DIRS = {"tests", "evals", "__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDE_FILE_SUFFIXES = (".pyc", ".pyo")
EXCLUDE_FILE_NAMES = {".DS_Store", "Thumbs.db"}

# Text files get CRLF -> LF normalization so the zip is byte-stable across OSes.
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".cfg", ".ini", ".toml"}

WORD_LIMIT = 5000  # advisory SKILL.md word limit (warn, do not fail)
FIXED_DATE = (1980, 1, 1, 0, 0, 0)  # deterministic zip timestamps


def read_version() -> str:
    data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    version = data.get("version")
    if not version:
        sys.exit(f"ERROR: no 'version' in {PLUGIN_JSON}")
    return version


def is_excluded_file(path: Path) -> bool:
    return (
        path.name in EXCLUDE_FILE_NAMES
        or path.suffix in EXCLUDE_FILE_SUFFIXES
    )


def iter_skill_files(src: Path):
    """Yield (abs_path, rel_path) for every file that should ship, pruning EXCLUDE_DIRS."""
    for dirpath, dirnames, filenames in os.walk(src):
        # prune excluded directories in place so os.walk doesn't descend into them
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for fname in sorted(filenames):
            abs_path = Path(dirpath) / fname
            if is_excluded_file(abs_path):
                continue
            rel_path = abs_path.relative_to(src)
            yield abs_path, rel_path


def stage(src: Path, staging: Path) -> int:
    """Copy shippable files into staging/<SKILL_NAME>/, LF-normalizing text. Returns count."""
    root = staging / SKILL_NAME
    if staging.exists():
        shutil.rmtree(staging)
    count = 0
    for abs_path, rel_path in iter_skill_files(src):
        dest = root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if abs_path.suffix in TEXT_SUFFIXES:
            text = abs_path.read_text(encoding="utf-8")
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            dest.write_bytes(normalized.encode("utf-8"))
        else:
            shutil.copyfile(abs_path, dest)
        count += 1
    return count


def make_zip(staging: Path, zip_path: Path) -> None:
    """Zip staging/<SKILL_NAME>/ so the archive root is the folder `<SKILL_NAME>/`."""
    root = staging / SKILL_NAME
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # explicit root folder entry
        root_info = zipfile.ZipInfo(f"{SKILL_NAME}/", date_time=FIXED_DATE)
        zf.writestr(root_info, b"")
        for abs_path, rel_path in sorted(
            ((p, p.relative_to(staging)) for p in root.rglob("*") if p.is_file()),
            key=lambda t: str(t[1]).replace(os.sep, "/"),
        ):
            arcname = str(rel_path).replace(os.sep, "/")
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, abs_path.read_bytes())


def word_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").split())


def main() -> int:
    ap = argparse.ArgumentParser(description="Package deep-research-skill into a zip.")
    ap.add_argument("--out", default=str(REPO_ROOT / "dist"), help="output dir (default: dist/)")
    args = ap.parse_args()

    if not SKILL_SRC.is_dir():
        sys.exit(f"ERROR: skill source not found: {SKILL_SRC}")

    version = read_version()
    staging = REPO_ROOT / ".build"
    out_dir = Path(args.out)
    zip_path = out_dir / f"{SKILL_NAME}-v{version}.zip"

    n_files = stage(SKILL_SRC, staging)
    make_zip(staging, zip_path)

    size = zip_path.stat().st_size
    skill_md = staging / SKILL_NAME / "SKILL.md"
    wc = word_count(skill_md) if skill_md.exists() else -1

    # verify root-folder structure of the produced zip
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    top_level = {n.split("/", 1)[0] for n in names}
    root_ok = top_level == {SKILL_NAME}

    print("=" * 60)
    print(f"  Built: {zip_path.relative_to(REPO_ROOT)}")
    print(f"  Version: {version}")
    print(f"  Size: {size / 1024:.0f} KB  ({size:,} bytes)")
    print(f"  Files: {n_files}")
    print(f"  Root folder = '{SKILL_NAME}/' only: {'OK' if root_ok else 'FAIL -> ' + str(top_level)}")
    print(f"  SKILL.md words: {wc}", end="")
    if wc > WORD_LIMIT:
        print(f"  ** WARN: exceeds advisory limit {WORD_LIMIT} **")
    else:
        print(f"  (<= {WORD_LIMIT} OK)")
    print("=" * 60)

    if not root_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
