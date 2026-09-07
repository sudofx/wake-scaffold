import os
import json
import sys

def find_root():
    curr = os.path.abspath(os.getcwd())
    while True:
        if os.path.exists(os.path.join(curr, "core_workspace")) or os.path.exists(os.path.join(curr, "identity.md")):
            return curr
        if os.path.exists(os.path.join(curr, "memory")):
            return os.path.join(curr, "memory")
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.abspath(os.getcwd())

def check_file(path):
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    return {"exists": exists, "size_bytes": size}

def validate_json(path):
    f_info = check_file(path)
    if not f_info["exists"]:
        return {**f_info, "valid_json": False, "type": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**f_info, "valid_json": True, "type": type(data).__name__}
    except Exception as e:
        return {**f_info, "valid_json": False, "error": str(e)}

def main():
    root = find_root()
    markdown_files = ["identity.md", "rules.md", "index.md"]
    json_files = ["core_workspace/commitments.json", "core_workspace/tool_runs.json"]
    
    md_results = {}
    for mf in markdown_files:
        paths_to_try = [
            os.path.join(root, mf),
            os.path.join(root, "memory", mf),
            os.path.join(root, "core_workspace", mf)
        ]
        found_path = None
        for p in paths_to_try:
            if os.path.exists(p):
                found_path = p
                break
        if found_path:
            md_results[mf] = check_file(found_path)
            md_results[mf]["located_at"] = os.path.relpath(found_path, root)
        else:
            md_results[mf] = {"exists": False, "size_bytes": 0, "located_at": None}

    json_results = {}
    for jf in json_files:
        path = os.path.join(root, jf)
        if not os.path.exists(path):
            alt_path = os.path.join(root, os.path.basename(jf))
            if os.path.exists(alt_path):
                path = alt_path
        json_results[jf] = validate_json(path)

    all_md_exist = all(info["exists"] for info in md_results.values())
    all_json_valid = all(info["exists"] and info.get("valid_json", False) for info in json_results.values())

    status = "STRUCTURALLY_COMPLETE" if (all_md_exist and all_json_valid) else "STRUCTURALLY_INVALID"

    report = {
        "status": status,
        "root_path": root,
        "markdown_checks": md_results,
        "json_checks": json_results
    }
    
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
