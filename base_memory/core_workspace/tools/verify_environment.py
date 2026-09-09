import json
from pathlib import Path


def find_manifest():
    current = Path.cwd().resolve()
    while True:
        candidate = current / "core_manifest.json"
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def main():
    cwd = Path.cwd().resolve()
    manifest_path = find_manifest()
    if manifest_path is None:
        print(json.dumps({"status": "STRUCTURALLY_INVALID", "cwd": str(cwd), "mechanism": "Could not locate core_manifest.json by parent traversal."}, indent=2))
        return 1
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "STRUCTURALLY_INVALID", "cwd": str(cwd), "manifest": str(manifest_path), "mechanism": f"Could not read valid core_manifest.json: {exc}"}, indent=2))
        return 1

    layout = manifest.get("layout")
    required = {
        "identity": ("identity", "identity.md"),
        "rules": ("identity", "rules.md"),
        "failure_modes": ("identity", "failure_modes.md"),
        "index": ("memories", "index.md"),
        "commitments": ("memories", "commitments.json"),
        "growth_plan": ("memories", "growth_plan.json"),
        "hypotheses": ("memories", "hypotheses.json"),
        "semantic_memory": ("memories", "semantic_memory.json"),
        "tool_runs": ("workspace", "tool_runs.json"),
    }
    if not isinstance(layout, dict):
        print(json.dumps({"status": "STRUCTURALLY_INVALID", "cwd": str(cwd), "manifest": str(manifest_path), "mechanism": "core_manifest.json has no valid layout mapping."}, indent=2))
        return 1

    memory_root = manifest_path.parent
    found = {}
    missing = []
    empty = []
    for label, (key, filename) in required.items():
        subdir = layout.get(key)
        if not isinstance(subdir, str) or not subdir.strip():
            missing.append(label)
            continue
        path = memory_root / subdir / filename
        if not path.is_file():
            missing.append(str(path.relative_to(memory_root)))
            continue
        size = path.stat().st_size
        found[label] = {"path": str(path), "size": size}
        if size == 0:
            empty.append(str(path.relative_to(memory_root)))

    if missing or empty:
        print(json.dumps({"status": "STRUCTURALLY_INVALID", "cwd": str(cwd), "memory_root": str(memory_root), "manifest": str(manifest_path), "missing": missing, "empty": empty, "found_files": found, "mechanism": "Resolved required files from core_manifest.json; one or more required files are missing or empty."}, indent=2))
        return 1

    print(json.dumps({"status": "STRUCTURALLY_COMPLETE", "cwd": str(cwd), "memory_root": str(memory_root), "manifest": str(manifest_path), "found_files": found, "mechanism": "Located core_manifest.json by parent traversal and resolved required core files from its declared layout."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
