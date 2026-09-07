import os
import json
import sys

def find_workspace_root():
    cwd = os.path.abspath(os.path.dirname(__file__))
    current = cwd
    for _ in range(5):
        for root, dirs, files in os.walk(current):
            if "identity.md" in files and "rules.md" in files:
                return os.path.abspath(root)
            if "base_memory" in dirs or "core_workspace" in dirs:
                return os.path.abspath(current)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.abspath(os.path.join(cwd, ".."))

def audit_state():
    root = find_workspace_root()
    report = {
        "workspace_root": root,
        "status": "STRUCTURALLY_COMPLETE",
        "audits": {},
        "warnings": []
    }

    md_files = ["identity.md", "rules.md", "index.md"]
    report["audits"]["markdown_files"] = {}
    for mf in md_files:
        found_path = None
        for dirpath, _, filenames in os.walk(root):
            if mf in filenames:
                found_path = os.path.relpath(os.path.join(dirpath, mf), root)
                break
        if found_path:
            size = os.path.getsize(os.path.join(root, found_path))
            report["audits"]["markdown_files"][mf] = {"exists": True, "size_bytes": size, "path": found_path}
            if size == 0:
                report["warnings"].append(f"Markdown file {mf} is empty.")
                report["status"] = "STRUCTURALLY_INVALID"
        else:
            report["audits"]["markdown_files"][mf] = {"exists": False, "size_bytes": 0, "path": None}
            report["warnings"].append(f"Markdown file {mf} missing.")
            report["status"] = "STRUCTURALLY_INVALID"

    commitments_path = None
    for dirpath, _, filenames in os.walk(root):
        if "commitments.json" in filenames:
            commitments_path = os.path.join(dirpath, "commitments.json")
            break
    
    if commitments_path and os.path.exists(commitments_path):
        try:
            with open(commitments_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            report["audits"]["commitments"] = {"exists": True, "valid_json": True, "count": len(data) if isinstance(data, list) else 0}
        except Exception as e:
            report["audits"]["commitments"] = {"exists": True, "valid_json": False, "error": str(e)}
            report["warnings"].append("commitments.json is invalid JSON.")
            report["status"] = "STRUCTURALLY_INVALID"
    else:
        report["audits"]["commitments"] = {"exists": False}

    tool_runs_path = None
    for dirpath, _, filenames in os.walk(root):
        if "tool_runs.json" in filenames:
            tool_runs_path = os.path.join(dirpath, "tool_runs.json")
            break

    if tool_runs_path and os.path.exists(tool_runs_path):
        try:
            with open(tool_runs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            is_list = isinstance(data, list)
            report["audits"]["tool_runs"] = {"exists": True, "valid_json": True, "count": len(data) if is_list else 0}
        except Exception as e:
            report["audits"]["tool_runs"] = {"exists": True, "valid_json": False, "error": str(e)}
            report["warnings"].append("tool_runs.json is invalid JSON.")
            report["status"] = "STRUCTURALLY_INVALID"
    else:
        report["audits"]["tool_runs"] = {"exists": False}

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    audit_state()
