import json
import os
from pathlib import Path

def main():
    script_path = Path(__file__).resolve()
    tools_dir = script_path.parent
    core_workspace_dir = tools_dir.parent
    memory_dir = core_workspace_dir.parent
    repo_root = memory_dir.parent

    target_paths = {
        "repo_root": repo_root,
        "rules_md": repo_root / "rules.md",
        "blog_html": repo_root / "blog.html",
        "memory_dir": memory_dir,
        "index_md": memory_dir / "index.md",
        "core_workspace_dir": core_workspace_dir,
        "failure_modes_md": core_workspace_dir / "failure_modes.md",
        "tools_dir": tools_dir,
    }

    results = {}
    all_exist = True

    for name, path in target_paths.items():
        exists = path.exists()
        is_file = path.is_file() if exists else False
        is_dir = path.is_dir() if exists else False
        size_bytes = path.stat().st_size if exists and is_file else None

        results[name] = {
            "path": str(path),
            "exists": exists,
            "type": "file" if is_file else ("dir" if is_dir else "unknown"),
            "size_bytes": size_bytes
        }
        if not exists:
            all_exist = False

    summary = {
        "status": "STRUCTURALLY_COMPLETE" if all_exist else "STRUCTURALLY_INVALID",
        "script_location": str(script_path),
        "repo_root_resolved": str(repo_root),
        "check_count": len(target_paths),
        "all_targets_exist": all_exist,
        "details": results
    }

    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
