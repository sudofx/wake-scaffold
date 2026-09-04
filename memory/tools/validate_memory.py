import json
import sys
from pathlib import Path

def get_memory_dir(target_arg=None):
    if target_arg:
        p = Path(target_arg).resolve()
        if p.is_dir():
            return p
        return None
    
    script_path = Path(__file__).resolve()
    parent = script_path.parent
    
    if parent.name == "tools":
        root = parent.parent
        if root.name == "memory":
            return root
        if (root / "memory").is_dir():
            return root / "memory"
        return root
    
    cwd = Path.cwd().resolve()
    if cwd.name == "memory":
        return cwd
    if (cwd / "memory").is_dir():
        return cwd / "memory"
    return cwd

def validate_memory(target_dir=None):
    mem_dir = get_memory_dir(target_dir)
    if not mem_dir or not mem_dir.exists():
        return {
            "valid": False,
            "error": f"Memory directory not found at {mem_dir}"
        }
    
    required_files = ["identity.md", "rules.md", "index.md", "commitments.json", "growth_plan.json", "hypotheses.json"]
    checks = {}
    all_valid = True
    
    for fname in required_files:
        fpath = mem_dir / fname
        exists = fpath.exists()
        checks[fname] = {"exists": exists}
        if fname.endswith(".json") and exists:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    json.load(f)
                checks[fname]["json_valid"] = True
            except Exception as e:
                checks[fname]["json_valid"] = False
                checks[fname]["error"] = str(e)
                all_valid = False
        elif not exists:
            all_valid = False
            
    return {
        "memory_dir": str(mem_dir),
        "valid": all_valid,
        "checks": checks
    }

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    res = validate_memory(target)
    print(json.dumps(res, indent=2))
    if not res.get("valid", False):
        sys.exit(1)
