import os
import json
from pathlib import Path

def inspect():
    cwd = Path.cwd()
    results = {
        "cwd": str(cwd),
        "parents": [str(p) for p in cwd.parents],
        "target_search": {}
    }
    
    targets = ["identity.md", "rules.md", "index.md", "blog.html", "tool_runs.json"]
    for target in targets:
        matches = []
        for p in [cwd] + list(cwd.parents):
            cand = p / target
            if cand.exists():
                matches.append(str(cand))
            cand_mem = p / "memory" / target
            if cand_mem.exists():
                matches.append(str(cand_mem))
        results["target_search"][target] = matches
        
    mem_dir = None
    for p in [cwd] + list(cwd.parents):
        if p.name == "memory":
            mem_dir = p
            break
        elif (p / "memory").exists():
            mem_dir = p / "memory"
            break
            
    if mem_dir:
        results["memory_dir"] = str(mem_dir)
        try:
            results["memory_contents"] = [str(f.relative_to(mem_dir)) for f in mem_dir.rglob("*") if f.is_file()]
        except Exception as e:
            results["memory_contents"] = str(e)
    else:
        results["memory_dir"] = None
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    inspect()
