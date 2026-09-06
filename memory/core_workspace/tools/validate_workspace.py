import os
import json
import sys

def main():
    cwd = os.getcwd()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    candidates = [
        cwd,
        script_dir,
        os.path.dirname(script_dir),
        os.path.dirname(cwd)
    ]
    
    found_root = None
    for cand in candidates:
        if os.path.exists(os.path.join(cand, 'memory')) or os.path.exists(os.path.join(cand, 'rules.md')):
            found_root = cand
            break
            
    details = {
        "cwd": cwd,
        "script_dir": script_dir,
        "candidates_checked": candidates,
        "found_root": found_root
    }
    
    if found_root:
        details["root_contents"] = os.listdir(found_root)
        details["memory_exists"] = os.path.exists(os.path.join(found_root, 'memory'))
        details["tools_exists"] = os.path.exists(os.path.join(found_root, 'tools'))
        status = "STRUCTURALLY_COMPLETE"
    else:
        details["cwd_contents"] = os.listdir(cwd) if os.path.exists(cwd) else []
        details["script_dir_contents"] = os.listdir(script_dir) if os.path.exists(script_dir) else []
        status = "STRUCTURALLY_INVALID"
        
    out = {
        "status": status,
        "mechanism": "Dynamic workspace path search relative to cwd and script directory",
        "details": details
    }
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
