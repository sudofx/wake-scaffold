import os
import sys
import json

def inspect():
    cwd = os.getcwd()
    items_cwd = os.listdir(cwd) if os.path.exists(cwd) else []
    parent = os.path.abspath(os.path.join(cwd, ".."))
    items_parent = os.listdir(parent) if os.path.exists(parent) else []
    
    info = {
        "python_version": sys.version,
        "cwd": cwd,
        "cwd_contents": items_cwd,
        "parent_dir": parent,
        "parent_contents": items_parent,
        "memory_in_cwd": os.path.exists(os.path.join(cwd, "memory")),
        "memory_in_parent": os.path.exists(os.path.join(parent, "memory")),
        "tools_in_cwd": os.path.exists(os.path.join(cwd, "tools")),
        "tools_in_parent": os.path.exists(os.path.join(parent, "tools"))
    }
    return info

if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2))
