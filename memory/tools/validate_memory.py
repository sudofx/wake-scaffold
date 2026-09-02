import json
import os
import sys

def validate_json_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully parsed JSON from {filepath}")
        return data
    except Exception as e:
        print(f"Error parsing JSON from {filepath}: {e}")
        return None

def validate_commitments(base_dir):
    path = os.path.join(base_dir, "commitments.json")
    if not os.path.exists(path):
        print(f"Missing {path}")
        return False
    data = validate_json_file(path)
    if data is None:
        return False
    
    commitments = []
    if isinstance(data, list):
        commitments = data
    elif isinstance(data, dict):
        if "commitments" in data and isinstance(data["commitments"], list):
            commitments = data["commitments"]
        else:
            commitments = [data]
    else:
        print(f"Invalid commitments structure in {path}: {type(data)}")
        return False

    print(f"Validated commitments in {path} (count: {len(commitments)})")
    return True

def validate_json_list_or_dict(base_dir, filename):
    path = os.path.join(base_dir, filename)
    if os.path.exists(path):
        data = validate_json_file(path)
        if data is None:
            return False
        print(f"Validated {filename}")
    return True

def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "memory"
    print(f"Validating memory directory: {target_dir}")
    
    ok = True
    ok = validate_commitments(target_dir) and ok
    ok = validate_json_list_or_dict(target_dir, "core_memories.json") and ok
    ok = validate_json_list_or_dict(target_dir, "growth_plan.json") and ok
    ok = validate_json_list_or_dict(target_dir, "hypotheses.json") and ok

    if not ok:
        print("Validation FAILED")
        sys.exit(1)
    
    print("Validation PASSED successfully")

if __name__ == "__main__":
    main()
