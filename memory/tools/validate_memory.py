import sys
import os
import json

def validate_memory(memory_dir):
    errors = []
    warnings = []

    if not os.path.isdir(memory_dir):
        return False, [f"Directory not found: {memory_dir}"], []

    # Required files
    required_files = ["identity.md", "commitments.json", "growth_plan.json", "hypotheses.json", "core_memories.json"]
    for fname in required_files:
        path = os.path.join(memory_dir, fname)
        if not os.path.isfile(path):
            errors.append(f"Missing required file: {fname}")

    # Validate commitments.json schema
    commitments_path = os.path.join(memory_dir, "commitments.json")
    if os.path.isfile(commitments_path):
        try:
            with open(commitments_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items = data.get("commitments", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for idx, c in enumerate(items):
                    if not isinstance(c, dict):
                        errors.append(f"commitments.json item #{idx} is not an object")
                        continue
                    for req in ["id", "to", "what", "status"]:
                        if req not in c or not str(c[req]).strip():
                            errors.append(f"commitments.json item #{idx} missing or empty required field: '{req}'")
            else:
                errors.append("commitments.json top-level structure must be a list or dict with 'commitments'")
        except Exception as e:
            errors.append(f"commitments.json parse error: {e}")

    # Validate growth_plan.json schema
    growth_path = os.path.join(memory_dir, "growth_plan.json")
    if os.path.isfile(growth_path):
        try:
            with open(growth_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items = data.get("projects", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for idx, p in enumerate(items):
                    if not isinstance(p, dict):
                        errors.append(f"growth_plan.json item #{idx} is not an object")
                        continue
                    for req in ["id", "title", "capability", "status"]:
                        if req not in p or not str(p[req]).strip():
                            errors.append(f"growth_plan.json item #{idx} missing or empty required field: '{req}'")
            else:
                errors.append("growth_plan.json top-level structure must be a list or dict with 'projects'")
        except Exception as e:
            errors.append(f"growth_plan.json parse error: {e}")

    # Validate hypotheses.json schema
    hypo_path = os.path.join(memory_dir, "hypotheses.json")
    if os.path.isfile(hypo_path):
        try:
            with open(hypo_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items = data.get("hypotheses", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for idx, h in enumerate(items):
                    if not isinstance(h, dict):
                        errors.append(f"hypotheses.json item #{idx} is not an object")
                        continue
                    for req in ["id", "prediction", "test_method", "status"]:
                        if req not in h or not str(h[req]).strip():
                            errors.append(f"hypotheses.json item #{idx} missing or empty required field: '{req}'")
            else:
                errors.append("hypotheses.json top-level structure must be a list or dict with 'hypotheses'")
        except Exception as e:
            errors.append(f"hypotheses.json parse error: {e}")

    # Validate core_memories.json schema
    core_path = os.path.join(memory_dir, "core_memories.json")
    if os.path.isfile(core_path):
        try:
            with open(core_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items = data.get("memories", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                if len(items) > 20:
                    errors.append(f"core_memories.json exceeds maximum allowed limit of 20 (found {len(items)})")
                for idx, m in enumerate(items):
                    if not isinstance(m, dict):
                        errors.append(f"core_memories.json item #{idx} is not an object")
                        continue
                    for req in ["lesson", "weight"]:
                        if req not in m or not str(m[req]).strip():
                            errors.append(f"core_memories.json item #{idx} missing or empty required field: '{req}'")
            else:
                errors.append("core_memories.json top-level structure must be a list or dict with 'memories'")
        except Exception as e:
            errors.append(f"core_memories.json parse error: {e}")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "memory"
    valid, errs, warns = validate_memory(target_dir)
    if warns:
        print("WARNINGS:")
        for w in warns:
            print(f"- {w}")
    if not valid:
        print("VALIDATION FAILED:")
        for e in errs:
            print(f"- {e}")
        sys.exit(1)
    else:
        print(f"VALIDATION PASSED: Workspace '{target_dir}' structure and schemas are valid.")
        sys.exit(0)
