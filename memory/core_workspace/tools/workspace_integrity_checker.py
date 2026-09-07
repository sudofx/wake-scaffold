import json
from pathlib import Path

def main():
    script_path = Path(__file__).resolve()
    tools_dir = script_path.parents[0]
    core_workspace_dir = script_path.parents[1]
    memory_dir = script_path.parents[2]
    repo_root = script_path.parents[3]

    checks = {
        "rules.md": (repo_root / "rules.md").exists(),
        "blog.html": (repo_root / "blog.html").exists(),
        "memory/index.md": (memory_dir / "index.md").exists(),
        "core_workspace/failure_modes.md": (core_workspace_dir / "failure_modes.md").exists(),
        "memory/identity.md": (memory_dir / "identity.md").exists(),
        "memory/commitments.json": (memory_dir / "commitments.json").exists(),
        "memory/growth_plan.json": (memory_dir / "growth_plan.json").exists(),
        "memory/hypotheses.json": (memory_dir / "hypotheses.json").exists()
    }

    all_exist = all(checks.values())
    status = "STRUCTURALLY_COMPLETE" if all_exist else "STRUCTURALLY_INVALID"

    result = {
        "status": status,
        "script_location": str(script_path),
        "repo_root_resolved": str(repo_root),
        "memory_dir_resolved": str(memory_dir),
        "check_count": len(checks),
        "all_targets_exist": all_exist,
        "details": {k: "EXISTS" if v else "MISSING" for k, v in checks.items()}
    }

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
