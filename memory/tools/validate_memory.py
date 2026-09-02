import json
import sys
from pathlib import Path

def find_memory_dir(given_path=None):
    candidates = []
    if given_path:
        p = Path(given_path)
        candidates.extend([p, Path.cwd() / p, Path.cwd().parent / p])
    
    candidates.extend([
        Path.cwd(),
        Path.cwd() / "memory",
        Path.cwd().parent,
        Path.cwd().parent / "memory"
    ])

    for cand in candidates:
        if cand.is_dir():
            if (cand / "commitments.json").exists() or (cand / "identity.md").exists():
                return cand.resolve()
    
    return Path.cwd().resolve()

def validate_json_file(file_path, expected_type=None):
    if not file_path.exists():
        print(f"MISSING: {file_path.name}")
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if expected_type and not isinstance(data, expected_type):
            print(f"INVALID SCHEMA: {file_path.name} expected {expected_type.__name__}, got {type(data).__name__}")
            return False
        item_count = len(data) if isinstance(data, (list, dict)) else 0
        print(f"OK: {file_path.name} (valid JSON, {item_count} items)")
        return True
    except Exception as e:
        print(f"ERROR parsing {file_path.name}: {e}")
        return False

def validate_text_file(file_path):
    if not file_path.exists():
        print(f"MISSING: {file_path.name}")
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"OK: {file_path.name} ({len(content)} chars)")
        return True
    except Exception as e:
        print(f"ERROR reading {file_path.name}: {e}")
        return False

def main():
    given_arg = sys.argv[1] if len(sys.argv) > 1 else None
    mem_dir = find_memory_dir(given_arg)
    print(f"Validating memory directory at: {mem_dir}")

    json_files = {
        "commitments.json": list,
        "growth_plan.json": list,
        "hypotheses.json": list,
        "core_memories.json": list,
    }
    
    text_files = ["identity.md", "index.md", "rules.md"]

    success = True

    for jf, exp_type in json_files.items():
        p = mem_dir / jf
        if p.exists():
            if not validate_json_file(p, exp_type):
                success = False
        else:
            alt_p = Path.cwd() / jf
            if alt_p.exists():
                if not validate_json_file(alt_p, exp_type):
                    success = False
            else:
                print(f"OPTIONAL/MISSING: {jf}")

    for tf in text_files:
        p = mem_dir / tf
        if p.exists():
            if not validate_text_file(p):
                success = False
        else:
            alt_p = Path.cwd() / tf:
                if not validate_text_file(alt_p):
                    success = False

    if success:
        print("SUCCESS: Memory validation passed.")
        sys.exit(0)
    else:
        print("FAILURE: Memory validation encountered errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
