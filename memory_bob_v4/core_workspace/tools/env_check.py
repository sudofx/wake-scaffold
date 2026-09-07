import json
from pathlib import Path

def main():
    script_path = Path(__file__).resolve()
    tools_dir = script_path.parent
    core_workspace_dir = tools_dir.parent
    memory_dir = core_workspace_dir.parent
    repo_root = memory_dir.parent

    out = {
        "script_path": str(script_path),
        "tools_dir": str(tools_dir),
        "memory_dir": str(memory_dir),
        "repo_root": str(repo_root),
        "memory_exists": memory_dir.exists(),
        "tools_exists": tools_dir.exists(),
        "memory_files": [p.name for p in memory_dir.iterdir()] if memory_dir.exists() else "Not found",
        "tools_files": [p.name for p in tools_dir.iterdir()] if tools_dir.exists() else "Not found"
    }
    print("Checking environment and workspace...")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
