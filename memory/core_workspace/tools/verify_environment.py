import os
import json

FILES = ["identity.md", "rules.md", "index.md"]
SEARCH_DIRS = ["memory", ".", "..", "memory/core_workspace"]

def check_file(filename):
    for d in SEARCH_DIRS:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return {"exists": True, "path": path, "size_bytes": os.path.getsize(path)}
    return {"exists": False, "path": None, "size_bytes": 0}

def verify():
    results = {}
    all_exist = True
    for f in FILES:
        res = check_file(f)
        results[f] = res
        if not res["exists"]:
            all_exist = False
    status = "STRUCTURALLY_COMPLETE" if all_exist else "STRUCTURALLY_INVALID"
    return {"status": status, "checks": results, "cwd": os.getcwd()}

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
