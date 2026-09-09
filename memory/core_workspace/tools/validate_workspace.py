import sys
import os
import json

def find_workspace_root(initial_target):
    search_starts = [
        os.path.abspath(initial_target or "."),
        os.path.abspath(os.path.dirname(__file__))
    ]
    
    anchors = ["rules.md", "index.md", "identity.md"]
    
    for start in search_starts:
        curr = start
        for _ in range(6):
            found_anchors = [f for f in anchors if os.path.exists(os.path.join(curr, f))]
            if len(found_anchors) >= 1:
                return curr
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
            
    return initial_target

def check_workspace(target_dir):
    root_dir = find_workspace_root(target_dir)
    print(f"CWD: {os.getcwd()}")
    print(f"Target dir: {target_dir} -> Resolved root: {root_dir}")
    
    required_files = [
        "rules.md",
        "index.md",
        "identity.md",
        "growth_plan.md",
        "hypotheses.md",
        "commitments.md",
        "tool_runs.json"
    ]
    status = {"found": [], "missing": [], "json_ok": [], "json_err": []}
    
    if os.path.exists(root_dir):
        print(f"Directory contents of '{root_dir}': {os.listdir(root_dir)}")
    else:
        print(f"Resolved root '{root_dir}' does not exist!")
    
    for f in required_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            status["found"].append(f)
            if f.endswith(".json"):
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        json.load(fp)
                    status["json_ok"].append(f)
                except Exception as e:
                    status["json_err"].append(f"{f}: {str(e)}")
        else:
            status["missing"].append(f)

    print(f"STATUS: FOUND={len(status['found'])} MISSING={len(status['missing'])} JSON_OK={len(status['json_ok'])} JSON_ERR={len(status['json_err'])}")
    if status["missing"]:
        print(f"Missing files: {status['missing']}")
    if status["json_err"]:
        print(f"JSON errors: {status['json_err']}")
        
    return len(status["missing"]) == 0 and len(status["json_err"]) == 0

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    ok = check_workspace(target)
    if ok:
        print("RESULT: STRUCTURALLY_COMPLETE")
        sys.exit(0)
    else:
        print("RESULT: STRUCTURALLY_INVALID")
        sys.exit(1)
