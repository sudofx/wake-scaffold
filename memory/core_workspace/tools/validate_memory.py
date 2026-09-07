import os
import json

def validate():
    search_paths = [".", "..", "memory", "core_workspace"]
    found_mem_path = None
    for path in search_paths:
        if os.path.exists(os.path.join(path, "identity.md")) or os.path.exists(os.path.join(path, "rules.md")):
            found_mem_path = path
            break
    
    base = found_mem_path if found_mem_path else "."
    required_files = ["identity.md", "rules.md", "index.md"]
    checks = {}
    missing = []
    
    for fname in required_files:
        full_p = os.path.join(base, fname)
        exists = os.path.exists(full_p)
        size = os.path.getsize(full_p) if exists else 0
        checks[fname] = {"exists": exists, "size_bytes": size}
        if not exists:
            missing.append(fname)
            
    status = "STRUCTURALLY_COMPLETE" if len(missing) == 0 else "STRUCTURALLY_INVALID"
    output = {
        "status": status,
        "base_path": os.path.abspath(base),
        "checks": checks,
        "missing": missing
    }
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    validate()
