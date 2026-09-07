import os
import json

def find_workspace_root():
    curr = os.path.abspath(os.getcwd())
    while curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, '.git')) or os.path.basename(curr) == 'wake-scaffold':
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.getcwd(), "..", ".."))

def find_file_in_tree(root, target_name):
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        if target_name in filenames:
            matches.append(os.path.join(dirpath, target_name))
    return matches

def validate():
    root = find_workspace_root()
    target_markdowns = ["identity.md", "rules.md", "index.md"]
    target_jsons = ["commitments.json", "tool_runs.json"]
    
    markdown_results = {}
    json_results = {}
    all_found = True
    
    for md in target_markdowns:
        matches = find_file_in_tree(root, md)
        if matches:
            filepath = matches[0]
            size = os.path.getsize(filepath)
            rel_path = os.path.relpath(filepath, root)
            markdown_results[md] = {
                "exists": True,
                "size_bytes": size,
                "located_at": rel_path
            }
        else:
            all_found = False
            markdown_results[md] = {
                "exists": False,
                "size_bytes": 0,
                "located_at": None
            }
            
    for jf in target_jsons:
        matches = find_file_in_tree(root, jf)
        if matches:
            filepath = matches[0]
            rel_path = os.path.relpath(filepath, root)
            size = os.path.getsize(filepath)
            valid_json = False
            record_count = 0
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                valid_json = True
                if isinstance(data, list):
                    record_count = len(data)
                elif isinstance(data, dict):
                    record_count = len(data)
            except Exception:
                all_found = False
                
            json_results[jf] = {
                "exists": True,
                "size_bytes": size,
                "located_at": rel_path,
                "valid_json": valid_json,
                "record_count": record_count
            }
        else:
            all_found = False
            json_results[jf] = {
                "exists": False,
                "size_bytes": 0,
                "located_at": None,
                "valid_json": False,
                "record_count": 0
            }
            
    status = "STRUCTURALLY_COMPLETE" if all_found else "STRUCTURALLY_INVALID"
    
    report = {
        "status": status,
        "root_path": root,
        "markdown_checks": markdown_results,
        "json_checks": json_results
    }
    
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    validate()
