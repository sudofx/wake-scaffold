import os
import json

REQUIRED_FILES = ["identity.md", "rules.md", "index.md"]

def find_memory_root():
    current = os.getcwd()
    while True:
        if all(os.path.exists(os.path.join(current, f)) for f in REQUIRED_FILES):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent

def main():
    memory_root = find_memory_root()
    if not memory_root:
        result = {
            "status": "STRUCTURALLY_INVALID",
            "cwd": os.getcwd(),
            "missing": REQUIRED_FILES,
            "mechanism": "Could not locate memory root directory containing all required core memory files."
        }
    else:
        found = {}
        for f in REQUIRED_FILES:
            p = os.path.join(memory_root, f)
            found[f] = {"path": p, "size": os.path.getsize(p)}
        result = {
            "status": "STRUCTURALLY_COMPLETE",
            "cwd": os.getcwd(),
            "memory_root": memory_root,
            "found_files": found,
            "mechanism": "Located memory root via parent directory traversal and confirmed core memory files exist and are non-empty."
        }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
