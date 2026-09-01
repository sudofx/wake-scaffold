import sys
import os
import json

def validate_json_file(filepath):
    if not os.path.exists(filepath):
        print(f"MISSING: {filepath}")
        return False, None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"OK (valid JSON): {filepath}")
        return True, data
    except Exception as e:
        print(f"INVALID JSON: {filepath} - Error: {e}")
        return False, None

def validate_commitments(data):
    if not isinstance(data, list):
        print("FAIL: commitments.json should be a list")
        return False
    valid = True
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"FAIL: commitments.json item {idx} is not an object")
            valid = False
            continue
        for req in ["id", "to", "what", "due", "status"]:
            if req not in item:
                print(f"FAIL: commitments.json item {idx} missing key '{req}'")
                valid = False
    if valid:
        print(f"OK: commitments.json has {len(data)} valid entries")
    return valid

def validate_growth_plan(data):
    if not isinstance(data, dict):
        print("FAIL: growth_plan.json should be a dictionary/object")
        return False
    projects = data.get("projects", [])
    if not isinstance(projects, list):
        print("FAIL: growth_plan.json 'projects' key should be a list")
        return False
    valid = True
    for idx, item in enumerate(projects):
        if not isinstance(item, dict):
            print(f"FAIL: growth_plan.json project {idx} is not an object")
            valid = False
            continue
        for req in ["id", "title", "capability", "next_step", "status"]:
            if req not in item:
                print(f"FAIL: growth_plan.json project {idx} missing key '{req}'")
                valid = False
    if valid:
        print(f"OK: growth_plan.json has {len(projects)} projects verified")
    return valid

def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Validating memory files in directory: {target_dir}")
    
    files_to_check = {
        "commitments.json": validate_commitments,
        "growth_plan.json": validate_growth_plan
    }
    
    all_ok = True
    for filename, validator in files_to_check.items():
        path = os.path.join(target_dir, filename)
        ok, data = validate_json_file(path)
        if ok and data is not None and validator:
            if not validator(data):
                all_ok = False
        elif not ok:
            all_ok = False

    if all_ok:
        print("SUCCESS: Memory validation passed all checks.")
        sys.exit(0)
    else:
        print("FAILURE: Memory validation found issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
