import json
import os
import sys

def validate_memory(memory_dir="memory"):
    errors = []
    warnings = []
    checked = []

    # 1. Identity
    identity_path = os.path.join(memory_dir, "identity.md")
    if os.path.exists(identity_path):
        checked.append("identity.md")
        with open(identity_path, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content.strip()) < 10:
                warnings.append("identity.md is unusually short.")
    else:
        errors.append("identity.md missing")

    # 2. Rules
    rules_path = os.path.join(memory_dir, "rules.md")
    if os.path.exists(rules_path):
        checked.append("rules.md")
    else:
        errors.append("rules.md missing")

    # 3. Commitments
    commitments_path = os.path.join(memory_dir, "commitments.json")
    if os.path.exists(commitments_path):
        checked.append("commitments.json")
        try:
            with open(commitments_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("commitments", data.get("items", []))
            
            for idx, item in enumerate(items):
                if isinstance(item, dict):
                    missing_keys = [k for k in ["what", "status"] if k not in item]
                    if missing_keys:
                        warnings.append(f"commitments item {idx} missing keys: {missing_keys}")
                else:
                    warnings.append(f"commitments item {idx} is not an object")
        except json.JSONDecodeError as e:
            errors.append(f"commitments.json is invalid JSON: {e}")
    else:
        warnings.append("commitments.json missing")

    # 4. Growth Plan
    growth_path = os.path.join(memory_dir, "growth_plan.json")
    if os.path.exists(growth_path):
        checked.append("growth_plan.json")
        try:
            with open(growth_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("projects", data.get("growth_plan", []))
            
            for idx, item in enumerate(items):
                if isinstance(item, dict):
                    missing_keys = [k for k in ["title", "status"] if k not in item]
                    if missing_keys:
                        warnings.append(f"growth_plan item {idx} missing keys: {missing_keys}")
                else:
                    warnings.append(f"growth_plan item {idx} is not an object")
        except json.JSONDecodeError as e:
            errors.append(f"growth_plan.json is invalid JSON: {e}")
    else:
        warnings.append("growth_plan.json missing")

    # Output report
    print("=== Memory Validation Report ===")
    print(f"Checked files: {', '.join(checked)}")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")
        print("\nStatus: FAILED")
        sys.exit(1)
    else:
        print("\nStatus: PASSED")
        sys.exit(0)

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "memory"
    validate_memory(target_dir)
