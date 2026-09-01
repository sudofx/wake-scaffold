import json
import sys
from pathlib import Path

def validate():
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("..")
    target_dir = target_dir.resolve()
    print(f"Validating memory workspace at: {target_dir}")
    
    files_to_check = {
        "commitments.json": ("json", ["commitments"]),
        "growth_plan.json": ("json", ["projects"]),
        "hypotheses.json": ("json", ["hypotheses"]),
        "core_memories.json": ("json", ["memories"]),
        "identity.md": ("text", None),
        "rules.md": ("text", None),
    }

    all_ok = True
    for name, (ftype, req_keys) in files_to_check.items():
        p = target_dir / name
        if not p.exists():
            print(f"FAIL: Missing file {name}")
            all_ok = False
            continue

        if ftype == "json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if req_keys and isinstance(data, dict):
                    found = [k for k in req_keys if k in data]
                    if not found:
                        print(f"WARN: {name} valid JSON dict but missing expected keys {req_keys}")
                print(f"PASS: {name} (valid JSON, {type(data).__name__})")
            except Exception as e:
                print(f"FAIL: {name} invalid JSON: {e}")
                all_ok = False
        elif ftype == "text":
            text = p.read_text(encoding="utf-8")
            if not text.strip():
                print(f"FAIL: {name} is empty")
                all_ok = False
            else:
                print(f"PASS: {name} ({len(text)} chars)")

    if all_ok:
        print("RESULT: ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("RESULT: CHECKS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    validate()
