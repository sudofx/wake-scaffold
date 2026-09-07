import json
import sys
from pathlib import Path

def main():
    script_path = Path(__file__).resolve()
    tools_dir = script_path.parent
    core_workspace_dir = tools_dir.parent
    memory_dir = core_workspace_dir.parent
    repo_root_dir = memory_dir.parent

    targets = {
        "rules_md": repo_root_dir / "rules.md",
        "blog_html": repo_root_dir / "blog.html",
        "memory_index": memory_dir / "index.md",
        "failure_modes": core_workspace_dir / "failure_modes.md",
        "tools_dir": tools_dir,
    }

    optional_targets = {
        "tool_runs_core": core_workspace_dir / "tool_runs.json",
        "tool_runs_tools": tools_dir / "tool_runs.json",
        "growth_plan": memory_dir / "growth_plan.json",
        "hypotheses": memory_dir / "hypotheses.json",
    }

    missing = []
    found = []

    for name, path in targets.items():
        if path.exists():
            found.append(name)
        else:
            missing.append(f"{name}: {path}")

    opt_found = [name for name, path in optional_targets.items() if path.exists()]
    opt_missing = [name for name, path in optional_targets.items() if not path.exists()]

    all_required = (len(missing) == 0)
    status = "STRUCTURALLY_COMPLETE" if all_required else "STRUCTURALLY_INVALID"

    result = {
        "status": status,
        "missing_required": missing,
        "found_required": found,
        "found_optional": opt_found,
        "missing_optional": opt_missing,
        "summary": f"{len(found)}/{len(targets)} required targets present",
        "repo_root": str(repo_root_dir)
    }

    print(json.dumps(result, indent=2))
    sys.exit(0 if all_required else 1)

if __name__ == "__main__":
    main()
