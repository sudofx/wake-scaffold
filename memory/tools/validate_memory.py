import os
import sys
import json

def find_memory_dir():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "..", "memory"),
        os.path.join(os.getcwd(), "memory"),
        os.path.join(script_dir, ".."),
        os.getcwd()
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            for test_file in ["commitments.json", "growth_plan.json", "hypotheses.json", "core_memories.json"]:
                if os.path.exists(os.path.join(c, test_file)):
                    return os.path.abspath(c)
    mem_dir = os.path.abspath(os.path.join(script_dir, "..", "memory"))
    if os.path.exists(mem_dir):
        return mem_dir
    return os.path.abspath(os.path.join(script_dir, ".."))

def validate_json_file(path):
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return True, data
    except Exception as e:
        return False, f"JSON parse error: {str(e)}"

def validate_commitments(path):
    ok, res = validate_json_file(path)
    if not ok:
        return False, res
    items = res if isinstance(res, list) else res.get("commitments", res.get("add", [])) if isinstance(res, dict) else []
    if not isinstance(items, list):
        return False, "Commitments data is not a list"
    return True, f"Validated {len(items)} commitment entries"

def validate_growth_plan(path):
    ok, res = validate_json_file(path)
    if not ok:
        return False, res
    items = res if isinstance(res, list) else res.get("projects", res.get("growth_plan", [])) if isinstance(res, dict) else []
    if not isinstance(items, list):
        return False, "Growth plan data is not a list"
    return True, f"Validated {len(items)} growth plan entries"

def validate_hypotheses(path):
    ok, res = validate_json_file(path):
    if not ok:
        return False, res
    items = res if isinstance(res, list) else res.get("hypotheses", []) if isinstance(res, dict) else []
    if not isinstance(items, list):
        return False, "Hypotheses data is not a list"
    return True, f"Validated {len(items)} hypothesis entries"

def main():
    target_dir = find_memory_dir()
    print(f"Target memory directory resolved to: {target_dir}")
    
    files_to_check = {
        "commitments.json": validate_commitments,
        "growth_plan.json": validate_growth_plan,
        "hypotheses.json": validate_hypotheses,
    }
    
    all_ok = True
    for fname, validator in files_to_check.items():
        fpath = os.path.join(target_dir, fname)
        if not os.path.exists(fpath):
            alt_path = os.path.join(os.path.dirname(target_dir), fname)
            if os.path.exists(alt_path):
                fpath = alt_path
            else:
                print(f"[SKIP] {fname}: File not found at {fpath}")
                continue
        
        ok, msg = validator(fpath)
        if ok:
            print(f"[PASS] {fname}: {msg}")
        else:
            print(f"[FAIL] {fname}: {msg}")
            all_ok = False

    if all_ok:
        print("Memory validation completed successfully.")
        sys.exit(0)
    else:
        print("Memory validation encountered failures.")
        sys.exit(1)

if __name__ == "__main__":
    main()
