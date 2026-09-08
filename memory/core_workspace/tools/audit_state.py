import json
import os
import sys

def find_repo_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "memory")) or os.path.exists(os.path.join(curr, "core_identity")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def audit_workspace():
    root = find_repo_root()
    mem_dir = os.path.join(root, "memory") if os.path.exists(os.path.join(root, "memory")) else root
    
    audit_results = {
        "workspace_root": mem_dir,
        "status": "STRUCTURALLY_COMPLETE",
        "audits": {
            "markdown_files": {},
            "json_files": {},
            "tool_consistency": {}
        }
    }
    
    md_targets = ["core_identity/identity.md", "core_identity/rules.md", "index.md", "failure_modes.md"]
    for rel_path in md_targets:
        full_p = os.path.join(mem_dir, rel_path)
        exists = os.path.exists(full_p)
        size = os.path.getsize(full_p) if exists else 0
        audit_results["audits"]["markdown_files"][rel_path] = {
            "exists": exists,
            "size_bytes": size
        }
        if not exists or size == 0:
            audit_results["status"] = "STRUCTURALLY_INVALID"

    json_targets = ["commitments.json", "tool_runs.json"]
    json_data = {}
    for rel_path in json_targets:
        full_p = os.path.join(mem_dir, rel_path)
        exists = os.path.exists(full_p)
        valid_json = False
        item_count = 0
        if exists:
            try:
                with open(full_p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    valid_json = True
                    item_count = len(data) if isinstance(data, (list, dict)) else 0
                    json_data[rel_path] = data
            except Exception:
                valid_json = False
        
        audit_results["audits"]["json_files"][rel_path] = {
            "exists": exists,
            "valid_json": valid_json,
            "count": item_count
        }
        if not exists or not valid_json:
            audit_results["status"] = "STRUCTURALLY_INVALID"

    tools_dir = os.path.join(root, "tools")
    if not os.path.exists(tools_dir):
        tools_dir = os.path.join(mem_dir, "tools")
        
    tools_on_disk = set(os.listdir(tools_dir)) if os.path.exists(tools_dir) else set()
    tool_runs = json_data.get("tool_runs.json", [])
    run_counts = {}
    missing_tools_referenced = []
    
    if isinstance(tool_runs, list):
        for run in tool_runs:
            fn = run.get("filename") or run.get("tool")
            if fn:
                run_counts[fn] = run_counts.get(fn, 0) + 1
                if fn not in tools_on_disk and fn not in missing_tools_referenced:
                    missing_tools_referenced.append(fn)

    audit_results["audits"]["tool_consistency"] = {
        "tools_directory_exists": os.path.exists(tools_dir),
        "tools_found_on_disk": sorted(list(tools_on_disk)),
        "execution_counts_by_tool": run_counts,
        "referenced_tools_missing_from_disk": missing_tools_referenced
    }
    
    print(json.dumps(audit_results, indent=2))

if __name__ == "__main__":
    audit_workspace()
