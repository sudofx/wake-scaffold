import os
import json
import sys

def find_memory_root():
    curr = os.path.abspath(os.getcwd())
    while True:
        if os.path.exists(os.path.join(curr, "identity.md")) or os.path.exists(os.path.join(curr, "core_workspace")):
            return curr
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.abspath(os.getcwd())

def main():
    root = find_memory_root()
    md_files = ["identity.md", "rules.md", "index.md"]
    md_results = {}
    for f in md_files:
        path = os.path.join(root, f)
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        md_results[f] = {"exists": exists, "size_bytes": size}
    
    json_results = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for file in filenames:
            if file.endswith('.json'):
                rel_path = os.path.relpath(os.path.join(dirpath, file), root)
                full_path = os.path.join(dirpath, file)
                is_valid_json = False
                item_count = 0
                data_type = None
                error = None
                try:
                    with open(full_path, 'r', encoding='utf-8') as jf:
                        data = json.load(jf)
                        is_valid_json = True
                        data_type = type(data).__name__
                        if isinstance(data, (list, dict)):
                            item_count = len(data)
                except Exception as e:
                    error = str(e)
                json_results[rel_path] = {
                    "valid_json": is_valid_json,
                    "type": data_type,
                    "items": item_count,
                    "error": error
                }

    all_md_ok = all(r["exists"] and r["size_bytes"] > 0 for r in md_results.values())
    all_json_ok = all(r["valid_json"] for r in json_results.values()) if json_results else True

    status = "STRUCTURALLY_COMPLETE" if (all_md_ok and all_json_ok) else "STRUCTURALLY_INVALID"

    report = {
        "status": status,
        "root_path": root,
        "markdown_checks": md_results,
        "json_checks": json_results
    }
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
