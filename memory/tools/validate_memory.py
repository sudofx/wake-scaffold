import sys
import json
from pathlib import Path

def find_target_dir(candidate_str):
    # Direct path check
    p = Path(candidate_str)
    if p.is_dir() and (p / "index.md").exists():
        return p

    # Relative to current working directory
    p_cwd = Path.cwd() / candidate_str
    if p_cwd.is_dir() and (p_cwd / "index.md").exists():
        return p_cwd

    # Parent directory check
    p_parent = Path.cwd().parent / candidate_str
    if p_parent.is_dir() and (p_parent / "index.md").exists():
        return p_parent

    # Fallback checks
    for search_path in [Path.cwd(), Path.cwd().parent, Path("."), Path("..")]:
        if (search_path / "index.md").exists():
            return search_path
        if (search_path / "memory" / "index.md").exists():
            return search_path / "memory"

    return p

def validate_memory(target_dir_str):
    target_path = find_target_dir(target_dir_str)
    if not target_path.is_dir():
        print(f"Error: Target path '{target_dir_str}' (resolved to '{target_path}') is not a directory or does not exist.")
        return 1

    required_files = [
        "identity.md",
        "rules.md",
        "index.md",
        "growth_plan.json",
        "hypotheses.json",
        "commitments.json",
        "core_memories.json",
        "known_limitations.json",
        "tool_runs.json"
    ]

    missing = []
    for f in required_files:
        p = target_path / f
        if not p.exists():
            missing.append(f)

    if missing:
        print(f"Validation FAILED in '{target_path}': Missing required memory files: {missing}")
        return 1

    json_files = [
        "growth_plan.json",
        "hypotheses.json",
        "commitments.json",
        "core_memories.json",
        "known_limitations.json",
        "tool_runs.json"
    ]

    invalid_json = []
    for jf in json_files:
        jp = target_path / jf
        try:
            with open(jp, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            invalid_json.append((jf, str(e)))

    if invalid_json:
        print(f"Validation FAILED in '{target_path}': Invalid JSON files found:")
        for jf, err in invalid_json:
            print(f"  - {jf}: {err}")
        return 1

    print(f"Validation SUCCESS: Memory directory '{target_path}' is valid and all required JSON files parsed successfully.")
    return 0

if __name__ == "__main__":
    target_arg = sys.argv[1] if len(sys.argv) > 1 else "memory"
    sys.exit(validate_memory(target_arg))
