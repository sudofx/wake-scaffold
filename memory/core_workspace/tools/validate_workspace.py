#!/usr/bin/env python3
import sys
import os
import json

def find_workspace_root(start_dir, expected_items):
    current = os.path.abspath(start_dir)
    while True:
        found_any = False
        for item in expected_items:
            path_direct = os.path.join(current, item)
            path_memory = os.path.join(current, "memory", item)
            if os.path.exists(path_direct) or os.path.exists(path_memory):
                found_any = True
                break
        if found_any:
            return current
        
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.abspath(start_dir)

def validate_workspace(target_dir):
    start_target = os.path.abspath(target_dir)
    expected_items = [
        "core_workspace",
        "core_identity",
        "core_memories",
        "rules.md",
        "index.md",
        "identity.md"
    ]
    
    # Auto-detect root if the direct target doesn't have the files
    target = find_workspace_root(start_target, expected_items)
    
    found = {}
    missing = []
    
    for item in expected_items:
        path_direct = os.path.join(target, item)
        path_memory = os.path.join(target, "memory", item)
        
        if os.path.exists(path_direct):
            found[item] = "directory" if os.path.isdir(path_direct) else "file"
        elif os.path.exists(path_memory):
            found[f"memory/{item}"] = "directory" if os.path.isdir(path_memory) else "file"
        else:
            missing.append(item)

    report = {
        "start_directory": start_target,
        "detected_root": target,
        "valid": len(found) > 0,
        "found_items": found,
        "missing_items": missing
    }
    
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(validate_workspace(target))
