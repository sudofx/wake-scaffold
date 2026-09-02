import sys
import json
from pathlib import Path

def find_memory_dir(target_arg=None):
    if target_arg:
        arg_path = Path(target_arg).resolve()
        if (arg_path / "memory").is_dir():
            return arg_path / "memory"
        if arg_path.name == "memory" and arg_path.is_dir():
            return arg_path
        if (arg_path / "identity.md").exists():
            return arg_path

    # Fallback auto-detection relative to script location and CWD
    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()

    candidates = [
        cwd,
        cwd.parent,
        script_dir,
        script_dir.parent,
    ]

    for cand in candidates:
        if (cand / "memory").is_dir():
            return cand / "memory"
        if (cand / "identity.md").exists():
            return cand

    return None

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    mem_dir = find_memory_dir(target)

    if not mem_dir or not mem_dir.exists():
        print(f"ERROR: Could not locate workspace memory directory (arg={target})")
        sys.exit(1)

    print(f"Validating workspace memory at: {mem_dir}")

    required_files = [
        "identity.md",
        "commitments.json",
        "growth_plan.json",
        "hypotheses.json",
        "blog.html",
    ]

    missing = []
    for fname in required_files:
        if not (mem_dir / fname).exists():
            missing.append(fname)

    if not (mem_dir / "journal").is_dir():
        missing.append("journal/")

    if missing:
        print(f"FAIL: Missing required memory files/dirs: {', '.join(missing)}")
        sys.exit(1)

    json_files = ["commitments.json", "growth_plan.json", "hypotheses.json"]
    for jfile in json_files:
        jp = mem_dir / jfile
        try:
            with open(jp, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"FAIL: {jfile} content is not a top-level list")
                    sys.exit(1)
        except Exception as e:
            print(f"FAIL: {jfile} JSON parse error: {e}")
            sys.exit(1)

    print("SUCCESS: Memory directory layout and JSON schemas verified.")
    sys.exit(0)

if __name__ == "__main__":
    main()
