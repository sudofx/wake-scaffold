import os
import json
from pathlib import Path

def find_repo_root():
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "memory" / "core_identity" / "identity.md").exists():
            return current
        if (current / "core_identity" / "identity.md").exists():
            return current.parent
        current = current.parent
    cwd = Path.cwd()
    for _ in range(5):
        if (cwd / "memory" / "core_identity" / "identity.md").exists():
            return cwd
        cwd = cwd.parent
    return Path.cwd()

def audit():
    root = find_repo_root()
    failures = []
    audits = {}

    md_files = [
        "memory/core_identity/identity.md",
        "memory/core_identity/rules.md",
        "memory/core_workspace/index.md"
    ]

    md_audit = {}
    for rel_path in md_files:
        full_path = root / rel_path
        exists = full_path.is_file()
        if not exists:
            failures.append(f"Missing core markdown file: {rel_path}")
            md_audit[rel_path] = {"exists": False, "size_bytes": 0}
        else:
            md_audit[rel_path] = {"exists": True, "size_bytes": full_path.stat().st_size}
    audits["markdown_files"] = md_audit

    json_files = [
        "memory/core_workspace/commitments.json",
        "memory/core_workspace/tool_runs.json"
    ]

    json_audit = {}
    for rel_path in json_files:
        full_path = root / rel_path
        if not full_path.is_file():
            failures.append(f"Missing core JSON file: {rel_path}")
            json_audit[rel_path] = {"exists": False, "valid_json": False}
        else:
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                json_audit[rel_path] = {"exists": True, "valid_json": True, "type": type(data).__name__}
                if rel_path == "memory/core_workspace/tool_runs.json":
                    if isinstance(data, list):
                        json_audit[rel_path]["record_count"] = len(data)
                    else:
                        failures.append("tool_runs.json is not a JSON list")
            except Exception as e:
                failures.append(f"Invalid JSON in {rel_path}: {e}")
                json_audit[rel_path] = {"exists": True, "valid_json": False}
    audits["json_files"] = json_audit

    tool_runs_path = root / "memory/core_workspace/tool_runs.json"
    if tool_runs_path.is_file():
        try:
            with open(tool_runs_path, "r", encoding="utf-8") as f:
                tool_runs = json.load(f)
            if isinstance(tool_runs, list):
                tools_dir = root / "tools"
                available_tools = [p.name for p in tools_dir.glob("*.py")] if tools_dir.is_dir() else []
                run_counts = {}
                for run in tool_runs:
                    fn = run.get("filename") or run.get("tool_name") or "unknown"
                    run_counts[fn] = run_counts.get(fn, 0) + 1
                audits["tool_execution_cross_validation"] = {
                    "total_recorded_runs": len(tool_runs),
                    "execution_counts_by_tool": run_counts,
                    "available_tools_on_disk": available_tools
                }
        except Exception as e:
            failures.append(f"Cross validation error: {e}")

    status = "STRUCTURALLY_COMPLETE" if not failures else "STRUCTURALLY_INVALID"
    result = {
        "workspace_root": str(root),
        "status": status,
        "failures": failures,
        "audits": audits
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    audit()
