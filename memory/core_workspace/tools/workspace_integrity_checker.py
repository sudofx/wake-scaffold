import json
import sys
from pathlib import Path

def main():
    script = Path(__file__).resolve()
    tools_dir = script.parent
    core_workspace = script.parents[1]
    memory_dir = script.parents[2]
    repo_root = script.parents[3]

    required_targets = {
        "rules.md": repo_root / "rules.md",
        "blog.html": repo_root / "blog.html",
        "memory_index": memory_dir / "index.md",
        "failure_modes": core_workspace / "failure_modes.md",
        "tool_runs": core_workspace / "tool_runs.json",
        "tools_dir": tools_dir,
    }

    discovered_targets = {}
    for filename in ["growth_plan.json", "hypotheses.json", "commitments.json"]:
        found_path = None
        for base in [repo_root, memory_dir, core_workspace]:
            p = base / filename
            if p.exists():
                found_path = p
                break
        discovered_targets[filename] = str(found_path) if found_path else "NOT_FOUND"

    target_status = {}
    missing = []
    for name, path in required_targets.items():
        exists = path.exists()
        target_status[name] = {"path": str(path), "exists": exists}
        if not exists:
            missing.append(name)

    all_exist = (len(missing) == 0)
    status = "STRUCTURALLY_COMPLETE" if all_exist else "STRUCTURALLY_INVALID"

    report = {
        "status": status,
        "script_location": str(script),
        "repo_root_resolved": str(repo_root),
        "memory_dir_resolved": str(memory_dir),
        "required_targets": target_status,
        "missing_required": missing,
        "discovered_targets": discovered_targets,
        "all_required_exist": all_exist
    }

    print(json.dumps(report, indent=2))
    return 0 if all_exist else 1

if __name__ == "__main__":
    sys.exit(main())
