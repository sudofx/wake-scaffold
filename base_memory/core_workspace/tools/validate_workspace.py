#!/usr/bin/env python3
"""Validate the active wake-scaffold memory layout from core_manifest.json.

This checks the declared layout, not an assumed flat collection of files.
Exit 0 means the advertised structural-validation capability passed.
Exit 1 means the manifest/layout is missing or structurally invalid.
"""
import json
import os
import sys
from pathlib import Path

REQUIRED_FILES = {
    "identity": ("identity.md", "rules.md", "failure_modes.md"),
    "memories": (
        "index.md",
        "commitments.json",
        "growth_plan.json",
        "hypotheses.json",
        "semantic_memory.json",
    ),
    "workspace": ("tool_runs.json",),
    "persona": ("blog/blog_posts.json", "blog/html/index.html"),
}
REQUIRED_DIRS = {
    "workspace": ("journal", "prompts", "tools"),
    "synthesis": (),
}
EXPECTED_LAYOUT_KEYS = {"identity", "memories", "workspace", "synthesis", "persona", "journal", "prompts"}


def find_manifest(start_dir: Path) -> tuple[Path | None, Path | None]:
    current = start_dir.resolve()
    for candidate in (current, *current.parents):
        manifest = candidate / "core_manifest.json"
        if manifest.is_file():
            return candidate, manifest
    return None, None


def validate_workspace(start_dir: str = ".", fallback_dir: Path | None = None) -> tuple[dict, int]:
    start = Path(start_dir).resolve()
    root, manifest_path = find_manifest(start)
    if root is None and fallback_dir is not None:
        root, manifest_path = find_manifest(fallback_dir.resolve())
    if root is None or manifest_path is None:
        report = {
            "status": "STRUCTURALLY_INVALID",
            "start_directory": str(start),
            "detected_root": None,
            "missing": ["core_manifest.json"],
            "errors": ["Could not locate core_manifest.json by walking upward."],
        }
        return report, 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = {
            "status": "STRUCTURALLY_INVALID",
            "start_directory": str(start),
            "detected_root": str(root),
            "missing": [],
            "errors": [f"Could not read valid core_manifest.json: {exc}"],
        }
        return report, 1

    layout = manifest.get("layout") if isinstance(manifest, dict) else None
    errors = []
    missing = []
    found = {}
    if not isinstance(layout, dict):
        errors.append("core_manifest.json has no layout mapping")
        layout = {}
    else:
        missing_keys = sorted(EXPECTED_LAYOUT_KEYS - set(layout))
        if missing_keys:
            errors.append("manifest layout missing keys: " + ", ".join(missing_keys))

    def path_for(rel: str) -> Path:
        return root / rel

    for key in ("identity", "memories", "workspace", "synthesis", "persona"):
        rel = layout.get(key)
        if not isinstance(rel, str) or not rel.strip():
            continue
        path = path_for(rel)
        if not path.is_dir():
            missing.append(rel + "/")
        else:
            found[key] = rel

    for key, names in REQUIRED_FILES.items():
        rel_dir = layout.get(key)
        if not isinstance(rel_dir, str):
            continue
        for name in names:
            path = path_for(rel_dir) / name
            if path.is_file() and path.stat().st_size > 0:
                found[f"{key}/{name}"] = str(path.relative_to(root))
            else:
                missing.append(str(path.relative_to(root)))

    for key, names in REQUIRED_DIRS.items():
        rel_dir = layout.get(key)
        if not isinstance(rel_dir, str):
            continue
        for name in names:
            path = path_for(rel_dir) / name
            if not path.is_dir():
                missing.append(str(path.relative_to(root)) + "/")
            else:
                found[f"{key}/{name}/"] = str(path.relative_to(root))

    # The manifest itself must describe the active memory tree.
    if not manifest_path.is_file():
        missing.append("core_manifest.json")

    valid = not errors and not missing
    report = {
        "status": "STRUCTURALLY_COMPLETE" if valid else "STRUCTURALLY_INVALID",
        "start_directory": str(start),
        "detected_root": str(root),
        "manifest": str(manifest_path.relative_to(root)),
        "identity_name": manifest.get("identity_name") if isinstance(manifest, dict) else None,
        "found": found,
        "missing": missing,
        "errors": errors,
    }
    return report, 0 if valid else 1


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    report, code = validate_workspace(target, fallback_dir=Path(__file__).resolve().parent)
    print(json.dumps(report, indent=2))
    sys.exit(code)
