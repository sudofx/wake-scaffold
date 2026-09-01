import json
import sys
import os

def validate_memory(memory_dir):
    errors = []
    
    check_dirs = [memory_dir]
    if memory_dir == ".":
        check_dirs.extend(["..", "../memory", "memory"])

    effective_dir = None
    for d in check_dirs:
        if os.path.exists(os.path.join(d, "identity.md")):
            effective_dir = d
            break

    if not effective_dir:
        effective_dir = memory_dir

    required_files = [
        "identity.md",
        "rules.md",
        "index.md",
        "commitments.json",
        "growth_plan.json",
        "hypotheses.json",
        "core_memories.json"
    ]
    
    for fname in required_files:
        path = os.path.join(effective_dir, fname)
        if not os.path.isfile(path):
            errors.append(f"Missing required file: {fname} (searched in {effective_dir})")
            
    json_files = {
        "commitments.json": {"allowed_statuses": ["open", "in_progress", "blocked", "closed"], "required_keys": ["id", "to", "what", "status"]},
        "growth_plan.json": {"allowed_statuses": ["proposed", "active", "blocked", "complete"], "required_keys": ["id", "title", "capability", "status"]},
        "hypotheses.json": {"allowed_statuses": ["testing", "confirmed", "refuted", "inconclusive"], "required_keys": ["id", "prediction", "test_method", "status"]}
    }
    
    for fname, schema in json_files.items():
        path = os.path.join(effective_dir, fname)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                errors.append(f"{fname}: Top-level structure must be a JSON array (list)")
                continue
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    errors.append(f"{fname}[{idx}]: Item must be an object (dict)")
                    continue
                for rkey in schema["required_keys"]:
                    if rkey not in item:
                        errors.append(f"{fname}[{idx}]: Missing required key '{rkey}'")
                if "status" in item and item["status"] not in schema["allowed_statuses"]:
                    errors.append(f"{fname}[{idx}]: Invalid status '{item['status']}'. Must be one of {schema['allowed_statuses']}")
        except json.JSONDecodeError as e:
            errors.append(f"{fname}: Invalid JSON syntax - {e}")
        except Exception as e:
            errors.append(f"{fname}: Failed to read/validate - {e}")
            
    cm_path = os.path.join(effective_dir, "core_memories.json")
    if os.path.exists(cm_path):
        try:
            with open(cm_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                errors.append("core_memories.json: Top-level structure must be a JSON array")
        except Exception as e:
            errors.append(f"core_memories.json: Invalid JSON - {e}")

    return errors, effective_dir

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    errs, eff_dir = validate_memory(target)
    print(f"Validated directory: {eff_dir}")
    if errs:
        print("Validation FAILED:")
        for err in errs:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("Validation PASSED: All memory files exist and adhere to schema.")
        sys.exit(0)
