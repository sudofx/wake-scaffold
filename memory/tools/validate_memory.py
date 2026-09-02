import sys
import json
import os

def validate_memory(memory_dir):
    required_files = [
        "identity.md",
        "rules.md",
        "index.md",
        "commitments.json",
        "growth_plan.json",
        "hypotheses.json"
    ]

    if not os.path.exists(memory_dir):
        if os.path.exists("identity.md"):
            memory_dir = "."

    missing = []
    invalid_json = []

    for fname in required_files:
        fpath = os.path.join(memory_dir, fname) if memory_dir != "." else fname
        if not os.path.exists(fpath):
            missing.append(fname)
            continue
        
        if fname.endswith(".json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:
                invalid_json.append((fname, str(e)))

    if missing or invalid_json:
        if missing:
            print(f"Error: Missing required memory files in '{memory_dir}': {', '.join(missing)}")
        if invalid_json:
            for fname, err in invalid_json:
                print(f"Error: Invalid JSON in {fname}: {err}")
        sys.exit(1)

    print(f"Memory validation successful for '{memory_dir}'. All required files present and JSON valid.")
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    elif os.path.exists("memory"):
        target_dir = "memory"
    else:
        target_dir = "."
        
    validate_memory(target_dir)
