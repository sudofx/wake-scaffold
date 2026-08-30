import os
import sys
import json

REQUIRED_MARKDOWN_FILES = [
    "identity.md",
    "rules.md",
    "index.md",
    "failure_modes.md"
]

JSON_FILES_TO_CHECK = [
    "commitments.json",
    "growth_plan.json",
    "core_memories.json",
    "journal_index.json"
]

def check_file_exists_and_nonempty(path):
    if not os.path.exists(path):
        return False, f"Missing file: {path}"
    if os.path.getsize(path) == 0:
        return False, f"Empty file: {path}"
    return True, f"OK: {path}"

def validate_json(path):
    if not os.path.exists(path):
        return True, f"Optional/Missing JSON skipped: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return True, f"Valid JSON: {path} ({type(data).__name__})"
    except Exception as e:
        return False, f"Invalid JSON in {path}: {e}"

def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "memory"
    if not os.path.exists(target_dir) and os.path.exists("identity.md"):
        target_dir = "."

    print("--- Memory Integrity Validator ---")
    print(f"Target directory: {os.path.abspath(target_dir)}")

    errors = []
    successes = []

    for md_file in REQUIRED_MARKDOWN_FILES:
        path = os.path.join(target_dir, md_file)
        ok, msg = check_file_exists_and_nonempty(path)
        if ok:
            successes.append(msg)
        else:
            errors.append(msg)

    for j_file in JSON_FILES_TO_CHECK:
        path = os.path.join(target_dir, j_file)
        ok, msg = validate_json(path)
        if ok:
            successes.append(msg)
        else:
            errors.append(msg)

    print("\n[PASSED CHECKS]")
    for s in successes:
        print(f" - {s}")

    if errors:
        print("\n[FAILED CHECKS]")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)
    else:
        print("\nAll memory integrity checks passed successfully.")

if __name__ == "__main__":
    main()
