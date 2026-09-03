import sys
import json
from pathlib import Path

def validate():
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1]).resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        if script_dir.name == 'tools':
            target_dir = script_dir.parent
        else:
            target_dir = Path.cwd()

    print(f"Validating memory directory: {target_dir}")
    
    required_files = [
        "identity.md",
        "rules.md",
        "index.md",
        "commitments.json",
        "growth_plan.json",
        "hypotheses.json",
        "core_memories.json"
    ]

    missing = []
    errors = []

    for fname in required_files:
        fpath = target_dir / fname
        if not fpath.exists():
            missing.append(fname)
            continue
        
        if fname.endswith(".json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, (dict, list)):
                    errors.append(f"{fname}: root JSON structure is invalid type ({type(data)})")
            except Exception as e:
                errors.append(f"{fname}: JSON syntax error ({e})")
        else:
            if fpath.stat().st_size == 0:
                errors.append(f"{fname}: file is empty")

    if missing:
        print(f"FAIL: Missing files: {', '.join(missing)}")
    if errors:
        print("FAIL: Content errors:")
        for err in errors:
            print(f"  - {err}")

    if not missing and not errors:
        print("SUCCESS: All required memory files present and valid.")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    validate()
