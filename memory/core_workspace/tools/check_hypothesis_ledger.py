import json
from pathlib import Path
import sys

def find_root():
    cwd = Path.cwd().resolve()
    for p in [cwd] + list(cwd.parents):
        if (p / ".git").exists() or (p / "memory").exists():
            return p
    return cwd

def main():
    root = find_root()
    memory_dir = root / "memory"
    
    candidates = set(root.glob("**/hypotheses.json"))
    if memory_dir.exists():
        candidates.update(memory_dir.glob("**/*hypothesis*.json"))
    
    found_files = []
    errors = []
    total_hypotheses = 0
    valid_statuses = {"testing", "untested", "confirmed", "refuted", "inconclusive"}
    
    for path in candidates:
        try:
            rel_path = str(path.relative_to(root))
        except ValueError:
            rel_path = str(path)
        found_files.append(rel_path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "hypotheses" in data:
                items = data["hypotheses"]
            else:
                items = []
            
            for idx, item in enumerate(items):
                total_hypotheses += 1
                if not isinstance(item, dict):
                    errors.append(f"{rel_path}[{idx}]: item is not an object")
                    continue
                if "id" not in item:
                    errors.append(f"{rel_path}[{idx}]: missing 'id'")
                if "status" in item and item["status"] not in valid_statuses:
                    errors.append(f"{rel_path}[{idx}]: invalid status '{item['status']}'")
        except Exception as e:
            errors.append(f"{rel_path}: parse error: {str(e)}")
            
    if errors:
        out = {
            "status": "STRUCTURALLY_INVALID",
            "files_checked": sorted(found_files),
            "total_hypotheses": total_hypotheses,
            "errors": errors
        }
    else:
        out = {
            "status": "STRUCTURALLY_COMPLETE",
            "files_checked": sorted(found_files),
            "total_hypotheses": total_hypotheses,
            "errors": []
        }
        
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
