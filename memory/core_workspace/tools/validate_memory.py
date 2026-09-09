import os
import json
import sys

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    required_files = ["identity.md", "rules.md", "index.md"]
    
    search_dirs = [root]
    if os.path.exists("..") and os.path.abspath(root) != os.path.abspath(".."):
        search_dirs.append("..")
        
    found = []
    missing = []
    
    for req in required_files:
        located = False
        for search_root in search_dirs:
            for dirpath, dirnames, filenames in os.walk(search_root):
                if any(f.lower() == req.lower() for f in filenames):
                    found.append(req)
                    located = True
                    break
            if located:
                break
        if not located:
            missing.append(req)
            
    status = "STRUCTURALLY_COMPLETE" if len(missing) == 0 else "STRUCTURALLY_INVALID"
    report = {
        "status": status,
        "mechanism": "workspace_file_existence_check",
        "found_files": found,
        "missing_files": missing
    }
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
