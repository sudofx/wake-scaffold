import json
from pathlib import Path

def diagnose():
    tool_file = Path(__file__).resolve()
    tool_dir = tool_file.parent
    
    parents = {
        "tool_dir": str(tool_dir),
        "core_workspace": str(tool_dir.parent),
        "memory": str(tool_dir.parent.parent),
        "repo_root": str(tool_dir.parent.parent.parent)
    }
    
    structure = {}
    for key, path_str in parents.items():
        p = Path(path_str)
        if p.exists() and p.is_dir():
            try:
                structure[key] = {
                    "path": str(p),
                    "exists": True,
                    "entries": sorted([e.name for e in p.iterdir() if not e.name.startswith('.')])[:15]
                }
            except Exception as e:
                structure[key] = {"path": str(p), "error": str(e)}
        else:
            structure[key] = {"path": str(path_str), "exists": False}
            
    return structure

if __name__ == '__main__':
    print(json.dumps(diagnose(), indent=2))
