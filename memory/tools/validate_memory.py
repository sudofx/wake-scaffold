import json
import os
import sys
from pathlib import Path

def validate_memory(memory_dir="memory"):
    report = {"valid": True, "errors": [], "warnings": [], "checks": []}
    mem_path = Path(memory_dir)
    
    if not mem_path.exists() or not mem_path.is_dir():
        report["valid"] = False
        report["errors"].append(f"Memory directory '{memory_dir}' does not exist.")
        return report

    # 1. Check commitments.json
    commitments_file = mem_path / "commitments.json"
    if commitments_file.exists():
        try:
            with open(commitments_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "commitments" not in data:
                report["errors"].append("commitments.json must be a JSON object with a 'commitments' array.")
                report["valid"] = False
            else:
                report["checks"].append(f"commitments.json structure valid ({len(data['commitments'])} commitments found).")
        except Exception as e:
            report["errors"].append(f"commitments.json invalid JSON: {e}")
            report["valid"] = False
    else:
        report["warnings"].append("commitments.json missing.")

    # 2. Check growth_plan.json
    growth_file = mem_path / "growth_plan.json"
    if growth_file.exists():
        try:
            with open(growth_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "projects" not in data:
                report["errors"].append("growth_plan.json must be a JSON object with a 'projects' array.")
                report["valid"] = False
            else:
                report["checks"].append(f"growth_plan.json structure valid ({len(data['projects'])} projects found).")
        except Exception as e:
            report["errors"].append(f"growth_plan.json invalid JSON: {e}")
            report["valid"] = False
    else:
        report["warnings"].append("growth_plan.json missing.")

    # 3. Check identity.md
    identity_file = mem_path / "identity.md"
    if identity_file.exists():
        try:
            text = identity_file.read_text(encoding="utf-8")
            required_fields = ["Name", "Created", "Purpose"]
            for req in required_fields:
                if req not in text:
                    report["warnings"].append(f"identity.md missing section/field: {req}")
            report["checks"].append("identity.md structure verified.")
        except Exception as e:
            report["errors"].append(f"Error reading identity.md: {e}")
            report["valid"] = False
    else:
        report["warnings"].append("identity.md missing.")

    # 4. Check rules.md and index.md
    for f_name in ["rules.md", "index.md"]:
        f_path = mem_path / f_name
        if f_path.exists():
            report["checks"].append(f"{f_name} present.")
        else:
            report["warnings"].append(f"{f_name} missing.")

    return report

if __name__ == "__main__":
    mem_dir = sys.argv[1] if len(sys.argv) > 1 else "memory"
    res = validate_memory(mem_dir)
    print(json.dumps(res, indent=2))
    if not res["valid"]:
        sys.exit(1)
